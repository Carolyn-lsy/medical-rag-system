# test_connection.py
"""
测试Milvus连接和模块导入
"""
import traceback

def test_milvus_connection():
    """测试Milvus连接"""
    print("=== 测试Milvus连接 ===")
    try:
        from pymilvus import connections, utility
        
        # 连接到Milvus
        connections.connect(
            alias="default",
            host='localhost',
            port='19530'
        )
        print("✅ Milvus连接成功！")
        
        # 获取服务器版本
        version = utility.get_server_version()
        print(f"✅ Milvus服务器版本: {version}")
        
        # 列出集合
        collections = utility.list_collections()
        print(f"✅ 当前集合数量: {len(collections)}")
        
        if collections:
            print(f"✅ 集合列表: {collections}")
        
        connections.disconnect("default")
        return True
        
    except Exception as e:
        print(f"❌ Milvus连接失败: {e}")
        traceback.print_exc()
        return False

def test_module_imports():
    """测试所有模块导入"""
    print("\n=== 测试模块导入 ===")
    
    modules_to_test = [
        ('src.config', 'Config'),
        ('src.data_loader', 'MedicalDataLoader'),
        ('src.preprocessor', 'TextPreprocessor'),
        ('src.vector_store', 'VectorStore'),
        ('src.answer_generator', 'AnswerGenerator')
    ]
    
    all_passed = True
    
    for module_name, class_name in modules_to_test:
        try:
            exec(f'from {module_name} import {class_name}')
            print(f"✅ {module_name} 导入成功")
        except ImportError as e:
            print(f"❌ {module_name} 导入失败: {e}")
            all_passed = False
        except Exception as e:
            print(f"⚠️  {module_name} 其他错误: {e}")
            all_passed = False
    
    return all_passed

if __name__ == "__main__":
    print("医疗RAG系统环境测试")
    print("=" * 50)
    
    # 测试连接
    conn_ok = test_milvus_connection()
    
    # 测试导入
    import_ok = test_module_imports()
    
    print("\n" + "=" * 50)
    if conn_ok and import_ok:
        print("🎉 所有测试通过！可以运行app.py了")
    else:
        print("⚠️  有些测试未通过，请检查以上错误")
    
    # 提示如何运行
    print("\n下一步:")
    if conn_ok and import_ok:
        print("运行: python app.py")
    else:
        print("1. 确保src/__init__.py文件已创建")
        print("2. 检查各模块文件是否存在")
        print("3. 重新运行此测试")