# check_doc_format.py
import json

with open('data/raw/medical_corpus.json', 'r', encoding='utf-8') as f:
    docs = json.load(f)

print(f"总文档数: {len(docs)}")
print("\n=== 文档结构分析 ===")

for i, doc in enumerate(docs):
    print(f"\n文档 {i+1}:")
    print(f"  类型: {type(doc)}")
    
    if isinstance(doc, dict):
        print(f"  字段: {list(doc.keys())}")
        
        # 查看内容字段
        content_fields = ['content', 'text', 'document', 'body', 'html']
        for field in content_fields:
            if field in doc:
                content = doc[field]
                preview = str(content)[:200].replace('\n', ' ')
                print(f"  内容字段 '{field}': {preview}...")
                
                # 检查是否是HTML
                if '<' in str(content) and '>' in str(content):
                    print(f"    格式: HTML")
                else:
                    print(f"    格式: 纯文本")
                break
    else:
        # 如果是字符串
        preview = str(doc)[:300].replace('\n', ' ')
        print(f"  内容: {preview}...")
        
        # 检查是否是HTML
        if '<' in str(doc) and '>' in str(doc):
            print(f"  格式: HTML")
        else:
            print(f"  格式: 纯文本")