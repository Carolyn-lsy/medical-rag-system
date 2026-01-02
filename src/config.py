# src/config.py
"""
配置文件
"""
from typing import List, Dict, Any  # 添加这行

class Config:
    """配置类"""
    
    # ========== Milvus 配置 ==========
    MILVUS_HOST = 'localhost'
    MILVUS_PORT = '19530'
    
    # ========== 向量模型配置 ==========
    # 嵌入模型（用于将文本转为向量）
    EMBEDDING_MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
    EMBEDDING_DIM = 384  # 该模型的向量维度
    
    # ========== 文本处理配置 ==========
    CHUNK_SIZE = 500     # 文本分块大小（字符数）
    CHUNK_OVERLAP = 50   # 块之间的重叠字符数
    
    # ========== 检索配置 ==========
    TOP_K = 3                    # 检索返回的最相关文档数
    SIMILARITY_THRESHOLD = 0.7   # 相似度阈值
    
    # ========== 集合配置 ==========
    COLLECTION_NAME = "medical_documents"  # Milvus集合名称
    
    # ========== 生成模型配置 ==========
    # 如果需要本地LLM，可以配置这里
    # GENERATION_MODEL = "chatglm2-6b"
    
    @classmethod
    def get_milvus_connection(cls) -> Dict[str, str]:
        """获取Milvus连接配置"""
        return {
            'host': cls.MILVUS_HOST,
            'port': cls.MILVUS_PORT,
            'alias': 'default'
        }
    
    @classmethod
    def get_collection_params(cls) -> Dict[str, Any]:
        """获取集合配置"""
        return {
            'collection_name': cls.COLLECTION_NAME,
            'embedding_dim': cls.EMBEDDING_DIM
        }