# src/preprocessor.py
"""
文本预处理模块
"""
import re
from typing import List, Dict, Any
from src.config import Config

class TextPreprocessor:
    """文本预处理器"""
    
    def __init__(self):
        print("初始化 TextPreprocessor")
    
    def clean_html(self, html_text: str) -> str:
        """清理HTML标签"""
        if not html_text:
            return ""
        
        # 简单的HTML标签清理
        clean_text = re.sub(r'<[^>]+>', '', html_text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        return clean_text
    
    def split_into_chunks(self, text: str, chunk_size: int = None, 
                         overlap: int = None) -> List[str]:
        """将长文本分割成块"""
        if not text:
            return []
        
        chunk_size = chunk_size or Config.CHUNK_SIZE
        overlap = overlap or Config.CHUNK_OVERLAP
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            
            # 如果没到结尾，尽量在句子边界处分割
            if end < text_length:
                # 寻找最近的句子结束符
                for punct in ['。', '.', '!', '?', '；', ';', '\n']:
                    last_punct = text.rfind(punct, start, end)
                    if last_punct != -1:
                        end = last_punct + 1  # 包含标点
                        break
            
            chunk = text[start:end].strip()
            if chunk:  # 只添加非空块
                chunks.append(chunk)
            
            # 移动起始位置，考虑重叠
            start = end - overlap if end - overlap > start else end
        
        print(f"✅ 将文本分割成 {len(chunks)} 个块")
        return chunks
    
    def process_document(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """处理单个文档"""
        text = document.get('content', '') or document.get('text', '')
        
        # 清理HTML
        clean_text = self.clean_html(text)
        
        # 分割成块
        chunks = self.split_into_chunks(clean_text)
        
        # 为每个块添加元数据
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            processed_chunks.append({
                'original_id': document.get('id', f'unknown_{i}'),
                'chunk_id': f"{document.get('id', 'doc')}_{i}",
                'text': chunk,
                'chunk_index': i,
                'total_chunks': len(chunks),
                'source': document.get('source', 'unknown'),
                'title': document.get('title', '')
            })
        
        return processed_chunks