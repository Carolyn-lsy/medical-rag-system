# test_milvus_final.py
from pymilvus import connections, utility
import time

print("=" * 50)
print("🧪 Milvus 最终连接测试")
print("=" * 50)

try:
    # 连接
    print("1. 尝试连接到 Milvus...")
    connections.connect(
        alias="default",
        host='localhost',
        port='19530'
    )
    print("   ✅ 连接成功")
    
    # 获取版本
    print("2. 获取服务器版本...")
    version = utility.get_server_version()
    print(f"   ✅ Milvus 版本: {version}")
    
    # 检查健康状态
    print("3. 检查服务状态...")
    # 简单查询测试
    collections = utility.list_collections()
    print(f"   ✅ 服务正常，现有集合: {collections}")
    
    print("\n" + "=" * 50)
    print("🎉 Milvus 已就绪！可以运行你的医疗RAG系统了！")
    print("=" * 50)
    
    # 显示启动命令
    print("\n📋 下一步：")
    print("1. 激活虚拟环境: .rag_venv\\Scripts\\activate")
    print("2. 启动应用: streamlit run app.py")
    print("3. 在浏览器打开显示的URL（通常是 http://localhost:8501）")
    
except Exception as e:
    print(f"\n❌ 测试失败: {e}")
    print("\n🔧 故障排除：")
    print("1. 检查容器状态: docker ps")
    print("2. 查看容器日志: docker logs milvus-standalone")
    print("3. 等待更长时间: Start-Sleep -Seconds 60")
    print("4. 重启容器: docker restart milvus-standalone")