# src/data_loader.py
"""
数据加载模块
"""
import json
from typing import List, Dict, Any
from src.config import Config

class MedicalDataLoader:
    """医疗数据加载器"""
    
    def __init__(self):
        print("初始化 MedicalDataLoader")
    
    def load_from_json(self, filepath: str) -> List[Dict[str, Any]]:
        """从JSON文件加载数据"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✅ 从 {filepath} 加载了 {len(data)} 条记录")
            return data
        except Exception as e:
            print(f"❌ 加载数据失败: {e}")
            return []
    
    def load_medical_corpus(self, corpus_path: str) -> List[Dict[str, Any]]:
        """加载医疗语料库"""
        return self.load_from_json(corpus_path)
    
    def load_medical_questions(self, questions_path: str) -> List[Dict[str, Any]]:
        """加载医疗问题集"""
        return self.load_from_json(questions_path)