import sys
import subprocess
import json
import urllib.request
import urllib.error

print("="*60)
print("Milvus-Lite 安装诊断")
print("="*60)
print(f"Python 版本: {sys.version}")
print(f"平台: {sys.platform}")

# 1. 检查 pip 版本
try:
    result = subprocess.run([sys.executable, '-m', 'pip', '--version'], 
                          capture_output=True, text=True)
    print(f"Pip 版本: {result.stdout.strip()}")
except:
    pass

# 2. 尝试从 PyPI 获取包信息
print("\n尝试获取 milvus-lite 包信息...")
try:
    url = 'https://pypi.org/pypi/milvus-lite/json'
    with urllib.request.urlopen(url) as response:
        data = json.load(response)
        
    print(f"✅ 找到包: milvus-lite")
    print(f"最新版本: {data['info']['version']}")
    print(f"描述: {data['info']['summary']}")
    
    # 显示所有版本
    versions = list(data['releases'].keys())
    print(f"\n可用版本 ({len(versions)} 个):")
    for v in versions[-5:]:  # 显示最近5个版本
        print(f"  - {v}")
        
    # 检查最新版本的文件
    latest = versions[-1]
    print(f"\n版本 {latest} 的文件:")
    for file in data['releases'][latest]:
        print(f"  - {file['filename']}")
        if 'win' in file['filename'].lower():
            print(f"    ✅ 这个可能是 Windows 版本")
            
except urllib.error.HTTPError as e:
    if e.code == 404:
        print("❌ milvus-lite 包不存在于 PyPI")
    else:
        print(f"❌ HTTP 错误: {e}")
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*60)
print("建议:")
print("1. 如果包不存在，可能需要联系老师获取安装包")
print("2. 或者使用 'milvus' 而不是 'milvus-lite'")
print("3. 或者使用 Docker 运行 Milvus")
print("="*60)
