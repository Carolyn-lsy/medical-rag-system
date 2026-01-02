# src/answer_generator.py
"""
答案生成模块
"""
from typing import List, Dict, Any  # 添加这行
from src.config import Config

class AnswerGenerator:
    """答案生成器"""
    
    def __init__(self):
        print("初始化 AnswerGenerator")
    
    def format_context(self, search_results: List[Dict]) -> str:
        """格式化检索到的上下文"""
        if not search_results:
            return "未找到相关上下文。"
        
        context_parts = []
        for i, result in enumerate(search_results[:Config.TOP_K]):
            text = result.get('text', '')
            source = result.get('metadata', {}).get('source', '未知来源')
            title = result.get('metadata', {}).get('title', '')
            
            context_part = f"【参考{i+1}】"
            if title:
                context_part += f" 标题：{title}"
            if source:
                context_part += f" 来源：{source}"
            context_part += f"\n{text}\n"
            
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    def generate_answer(self, question: str, context: str) -> str:
        """生成答案（基础版本）"""
        # 这是一个简单的模板生成
        # 实际项目中，这里会集成LLM（如ChatGLM、GPT等）
        
        prompt = f"""基于以下医疗知识，请回答问题。

问题：{question}

相关医疗知识：
{context}

请基于以上知识，给出专业、准确的回答："""
        
        # 简单模拟回答（实际应该调用LLM）
        answer = f"""根据相关医疗知识，关于"{question}"：

{context}

（注：这是一个基于检索的答案。完整的RAG系统会在这里集成语言模型生成更自然的回答。）"""
        
        return answer
    
    def simple_answer(self, question: str, search_results: List[Dict]) -> Dict[str, Any]:
        """生成简单答案"""
        context = self.format_context(search_results)
        answer = self.generate_answer(question, context)
        
        return {
            'question': question,
            'context': context,
            'answer': answer,
            'sources': [r.get('metadata', {}) for r in search_results]
        }