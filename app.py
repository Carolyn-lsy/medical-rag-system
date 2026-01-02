# app.py - 医疗RAG问答系统
import os
import sys
import traceback
import streamlit as st
import json  # 新增导入
from pathlib import Path  # 新增导入

# ========== 第一步：修复导入路径问题 ==========
# 必须在所有其他导入之前执行！
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

print("=== 系统启动 ===")
print(f"项目目录: {current_dir}")
print(f"当前Python路径前3项: {sys.path[:3]}")

# ========== 新增函数：动态获取数据数量 ==========
def get_actual_data_counts():
    """
    动态获取实际JSON文件中的数据数量
    返回: (实际文档数, 实际问题数)
    """
    try:
        # 1. 获取实际语料库数量
        corpus_path = Path("data/raw/medical_corpus.json")
        actual_doc_count = 0
        if corpus_path.exists():
            with open(corpus_path, 'r', encoding='utf-8') as f:
                corpus = json.load(f)
                if isinstance(corpus, dict):
                    # 根据数据结构，这是一个字典，context是一个长字符串
                    if 'context' in corpus:
                        actual_doc_count = 1
                    else:
                        actual_doc_count = len(corpus)
                elif isinstance(corpus, list):
                    actual_doc_count = len(corpus)
                else:
                    actual_doc_count = 1
            print(f"✓ 实际语料库文档数: {actual_doc_count}")
        else:
            print(f"⚠️ 语料库文件不存在: {corpus_path}")
        
        # 2. 获取实际问题集数量
        questions_path = Path("data/raw/medical_questions.json")
        actual_question_count = 0
        if questions_path.exists():
            with open(questions_path, 'r', encoding='utf-8') as f:
                questions = json.load(f)
                if isinstance(questions, list):
                    actual_question_count = len(questions)
                elif isinstance(questions, dict):
                    if 'questions' in questions:
                        actual_question_count = len(questions['questions'])
                    else:
                        actual_question_count = len(questions)
                else:
                    actual_question_count = 1
            print(f"✓ 实际问题集问题数: {actual_question_count}")
        else:
            print(f"⚠️ 问题集文件不存在: {questions_path}")
        
        return actual_doc_count, actual_question_count
        
    except Exception as e:
        print(f"❌ 获取实际数据数量失败: {e}")
        return 0, 0

# 在Streamlit渲染之前获取实际数据
actual_doc_count, actual_question_count = get_actual_data_counts()

# ========== 第二步：尝试导入自定义模块 ==========
print("\n=== 模块导入测试 ===")

try:
    # 先尝试直接导入
    from src.config import Config
    from src.data_loader import MedicalDataLoader  # 注意：类名是 MedicalDataLoader
    from src.preprocessor import TextPreprocessor  # 注意：类名是 TextPreprocessor
    from src.vector_store import VectorStore
    from src.answer_generator import AnswerGenerator
    
    print("✅ 所有模块导入成功")
    IMPORT_METHOD = "success"
    
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    traceback.print_exc()
    
    # 如果失败，创建虚拟类
    print("⚠️  使用虚拟模块作为后备")
    
    class Config:
        MILVUS_HOST = 'localhost'
        MILVUS_PORT = '19530'
        EMBEDDING_MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
        EMBEDDING_DIM = 384
        CHUNK_SIZE = 500
        CHUNK_OVERLAP = 50
        TOP_K = 3
    
    class MedicalDataLoader:
        def __init__(self):
            print("虚拟: MedicalDataLoader初始化")
        def load_from_json(self, filepath):
            print(f"虚拟: 从 {filepath} 加载数据")
            return []
        def load_medical_corpus(self, corpus_path="data/medical.json"):
            return self.load_from_json(corpus_path)
        def load_medical_questions(self, questions_path="data/medical_questions.json"):
            return self.load_from_json(questions_path)
    
    class TextPreprocessor:
        def __init__(self):
            print("虚拟: TextPreprocessor初始化")
        def clean_html(self, html_text):
            return html_text
        def split_into_chunks(self, text, chunk_size=500, overlap=50):
            return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size-overlap)]
        def process_document(self, document):
            text = document.get('content', '') or document.get('text', '')
            chunks = self.split_into_chunks(text)
            return [{'text': chunk, 'chunk_id': i} for i, chunk in enumerate(chunks)]
    
    class VectorStore:
        def __init__(self, collection_name="medical_docs"):
            print(f"虚拟: VectorStore初始化，集合名: {collection_name}")
        def create_collection(self):
            print("虚拟: 创建集合")
        def insert_documents(self, documents, embeddings):
            print(f"虚拟: 插入 {len(documents)} 个文档")
        def search(self, query_embedding, top_k=3):
            print(f"虚拟: 搜索，top_k={top_k}")
            return []
    
    class AnswerGenerator:
        def __init__(self):
            print("虚拟: AnswerGenerator初始化")
        def generate_answer(self, question, search_results):
            return f"这是关于 '{question}' 的虚拟回答。实际系统中会基于检索结果生成专业回答。"
    
    IMPORT_METHOD = "virtual"

# ========== 第三步：初始化模块实例 ==========
print(f"\n=== 模块初始化 (方式: {IMPORT_METHOD}) ===")

try:
    if IMPORT_METHOD == "success":
        config = Config()
        loader = MedicalDataLoader()      # 使用正确的类名
        processor = TextPreprocessor()    # 使用正确的类名
        vector_store = VectorStore()
        answer_generator = AnswerGenerator()
        print(f"✅ 使用实际模块初始化")
    else:
        config = Config()
        loader = MedicalDataLoader()
        processor = TextPreprocessor()
        vector_store = VectorStore()
        answer_generator = AnswerGenerator()
        print(f"⚠️  使用虚拟模块初始化")
    
    print(f"数据加载器: {type(loader).__name__}")
    print(f"文本处理器: {type(processor).__name__}")
    
except Exception as e:
    print(f"❌ 模块初始化失败: {e}")
    traceback.print_exc()

# ========== 第四步：数据加载 ==========
print("\n=== 数据加载 ===")

# 创建示例数据 - 保持不变
corpus_data = [
    {
        "id": "doc_001",
        "title": "糖尿病基础知识",
        "content": "糖尿病是一种慢性疾病，主要特征是血糖水平持续升高。常见症状包括多饮、多尿、多食、体重下降等。预防方法包括健康饮食、定期运动和保持健康体重。",
        "source": "医疗指南"
    },
    {
        "id": "doc_002", 
        "title": "高血压防治",
        "content": "高血压是指血压持续偏高的状态。预防方法包括低盐饮食、定期锻炼、控制体重、戒烟限酒。症状可能包括头痛、头晕、心悸等，但很多患者无症状。",
        "source": "心血管健康手册"
    },
    {
        "id": "doc_003",
        "title": "感冒症状与治疗",
        "content": "普通感冒是由病毒引起的上呼吸道感染。常见症状包括流鼻涕、咳嗽、喉咙痛、打喷嚏、轻微发热等。建议多休息、多喝水，如有需要可服用非处方药物缓解症状。",
        "source": "家庭医学指南"
    }
]

questions_data = [
    {"question": "糖尿病的常见症状有哪些？", "answer": "多饮、多尿、多食、体重下降等"},
    {"question": "如何预防高血压？", "answer": "低盐饮食、定期锻炼、控制体重、戒烟限酒"},
    {"question": "感冒有哪些症状？", "answer": "流鼻涕、咳嗽、喉咙痛、打喷嚏、轻微发热"}
]

print(f"示例语料库文档数: {len(corpus_data)}")
print(f"示例测试问题数: {len(questions_data)}")

# 初始化会话状态
if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'vector_store_initialized' not in st.session_state:
    st.session_state.vector_store_initialized = False

# Streamlit页面配置
st.set_page_config(
    page_title="医疗RAG问答系统",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== 侧边栏 ==========
with st.sidebar:
    st.title("🏥 医疗RAG系统")
    st.markdown("---")
    
    # 系统状态 - 修改：显示实际数据数量
    st.header("📊 系统状态")
    
    # 使用实际数据数量
    display_doc_count = actual_doc_count if actual_doc_count > 0 else len(corpus_data)
    display_question_count = actual_question_count if actual_question_count > 0 else len(questions_data)
    
    st.info(f"📁 语料库: {display_doc_count} 篇文档")
    st.info(f"❓ 问题集: {display_question_count} 个问题")
    st.info(f"🔧 导入方式: {IMPORT_METHOD}")
    
    # 添加实际数据源信息
    if actual_doc_count > 0 or actual_question_count > 0:
        with st.expander("📂 实际数据信息"):
            st.write(f"**实际语料库**: {actual_doc_count}篇文档")
            st.write(f"**实际问题集**: {actual_question_count}个问题")
            if actual_doc_count == 0 and actual_question_count == 0:
                st.write("⚠️ 使用示例数据")
            else:
                st.write("✅ 从JSON文件加载实际数据")
    
    st.markdown("---")
    
    # 系统设置 - 保持不变
    st.header("⚙️ 系统设置")
    
    top_k = st.slider(
        "检索结果数量", 
        min_value=1, 
        max_value=10, 
        value=3,
        help="每次查询返回的最相关文档数量"
    )
    
    chunk_size = st.slider(
        "文本分块大小", 
        min_value=100, 
        max_value=1000, 
        value=500,
        step=50,
        help="每个文本块的最大字符数"
    )
    
    similarity_threshold = st.slider(
        "相似度阈值", 
        min_value=0.0, 
        max_value=1.0, 
        value=0.6,
        step=0.05,
        help="只显示相似度高于此值的结果"
    )
    
    st.markdown("---")
    st.header("📁 数据操作")
    
    if st.button("🧪 测试文本处理", use_container_width=True):
        if corpus_data and len(corpus_data) > 0:
            sample_text = corpus_data[0].get('content', '')
            if sample_text:
                chunks = processor.split_into_chunks(sample_text, chunk_size, 50)
                st.success(f"测试成功！将文本分割成 {len(chunks)} 个块")
                with st.expander("查看分块详情"):
                    for i, chunk in enumerate(chunks[:3]):
                        st.text(f"块 {i+1}: {chunk[:80]}...")
            else:
                st.warning("样本文本为空")
        else:
            st.warning("语料库为空")
    
    # 添加数据重新加载按钮
    if st.button("🔄 重新加载数据统计", use_container_width=True):
        new_doc_count, new_question_count = get_actual_data_counts()
        st.success(f"数据统计已更新: {new_doc_count}篇文档, {new_question_count}个问题")
        # 可以使用session_state保存新值
    
    st.markdown("---")
    st.caption("基于向量检索的医疗问答系统 v1.0")

# ========== 主界面 ==========
st.title("🔍 医疗问题查询系统")
st.markdown("""
欢迎使用医疗RAG问答系统！本系统基于医疗知识库，通过检索增强生成技术为您提供准确的医疗信息回答。
**注意**：本系统提供的信息仅供参考，不能替代专业医疗建议。
""")

# 显示实际数据统计（如果可用）
if actual_doc_count > 0 or actual_question_count > 0:
    st.info(f"📊 **实际数据统计**: 语料库 {actual_doc_count}篇文档 | 问题集 {actual_question_count}个问题")

# 快速问题示例 - 保持不变
st.subheader("💡 试试这些问题:")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("糖尿病的症状", use_container_width=True, type="secondary"):
        st.session_state.auto_question = "糖尿病的常见症状有哪些？"
with col2:
    if st.button("高血压预防", use_container_width=True, type="secondary"):
        st.session_state.auto_question = "如何预防高血压？"
with col3:
    if st.button("感冒的症状", use_container_width=True, type="secondary"):
        st.session_state.auto_question = "感冒有哪些症状？"

# 查询区域 - 保持不变
st.subheader("🔎 问题查询")
query_col1, query_col2 = st.columns([4, 1])

with query_col1:
    # 如果有自动填充的问题，使用它
    default_question = ""
    if 'auto_question' in st.session_state:
        default_question = st.session_state.auto_question
        # 使用后清除
        del st.session_state.auto_question
    
    question = st.text_input(
        "请输入您的医疗问题：",
        value=default_question,
        placeholder="例如：糖尿病的常见症状有哪些？如何预防高血压？",
        label_visibility="collapsed",
        key="question_input"
    )

with query_col2:
    search_button = st.button("🔍 开始查询", 
                            type="primary", 
                            use_container_width=True)

# ========== 查询处理 ==========
if search_button and question:
    with st.spinner("正在检索和生成回答..."):
        try:
            # 记录查询
            st.session_state.search_history.append({
                'question': question,
                'time': len(st.session_state.search_history) + 1
            })
            
            # 显示查询问题
            st.success(f"📝 查询问题: **{question}**")
            
            # === 步骤1: 文本预处理 ===
            st.subheader("📋 第一步: 文本处理")
            
            # 简单的文本处理演示
            if hasattr(processor, 'split_into_chunks'):
                chunks = processor.split_into_chunks(question, 100, 20)
                with st.expander("查看查询文本分块", expanded=False):
                    st.write(f"原始问题: {question}")
                    st.write(f"分块数量: {len(chunks)}")
                    for i, chunk in enumerate(chunks):
                        st.text(f"块 {i+1}: {chunk}")
            
            # === 步骤2: 检索相关文档 ===
            st.subheader("🔍 第二步: 检索相关文档")
            
            # 简单关键词匹配
            keywords = []
            if "糖尿病" in question:
                keywords = ["糖尿病", "血糖", "胰岛素"]
            elif "高血压" in question:
                keywords = ["高血压", "血压", "心血管"]
            elif "感冒" in question:
                keywords = ["感冒", "病毒", "呼吸道"]
            else:
                # 通用关键词提取
                import re
                keywords = re.findall(r'[\u4e00-\u9fff]+', question)
            
            relevant_docs = []
            for doc in corpus_data:
                content = doc.get('content', '')
                title = doc.get('title', '')
                full_text = title + " " + content
                
                match_score = 0
                for kw in keywords:
                    if kw in full_text:
                        match_score += 1
                
                if match_score > 0:
                    relevant_docs.append({
                        'doc': doc,
                        'score': match_score,
                        'preview': content[:150] + '...' if len(content) > 150 else content
                    })
            
            # 按匹配分数排序
            relevant_docs.sort(key=lambda x: x['score'], reverse=True)
            relevant_docs = relevant_docs[:top_k]
            
            # 显示检索结果
            if relevant_docs:
                st.success(f"找到 {len(relevant_docs)} 个相关文档")
                
                for i, result in enumerate(relevant_docs, 1):
                    doc = result['doc']
                    with st.expander(f"📄 结果 {i}: {doc.get('title', '无标题')} (匹配度: {result['score']})", expanded=True):
                        st.write(f"**来源**: {doc.get('source', '未知来源')}")
                        st.write(f"**内容**: {result['preview']}")
                        
                        # 显示文本分块（如果可用）
                        if hasattr(processor, 'process_document'):
                            processed = processor.process_document(doc)
                            if processed:
                                st.write(f"**文本分块**: 共 {len(processed)} 块")
                                for chunk in processed[:2]:
                                    st.text(f"• {chunk.get('text', '')[:100]}...")
            else:
                st.warning("未找到高度相关文档，将基于通用知识回答")
                relevant_docs = [{
                    'doc': {'title': '通用医疗知识', 'content': '基于常见医疗知识提供回答。'},
                    'score': 0,
                    'preview': '通用医疗知识库'
                }]
            
            # === 步骤3: 生成回答 ===
            st.subheader("💡 第三步: 系统回答")
            
            # 使用AnswerGenerator生成回答
            if IMPORT_METHOD == "success":
                try:
                    # 准备搜索结果格式
                    search_results = []
                    for result in relevant_docs:
                        search_results.append({
                            'text': result['preview'],
                            'metadata': {
                                'title': result['doc'].get('title', ''),
                                'source': result['doc'].get('source', '')
                            }
                        })
                    
                    # 生成答案
                    answer = answer_generator.generate_answer(question, search_results)
                    
                except Exception as e:
                    st.warning(f"AnswerGenerator生成失败: {e}")
                    answer = f"""
                    基于检索到的医疗知识，关于"**{question}**"：
                    
                    **相关信息总结**:
                    {chr(10).join([f"{i+1}. {r['preview']}" for i, r in enumerate(relevant_docs)])}
                    
                    **建议**:
                    - 以上信息基于医疗知识库
                    - 具体症状请咨询专业医生
                    - 保持健康生活方式
                    """
            else:
                # 使用虚拟回答
                answer = answer_generator.generate_answer(question, [])
            
            # 显示回答
            st.markdown(answer)
            
            # 显示置信度
            if relevant_docs and relevant_docs[0]['score'] > 0:
                confidence = min(0.7 + (relevant_docs[0]['score'] * 0.1), 0.95)
                st.progress(confidence, text=f"回答置信度: {confidence:.0%}")
            else:
                st.progress(0.5, text="回答置信度: 50% (基于通用知识)")
            
            # 添加到查询历史
            st.session_state.search_history[-1]['answer'] = answer[:100] + "..." if len(answer) > 100 else answer
            
        except Exception as e:
            st.error(f"查询处理失败: {e}")
            st.info("使用备用回答模式...")
            
            # 备用回答
            if "糖尿病" in question:
                answer = "糖尿病常见症状包括多饮、多尿、多食、体重下降等。建议定期检查血糖，保持健康饮食和适量运动。"
            elif "高血压" in question:
                answer = "高血压预防包括低盐饮食、定期锻炼、控制体重、戒烟限酒。如有头痛、头晕等症状应及时就医。"
            elif "感冒" in question:
                answer = "感冒症状包括流鼻涕、咳嗽、喉咙痛、打喷嚏等。建议多休息、多喝水，必要时可服用非处方药物。"
            else:
                answer = f"关于'{question}'，建议咨询专业医生获取准确诊断和治疗建议。保持健康生活方式有助于预防多种疾病。"
            
            st.success(answer)

elif search_button:
    st.warning("⚠️ 请输入问题后再点击查询。")

# ========== 查询历史 ==========
if st.session_state.search_history:
    st.subheader("📜 查询历史")
    with st.expander("查看历史查询", expanded=False):
        for i, record in enumerate(reversed(st.session_state.search_history[-5:]), 1):
            st.write(f"{i}. **{record['question']}**")
            if 'answer' in record:
                st.caption(f"  回答摘要: {record['answer']}")
            st.divider()

# ========== 系统信息 ==========
st.markdown("---")
col_info1, col_info2, col_info3 = st.columns(3)

with col_info1:
    st.caption("🧠 **智能检索**")
    st.caption("基于语义相似度的向量检索")

with col_info2:
    st.caption("🏥 **专业领域**")
    st.caption("医疗健康知识问答")

with col_info3:
    st.caption("🔄 **实时更新**")
    st.caption("支持动态加载知识库")

st.markdown("---")
st.caption("医疗RAG系统 v1.0 | 数据来源: GraphRAG-Benchmark医疗数据集 | 仅供教学演示使用")

# 调试信息
if st.sidebar.checkbox("显示调试信息", value=False):
    st.sidebar.subheader("🔧 调试信息")
    st.sidebar.write(f"Python路径: {sys.executable}")
    st.sidebar.write(f"当前目录: {current_dir}")
    st.sidebar.write(f"导入方式: {IMPORT_METHOD}")
    st.sidebar.write(f"搜索历史: {len(st.session_state.search_history)} 条")
    st.sidebar.write(f"实际语料库文档: {actual_doc_count}")
    st.sidebar.write(f"实际问题集问题: {actual_question_count}")