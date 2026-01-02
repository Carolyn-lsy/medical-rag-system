# src/vector_store.py
"""
向量存储模块
"""
import numpy as np
from typing import List, Dict, Any  # 添加这行
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
from src.config import Config

class VectorStore:
    """向量存储管理器"""
    
    def __init__(self, collection_name: str = None):
        self.collection_name = collection_name or Config.COLLECTION_NAME
        self.embedding_dim = Config.EMBEDDING_DIM
        self.connected = False
        self.collection = None
        self.connect()
    
    def connect(self):
        """连接到Milvus"""
        try:
            connections.connect(**Config.get_milvus_connection())
            self.connected = True
            print(f"✅ 连接到Milvus: {Config.MILVUS_HOST}:{Config.MILVUS_PORT}")
        except Exception as e:
            print(f"❌ Milvus连接失败: {e}")
            self.connected = False
    
    def create_collection(self) -> Collection:
        """创建集合（如果不存在）"""
        if not self.connected:
            print("❌ 未连接到Milvus")
            return None
        
        # 检查集合是否已存在
        if utility.has_collection(self.collection_name):
            print(f"✅ 集合 '{self.collection_name}' 已存在")
            self.collection = Collection(self.collection_name)
            return self.collection
        
        print(f"🔄 创建集合: {self.collection_name}")
        
        # 定义字段
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=200),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim),
            FieldSchema(name="metadata", dtype=DataType.JSON)
        ]
        
        # 创建schema
        schema = CollectionSchema(fields, description="医疗文档向量存储")
        
        # 创建集合
        self.collection = Collection(
            name=self.collection_name,
            schema=schema,
            using='default',
            shards_num=2
        )
        
        print(f"✅ 成功创建集合: {self.collection_name}")
        return self.collection
    
    def insert_documents(self, documents: List[Dict], embeddings: List[List[float]]) -> bool:
        """插入文档和向量"""
        if not self.connected or not self.collection:
            print("❌ 集合未初始化")
            return False
        
        # 准备数据
        chunk_ids = [doc['chunk_id'] for doc in documents]
        texts = [doc['text'] for doc in documents]
        metadatas = [{
            'original_id': doc['original_id'],
            'chunk_index': doc['chunk_index'],
            'total_chunks': doc['total_chunks'],
            'source': doc['source'],
            'title': doc['title']
        } for doc in documents]
        
        # 插入数据
        data = [
            chunk_ids,      # chunk_id 字段
            texts,          # text 字段
            embeddings,     # embedding 字段
            metadatas       # metadata 字段
        ]
        
        try:
            insert_result = self.collection.insert(data)
            print(f"✅ 插入了 {len(documents)} 个文档块")
            return insert_result
        except Exception as e:
            print(f"❌ 插入失败: {e}")
            return False
    
    def create_index(self, index_type: str = "IVF_FLAT", metric_type: str = "L2", nlist: int = 128) -> bool:
        """创建索引以加速搜索"""
        if not self.collection:
            print("❌ 集合未初始化")
            return False
        
        index_params = {
            "metric_type": metric_type,
            "index_type": index_type,
            "params": {"nlist": nlist}
        }
        
        try:
            self.collection.create_index("embedding", index_params)
            print(f"✅ 在 'embedding' 字段上创建了 {index_type} 索引")
            return True
        except Exception as e:
            print(f"❌ 创建索引失败: {e}")
            return False
    
    def search(self, query_embedding: List[float], top_k: int = None) -> List[Dict]:
        """搜索相似文档"""
        if not self.collection:
            print("❌ 集合未初始化")
            return []
        
        top_k = top_k or Config.TOP_K
        
        # 确保集合已加载
        self.collection.load()
        
        # 搜索参数
        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10}
        }
        
        try:
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["chunk_id", "text", "metadata"]
            )
            
            # 格式化结果
            formatted_results = []
            for hits in results:
                for hit in hits:
                    formatted_results.append({
                        'chunk_id': hit.entity.get('chunk_id'),
                        'text': hit.entity.get('text'),
                        'metadata': hit.entity.get('metadata'),
                        'score': hit.score,
                        'distance': hit.distance
                    })
            
            return formatted_results
            
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
            return []