# verify_data.py
import json
from pathlib import Path

def verify_data():
    """验证数据是否正确复制"""
    print("=== 验证医疗数据 ===\n")
    
    # 检查文件是否存在
    corpus_path = Path("data/raw/medical_corpus.json")
    questions_path = Path("data/raw/medical_questions.json")
    
    print("1. 检查文件是否存在:")
    print(f"   语料库: {corpus_path} → {'✅ 存在' if corpus_path.exists() else '❌ 不存在'}")
    print(f"   问题集: {questions_path} → {'✅ 存在' if questions_path.exists() else '❌ 不存在'}")
    
    if not corpus_path.exists() or not questions_path.exists():
        print("\n❌ 文件缺失，请先复制数据")
        return False
    
    print("\n2. 分析语料库数据:")
    try:
        with open(corpus_path, 'r', encoding='utf-8') as f:
            corpus = json.load(f)
        
        print(f"   ✅ 成功读取")
        print(f"   文档数量: {len(corpus)}")
        
        if corpus and isinstance(corpus, list):
            first_doc = corpus[0]
            print(f"\n   第一条文档结构:")
            print(f"     类型: {type(first_doc)}")
            print(f"     键: {list(first_doc.keys())}")
            
            # 查看内容
            content_keys = ['content', 'text', 'document', 'body']
            content = None
            for key in content_keys:
                if key in first_doc:
                    content = first_doc[key]
                    print(f"     内容键: {key}")
                    break
            
            if content:
                preview = str(content)[:300].replace('\n', ' ')
                print(f"\n     内容预览:")
                print(f"     {preview}...")
                
                # 检查格式
                if '<' in str(content) and '>' in str(content):
                    print(f"\n     📄 检测到HTML格式")
                else:
                    print(f"\n     📝 纯文本格式")
            else:
                print(f"\n     内容: {str(first_doc)[:200]}...")
    except Exception as e:
        print(f"   ❌ 读取失败: {e}")
        return False
    
    print("\n3. 分析问题集数据:")
    try:
        with open(questions_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        print(f"   ✅ 成功读取")
        print(f"   问题数量: {len(questions)}")
        
        if questions:
            first_q = questions[0]
            print(f"\n   第一个问题:")
            
            if isinstance(first_q, dict):
                print(f"     类型: 字典")
                print(f"     键: {list(first_q.keys())}")
                
                # 显示问题和答案
                if 'question' in first_q:
                    print(f"     问题: {first_q['question'][:100]}...")
                if 'answer' in first_q:
                    print(f"     答案: {first_q['answer'][:100]}...")
            else:
                print(f"     类型: {type(first_q)}")
                print(f"     内容: {str(first_q)[:100]}...")
    except Exception as e:
        print(f"   ❌ 读取失败: {e}")
        return False
    
    print("\n" + "="*50)
    print("🎉 数据验证通过！可以开始构建RAG系统了。")
    return True

if __name__ == "__main__":
    verify_data()