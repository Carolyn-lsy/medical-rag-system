# check_final.py
import json

with open('data/raw/medical_corpus.json', 'r', encoding='utf-8') as f:
    docs = json.load(f)

print(f"数据类型: {type(docs)}")

if isinstance(docs, dict):
    print(f"文档数（字典键数）: {len(docs)}")
    
    # 查看前2个键
    for i, key in enumerate(list(docs.keys())[:2]):
        doc = docs[key]
        print(f"\n=== 文档 {key} ===")
        print(f"文档类型: {type(doc)}")
        
        if isinstance(doc, dict):
            print(f"字段: {list(doc.keys())}")
            
            # 找内容
            for field in ['content', 'text', 'document', 'body', 'html']:
                if field in doc:
                    content = doc[field]
                    preview = str(content)[:300]
                    print(f"内容字段 '{field}': {preview}...")
                    
                    # 检查HTML
                    if '<' in str(content) and '>' in str(content):
                        print("格式: HTML")
                    else:
                        print("格式: 纯文本")
                    break
        else:
            # 直接是字符串
            preview = str(doc)[:300]
            print(f"内容: {preview}...")
            
            if '<' in str(doc) and '>' in str(doc):
                print("格式: HTML")
            else:
                print("格式: 纯文本")
                
elif isinstance(docs, list):
    print(f"文档数（列表长度）: {len(docs)}")
    
    for i, doc in enumerate(docs[:2]):
        print(f"\n=== 文档 {i+1} ===")
        print(f"类型: {type(doc)}")
        
        if isinstance(doc, dict):
            print(f"字段: {list(doc.keys())}")
            # ... 类似上面的处理
        else:
            preview = str(doc)[:300]
            print(f"内容: {preview}...")
else:
    print(f"未知数据类型: {type(docs)}")