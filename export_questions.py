import json
import pandas as pd
from pathlib import Path

# TODO: 请将这里的路径修改为你实际找到的 medical_questions.json 的路径
questions_file_path = Path("./data/raw/medical_questions.json")  # 示例路径，请修改

try:
    with open(questions_file_path, 'r', encoding='utf-8') as f:
        questions_data = json.load(f)
    
    print(f"✅ 成功加载问题集文件，来自: {questions_file_path}")
    print(f"📊 数据格式: {type(questions_data)}")
    
    # 将数据转换为Pandas DataFrame（适用于列表或字典格式）
    if isinstance(questions_data, list):
        df = pd.DataFrame(questions_data)
        print(f"📈 问题数量: {len(df)} 条")
    elif isinstance(questions_data, dict):
        # 如果数据是字典，且字典的某个键对应问题列表
        # 这里需要根据实际结构调整，常见的是字典内有一个 'questions' 键
        for key in ['questions', 'data', 'items']:
            if key in questions_data and isinstance(questions_data[key], list):
                df = pd.DataFrame(questions_data[key])
                print(f"📈 问题数量: {len(df)} 条 (来自字典键: '{key}')")
                break
        else:
            # 如果字典没有明确的列表键，则将整个字典转换
            df = pd.DataFrame([questions_data])
            print("📝 数据为单条字典，已转换为单行DataFrame。")
    else:
        print("❌ 无法识别的数据格式")
        exit(1)
    
    # 导出到Excel
    output_file = "medical_questions_exported.xlsx"
    df.to_excel(output_file, index=False, engine='openpyxl')
    print(f"🎉 成功导出！文件已保存为: {output_file}")
    print(f"📋 包含列: {list(df.columns)}")
    
except FileNotFoundError:
    print(f"❌ 文件未找到: {questions_file_path}")
    print("请检查文件路径，并使用第一步中的 find 命令确认位置。")
except json.JSONDecodeError as e:
    print(f"❌ JSON 文件格式错误: {e}")
except Exception as e:
    print(f"❌ 发生未知错误: {e}")