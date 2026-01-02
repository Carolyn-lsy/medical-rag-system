# flask_app.py - 医疗RAG系统（中英文双查询版）
from flask import Flask, render_template, request, jsonify, send_file
import json
import pandas as pd
from pathlib import Path
import os
import tempfile
from datetime import datetime
import re

app = Flask(__name__)

# ========== 医疗术语词典（双语版） ==========
MEDICAL_TERMS = {
    "symptoms": {
        "头痛": ["headache", "cephalalgia"],
        "胃疼": ["stomachache", "stomach pain", "gastralgia", "abdominal pain"],
        "发烧": ["fever", "pyrexia"],
        "咳嗽": ["cough", "tussis"],
        "腹泻": ["diarrhea", "diarrhoea"],
        "呕吐": ["vomit", "emesis", "throw up"],
        "胸闷": ["chest tightness", "chest distress"],
        "头晕": ["dizziness", "vertigo"],
        "乏力": ["fatigue", "weakness", "tiredness"],
        "皮疹": ["rash", "skin rash"],
        "疼痛": ["pain", "ache", "soreness"],
        "发炎": ["inflammation", "swelling"],
        "恶心": ["nausea", "sick"],
        "呼吸困难": ["difficulty breathing", "dyspnea"],
        "心悸": ["palpitation", "heart palpitations"]
    },
    "diseases": {
        "糖尿病": ["diabetes", "diabetes mellitus"],
        "高血压": ["hypertension", "high blood pressure"],
        "感冒": ["cold", "common cold"],
        "流感": ["flu", "influenza"],
        "肺炎": ["pneumonia"],
        "胃炎": ["gastritis", "stomach inflammation"],
        "心脏病": ["heart disease", "cardiac disease"],
        "癌症": ["cancer", "carcinoma", "tumor"],
        "哮喘": ["ashtma"],
        "关节炎": ["arthritis"],
        "皮肤癌": ["skin cancer", "basal cell carcinoma", "squamous cell carcinoma"],
        "冠心病": ["coronary heart disease", "coronary artery disease"],
        "中风": ["stroke", "cerebral infarction"],
        "肝炎": ["hepatitis"],
        "肾炎": ["nephritis"]
    },
    "body_parts": {
        "胃": ["stomach", "gastric"],
        "心脏": ["heart", "cardiac"],
        "肺": ["lung", "pulmonary"],
        "肝脏": ["liver", "hepatic"],
        "肾脏": ["kidney", "renal"],
        "皮肤": ["skin", "dermal"],
        "眼睛": ["eye", "ocular"],
        "耳朵": ["ear", "otic"],
        "鼻子": ["nose", "nasal"],
        "喉咙": ["throat", "pharyngeal"]
    },
    "treatments": {
        "手术": ["surgery", "operation"],
        "药物治疗": ["medication", "drug therapy"],
        "化疗": ["chemotherapy"],
        "放疗": ["radiotherapy", "radiation therapy"],
        "物理治疗": ["physical therapy", "physiotherapy"],
        "检查": ["examination", "check-up"],
        "诊断": ["diagnosis", "diagnostic"],
        "预防": ["prevention", "preventive"]
    }
}

# ========== 双语医疗知识库 ==========
BILINGUAL_KNOWLEDGE_BASE = {
    "diabetes": {
        "title_en": "Diabetes Information",
        "title_cn": "糖尿病信息",
        "content_en": "Diabetes is a chronic metabolic disorder characterized by high blood sugar levels over a prolonged period. Common symptoms include increased thirst (polydipsia), frequent urination (polyuria), constant hunger (polyphagia), and unexplained weight loss. Long-term complications include cardiovascular disease, stroke, chronic kidney disease, foot ulcers, and damage to the eyes. Management involves lifestyle changes (diet and exercise), blood sugar monitoring, and sometimes insulin or other medications.",
        "content_cn": "糖尿病是一种慢性代谢紊乱疾病，特征是长期血糖水平升高。常见症状包括多饮、多尿、多食和不明原因的体重减轻。长期并发症包括心血管疾病、中风、慢性肾病、足部溃疡和眼睛损伤。管理涉及生活方式改变（饮食和运动）、血糖监测，有时需要胰岛素或其他药物。",
        "keywords": ["diabetes", "blood sugar", "insulin", "糖尿病", "血糖", "胰岛素"]
    },
    "hypertension": {
        "title_en": "Hypertension Prevention",
        "title_cn": "高血压预防",
        "content_en": "Hypertension (high blood pressure) is a condition in which the force of blood against artery walls is too high. Normal blood pressure is below 120/80 mmHg. Prevention strategies include: 1) Reducing sodium intake, 2) Regular physical activity (30 minutes most days), 3) Maintaining healthy weight, 4) Limiting alcohol consumption, 5) Avoiding tobacco, 6) Managing stress, 7) Eating potassium-rich foods. Untreated hypertension can lead to heart attack, stroke, and kidney damage.",
        "content_cn": "高血压（血压过高）是血液对动脉壁压力过高的状况。正常血压低于120/80 mmHg。预防策略包括：1) 减少钠摄入，2) 定期体育活动（大多数日子30分钟），3) 保持健康体重，4) 限制饮酒，5) 避免烟草，6) 管理压力，7) 食用富含钾的食物。未治疗的高血压可能导致心脏病发作、中风和肾脏损伤。",
        "keywords": ["hypertension", "blood pressure", "血压", "高血压", "心血管"]
    },
    "common_cold": {
        "title_en": "Common Cold Symptoms and Treatment",
        "title_cn": "感冒症状与治疗",
        "content_en": "The common cold is a viral infection of your upper respiratory tract (nose and throat). Symptoms usually appear 1-3 days after exposure and include: runny or stuffy nose, sore throat, cough, congestion, slight body aches, mild headache, sneezing, low-grade fever. Treatment focuses on symptom relief: rest, drink plenty of fluids, use saline nasal spray, gargle with salt water, use over-the-counter cold medications. Antibiotics are not effective against cold viruses.",
        "content_cn": "普通感冒是上呼吸道（鼻子和喉咙）的病毒感染。症状通常在暴露后1-3天出现，包括：流鼻涕或鼻塞、喉咙痛、咳嗽、充血、轻微身体疼痛、轻度头痛、打喷嚏、低烧。治疗侧重于缓解症状：休息、多喝水、使用盐水鼻喷雾、盐水漱口、使用非处方感冒药。抗生素对感冒病毒无效。",
        "keywords": ["cold", "common cold", "virus", "感冒", "病毒", "呼吸道"]
    },
    "skin_cancer": {
        "title_en": "Skin Cancer Basics",
        "title_cn": "皮肤癌基础知识",
        "content_en": "Basal cell carcinoma (BCC) is the most common type of skin cancer. It rarely spreads to other parts of the body but can be locally destructive if untreated. Risk factors include: fair skin, history of sunburns, excessive sun exposure, family history, radiation exposure. Warning signs: pearly or waxy bump, flat flesh-colored or brown scar-like lesion, bleeding or scabbing sore that heals and returns. Prevention: use sunscreen (SPF 30+), wear protective clothing, avoid midday sun, don't use tanning beds.",
        "content_cn": "基底细胞癌是最常见的皮肤癌类型。它很少扩散到身体其他部位，但如果不治疗可能会局部破坏。风险因素包括：白皙皮肤、晒伤史、过度日晒、家族史、辐射暴露。警告信号：珍珠状或蜡状肿块、平坦的肉色或棕色疤痕样病变、出血或结痂的疮口愈合后又复发。预防：使用防晒霜（SPF 30+）、穿防护服、避免中午阳光、不使用日光浴床。",
        "keywords": ["skin cancer", "basal cell carcinoma", "skin", "cancer", "皮肤癌", "基底细胞", "皮肤", "癌症"]
    },
    "headache": {
        "title_en": "Headache Relief Methods",
        "title_cn": "头痛缓解方法",
        "content_en": "For tension headaches: 1) Apply warm or cold compress to forehead and neck, 2) Practice relaxation techniques (deep breathing, meditation), 3) Improve posture, 4) Regular exercise, 5) Adequate sleep, 6) Stay hydrated. For migraine headaches: 1) Rest in quiet, dark room, 2) Apply cold packs, 3) Moderate caffeine, 4) Prescription medications as directed. Seek medical attention if: sudden severe headache, headache after head injury, headache with fever/stiff neck/confusion/seizures.",
        "content_cn": "对于紧张性头痛：1) 在前额和颈部敷温或冷敷布，2) 练习放松技巧（深呼吸、冥想），3) 改善姿势，4) 定期锻炼，5) 充足睡眠，6) 保持水分。对于偏头痛：1) 在安静、黑暗的房间休息，2) 使用冷敷包，3) 适量咖啡因，4) 按指示使用处方药。如有以下情况请就医：突然剧烈头痛、头部受伤后头痛、伴有发烧/颈部僵硬/意识模糊/癫痫发作的头痛。",
        "keywords": ["headache", "migraine", "pain relief", "头痛", "偏头痛", "疼痛缓解"]
    },
    "stomach_pain": {
        "title_en": "Stomach Pain Causes and Care",
        "title_cn": "胃疼原因与护理",
        "content_en": "Common causes of stomach pain: 1) Indigestion or gas, 2) Gastroenteritis (stomach flu), 3) Constipation, 4) Irritable bowel syndrome, 5) Food poisoning, 6) Lactose intolerance, 7) Ulcers, 8) Gallstones. Home care: 1) Drink clear fluids, 2) Avoid solid food initially, 3) BRAT diet (bananas, rice, applesauce, toast), 4) Avoid dairy, fatty foods, 5) Use heating pad, 6) Rest. See doctor if: severe pain, lasts more than 2 days, fever over 101°F, vomiting blood, black stools.",
        "content_cn": "胃疼常见原因：1) 消化不良或胀气，2) 胃肠炎（胃流感），3) 便秘，4) 肠易激综合征，5) 食物中毒，6) 乳糖不耐症，7) 溃疡，8) 胆结石。家庭护理：1) 喝清液，2) 最初避免固体食物，3) BRAT饮食（香蕉、米饭、苹果酱、吐司），4) 避免乳制品、油腻食物，5) 使用加热垫，6) 休息。如有以下情况看医生：剧烈疼痛、持续超过2天、发烧超过38.3°C、吐血、黑色粪便。",
        "keywords": ["stomach pain", "stomachache", "abdominal pain", "indigestion", "胃疼", "胃痛", "腹痛", "消化不良"]
    }
}

# ========== 核心函数 ==========
def get_data_counts():
    """获取实际数据数量"""
    try:
        corpus_path = Path("data/raw/medical_corpus.json")
        doc_count = 0
        corpus_data = {}
        if corpus_path.exists():
            with open(corpus_path, 'r', encoding='utf-8') as f:
                corpus_data = json.load(f)
                if isinstance(corpus_data, dict) and 'context' in corpus_data:
                    doc_count = 1
                elif isinstance(corpus_data, list):
                    doc_count = len(corpus_data)
        
        questions_path = Path("data/raw/medical_questions.json")
        question_count = 0
        if questions_path.exists():
            with open(questions_path, 'r', encoding='utf-8') as f:
                questions_data = json.load(f)
                if isinstance(questions_data, list):
                    question_count = len(questions_data)
        
        return doc_count, question_count, corpus_data
    except Exception as e:
        print(f"数据加载错误: {e}")
        return 0, 0, {}

def detect_query_language(query):
    """检测查询语言"""
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', query))
    has_english = bool(re.search(r'[a-zA-Z]', query))
    
    if has_chinese and not has_english:
        return "chinese"
    elif has_english and not has_chinese:
        return "english"
    elif has_chinese and has_english:
        # 混合查询，以中文为主
        return "chinese"
    else:
        return "unknown"

def translate_chinese_to_english(chinese_query):
    """将中文查询翻译为英文搜索词"""
    search_terms = []
    translation_map = {}
    
    # 查找医疗术语
    for category, terms in MEDICAL_TERMS.items():
        for chinese, english_list in terms.items():
            if chinese in chinese_query:
                search_terms.extend(english_list)
                translation_map[chinese] = english_list[0]  # 取第一个翻译
    
    # 如果没有找到术语，提取中文字符
    if not search_terms:
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,}', chinese_query)
        search_terms = chinese_words
    
    return search_terms, translation_map

def search_chinese_query(query):
    """中文查询处理"""
    print(f"🔍 中文查询: '{query}'")
    
    # 翻译为英文搜索词
    search_terms, translation_map = translate_chinese_to_english(query)
    print(f"   翻译结果: {translation_map}")
    print(f"   搜索词: {search_terms}")
    
    results = []
    
    # 在双语知识库中搜索
    for key, knowledge in BILINGUAL_KNOWLEDGE_BASE.items():
        match_score = 0
        matched_terms = []
        
        # 检查英文关键词
        for term in search_terms:
            if term.lower() in [kw.lower() for kw in knowledge["keywords"]]:
                match_score += 2
                matched_terms.append(term)
        
        # 检查直接中文匹配
        if any(word in query for word in knowledge["keywords"] if re.search(r'[\u4e00-\u9fff]', str(word))):
            match_score += 3
        
        if match_score > 0:
            results.append({
                'title': knowledge["title_cn"],
                'content': knowledge["content_cn"],
                'source': '医疗知识库',
                'score': match_score,
                'matched_terms': matched_terms,
                'translation': translation_map
            })
    
    # 按匹配分数排序
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:3]

def search_english_query(query):
    """英文查询处理"""
    print(f"🔍 English query: '{query}'")
    
    query_lower = query.lower()
    results = []
    
    # 在双语知识库中搜索
    for key, knowledge in BILINGUAL_KNOWLEDGE_BASE.items():
        match_score = 0
        matched_terms = []
        
        # 检查英文关键词匹配
        for keyword in knowledge["keywords"]:
            if isinstance(keyword, str) and keyword.lower() in query_lower:
                match_score += 2
                matched_terms.append(keyword)
        
        # 检查标题和内容中的匹配
        if knowledge["title_en"].lower() in query_lower:
            match_score += 3
        
        if match_score > 0:
            results.append({
                'title': knowledge["title_en"],
                'content': knowledge["content_en"],
                'source': 'Medical Knowledge Base',
                'score': match_score,
                'matched_terms': matched_terms
            })
    
    # 按匹配分数排序
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:3]

def generate_chinese_answer(query, search_results):
    """生成中文回答"""
    if not search_results:
        return """
        <div class='answer-container'>
            <h4>🔍 查询结果：'{query}'</h4>
            <div class='no-results'>
                <p>暂时没有找到相关信息，您可以尝试：</p>
                <ul>
                    <li>使用更具体的医疗术语</li>
                    <li>尝试英文查询</li>
                    <li>参考常见问题：糖尿病、高血压、感冒等</li>
                </ul>
            </div>
            <div class='medical-note'>
                <p><strong>💡 重要提示：</strong></p>
                <ul>
                    <li>本系统提供的信息仅供参考</li>
                    <li>不能替代专业医疗建议</li>
                    <li>如有症状请及时就医</li>
                </ul>
            </div>
        </div>
        """.replace("{query}", query)
    
    answer_parts = []
    answer_parts.append(f"<div class='answer-container'>")
    answer_parts.append(f"<h4>🔍 查询结果：'{query}'</h4>")
    
    # 显示翻译提示
    if search_results and 'translation' in search_results[0] and search_results[0]['translation']:
        translation = search_results[0]['translation']
        if translation:
            trans_text = "，".join([f"{chi}→{eng}" for chi, eng in translation.items()])
            answer_parts.append(f"<div class='translation-hint'>🌐 术语翻译：{trans_text}</div>")
    
    for i, result in enumerate(search_results, 1):
        answer_parts.append(f"""
        <div class='search-result'>
            <div class='result-header'>
                <span class='result-number'>#{i}</span>
                <span class='result-title'>{result['title']}</span>
                <span class='result-score'>相关度：{result['score']}</span>
            </div>
            <div class='result-content'>
                <p>{result['content']}</p>
                <p class='result-source'><strong>来源：</strong> {result['source']}</p>
            </div>
        </div>
        """)
    
    answer_parts.append("""
    <div class='medical-note'>
        <p><strong>💡 重要提示：</strong></p>
        <ul>
            <li>本系统提供的信息仅供参考，不能替代专业医疗建议</li>
            <li>具体诊断和治疗请咨询执业医师</li>
            <li>如遇紧急情况，请立即拨打120或前往医院急诊</li>
            <li>保持健康生活方式是最好的疾病预防方法</li>
        </ul>
    </div>
    """)
    answer_parts.append("</div>")
    
    return "\n".join(answer_parts)

def generate_english_answer(query, search_results):
    """生成英文回答"""
    if not search_results:
        return """
        <div class='answer-container'>
            <h4>🔍 Search Results: '{query}'</h4>
            <div class='no-results'>
                <p>No relevant information found. You can try:</p>
                <ul>
                    <li>Using more specific medical terms</li>
                    <li>Trying Chinese query</li>
                    <li>Reference common topics: diabetes, hypertension, common cold, etc.</li>
                </ul>
            </div>
            <div class='medical-note'>
                <p><strong>💡 Important Note:</strong></p>
                <ul>
                    <li>Information provided is for reference only</li>
                    <li>Not a substitute for professional medical advice</li>
                    <li>Consult a doctor for symptoms</li>
                </ul>
            </div>
        </div>
        """.replace("{query}", query)
    
    answer_parts = []
    answer_parts.append(f"<div class='answer-container'>")
    answer_parts.append(f"<h4>🔍 Search Results: '{query}'</h4>")
    
    for i, result in enumerate(search_results, 1):
        # 显示匹配的关键词
        match_info = ""
        if 'matched_terms' in result and result['matched_terms']:
            match_info = f"<div class='match-info'>Matching terms: {', '.join(result['matched_terms'])}</div>"
        
        answer_parts.append(f"""
        <div class='search-result'>
            <div class='result-header'>
                <span class='result-number'>#{i}</span>
                <span class='result-title'>{result['title']}</span>
                <span class='result-score'>Relevance: {result['score']}</span>
            </div>
            {match_info}
            <div class='result-content'>
                <p>{result['content']}</p>
                <p class='result-source'><strong>Source:</strong> {result['source']}</p>
            </div>
        </div>
        """)
    
    answer_parts.append("""
    <div class='medical-note'>
        <p><strong>💡 Important Medical Disclaimer:</strong></p>
        <ul>
            <li>This information is for educational purposes only</li>
            <li>Not a substitute for professional medical advice, diagnosis, or treatment</li>
            <li>Always seek the advice of your physician with any medical questions</li>
            <li>In case of emergency, call your local emergency number immediately</li>
            <li>Maintaining a healthy lifestyle is the best prevention</li>
        </ul>
    </div>
    """)
    answer_parts.append("</div>")
    
    return "\n".join(answer_parts)

# ========== Flask 路由 ==========
@app.route('/')
def index():
    """主页"""
    doc_count, question_count, _ = get_data_counts()
    
    # 双语示例问题
    sample_questions_chinese = [
        {"text": "糖尿病的症状", "question": "糖尿病的常见症状有哪些？"},
        {"text": "高血压预防", "question": "如何预防高血压？"},
        {"text": "胃疼怎么办", "question": "胃疼应该怎么处理？"}
    ]
    
    sample_questions_english = [
        {"text": "Diabetes symptoms", "question": "What are the symptoms of diabetes?"},
        {"text": "Headache relief", "question": "How to relieve headache?"},
        {"text": "Skin cancer info", "question": "Information about skin cancer"}
    ]
    
    return render_template('index.html',
                         doc_count=doc_count,
                         question_count=question_count,
                         sample_questions_chinese=sample_questions_chinese,
                         sample_questions_english=sample_questions_english)

@app.route('/api/query-chinese', methods=['POST'])
def handle_chinese_query():
    """处理中文查询"""
    data = request.json
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({'success': False, 'error': '请输入问题'})
    
    print(f"\n=== 中文查询处理 ===")
    print(f"问题: '{question}'")
    
    # 中文搜索
    search_results = search_chinese_query(question)
    
    # 生成中文回答
    answer_html = generate_chinese_answer(question, search_results)
    
    return jsonify({
        'success': True,
        'question': question,
        'language': 'chinese',
        'answer': answer_html,
        'results_count': len(search_results),
        'has_translation': bool(search_results and 'translation' in search_results[0])
    })

@app.route('/api/query-english', methods=['POST'])
def handle_english_query():
    """处理英文查询"""
    data = request.json
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({'success': False, 'error': 'Please enter a question'})
    
    print(f"\n=== English Query Processing ===")
    print(f"Question: '{question}'")
    
    # 英文搜索
    search_results = search_english_query(question)
    
    # 生成英文回答
    answer_html = generate_english_answer(question, search_results)
    
    return jsonify({
        'success': True,
        'question': question,
        'language': 'english',
        'answer': answer_html,
        'results_count': len(search_results)
    })

@app.route('/api/auto-detect-query', methods=['POST'])
def handle_auto_query():
    """自动检测语言查询（兼容旧版）"""
    data = request.json
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({'success': False, 'error': '请输入问题/Please enter a question'})
    
    # 检测语言
    language = detect_query_language(question)
    
    if language == "chinese":
        return handle_chinese_query()
    elif language == "english":
        return handle_english_query()
    else:
        # 默认用中文处理
        return handle_chinese_query()

@app.route('/api/export-data')
def export_data():
    """导出数据为Excel文件"""
    try:
        print("=== 开始导出数据 ===")
        
        questions_path = Path("data/raw/medical_questions.json")
        
        if not questions_path.exists():
            return jsonify({'success': False, 'error': '问题集文件不存在'}), 404
        
        # 处理问题集
        with open(questions_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        questions_list = []
        if isinstance(questions, list):
            questions_list = questions
        elif isinstance(questions, dict) and 'questions' in questions:
            questions_list = questions['questions']
        else:
            questions_list = [questions]
        
        questions_data = []
        for i, q in enumerate(questions_list):
            questions_data.append({
                'Index': i + 1,
                'ID': q.get('id', f'Q{i+1}'),
                'Question': q.get('question', ''),
                'Answer': q.get('answer', ''),
                'Question Type': q.get('question_type', ''),
                'Source': q.get('source', '')
            })
        
        df_questions = pd.DataFrame(questions_data)
        
        # 添加双语知识库
        knowledge_data = []
        for key, knowledge in BILINGUAL_KNOWLEDGE_BASE.items():
            knowledge_data.append({
                'Topic': key,
                'Title (EN)': knowledge['title_en'],
                'Title (CN)': knowledge['title_cn'],
                'Keywords': ', '.join(knowledge['keywords']),
                'Content Preview (EN)': knowledge['content_en'][:200] + '...',
                'Content Preview (CN)': knowledge['content_cn'][:200] + '...'
            })
        
        df_knowledge = pd.DataFrame(knowledge_data)
        
        # 创建Excel文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            with pd.ExcelWriter(tmp.name, engine='openpyxl') as writer:
                # 写入问题集
                df_questions.to_excel(writer, sheet_name=f'Questions ({len(df_questions)})', index=False)
                
                # 写入知识库
                df_knowledge.to_excel(writer, sheet_name='Medical Knowledge', index=False)
                
                # 数据统计
                stats_data = {
                    'Category': ['Total Questions', 'Medical Topics', 'Export Time'],
                    'Value': [len(df_questions), len(df_knowledge), datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
                }
                df_stats = pd.DataFrame(stats_data)
                df_stats.to_excel(writer, sheet_name='Statistics', index=False)
            
            tmp_path = tmp.name
        
        filename = f'medical_data_{timestamp}.xlsx'
        
        return send_file(
            tmp_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        print(f"导出失败: {e}")
        return jsonify({'success': False, 'error': f'Export failed: {str(e)}'}), 500

@app.route('/api/system-info')
def system_info():
    """获取系统信息"""
    doc_count, question_count, _ = get_data_counts()
    
    return jsonify({
        'success': True,
        'system': {
            'name': 'Medical RAG System (Bilingual)',
            'version': '2.0',
            'languages': ['Chinese', 'English']
        },
        'data': {
            'corpus_documents': doc_count,
            'question_set': question_count,
            'knowledge_topics': len(BILINGUAL_KNOWLEDGE_BASE)
        },
        'endpoints': {
            'chinese_query': '/api/query-chinese',
            'english_query': '/api/query-english',
            'auto_query': '/api/auto-detect-query',
            'export_data': '/api/export-data'
        }
    })

# ========== 主程序 ==========
if __name__ == '__main__':
    print("=" * 60)
    print("🏥 医疗RAG系统 (中英文双查询版)")
    print("=" * 60)
    print("🎯 核心功能:")
    print("  • 独立中文查询接口: /api/query-chinese")
    print("  • 独立英文查询接口: /api/query-english")
    print("  • 智能医疗术语翻译")
    print("  • 双语知识库 (6个核心医疗主题)")
    print("  • 完整数据导出功能")
    print("")
    print("🌐 访问地址: http://localhost:5000")
    print("📊 系统信息: http://localhost:5000/api/system-info")
    print("📥 数据导出: http://localhost:5000/api/export-data")
    print("=" * 60)
    
    # 确保templates文件夹存在
    os.makedirs('templates', exist_ok=True)
    
    # 检查依赖
    try:
        import pandas
        import openpyxl
        print("✅ 依赖检查通过")
    except ImportError as e:
        print(f"⚠️  缺少依赖: {e}")
        print("请运行: pip install pandas openpyxl")
    
    app.run(debug=True, host='0.0.0.0', port=5000)