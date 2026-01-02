import json
import pandas as pd
from pathlib import Path

# TODO: 请将这里的路径修改为你实际找到的 medical_corpus.json 的路径
corpus_file_path = Path("./data/raw/medical_corpus.json")  # 示例路径，请修改

try:
    with open(corpus_file_path, 'r', encoding='utf-8') as f:
        corpus_data = json.load(f)
    
    print(f"✅ 成功加载语料库文件，来自: {corpus_file_path}")
    print(f"📊 数据格式: {type(corpus_data)}")
    
    # 处理语料库数据
    if isinstance(corpus_data, list):
        df = pd.DataFrame(corpus_data)
        print(f"📄 文档数量: {len(df)} 篇")
    elif isinstance(corpus_data, dict):
        # 语料库可能是字典结构，例如 {"doc1": "内容1", "doc2": "内容2"}
        # 将其转换为每行一个文档的DataFrame
        df = pd.DataFrame(list(corpus_data.items()), columns=['文档ID', '内容'])
        print(f"📄 文档数量: {len(df)} 篇 (从字典转换而来)")
    else:
        print("❌ 无法识别的数据格式")
        exit(1)
    
    # 导出到Excel
    output_file = "medical_corpus_exported.xlsx"
    df.to_excel(output_file, index=False, engine='openpyxl')
    print(f"🎉 成功导出！文件已保存为: {output_file}")
    print(f"📋 包含列: {list(df.columns)}")
    
except FileNotFoundError:
    print(f"❌ 文件未找到: {corpus_file_path}")
    print("请检查文件路径，并使用第一步中的 find 命令确认位置。")
except json.JSONDecodeError as e:
    print(f"❌ JSON 文件格式错误: {e}")
except Exception as e:
    print(f"❌ 发生未知错误: {e}")