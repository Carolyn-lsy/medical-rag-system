# examine_data_structure.py
import json
from pathlib import Path

def examine_corpus_structure():
    """查看语料库文件的实际结构"""
    corpus_path = Path("data/raw/medical_corpus.json")
    
    print("=== 查看语料库文件结构 ===")
    print(f"文件: {corpus_path}")
    
    with open(corpus_path, 'r', encoding='utf-8') as f:
        corpus = json.load(f)
    
    print(f"\n数据类型: {type(corpus)}")
    
    if isinstance(corpus, dict):
        print(f"字典键: {list(corpus.keys())}")
        print(f"\n字典内容预览:")
        
        for key, value in corpus.items():
            print(f"\n键 '{key}':")
            print(f"  类型: {type(value)}")
            
            if isinstance(value, list):
                print(f"  列表长度: {len(value)}")
                if len(value) > 0:
                    print(f"  第一个元素类型: {type(value[0])}")
                    if isinstance(value[0], dict):
                        print(f"  第一个元素的键: {list(value[0].keys())[:5]}...")
                    else:
                        print(f"  第一个元素: {str(value[0])[:100]}...")
            elif isinstance(value, dict):
                print(f"  字典键: {list(value.keys())[:5]}...")
            else:
                print(f"  值: {str(value)[:100]}...")
    
    elif isinstance(corpus, list):
        print(f"列表长度: {len(corpus)}")
        if len(corpus) > 0:
            print(f"第一个元素类型: {type(corpus[0])}")
            if isinstance(corpus[0], dict):
                print(f"第一个元素的键: {list(corpus[0].keys())[:5]}...")

def examine_questions_structure():
    """查看问题集文件的实际结构"""
    questions_path = Path("data/raw/medical_questions.json")
    
    print("\n=== 查看问题集文件结构 ===")
    print(f"文件: {questions_path}")
    
    with open(questions_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    print(f"\n数据类型: {type(questions)}")
    
    if isinstance(questions, list):
        print(f"列表长度: {len(questions)}")
        if len(questions) > 0:
            print(f"第一个问题结构:")
            for key, value in questions[0].items():
                print(f"  '{key}': {type(value)} - {str(value)[:80]}...")
    
    elif isinstance(questions, dict):
        print(f"字典键: {list(questions.keys())}")

if __name__ == "__main__":
    examine_corpus_structure()
    examine_questions_structure()