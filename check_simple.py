# check_simple.py
import json

with open('data/raw/medical_corpus.json', 'r', encoding='utf-8') as f:
    docs = json.load(f)

print(f"总文档数: {len(docs)}")

for i, doc in enumerate(docs[:2]):  # 只看前2个
    print(f"\n=== 文档 {i+1} ===")
    print(f"类型: {type(doc)}")
    print(f"长度: {len(str(doc))} 字符")
    
    # 显示前500字符
    preview = str(doc)[:500]
    print(f"预览:\n{preview}")
    
    # 检查HTML标签
    if '<div' in preview or '<p>' in preview or '<html' in preview:
        print("格式: 包含HTML标签")
    else:
        print("格式: 可能是纯文本")