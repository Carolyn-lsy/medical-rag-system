# test_import.py
import sys

print("测试不同的 Milvus 导入方式...")

# 测试1: 尝试 milvus 包
try:
    from milvus import default_server
    print("✅ 成功: from milvus import default_server")
    print("   这说明需要安装 'milvus' 包")
except ImportError as e:
    print(f"❌ from milvus import default_server: {e}")

# 测试2: 尝试 pymilvus (官方 Python 客户端)
try:
    import pymilvus
    print(f"✅ pymilvus 版本: {pymilvus.__version__}")
    print("   这是 Milvus 的官方 Python 客户端")
except ImportError as e:
    print(f"❌ pymilvus: {e}")

# 测试3: 尝试 milvus_lite (轻量版)
try:
    import milvus_lite
    print("✅ 成功导入 milvus_lite")
    print("   这是 Milvus 的轻量版本")
except ImportError as e:
    print(f"❌ milvus_lite: {e}")

print("\n测试完成。")
print("推荐使用 pymilvus 作为 Milvus 的 Python 客户端。")