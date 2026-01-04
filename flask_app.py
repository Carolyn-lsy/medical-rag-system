# flask_app.py - 优化版，避免translate库卡顿
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

app = Flask(__name__)

# ========== 配置路径 ==========
BASE_DIR = Path(__file__).parent.absolute()
CORPUS_PATH = BASE_DIR / "data" / "raw" / "medical_corpus.json"
QUESTIONS_PATH = BASE_DIR / "data" / "raw" / "medical_questions.json"

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

# ========== 优化翻译函数 ==========
import time

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

# ========== 数据加载函数（优化版，避免在加载时翻译） ==========
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
    corpus_data = load_corpus_data()
    questions_data = load_questions_data()
    
    doc_count = corpus_data['doc_count'] if corpus_data else 1
    question_count = questions_data['total_count'] if questions_data else 0
    
    return doc_count, question_count, corpus_data, questions_data

# ========== 智能搜索函数（延迟翻译） ==========
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

# ========== Flask路由 ==========
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
        # 使用简易翻译显示示例问题，避免卡顿
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
                         sample_questions=display_questions)

@app.route('/api/query', methods=['POST'])
def handle_query():
    """处理查询请求"""
    try:
        data = request.json
        question = data.get('question', '').strip()
        answer_language = data.get('answer_language', 'zh')
        
        if not question:
            return jsonify({'success': False, 'error': '请输入问题'})
        
        _, _, _, questions_data = get_data_counts()
        
        if not questions_data:
            return jsonify({
                'success': False,
                'error': '无法加载问题数据，请检查数据文件'
            })
        
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
            'answer_language': answer_language
        })
    
    except Exception as e:
        print(f"查询处理错误: {e}")
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        })

def generate_answer_html(question, search_results, answer_language='zh'):
    """生成回答HTML"""
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
    html_parts.append('<h4>🔍 查询结果</h4>')
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
        }
    }
    
    return jsonify({'success': True, 'data': stats})

if __name__ == '__main__':
    print("=" * 60)
    print("🏥 双语医疗RAG问答系统 (优化版，解决卡顿问题)")
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
    
    doc_count, question_count, _, _ = get_data_counts()
    
    print(f"\n📊 数据统计:")
    print(f"   语料库: {doc_count} 篇文档")
    print(f"   问题集: {question_count} 个问题")
    
    print(f"\n🌐 访问地址: http://localhost:5000")
    print(f"\n⚡ 系统特性:")
    print(f"   • 支持中英文任意语言提问")
    print(f"   • 可选择中文或英文回答")
    print(f"   • 使用translate库进行高质量翻译")
    print(f"   • 智能关键词匹配")
    print(f"   • 数据导出功能")
    print(f"   • 优化性能，避免卡顿")
    
    print("\n🎯 使用说明:")
    print(f"   1. 在输入框中用中文或英文提问")
    print(f"   2. 选择想要的回答语言（中文/英文）")
    print(f"   3. 系统会自动匹配最相关的问题和答案")
    print(f"   4. 可以点击'示例问题'快速测试")
    
    print("=" * 60)
    
    # 等待翻译队列初始化
    time.sleep(1)
    
    os.makedirs('templates', exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)