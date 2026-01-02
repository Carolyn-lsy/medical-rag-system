# examine_data.py - 查看和导出数据库内容
import json
import pandas as pd
from pathlib import Path

def examine_and_export_data():
    """查看和导出数据库内容"""
    print("=== 医疗RAG数据查看与导出 ===")
    
    # 1. 查看语料库
    print("\n1. 语料库分析:")
    corpus_path = Path("data/raw/medical_corpus.json")
    if corpus_path.exists():
        with open(corpus_path, 'r', encoding='utf-8') as f:
            corpus = json.load(f)
        
        print(f"   文件: {corpus_path}")
        print(f"   数据类型: {type(corpus)}")
        
        if isinstance(corpus, dict):
            print(f"   字典键: {list(corpus.keys())}")
            if 'corpus_name' in corpus:
                print(f"   语料库名称: {corpus['corpus_name']}")
            if 'context' in corpus:
                content = corpus['context']
                print(f"   内容长度: {len(content)} 字符")
                print(f"   内容预览:")
                print(f"   {content[:200]}...")
                
                # 分析内容结构
                sentences = content.split('. ')
                print(f"   句子数量: {len(sentences)}")
                
                # 提取关键主题
                medical_keywords = ['癌症', '治疗', '症状', '预防', '诊断', '细胞', '皮肤']
                found_keywords = [kw for kw in medical_keywords if kw in content]
                if found_keywords:
                    print(f"   医疗关键词: {found_keywords[:5]}")
    else:
        print(f"   ❌ 文件不存在: {corpus_path}")
    
    # 2. 查看问题集
    print("\n2. 问题集分析:")
    questions_path = Path("data/raw/medical_questions.json")
    if questions_path.exists():
        with open(questions_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        print(f"   文件: {questions_path}")
        print(f"   数据类型: {type(questions)}")
        
        if isinstance(questions, list):
            print(f"   问题总数: {len(questions)}")
            
            # 统计问题类型
            question_types = {}
            sources = {}
            
            for i, q in enumerate(questions[:100]):  # 只分析前100个
                q_type = q.get('question_type', '未知')
                source = q.get('source', '未知')
                
                question_types[q_type] = question_types.get(q_type, 0) + 1
                sources[source] = sources.get(source, 0) + 1
            
            print(f"   问题类型分布:")
            for q_type, count in question_types.items():
                percentage = (count / min(100, len(questions))) * 100
                print(f"     {q_type}: {count} ({percentage:.1f}%)")
            
            print(f"   来源分布:")
            for source, count in sources.items():
                percentage = (count / min(100, len(questions))) * 100
                print(f"     {source}: {count} ({percentage:.1f}%)")
            
            # 显示示例问题
            print(f"\n   示例问题 (前5个):")
            for i, q in enumerate(questions[:5]):
                question_text = q.get('question', '')
                answer = q.get('answer', '')
                print(f"   {i+1}. 问题: {question_text[:80]}...")
                if answer:
                    print(f"      答案: {answer[:80]}...")
                print()
    else:
        print(f"   ❌ 文件不存在: {questions_path}")
    
    # 3. 导出为Excel
    print("\n3. 导出为Excel文件...")
    try:
        with pd.ExcelWriter('medical_data_analysis.xlsx', engine='openpyxl') as writer:
            # 导出语料库信息
            corpus_data = []
            if corpus_path.exists():
                with open(corpus_path, 'r', encoding='utf-8') as f:
                    corpus = json.load(f)
                
                if isinstance(corpus, dict) and 'context' in corpus:
                    # 分割长文本为段落
                    context = corpus['context']
                    paragraphs = [p.strip() for p in context.split('\n\n') if p.strip()]
                    
                    for i, para in enumerate(paragraphs[:50]):  # 最多50个段落
                        corpus_data.append({
                            '段落ID': f'para_{i+1:03d}',
                            '语料库名称': corpus.get('corpus_name', '未知'),
                            '内容': para[:500] + '...' if len(para) > 500 else para,
                            '字符数': len(para)
                        })
                
                df_corpus = pd.DataFrame(corpus_data)
                df_corpus.to_excel(writer, sheet_name='语料库内容', index=False)
            
            # 导出问题集信息
            questions_data = []
            if questions_path.exists():
                with open(questions_path, 'r', encoding='utf-8') as f:
                    questions = json.load(f)
                
                if isinstance(questions, list):
                    for i, q in enumerate(questions[:1000]):  # 最多1000个问题
                        questions_data.append({
                            '问题ID': q.get('id', f'q_{i+1:04d}'),
                            '问题': q.get('question', ''),
                            '答案摘要': q.get('answer', '')[:200] if q.get('answer') else '',
                            '问题类型': q.get('question_type', '未知'),
                            '来源': q.get('source', '未知'),
                            '证据': q.get('evidence', '')[:100] if q.get('evidence') else ''
                        })
                
                df_questions = pd.DataFrame(questions_data)
                df_questions.to_excel(writer, sheet_name='问题集', index=False)
            
            # 导出统计信息
            stats_data = []
            if corpus_path.exists():
                with open(corpus_path, 'r', encoding='utf-8') as f:
                    corpus = json.load(f)
                if isinstance(corpus, dict) and 'context' in corpus:
                    context = corpus['context']
                    stats_data.append({
                        '统计项': '语料库',
                        '值': '1篇文档',
                        '详细信息': f'内容长度: {len(context)} 字符'
                    })
            
            if questions_path.exists():
                with open(questions_path, 'r', encoding='utf-8') as f:
                    questions = json.load(f)
                if isinstance(questions, list):
                    stats_data.append({
                        '统计项': '问题集',
                        '值': f'{len(questions)} 个问题',
                        '详细信息': '详细问题见"问题集"工作表'
                    })
            
            df_stats = pd.DataFrame(stats_data)
            df_stats.to_excel(writer, sheet_name='数据统计', index=False)
        
        print(f"   ✅ 已导出到: medical_data_analysis.xlsx")
        print(f"   文件包含: 语料库内容、问题集、数据统计 三个工作表")
        
    except Exception as e:
        print(f"   ❌ 导出失败: {e}")
    
    print("\n=== 完成 ===")
    print("使用说明:")
    print("1. 运行 'python flask_app.py' 启动网页应用")
    print("2. 访问 http://localhost:5000 使用系统")
    print("3. 点击侧边栏的'导出数据到Excel'按钮下载数据")
    print("4. 或直接查看生成的 medical_data_analysis.xlsx 文件")

if __name__ == "__main__":
    examine_and_export_data()