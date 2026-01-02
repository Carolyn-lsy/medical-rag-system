# test_milvus_connect.py
from pymilvus import connections, utility
import time

print("=== 测试 Milvus 连接 ===")

try:
    # 连接到Docker中的Milvus
    connections.connect(
        alias="default",
        host='localhost',   # Docker服务在本地
        port='19530'        # Milvus默认端口
    )
    print("✅ 连接建立成功")
    
    # 获取服务器版本
    version = utility.get_server_version()
    print(f"✅ Milvus 版本: {version}")
    
    # 列出已有集合（刚开始应该是空的）
    collections = utility.list_collections()
    print(f"✅ 现有集合: {collections}")
    
    print("\n🎉 Milvus 连接测试通过！可以开始使用向量数据库了。")
    
except Exception as e:
    print(f"❌ 连接失败: {e}")
    print("\n可能的原因：")
    print("1. Milvus容器未启动 - 运行 'docker ps' 检查")
    print("2. 端口冲突 - 确保19530端口可用")
    print("3. 网络问题 - 等待几秒再试")