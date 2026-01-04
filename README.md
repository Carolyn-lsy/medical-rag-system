# 🏥 双语医疗RAG问答系统

基于Flask的医疗检索增强生成系统，支持中英文双语问答。

## ✨ 功能特性
- 🌐 中英文任意语言提问
- 🏥 专业的医疗知识库
- 🔍 智能关键词匹配
- 📊 数据统计与导出
- ⚡ 优化的翻译系统（避免卡顿）

## 🚀 快速开始
1. 安装依赖：`pip install -r requirements.txt`
2. 启动服务：`python flask_app.py`
3. 访问：`http://localhost:5000`

## 📁 项目结构
- `flask_app.py` - Flask后端服务器
- `index.html` - 前端Web界面
- `data/raw/` - 医疗数据文件
- `medical_terms.json` - 医学术语词典

## 🔧 技术栈
- 后端：Flask (Python)
- 前端：HTML5 + CSS3 + JavaScript
- 翻译：translate库
- 数据处理：pandas