# flask_app.py - RAG增强版
from flask import Flask, render_template, request, jsonify, send_file
import json
import pandas as pd
from pathlib import Path
import os
import tempfile
import random
import re
from collections import defaultdict
import hashlib
import threading
import queue
import time
from typing import List, Dict, Tuple, Optional

app = Flask(__name__)

# ========== 配置路径 ==========
BASE_DIR = Path(__file__).parent.absolute()
CORPUS_PATH = BASE_DIR / "data" / "raw" / "medical_corpus.json"
QUESTIONS_PATH = BASE_DIR / "data" / "raw" / "medical_questions.json"

# ========== RAG配置 ==========
RAG_CONFIG = {
    'chunk_size': 500,  # 每个chunk的字符数
    'chunk_overlap': 50,  # chunk之间的重叠字符数
    'top_k_retrieval': 3,  # 检索返回的chunk数量
    'embedding_model': 'all-MiniLM-L6-v2',  # 轻量级嵌入模型
    'use_semantic_search': True,  # 是否使用语义搜索
    'hybrid_search': True,  # 是否使用混合搜索
}

# ========== 向量存储和嵌入模型 ==========
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    try:
        import faiss
        HAS_FAISS = True
    except ImportError:
        import subprocess, sys
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'faiss-cpu'])
        import faiss
        HAS_FAISS = True
    
    # 初始化嵌入模型
    print("🔄 正在加载嵌入模型...")
    embedding_model = SentenceTransformer(RAG_CONFIG['embedding_model'])
    print("✅ 嵌入模型加载完成")
    
    # 向量存储
    vector_store = {
        'corpus_chunks': [],
        'corpus_embeddings': None,
        'corpus_faiss_index': None,
        'question_embeddings': None,
        'questions': [],
        'question_faiss_index': None
    }
    
    HAS_EMBEDDING = True
except ImportError as e:
    print(f"⚠️  未安装sentence-transformers: {e}")
    print("  使用 pip install sentence-transformers 安装")
    HAS_EMBEDDING = False
    embedding_model = None
    vector_store = None

# ========== 翻译队列系统（避免卡顿） ==========
class TranslationQueue:
    def __init__(self):
        self.queue = queue.Queue()
        self.results = {}
        self.worker_thread = None
        self.start_worker()
    
    def start_worker(self):
        """启动翻译工作线程"""
        self.worker_thread = threading.Thread(target=self._translation_worker, daemon=True)
        self.worker_thread.start()
        print("✅ 翻译队列工作线程已启动")
    
    def _translation_worker(self):
        """翻译工作线程"""
        from translate import Translator
        
        # 创建translator实例
        translator_en_to_zh = Translator(to_lang="zh", from_lang="en")
        translator_zh_to_en = Translator(to_lang="en", from_lang="zh")
        
        while True:
            try:
                task = self.queue.get()
                if task is None:  # 停止信号
                    break
                    
                task_id, text, direction = task
                
                try:
                    if direction == 'en_to_zh':
                        result = translator_en_to_zh.translate(text)
                    else:  # zh_to_en
                        result = translator_zh_to_en.translate(text)
                    
                    self.results[task_id] = result
                except Exception as e:
                    print(f"翻译失败 ({direction}): {e}")
                    self.results[task_id] = text  # 失败时返回原文本
                    
                self.queue.task_done()
                
            except Exception as e:
                print(f"翻译工作线程错误: {e}")
    
    def translate(self, text, direction='en_to_zh', timeout=10):
        """提交翻译任务（异步）"""
        if not text or not any('a' <= char.lower() <= 'z' for char in text) if direction == 'en_to_zh' else not any('\u4e00' <= char <= '\u9fff' for char in text):
            return text
        
        task_id = hashlib.md5(f"{text}_{direction}".encode()).hexdigest()
        
        # 如果已经有结果，直接返回
        if task_id in self.results:
            return self.results[task_id]
        
        # 提交任务到队列
        self.queue.put((task_id, text, direction))
        
        # 等待结果（带超时）
        start_time = time.time()
        while task_id not in self.results:
            if time.time() - start_time > timeout:
                print(f"翻译超时: {text[:50]}...")
                return text  # 超时返回原文本
            time.sleep(0.1)
        
        return self.results.get(task_id, text)

# 初始化翻译队列
try:
    from translate import Translator
    translation_queue = TranslationQueue()
    HAS_TRANSLATE = True
    print("✅ translate库已成功初始化（使用队列系统）")
except ImportError as e:
    HAS_TRANSLATE = False
    print(f"⚠️  translate库未安装: {e}")
    translation_queue = None

# ========== 文档处理函数 ==========
def split_text_into_chunks(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
    """将文本分割成chunks"""
    if not text:
        return []
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        
        # 如果不在文本末尾，尝试在句子边界处分割
        if end < text_length:
            # 找最近的句子结束符
            sentence_endings = ['.', '!', '?', '。', '！', '？', '\n\n']
            for sep in sentence_endings:
                sep_pos = text.rfind(sep, start, end)
                if sep_pos != -1 and sep_pos > start + chunk_size // 2:
                    end = sep_pos + 1
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # 移动开始位置，考虑重叠
        start = end - chunk_overlap
    
    return chunks

def create_corpus_chunks(corpus_data: Dict) -> List[Dict]:
    """创建语料库chunks"""
    if not corpus_data or 'full_content' not in corpus_data:
        return []
    
    full_content = corpus_data['full_content']
    raw_chunks = split_text_into_chunks(
        full_content, 
        RAG_CONFIG['chunk_size'], 
        RAG_CONFIG['chunk_overlap']
    )
    
    chunks = []
    for i, chunk_text in enumerate(raw_chunks):
        chunks.append({
            'id': f'chunk_{i:04d}',
            'text': chunk_text,
            'char_count': len(chunk_text),
            'word_count': len(chunk_text.split()),
            'chunk_index': i,
            'source': 'corpus'
        })
    
    print(f"📄 已将语料库分割成 {len(chunks)} 个chunks")
    return chunks

# ========== 向量化函数 ==========
def compute_embeddings(texts: List[str]) -> np.ndarray:
    """计算文本的嵌入向量"""
    if not HAS_EMBEDDING or not embedding_model:
        return None
    
    try:
        # 批量计算嵌入
        embeddings = embedding_model.encode(texts, show_progress_bar=False)
        return embeddings
    except Exception as e:
        print(f"计算嵌入失败: {e}")
        return None

def build_vector_store(corpus_data: Dict, questions_data: Dict):
    """构建向量存储（含faiss索引）"""
    if not HAS_EMBEDDING:
        return
    print("🔄 正在构建向量存储...")
    # 处理语料库
    if corpus_data:
        corpus_chunks = create_corpus_chunks(corpus_data)
        if corpus_chunks:
            chunk_texts = [chunk['text'] for chunk in corpus_chunks]
            corpus_embeddings = compute_embeddings(chunk_texts)
            vector_store['corpus_chunks'] = corpus_chunks
            vector_store['corpus_embeddings'] = corpus_embeddings
            # 构建faiss索引
            if HAS_FAISS and corpus_embeddings is not None:
                dim = corpus_embeddings.shape[1]
                index = faiss.IndexFlatL2(dim)
                index.add(np.array(corpus_embeddings, dtype=np.float32))
                vector_store['corpus_faiss_index'] = index
            print(f"   ✓ 语料库向量: {len(corpus_chunks)} chunks")
    # 处理问题
    if questions_data and 'all_questions' in questions_data:
        questions = []
        for q in questions_data['all_questions']:
            question_text = q.get('raw_question', '')
            answer_text = q.get('raw_answer', '')
            combined_text = f"问题: {question_text}\n答案: {answer_text}"
            questions.append(combined_text)
        if questions:
            question_embeddings = compute_embeddings(questions)
            vector_store['questions'] = questions_data['all_questions']
            vector_store['question_embeddings'] = question_embeddings
            # 构建faiss索引
            if HAS_FAISS and question_embeddings is not None:
                dim = question_embeddings.shape[1]
                index = faiss.IndexFlatL2(dim)
                index.add(np.array(question_embeddings, dtype=np.float32))
                vector_store['question_faiss_index'] = index
            print(f"   ✓ 问题向量: {len(questions)} 个问题")
    print("✅ 向量存储构建完成")

# ========== 检索函数 ==========
def semantic_search(query: str, embeddings: np.ndarray, texts: List[Dict], top_k: int = 3) -> List[Dict]:
    """语义搜索（faiss加速）"""
    if not HAS_EMBEDDING or embeddings is None:
        return []
    try:
        query_embedding = embedding_model.encode([query])[0]
        if HAS_FAISS and vector_store.get('corpus_faiss_index') is not None:
            D, I = vector_store['corpus_faiss_index'].search(np.array([query_embedding], dtype=np.float32), top_k)
            results = []
            for idx, dist in zip(I[0], D[0]):
                if idx < len(texts):
                    results.append({
                        'text': texts[idx]['text'] if isinstance(texts[idx], dict) else texts[idx],
                        'metadata': texts[idx] if isinstance(texts[idx], dict) else {},
                        'similarity': float(-dist),
                        'source': 'semantic_search'
                    })
            return results
        else:
            # fallback: numpy
            similarities = np.dot(embeddings, query_embedding) / (
                np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding)
            )
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            results = []
            for idx in top_indices:
                if idx < len(texts):
                    results.append({
                        'text': texts[idx]['text'] if isinstance(texts[idx], dict) else texts[idx],
                        'metadata': texts[idx] if isinstance(texts[idx], dict) else {},
                        'similarity': float(similarities[idx]),
                        'source': 'semantic_search'
                    })
            return results
    except Exception as e:
        print(f"语义搜索失败: {e}")
        return []

def keyword_search(query: str, texts: List[Dict], top_k: int = 3) -> List[Dict]:
    """关键词搜索"""
    query_terms = query.lower().split()
    scored_texts = []
    
    for i, text_item in enumerate(texts):
        if isinstance(text_item, dict):
            text = text_item.get('text', '')
            metadata = text_item
        else:
            text = text_item
            metadata = {'text': text}
        
        text_lower = text.lower()
        score = 0
        
        # 计算匹配分数
        for term in query_terms:
            if term in text_lower:
                score += 1
            # 部分匹配
            if len(term) > 3 and any(term in word for word in text_lower.split()):
                score += 0.5
        
        if score > 0:
            scored_texts.append({
                'text': text,
                'metadata': metadata,
                'score': score,
                'source': 'keyword_search'
            })
    
    # 按分数排序
    scored_texts.sort(key=lambda x: x['score'], reverse=True)
    return scored_texts[:top_k]

def hybrid_retrieval(query: str, corpus_data: Dict, questions_data: Dict, top_k: int = 3) -> List[Dict]:
    """混合检索：结合语义搜索和关键词搜索"""
    all_results = []
    
    # 1. 从语料库检索
    if vector_store and vector_store['corpus_embeddings'] is not None:
        semantic_results = semantic_search(
            query, 
            vector_store['corpus_embeddings'],
            vector_store['corpus_chunks'],
            top_k=top_k
        )
        all_results.extend(semantic_results)
    
    # 2. 关键词搜索语料库
    if corpus_data and 'paragraphs' in corpus_data:
        paragraphs = [{'text': p, 'metadata': {}} for p in corpus_data['paragraphs']]
        keyword_results = keyword_search(query, paragraphs, top_k=top_k)
        all_results.extend(keyword_results)
    
    # 3. 从问题库检索
    if RAG_CONFIG['hybrid_search'] and questions_data and 'all_questions' in questions_data:
        # 使用传统搜索函数
        search_results = search_in_questions(query, questions_data, answer_language='zh', top_k=top_k)
        for result in search_results:
            all_results.append({
                'text': f"{result.get('display_question', '')}\n{result.get('display_answer', '')}",
                'metadata': result,
                'similarity': result.get('confidence', 0.5),
                'source': 'question_search'
            })
    
    # 去重和排序
    unique_results = []
    seen_texts = set()
    
    for result in all_results:
        text_hash = hashlib.md5(result['text'].encode()).hexdigest()
        if text_hash not in seen_texts:
            seen_texts.add(text_hash)
            
            # 归一化分数
            if 'similarity' in result:
                score = result['similarity']
            elif 'score' in result:
                score = result['score'] / 10  # 归一化到0-1范围
            else:
                score = 0.5
            
            result['confidence'] = min(score, 0.95)
            unique_results.append(result)
    
    # 按置信度排序
    unique_results.sort(key=lambda x: x.get('confidence', 0), reverse=True)
    return unique_results[:top_k]

# ========== 答案生成函数 ==========
def generate_answer_from_context(query: str, retrieved_contexts: List[Dict], answer_language: str = 'zh') -> Dict:
    """基于检索到的上下文生成答案"""
    if not retrieved_contexts:
        return {
            'answer': '抱歉，我没有找到足够的信息来回答这个问题。',
            'sources': [],
            'confidence': 0.0
        }
    
    # 合并上下文
    context_texts = []
    sources = []
    
    for i, ctx in enumerate(retrieved_contexts):
        context_text = ctx.get('text', '')
        source_info = ctx.get('metadata', {})
        confidence = ctx.get('confidence', 0.5)
        
        context_texts.append(f"[来源{i+1}, 置信度:{confidence:.2f}] {context_text}")
        sources.append({
            'text': context_text[:200] + "..." if len(context_text) > 200 else context_text,
            'confidence': confidence,
            'source_type': ctx.get('source', 'unknown')
        })
    
    combined_context = "\n\n".join(context_texts)
    
    # 基于上下文的简单答案生成
    query_lower = query.lower()
    context_lower = combined_context.lower()
    
    # 尝试提取直接答案
    answer = ""
    
    # 如果是定义类问题
    if any(word in query_lower for word in ['是什么', '什么是', '定义', 'definition', 'what is']):
        # 提取第一个包含查询关键词的句子
        sentences = re.split(r'[。.！!？?\n]', combined_context)
        for sentence in sentences:
            if any(term in sentence.lower() for term in query_lower.split()):
                answer = sentence.strip()
                break
    
    # 如果是症状或治疗类问题
    elif any(word in query_lower for word in ['症状', '表现', 'symptom', 'treatment', '治疗', '疗法']):
        # 提取包含相关信息的段落
        paragraphs = combined_context.split('\n\n')
        relevant_paras = []
        for para in paragraphs:
            para_lower = para.lower()
            if ('症状' in para_lower or 'symptom' in para_lower) and '治疗' in query_lower:
                relevant_paras.append(para)
            elif ('治疗' in para_lower or 'treatment' in para_lower) and '治疗' in query_lower:
                relevant_paras.append(para)
        
        if relevant_paras:
            answer = "\n".join(relevant_paras[:2])
    
    # 如果没有提取到特定答案，使用最相关的上下文
    if not answer:
        answer = retrieved_contexts[0].get('text', '')
        # 截取合理长度
        if len(answer) > 500:
            sentences = re.split(r'[。.！!？?]', answer)
            answer = ""
            for sentence in sentences:
                if len(answer + sentence) < 500:
                    answer += sentence + "。"
                else:
                    break
    
    # 清理答案格式
    answer = re.sub(r'\s+', ' ', answer).strip()
    
    # 添加提示信息
    if len(answer) > 0:
        answer += "\n\n（以上信息基于医疗知识库，仅供参考。具体病情请咨询专业医生。）"
    
    # 翻译答案（如果需要）
    if answer_language == 'en':
        answer = translate_to_english_fast(answer)
    elif answer_language == 'zh':
        answer = translate_to_chinese_fast(answer)
    
    # 计算平均置信度
    avg_confidence = sum(s['confidence'] for s in sources) / len(sources) if sources else 0.5
    
    return {
        'answer': answer,
        'sources': sources,
        'confidence': avg_confidence
    }

# ========== RAG问答函数 ==========
def rag_query(query: str, corpus_data: Dict, questions_data: Dict, answer_language: str = 'zh') -> Dict:
    """RAG问答主函数"""
    start_time = time.time()
    
    # 1. 检索相关上下文
    retrieved_contexts = hybrid_retrieval(
        query, 
        corpus_data, 
        questions_data, 
        top_k=RAG_CONFIG['top_k_retrieval']
    )
    
    retrieval_time = time.time() - start_time
    
    # 2. 生成答案
    generation_start = time.time()
    result = generate_answer_from_context(query, retrieved_contexts, answer_language)
    generation_time = time.time() - generation_start
    
    # 3. 准备返回结果
    total_time = time.time() - start_time
    
    # 准备源文档信息
    source_documents = []
    for i, ctx in enumerate(retrieved_contexts[:3]):
        source_text = ctx.get('text', '')
        if len(source_text) > 150:
            source_text = source_text[:150] + "..."
        
        source_documents.append({
            'id': i + 1,
            'content': source_text,
            'confidence': ctx.get('confidence', 0.5),
            'source_type': ctx.get('source', 'unknown')
        })
    
    return {
        'answer': result['answer'],
        'confidence': result['confidence'],
        'source_documents': source_documents,
        'retrieved_count': len(retrieved_contexts),
        'timing': {
            'retrieval': f"{retrieval_time:.2f}s",
            'generation': f"{generation_time:.2f}s",
            'total': f"{total_time:.2f}s"
        },
        'used_rag': True
    }

# ========== 优化翻译函数 ==========
def translate_to_chinese_fast(text):
    """快速翻译成中文（使用缓存和队列）"""
    if not text or not isinstance(text, str):
        return text or ""
    
    # 检查是否需要翻译
    if not any('a' <= char.lower() <= 'z' for char in text):
        return text
    
    # 使用翻译队列
    if translation_queue:
        return translation_queue.translate(text, direction='en_to_zh', timeout=5)
    
    # 降级到简易翻译
    return simple_translate_to_chinese(text)

def translate_to_english_fast(text):
    """快速翻译成英文（使用缓存和队列）"""
    if not text or not isinstance(text, str):
        return text or ""
    
    # 检查是否需要翻译
    if not any('\u4e00' <= char <= '\u9fff' for char in text):
        return text
    
    # 使用翻译队列
    if translation_queue:
        return translation_queue.translate(text, direction='zh_to_en', timeout=5)
    
    # 降级到简易翻译
    return simple_translate_to_english(text)

def simple_translate_to_chinese(text):
    """简易翻译：英文到中文（备份方案）"""
    if not text:
        return text
    
    # 关键医学术语翻译
    medical_terms = {
        'skin cancer': '皮肤癌',
        'cancer': '癌症',
        'diabetes': '糖尿病',
        'high blood pressure': '高血压',
        'pneumonia': '肺炎',
        'heart disease': '心脏病',
        'common cold': '普通感冒',
        'basal cell carcinoma': '基底细胞癌',
        'squamous cell carcinoma': '鳞状细胞癌',
        'nonmelanoma': '非黑色素瘤',
        'melanoma': '黑色素瘤',
        'CSCC': '皮肤鳞状细胞癌',
        'BCC': '基底细胞癌',
    }
    
    result = text
    for en, zh in medical_terms.items():
        if en.lower() in result.lower():
            result = re.sub(r'\b' + re.escape(en) + r'\b', zh, result, flags=re.IGNORECASE)
    
    return result

def simple_translate_to_english(text):
    """简易翻译：中文到英文（备份方案）"""
    if not text:
        return text
    
    medical_terms = {
        '皮肤癌': 'skin cancer',
        '癌症': 'cancer',
        '糖尿病': 'diabetes',
        '高血压': 'high blood pressure',
        '肺炎': 'pneumonia',
        '心脏病': 'heart disease',
        '感冒': 'common cold',
        '基底细胞癌': 'basal cell carcinoma',
        '鳞状细胞癌': 'squamous cell carcinoma',
        '非黑色素瘤': 'nonmelanoma',
        '黑色素瘤': 'melanoma',
    }
    
    result = text
    for zh, en in medical_terms.items():
        if zh in result:
            result = result.replace(zh, en)
    
    return result

def ensure_pure_chinese(text):
    """确保文本是纯中文"""
    if not text:
        return text
    
    if any('a' <= char.lower() <= 'z' for char in text):
        return translate_to_chinese_fast(text)
    
    return text

def ensure_pure_english(text):
    """确保文本是纯英文"""
    if not text:
        return text
    
    if any('\u4e00' <= char <= '\u9fff' for char in text):
        return translate_to_english_fast(text)
    
    return text

def load_corpus_data():
    """加载语料库数据"""
    try:
        if CORPUS_PATH.exists():
            with open(CORPUS_PATH, 'r', encoding='utf-8') as f:
                corpus = json.load(f)
            
            if isinstance(corpus, dict) and 'context' in corpus:
                context = corpus.get('context', '')
                paragraphs = [p.strip() for p in context.split('\n\n') if p.strip()]
                
                return {
                    'corpus_name': corpus.get('corpus_name', '医疗知识库'),
                    'doc_count': 1,
                    'paragraphs': paragraphs,
                    'full_content': context
                }
        else:
            print(f"语料库文件不存在: {CORPUS_PATH}")
        return None
    except Exception as e:
        print(f"加载语料库失败: {e}")
        return None

def load_questions_data():
    """加载问题集数据（不进行翻译，延迟翻译）"""
    try:
        if QUESTIONS_PATH.exists():
            with open(QUESTIONS_PATH, 'r', encoding='utf-8') as f:
                questions = json.load(f)
            
            if isinstance(questions, list):
                question_types = defaultdict(int)
                all_questions = []
                
                for q in questions:
                    if isinstance(q, dict) and 'question' in q and 'answer' in q:
                        q_type = q.get('question_type', '其他')
                        question_types[q_type] += 1
                        
                        question_text = q.get('question', '')
                        answer_text = q.get('answer', '')
                        
                        # 判断原始语言，但不立即翻译
                        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in question_text)
                        
                        if has_chinese:
                            # 原始是中文，保存原文本
                            question_cn = question_text
                            answer_cn = answer_text
                            # 英文版本先设为空，需要时再翻译
                            question_en = ""
                            answer_en = ""
                        else:
                            # 原始是英文，保存原文本
                            question_en = question_text
                            answer_en = answer_text
                            # 中文版本先设为空，需要时再翻译
                            question_cn = ""
                            answer_cn = ""
                        
                        all_questions.append({
                            'question_cn': question_cn,
                            'question_en': question_en,
                            'answer_cn': answer_cn,
                            'answer_en': answer_en,
                            'type': q_type,
                            'source': q.get('source', 'Medical'),
                            'original_lang': 'zh' if has_chinese else 'en',
                            'raw_question': question_text,  # 保存原始问题
                            'raw_answer': answer_text,      # 保存原始答案
                        })
                
                sample_questions = all_questions[:50] if len(all_questions) > 50 else all_questions
                
                return {
                    'total_count': len(all_questions),
                    'sample_questions': sample_questions,
                    'question_types': dict(question_types),
                    'all_questions': all_questions
                }
        else:
            print(f"问题集文件不存在: {QUESTIONS_PATH}")
        return None
    except Exception as e:
        print(f"加载问题集失败: {e}")
        return None

def get_data_counts():
    """获取数据统计"""
    global GLOBAL_CORPUS_DATA, GLOBAL_QUESTIONS_DATA
    corpus_data = GLOBAL_CORPUS_DATA
    questions_data = GLOBAL_QUESTIONS_DATA
    doc_count = corpus_data['doc_count'] if corpus_data else 1
    question_count = questions_data['total_count'] if questions_data else 0
    return doc_count, question_count, corpus_data, questions_data

# ========== 智能搜索函数（延迟翻译） ==========
# 全局变量用于缓存数据和向量存储
GLOBAL_CORPUS_DATA = None
GLOBAL_QUESTIONS_DATA = None
GLOBAL_VECTOR_STORE_READY = False

def initialize_data_and_vectors():
    """启动时加载数据和构建向量存储，只运行一次"""
    global GLOBAL_CORPUS_DATA, GLOBAL_QUESTIONS_DATA, GLOBAL_VECTOR_STORE_READY
    GLOBAL_CORPUS_DATA = load_corpus_data()
    GLOBAL_QUESTIONS_DATA = load_questions_data()
    if HAS_EMBEDDING and GLOBAL_CORPUS_DATA and GLOBAL_QUESTIONS_DATA:
        build_vector_store(GLOBAL_CORPUS_DATA, GLOBAL_QUESTIONS_DATA)
        GLOBAL_VECTOR_STORE_READY = True
    else:
        GLOBAL_VECTOR_STORE_READY = False

# 可选：暴露一个刷新接口（如有需要可手动刷新数据和向量）
def refresh_data_and_vectors():
    initialize_data_and_vectors()
def search_in_questions(query, questions_data, answer_language='zh', top_k=5):
    """智能搜索算法（延迟翻译）"""
    if not questions_data or 'all_questions' not in questions_data:
        return []
    
    query = query.strip()
    if not query:
        return []
    
    # 判断查询语言
    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in query)
    query_lang = 'zh' if has_chinese else 'en'
    
    results = []
    
    for q in questions_data['all_questions']:
        score = 0
        
        # 获取原始文本
        raw_question = q.get('raw_question', '')
        raw_answer = q.get('raw_answer', '')
        original_lang = q.get('original_lang', 'en')
        
        # 根据查询语言进行匹配（使用原始文本）
        if query_lang == 'zh':
            # 中文查询
            query_lower = query.lower()
            if original_lang == 'zh':
                # 原始是中文，直接匹配
                if query_lower in raw_question.lower():
                    score += 10
                elif any(word in raw_question.lower() for word in query_lower.split()):
                    score += 5
            else:
                # 原始是英文，翻译后匹配
                translated_question = simple_translate_to_chinese(raw_question)
                if query_lower in translated_question.lower():
                    score += 8
        else:
            # 英文查询
            query_lower = query.lower()
            if original_lang == 'en':
                # 原始是英文，直接匹配
                if query_lower in raw_question.lower():
                    score += 10
                elif any(word in raw_question.lower() for word in query_lower.split()):
                    score += 5
            else:
                # 原始是中文，翻译后匹配
                translated_question = simple_translate_to_english(raw_question)
                if query_lower in translated_question.lower():
                    score += 8
        
        if score > 0:
            # 根据用户选择的回答语言选择显示内容（延迟翻译）
            if answer_language == 'en':
                # 英文回答
                if original_lang == 'en':
                    display_question = ensure_pure_english(raw_question)
                    display_answer = ensure_pure_english(raw_answer)
                else:
                    display_question = translate_to_english_fast(raw_question)
                    display_answer = translate_to_english_fast(raw_answer)
            else:
                # 中文回答
                if original_lang == 'zh':
                    display_question = ensure_pure_chinese(raw_question)
                    display_answer = ensure_pure_chinese(raw_answer)
                else:
                    display_question = translate_to_chinese_fast(raw_question)
                    display_answer = translate_to_chinese_fast(raw_answer)
            
            confidence = min(score / 10, 0.95)
            
            # 翻译类型和来源
            q_type = q.get('type', 'Medical')
            source = q.get('source', 'Medical Database')
            
            if answer_language == 'zh':
                if q_type == 'Fact Retrieval':
                    q_type = '事实检索'
                elif q_type == 'Medical':
                    q_type = '医疗信息'
                if source == 'Medical Database':
                    source = '医疗数据库'
            
            results.append({
                'display_question': display_question,
                'display_answer': display_answer,
                'type': q_type,
                'source': source,
                'confidence': confidence,
                'original_lang': original_lang
            })
    
    # 排序并返回
    results.sort(key=lambda x: x['confidence'], reverse=True)
    
    # 去重
    unique_results = []
    seen_questions = set()
    
    for result in results:
        question_key = hashlib.md5(result['display_question'].encode()).hexdigest()
        if question_key not in seen_questions:
            seen_questions.add(question_key)
            unique_results.append(result)
        
        if len(unique_results) >= top_k:
            break
    
    return unique_results

    # ...existing code...
@app.route('/')
def index():
    """主页"""
    doc_count, question_count, corpus_data, questions_data = get_data_counts()
    sample_questions = []
    if questions_data and 'sample_questions' in questions_data:
        all_samples = questions_data['sample_questions'][:20]
        if len(all_samples) >= 3:
            sample_questions = random.sample(all_samples, 3)
        else:
            sample_questions = all_samples
    display_questions = []
    for i, sq in enumerate(sample_questions):
        question_text = sq.get('raw_question', '')
        if sq.get('original_lang') == 'en':
            display_text = simple_translate_to_chinese(question_text)
        else:
            display_text = question_text
        if len(display_text) > 40:
            display_text = display_text[:40] + "..."
        display_questions.append({
            'text': display_text,
            'full_question': question_text,
            'index': i,
            'lang': sq.get('original_lang', 'en')
        })
    return render_template('index.html',
                         doc_count=doc_count,
                         question_count=question_count,
                         sample_questions=display_questions,
                         has_rag=HAS_EMBEDDING)

@app.route('/api/query', methods=['POST'])
def handle_query():
    """处理查询请求"""
    try:
        data = request.json
        question = data.get('question', '').strip()
        answer_language = data.get('answer_language', 'zh')
        use_rag = data.get('use_rag', True)  # 是否使用RAG
        
        if not question:
            return jsonify({'success': False, 'error': '请输入问题'})
        
        _, _, corpus_data, questions_data = get_data_counts()
        
        if not corpus_data or not questions_data:
            return jsonify({
                'success': False,
                'error': '无法加载数据，请检查数据文件'
            })
        
        # 根据是否使用RAG选择不同的处理方式
        if use_rag and HAS_EMBEDDING:
            # 使用RAG
            rag_result = rag_query(question, corpus_data, questions_data, answer_language)
            
            # 生成HTML响应
            answer_html = generate_rag_answer_html(question, rag_result, answer_language)
            
            return jsonify({
                'success': True,
                'question': question,
                'answer': answer_html,
                'confidence': rag_result['confidence'],
                'result_count': rag_result['retrieved_count'],
                'query_language': 'zh' if any('\u4e00' <= char <= '\u9fff' for char in question) else 'en',
                'answer_language': answer_language,
                'used_rag': True,
                'timing': rag_result['timing']
            })
        else:
            # 使用传统搜索
            search_results = search_in_questions(
                question, 
                questions_data, 
                answer_language=answer_language,
                top_k=5
            )
            
            answer_html = generate_answer_html(question, search_results, answer_language)
            
            result_count = len(search_results)
            if search_results:
                avg_confidence = sum(r.get('confidence', 0.5) for r in search_results) / result_count
            else:
                avg_confidence = 0
            
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in question)
            query_language = 'zh' if has_chinese else 'en'
            
            return jsonify({
                'success': True,
                'question': question,
                'answer': answer_html,
                'confidence': avg_confidence,
                'result_count': result_count,
                'query_language': query_language,
                'answer_language': answer_language,
                'used_rag': False
            })
    
    except Exception as e:
        print(f"查询处理错误: {e}")
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        })

def generate_answer_html(question, search_results, answer_language='zh'):
    """生成传统搜索的回答HTML"""
    if not search_results:
        return f'''
        <div class="no-results">
            <h4>🤔 未找到相关信息</h4>
            <p>暂时没有找到与"<strong>{question}</strong>"直接相关的医疗信息。</p>
            <div class="suggestions">
                <p>建议：</p>
                <ul>
                    <li>尝试使用更具体的医疗术语（如"糖尿病症状"、"高血压治疗"）</li>
                    <li>检查问题是否包含拼写错误</li>
                    <li>尝试询问常见疾病（如感冒、头痛、糖尿病等）</li>
                    <li>您也可以用英文提问</li>
                </ul>
            </div>
        </div>
        '''
    
    html_parts = []
    
    html_parts.append('<div class="answer-container">')
    html_parts.append('<h4>🔍 查询结果（传统搜索）</h4>')
    html_parts.append(f'<p class="query-display">问题：<strong>{question}</strong></p>')
    
    for i, result in enumerate(search_results, 1):
        display_question = result.get('display_question', '')
        display_answer = result.get('display_answer', '')
        source = result.get('source', '医疗数据库')
        q_type = result.get('type', '医疗信息')
        confidence = result.get('confidence', 0.7) * 100
        
        html_parts.append(f'''
        <div class="search-result">
            <div class="result-header">
                <span class="result-number">#{i}</span>
                <span class="result-type">{q_type}</span>
                <span class="result-confidence">置信度: {confidence:.0f}%</span>
            </div>
            <div class="result-content">
                <p><strong>相关信息:</strong> {display_question}</p>
                <div class="answer-box">
                    <strong>答案:</strong> {display_answer}
                </div>
                <p style="margin-top: 10px;"><strong>来源:</strong> <span class="source-badge">{source}</span></p>
            </div>
        </div>
        ''')
    
    advice = '''
    <div class="medical-advice">
        <h5>💡 医疗建议</h5>
        <ul>
            <li>以上信息基于医疗数据库，仅供参考</li>
            <li>具体症状请咨询专业医生</li>
            <li>如遇紧急情况，请立即就医</li>
            <li>保持健康生活方式有助于疾病预防</li>
        </ul>
    </div>
    '''
    
    html_parts.append(advice)
    html_parts.append('</div>')
    return '\n'.join(html_parts)

def generate_rag_answer_html(question, rag_result, answer_language='zh'):
    """生成RAG回答的HTML"""
    answer = rag_result.get('answer', '')
    confidence = rag_result.get('confidence', 0.5) * 100
    source_documents = rag_result.get('source_documents', [])
    timing = rag_result.get('timing', {})
    
    html_parts = []
    
    html_parts.append('<div class="answer-container rag-answer">')
    html_parts.append('<h4>🧠 智能分析结果（RAG系统）</h4>')
    html_parts.append(f'<p class="query-display">问题：<strong>{question}</strong></p>')
    
    # 显示RAG系统信息
    html_parts.append(f'''
    <div class="rag-info">
        <div class="rag-metrics">
            <span class="rag-metric"><strong>置信度:</strong> {confidence:.0f}%</span>
            <span class="rag-metric"><strong>检索文档:</strong> {len(source_documents)} 个</span>
            <span class="rag-metric"><strong>检索时间:</strong> {timing.get('retrieval', 'N/A')}</span>
            <span class="rag-metric"><stron.g>生成时间:</strong> {timing.get('generation', 'N/A')}</span>
        </div>
    </div>
    ''')
    
    # 显示生成的答案
    answer_html = answer.replace('\n', '<br>')
    html_parts.append(f'''
    <div class="generated-answer">
        <h5>💬 生成答案：</h5>
        <div class="answer-content">
            {answer_html}
        </div>
    </div>
    ''')
    
    # 显示源文档
    if source_documents:
        html_parts.append('''
        <div class="source-documents">
            <h5>📚 参考来源：</h5>
        ''')
        
        for i, source in enumerate(source_documents, 1):
            source_type_badge = {
                'semantic_search': '🔍 语义匹配',
                'keyword_search': '🔑 关键词匹配',
                'question_search': '❓ 问题库匹配'
            }.get(source.get('source_type', 'unknown'), '📄 文档')
            
            html_parts.append(f'''
            <div class="source-document">
                <div class="source-header">
                    <span class="source-number">#{i}</span>
                    <span class="source-type">{source_type_badge}</span>
                    <span class="source-confidence">相关度: {source.get('confidence', 0.5)*100:.0f}%</span>
                </div>
                <div class="source-content">
                    {source.get('content', '')}
                </div>
            </div>
            ''')
        
        html_parts.append('</div>')
    
    # 医疗建议
    html_parts.append('''
    <div class="medical-advice">
        <h5>💡 医疗建议</h5>
        <ul>
            <li>以上信息基于医疗知识库的智能分析，仅供参考</li>
            <li>具体症状请咨询专业医生</li>
            <li>如遇紧急情况，请立即就医</li>
            <li>保持健康生活方式有助于疾病预防</li>
        </ul>
    </div>
    ''')
    
    html_parts.append('</div>')
    return '\n'.join(html_parts)

@app.route('/api/export-data')
def export_data():
    """导出数据为Excel"""
    try:
        corpus_data = load_corpus_data()
        questions_data = load_questions_data()
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            with pd.ExcelWriter(tmp.name, engine='openpyxl') as writer:
                if corpus_data and 'paragraphs' in corpus_data:
                    corpus_df = pd.DataFrame({
                        'Paragraph ID': [f'P{i+1:03d}' for i in range(len(corpus_data['paragraphs']))],
                        'Content': corpus_data['paragraphs'][:100],
                        'Character Count': [len(p) for p in corpus_data['paragraphs'][:100]]
                    })
                    corpus_df.to_excel(writer, sheet_name='Corpus Content', index=False)
                
                if questions_data and 'sample_questions' in questions_data:
                    questions_list = []
                    for i, q in enumerate(questions_data['sample_questions'][:200]):
                        questions_list.append({
                            'No.': i+1,
                            'Question (CN)': q.get('question_cn', ''),
                            'Question (EN)': q.get('question_en', ''),
                            'Answer (CN)': q.get('answer_cn', '')[:200] if q.get('answer_cn') else '',
                            'Answer (EN)': q.get('answer_en', '')[:200] if q.get('answer_en') else '',
                            'Type': q.get('type', 'Unknown'),
                            'Source': q.get('source', 'Unknown')
                        })
                    
                    questions_df = pd.DataFrame(questions_list)
                    questions_df.to_excel(writer, sheet_name='Question Samples', index=False)
                
                stats_data = [
                    {'Item': 'Corpus', 'Value': corpus_data['doc_count'] if corpus_data else 1, 'Description': 'Number of documents'},
                    {'Item': 'Question Set', 'Value': questions_data['total_count'] if questions_data else 0, 'Description': 'Total questions'},
                ]
                
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_excel(writer, sheet_name='Statistics', index=False)
            
            tmp_path = tmp.name
        
        return send_file(
            tmp_path,
            as_attachment=True,
            download_name='Medical_RAG_System_Data.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/data-stats')
def data_stats():
    """获取数据统计API"""
    doc_count, question_count, corpus_data, questions_data = get_data_counts()
    
    stats = {
        'corpus': {
            'document_count': doc_count,
            'corpus_name': corpus_data.get('corpus_name', '医疗知识库') if corpus_data else 'Unknown',
            'has_data': corpus_data is not None
        },
        'questions': {
            'total_count': question_count,
            'type_count': len(questions_data.get('question_types', {})) if questions_data else 0,
            'has_data': questions_data is not None
        },
        'rag': {
            'enabled': HAS_EMBEDDING,
            'chunk_size': RAG_CONFIG['chunk_size'],
            'top_k_retrieval': RAG_CONFIG['top_k_retrieval'],
            'hybrid_search': RAG_CONFIG['hybrid_search']
        }
    }
    
    return jsonify({'success': True, 'data': stats})

@app.route('/api/rag-status')
def rag_status():
    """获取RAG系统状态"""
    return jsonify({
        'success': True,
        'rag_enabled': HAS_EMBEDDING,
        'vector_store_ready': vector_store is not None and len(vector_store.get('corpus_chunks', [])) > 0,
        'config': RAG_CONFIG
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🧠 双语医疗RAG问答系统 (RAG增强版)")
    print("=" * 60)
    print("📂 检查数据文件...")
    if CORPUS_PATH.exists():
        print(f"   ✓ 语料库文件: {CORPUS_PATH}")
    else:
        print(f"   ✗ 语料库文件不存在: {CORPUS_PATH}")
        print(f"     请将 medical_corpus.json 放置在: {CORPUS_PATH}")
    if QUESTIONS_PATH.exists():
        print(f"   ✓ 问题集文件: {QUESTIONS_PATH}")
    else:
        print(f"   ✗ 问题集文件不存在: {QUESTIONS_PATH}")
        print(f"     请将 medical_questions.json 放置在: {QUESTIONS_PATH}")
    # 启动时全局加载数据和向量
    initialize_data_and_vectors()
    doc_count, question_count, _, _ = get_data_counts()
    print(f"\n📊 数据统计:")
    print(f"   语料库: {doc_count} 篇文档")
    print(f"   问题集: {question_count} 个问题")
    if GLOBAL_VECTOR_STORE_READY:
        print(f"\n🔧 RAG系统已就绪")
    else:
        print(f"\n⚠️  RAG系统未启用或数据不完整")
        if not HAS_EMBEDDING:
            print(f"   请安装: pip install sentence-transformers")
    print(f"\n🌐 访问地址: http://localhost:5000")
    print(f"\n⚡ 系统特性:")
    print(f"   • 支持中英文任意语言提问")
    print(f"   • 可选择中文或英文回答")
    print(f"   • RAG检索增强生成")
    print(f"   • 混合搜索（语义+关键词）")
    print(f"   • 智能答案生成")
    print(f"   • 数据导出功能")
    print("\n🎯 使用说明:")
    print(f"   1. 在输入框中用中文或英文提问")
    print(f"   2. 选择想要的回答语言（中文/英文）")
    print(f"   3. 系统会使用RAG智能检索相关信息")
    print(f"   4. 可以点击'示例问题'快速测试")
    print(f"   5. 可在前端选择启用/禁用RAG功能")
    print("=" * 60)
    time.sleep(1)
    os.makedirs('templates', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)