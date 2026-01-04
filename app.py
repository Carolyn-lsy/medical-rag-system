# app.py - Streamlit主界面
import streamlit as st
import requests
import json
import pandas as pd
from PIL import Image
import base64

# 页面配置
st.set_page_config(
    page_title="智能医疗RAG系统",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
def local_css():
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #4B5563;
        text-align: center;
        margin-bottom: 2rem;
    }
    .result-card {
        background-color: #F8FAFC;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-left: 4px solid #3B82F6;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .confidence-badge {
        background-color: #10B981;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.875rem;
        font-weight: 600;
    }
    .language-tab {
        display: flex;
        margin-bottom: 1rem;
        border-bottom: 1px solid #E5E7EB;
    }
    .language-tab button {
        padding: 0.5rem 1rem;
        background: none;
        border: none;
        cursor: pointer;
        font-weight: 600;
        color: #6B7280;
        border-bottom: 2px solid transparent;
    }
    .language-tab button.active {
        color: #3B82F6;
        border-bottom: 2px solid #3B82F6;
    }
    .medical-advice {
        background-color: #ECFDF5;
        border-radius: 10px;
        padding: 1.5rem;
        margin-top: 2rem;
        border-left: 4px solid #10B981;
    }
    </style>
    """, unsafe_allow_html=True)

# 初始化Session State
def init_session_state():
    if 'language' not in st.session_state:
        st.session_state.language = 'zh'  # 默认中文回答
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []
    if 'api_base_url' not in st.session_state:
        st.session_state.api_base_url = "http://localhost:5000"

# 侧边栏
def sidebar():
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/hospital.png", width=80)
        st.title("⚙️ 系统设置")
        
        # 语言选择
        st.subheader("🌐 回答语言")
        language = st.radio(
            "选择回答语言:",
            ["中文", "English"],
            index=0 if st.session_state.language == 'zh' else 1,
            horizontal=True
        )
        st.session_state.language = 'zh' if language == "中文" else 'en'
        
        st.divider()
        
        # 系统状态
        st.subheader("📊 系统状态")
        
        # 连接到后端API获取状态
        try:
            response = requests.get(f"{st.session_state.api_base_url}/api/status")
            if response.status_code == 200:
                data = response.json()
                st.metric("问题数量", f"{data.get('question_count', 0):,}")
                st.metric("语料库文档", f"{data.get('doc_count', 0):,}")
                st.metric("Milvus状态", "✅ 在线" if data.get('milvus_connected', False) else "❌ 离线")
        except:
            st.warning("后端API连接失败")
        
        st.divider()
        
        # 快速示例
        st.subheader("💡 试试这些问题")
        examples = [
            "感冒的症状有哪些？",
            "What are symptoms of diabetes?",
            "如何预防高血压？",
            "皮肤癌的治疗方法",
            "头痛的原因是什么？"
        ]
        
        for example in examples:
            if st.button(example, use_container_width=True):
                st.session_state.query_text = example

# 主页面
def main_page():
    # 页头
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<h1 class="main-header">🏥 智能医疗RAG系统</h1>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">基于Milvus向量数据库的检索增强生成系统</p>', unsafe_allow_html=True)
    
    # 查询区域
    st.markdown("---")
    st.subheader("🔍 医疗问题查询")
    
    # 双列布局
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_area(
            "请输入您的医疗问题（支持中英文）:",
            height=120,
            placeholder="例如：感冒的症状有哪些？\n或：What are symptoms of diabetes?",
            key="query_input"
        )
    
    with col2:
        st.write("")  # 空白
        st.write("")
        if st.button("🚀 开始查询", type="primary", use_container_width=True):
            if query:
                process_query(query)
            else:
                st.warning("请输入问题")
        
        if st.button("🔄 清空查询", use_container_width=True):
            st.session_state.query_input = ""
            st.rerun()
    
    # 结果显示区域
    if 'query_result' in st.session_state:
        display_results()
    
    # 系统特性展示
    st.markdown("---")
    st.subheader("✨ 系统特性")
    
    cols = st.columns(3)
    features = [
        ("🧠 智能检索", "基于Milvus向量数据库的语义搜索"),
        ("🌐 双语支持", "中英文混合输入，可选择回答语言"),
        ("🏥 专业医疗", "基于真实医疗数据，权威可靠"),
        ("⚡ 实时响应", "毫秒级检索速度"),
        ("📊 可视化", "直观的结果展示和置信度"),
        ("🔧 可扩展", "支持动态更新知识库")
    ]
    
    for i, (title, desc) in enumerate(features):
        with cols[i % 3]:
            with st.container():
                st.markdown(f"**{title}**")
                st.caption(desc)
                st.write("")

def process_query(query):
    """处理查询请求"""
    with st.spinner("🔍 正在检索医疗知识库..."):
        try:
            # 发送请求到后端API
            payload = {
                'question': query,
                'language': st.session_state.language
            }
            
            response = requests.post(
                f"{st.session_state.api_base_url}/api/query",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                st.session_state.query_result = result
                st.session_state.current_query = query
                
                # 添加到历史
                st.session_state.query_history.insert(0, {
                    'query': query,
                    'time': pd.Timestamp.now(),
                    'result_count': result.get('result_count', 0)
                })
                
            else:
                st.error(f"查询失败: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            st.error(f"网络错误: {str(e)}")
        except Exception as e:
            st.error(f"查询出错: {str(e)}")

def display_results():
    """显示查询结果"""
    result = st.session_state.query_result
    
    if not result.get('success', False):
        st.error("查询失败")
        return
    
    # 显示查询信息
    st.markdown(f"### 📝 查询: *{st.session_state.current_query}*")
    
    # 显示结果数量
    result_count = result.get('result_count', 0)
    if result_count == 0:
        st.info("未找到相关信息，请尝试其他查询词")
        return
    
    # 显示置信度
    confidence = result.get('confidence', 0) * 100
    st.progress(confidence / 100, text=f"置信度: {confidence:.1f}%")
    
    # 显示结果
    for i, item in enumerate(result.get('results', []), 1):
        with st.container():
            st.markdown(f"#### 📄 结果 #{i}")
            
            # 结果卡片
            with st.expander(f"**{item.get('question', '')}**", expanded=True):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # 双语显示
                    if st.session_state.language == 'zh':
                        st.markdown(f"**答案:** {item.get('answer_zh', item.get('answer', ''))}")
                    else:
                        st.markdown(f"**Answer:** {item.get('answer_en', item.get('answer', ''))}")
                    
                    # 来源和类型
                    st.caption(f"类型: {item.get('type', 'Medical')} | 来源: {item.get('source', 'Unknown')}")
                
                with col2:
                    score = item.get('score', 0) * 100
                    st.metric("相关度", f"{score:.0f}%")
            
            st.divider()
    
    # 医疗建议
    st.markdown("---")
    with st.container():
        st.markdown("### 💡 医疗建议")
        if st.session_state.language == 'zh':
            advice = """
            1. **信息仅供参考** - 以上信息基于医疗数据库，不能替代专业医疗建议
            2. **咨询专业医生** - 如有具体症状，请咨询专业医生进行诊断
            3. **紧急情况就医** - 如遇紧急医疗情况，请立即就医
            4. **健康生活方式** - 保持健康饮食和适量运动有助于疾病预防
            """
        else:
            advice = """
            1. **For Reference Only** - The above information is based on medical databases and cannot replace professional medical advice
            2. **Consult Professionals** - For specific symptoms, please consult a professional doctor
            3. **Emergency Care** - Seek immediate medical attention in case of emergencies
            4. **Healthy Lifestyle** - Maintaining a healthy diet and regular exercise helps prevent diseases
            """
        
        st.info(advice)

# 历史记录页面
def history_page():
    st.title("📜 查询历史")
    
    if not st.session_state.query_history:
        st.info("暂无查询历史")
        return
    
    # 显示历史记录
    for i, history in enumerate(st.session_state.query_history[:10]):
        with st.expander(f"{i+1}. {history['query'][:50]}...", expanded=i==0):
            st.write(f"**查询时间:** {history['time'].strftime('%Y-%m-%d %H:%M:%S')}")
            st.write(f"**查询内容:** {history['query']}")
            st.write(f"**结果数量:** {history['result_count']}")

# 数据管理页面
def data_page():
    st.title("📊 数据管理")
    
    tab1, tab2, tab3 = st.tabs(["数据统计", "数据预览", "数据上传"])
    
    with tab1:
        try:
            response = requests.get(f"{st.session_state.api_base_url}/api/stats")
            if response.status_code == 200:
                stats = response.json()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("总问题数", stats.get('total_questions', 0))
                with col2:
                    st.metric("语料库文档", stats.get('corpus_docs', 0))
                with col3:
                    st.metric("Milvus向量", stats.get('vector_count', 0))
                
                # 问题类型分布
                if 'question_types' in stats:
                    st.subheader("问题类型分布")
                    type_data = pd.DataFrame(
                        list(stats['question_types'].items()),
                        columns=['类型', '数量']
                    )
                    st.bar_chart(type_data.set_index('类型'))
            else:
                st.error("获取统计数据失败")
        except:
            st.error("无法连接到后端API")
    
    with tab2:
        if st.button("预览数据样本"):
            try:
                response = requests.get(f"{st.session_state.api_base_url}/api/sample")
                if response.status_code == 200:
                    sample = response.json()
                    df = pd.DataFrame(sample.get('data', []))
                    st.dataframe(df)
                else:
                    st.error("获取数据样本失败")
            except:
                st.error("无法连接到后端API")
    
    with tab3:
        st.warning("数据上传功能需要管理员权限")
        uploaded_file = st.file_uploader("上传JSON数据文件", type=['json'])
        if uploaded_file:
            if st.button("上传到系统"):
                try:
                    # 读取并验证JSON
                    data = json.load(uploaded_file)
                    st.success(f"成功读取 {len(data)} 条数据")
                    
                    # TODO: 上传到后端
                except json.JSONDecodeError:
                    st.error("文件格式错误，请上传有效的JSON文件")

# 主函数
def main():
    # 应用CSS
    local_css()
    
    # 初始化
    init_session_state()
    
    # 侧边栏
    sidebar()
    
    # 主页面选择
    pages = {
        "🏠 首页": main_page,
        "📜 历史记录": history_page,
        "📊 数据管理": data_page
    }
    
    # 在侧边栏添加页面导航
    st.sidebar.markdown("---")
    st.sidebar.subheader("📱 页面导航")
    
    # 创建单选按钮用于页面选择
    selected_page = st.sidebar.radio(
        "选择页面:",
        list(pages.keys())
    )
    
    # 显示选中的页面
    pages[selected_page]()

if __name__ == "__main__":
    main()