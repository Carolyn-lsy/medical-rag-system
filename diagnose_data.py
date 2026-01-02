# diagnose_data.py
import json
from pathlib import Path

print("=== 数据诊断 ===")

# 检查语料库
corpus_path = Path("data/raw/medical_corpus.json")
if corpus_path.exists():
    with open(corpus_path, 'r', encoding='utf-8') as f:
        corpus = json.load(f)
    
    print(f"📁 语料库文件: {corpus_path}")
    print(f"📊 数据类型: {type(corpus)}")
    
    if isinstance(corpus, dict):
        print(f"📋 字典键: {list(corpus.keys())}")
        if 'context' in corpus:
            print(f"📏 context长度: {len(corpus['context'])}")
            print(f"📝 context前500字符: {corpus['context'][:500]}...")
    elif isinstance(corpus, list):
        print(f"📋 列表长度: {len(corpus)}")
        if corpus:
            print(f"📋 第一条数据: {corpus[0]}")
else:
    print(f"❌ 语料库文件不存在: {corpus_path}")

print("\n=== 诊断完成 ===")