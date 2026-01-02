# test_app_counts.py
import json
import sys
import os
from pathlib import Path

def get_data_counts_standalone():
    """
    独立版本的数据统计函数，不依赖Flask
    """
    try:
        # 1. 获取语料库数量
        corpus_path = Path("data/raw/medical_corpus.json")
        if not corpus_path.exists():
            # 尝试其他可能的路径
            corpus_path = Path("GraphRAG-Benchmark-main/data/raw/medical_corpus.json")
            if not corpus_path.exists():
                print(f"警告: 未找到语料库文件")
                # 尝试在当前目录搜索
                possible_paths = list(Path(".").rglob("medical_corpus.json"))
                if possible_paths:
                    corpus_path = possible_paths[0]
                    print(f"  找到文件: {corpus_path}")
                else:
                    return 0, 0, []
        
        print(f"语料库文件: {corpus_path}")
        with open(corpus_path, 'r', encoding='utf-8') as f:
            corpus = json.load(f)
            # 确保corpus是列表
            if isinstance(corpus, dict):
                # 如果corpus是字典，检查是否有'documents'键
                if 'documents' in corpus:
                    doc_count = len(corpus['documents'])
                    print(f"  格式: 字典，包含 'documents' 键")
                elif 'docs' in corpus:
                    doc_count = len(corpus['docs'])
                    print(f"  格式: 字典，包含 'docs' 键")
                else:
                    doc_count = 1  # 整个字典算一个文档
                    print(f"  格式: 字典，无明确文档键")
            elif isinstance(corpus, list):
                doc_count = len(corpus)
                print(f"  格式: 列表")
            else:
                doc_count = 1
                print(f"  格式: 其他 ({type(corpus)})")
        
        # 2. 获取问题集数量
        questions_path = Path("data/raw/medical_questions.json")
        if not questions_path.exists():
            # 尝试其他可能的路径
            questions_path = Path("GraphRAG-Benchmark-main/data/raw/medical_questions.json")
            if not questions_path.exists():
                print(f"警告: 未找到问题集文件")
                # 尝试在当前目录搜索
                possible_paths = list(Path(".").rglob("medical_questions.json"))
                if possible_paths:
                    questions_path = possible_paths[0]
                    print(f"  找到文件: {questions_path}")
                else:
                    return doc_count, 0, []
        
        print(f"问题集文件: {questions_path}")
        with open(questions_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
            if isinstance(questions, dict):
                # 如果questions是字典，检查是否有'questions'键
                if 'questions' in questions:
                    question_count = len(questions['questions'])
                    questions_list = questions['questions']
                    print(f"  格式: 字典，包含 'questions' 键")
                elif 'queries' in questions:
                    question_count = len(questions['queries'])
                    questions_list = questions['queries']
                    print(f"  格式: 字典，包含 'queries' 键")
                else:
                    question_count = 1
                    questions_list = [questions]
                    print(f"  格式: 字典，无明确问题键")
            elif isinstance(questions, list):
                question_count = len(questions)
                questions_list = questions
                print(f"  格式: 列表")
            else:
                question_count = 1
                questions_list = [questions]
                print(f"  格式: 其他 ({type(questions)})")
        
        return doc_count, question_count, questions_list
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
        return 0, 0, []
    except Exception as e:
        print(f"❌ 数据加载错误: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0, []

if __name__ == "__main__":
    print("=" * 60)
    print("测试医疗RAG系统数据统计")
    print("=" * 60)
    
    # 显示当前工作目录
    print(f"当前目录: {os.getcwd()}")
    
    # 检查常见目录
    print(f"\n📁 目录检查:")
    common_dirs = [".", "data", "data/raw", "GraphRAG-Benchmark-main", "GraphRAG-Benchmark-main/data"]
    for dir_path in common_dirs:
        if os.path.exists(dir_path):
            print(f"  ✓ {dir_path}/")
        else:
            print(f"  ✗ {dir_path}/ (不存在)")
    
    # 运行测试
    print(f"\n📊 数据统计测试:")
    doc_count, question_count, questions = get_data_counts_standalone()
    
    print(f"\n✅ 统计结果:")
    print(f"  语料库文档数: {doc_count}")
    print(f"  问题集问题数: {question_count}")
    
    if questions and len(questions) > 0:
        print(f"\n📝 前5个问题示例:")
        for i in range(min(5, len(questions))):
            q = questions[i]
            if isinstance(q, dict):
                if 'question' in q:
                    question_text = q['question']
                elif 'text' in q:
                    question_text = q['text']
                elif 'query' in q:
                    question_text = q['query']
                else:
                    question_text = str(q)[:100]
                
                # 获取问题ID
                q_id = q.get('id', q.get('question_id', i+1))
                q_type = q.get('question_type', q.get('type', '未知'))
                
                print(f"  {i+1}. [ID:{q_id}] [{q_type}]")
                print(f"     {question_text[:80]}...")
            elif isinstance(q, str):
                print(f"  {i+1}. {q[:80]}...")
            else:
                print(f"  {i+1}. {str(q)[:80]}...")
    
    # 验证与之前结果的对比
    print(f"\n🔍 验证对比:")
    print(f"  之前验证脚本显示: 2篇文档, 2062个问题")
    print(f"  当前统计显示: {doc_count}篇文档, {question_count}个问题")
    
    if doc_count == 2 and question_count == 2062:
        print(f"  ✅ 与之前结果一致!")
    else:
        print(f"  ⚠️  与之前结果不一致，可能原因:")
        print(f"    1. 读取了不同的文件")
        print(f"    2. 数据格式解析方式不同")
        print(f"    3. 文件路径不正确")
    
    print(f"\n💡 建议:")
    print(f"  1. 确保 'app.py' 中的 get_data_counts() 函数使用相同的逻辑")
    print(f"  2. 检查数据文件的实际路径")
    print(f"  3. 如果数据格式复杂，可能需要调整解析逻辑")
    
    print(f"\n" + "=" * 60)