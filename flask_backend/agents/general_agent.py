from .base_agent import BaseAgent
from qwen_agent.agents import Assistant
from typing import List
from utils.logger import logger

class GeneralAgent(BaseAgent):
    """通用助手Agent"""
    
    def _init_agent(self) -> Assistant:
        llm_cfg = {
            'model': 'qwen-turbo-latest',
            'timeout': 30,
            'retry_count': 3,
        }
        
        return Assistant(
            llm=llm_cfg,
            name='通用助手',
            description='智能对话助手，可以回答各种问题',
            system_message=self.get_system_prompt(),
            function_list=self.get_function_list()
        )
    
    def get_system_prompt(self) -> str:
        return """我是一个智能通用助手，可以帮助用户解答各种问题。我具备以下能力：

1. 回答常识性问题
2. 提供学习和工作建议
3. 协助解决问题
4. 进行创意写作
5. 代码编程帮助
6. 翻译和语言学习
7. 数据分析和计算
8. 生活建议和规划

我会以友好、专业的态度为用户提供准确、有用的信息和建议。如果遇到我不确定的问题，我会诚实地告知用户，并尽可能提供相关的参考信息。"""
    
    def get_function_list(self) -> List[str]:
        return []  # 通用助手暂时不需要特殊工具