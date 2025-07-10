from abc import ABC, abstractmethod
from typing import List, Dict, Any
import os
import dashscope
from qwen_agent.agents import Assistant
from utils.logger import logger

class BaseAgent(ABC):
    """Agent基类，定义所有Agent的通用接口"""
    
    def __init__(self, agent_id: str, user_id: str):
        self.agent_id = agent_id
        self.user_id = user_id
        self.session_id = f"{user_id}_{agent_id}"
        self.messages = []  # 会话历史
        
        # 配置DashScope
        dashscope.api_key = os.getenv('ALIBABA_API_KEY', '')
        dashscope.timeout = 30
        
        # 初始化qwen-agent
        self.bot = self._init_agent()
    
    @abstractmethod
    def _init_agent(self) -> Assistant:
        """初始化具体的Agent实例"""
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        pass
    
    @abstractmethod
    def get_function_list(self) -> List[str]:
        """获取可用的工具函数列表"""
        pass
    
    def chat(self, user_input: str, file_path: str = None) -> Dict[str, Any]:
        """处理用户输入并返回响应"""
        logger.info(f"[{self.session_id}] 开始处理聊天请求 - 输入长度: {len(user_input)}, 文件: {file_path}")
        
        try:
            # 构建消息
            if file_path:
                message = {
                    'role': 'user', 
                    'content': [{'text': user_input}, {'file': file_path}]
                }
                logger.info(f"[{self.session_id}] 构建带文件的消息")
            else:
                message = {'role': 'user', 'content': user_input}
                logger.info(f"[{self.session_id}] 构建文本消息")
            
            self.messages.append(message)
            logger.info(f"[{self.session_id}] 消息已添加到历史，当前历史长度: {len(self.messages)}")
            
            # 调用qwen-agent
            logger.info(f"[{self.session_id}] 开始调用qwen-agent")
            response = []
            response_count = 0
            for resp in self.bot.run(self.messages):
                response = resp
                response_count += 1
                logger.debug(f"[{self.session_id}] 收到qwen-agent响应 #{response_count}")
            
            logger.info(f"[{self.session_id}] qwen-agent调用完成，响应数量: {len(response)}")
            self.messages.extend(response)
            
            # 提取最后的助手回复
            assistant_reply = None
            for msg in reversed(response):
                if msg.get('role') == 'assistant':
                    assistant_reply = msg.get('content', '')
                    break
            
            logger.info(f"[{self.session_id}] 提取助手回复完成 - 回复长度: {len(assistant_reply) if assistant_reply else 0}")
            
            result = {
                'success': True,
                'response': assistant_reply,
                'session_id': self.session_id,
                'message_count': len(self.messages)
            }
            
            logger.info(f"[{self.session_id}] 聊天处理成功完成")
            return result
            
        except Exception as e:
            logger.error(f"[{self.session_id}] 聊天处理失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'session_id': self.session_id
            }
    
    def chat_stream(self, user_input: str, file_path: str = None):
        """处理用户输入并返回流式响应"""
        logger.info(f"[{self.session_id}] 开始处理流式聊天请求 - 输入长度: {len(user_input)}, 文件: {file_path}")
        
        try:
            # 构建消息
            if file_path:
                message = {
                    'role': 'user', 
                    'content': [{'text': user_input}, {'file': file_path}]
                }
                logger.info(f"[{self.session_id}] 构建带文件的消息")
            else:
                message = {'role': 'user', 'content': user_input}
                logger.info(f"[{self.session_id}] 构建文本消息")
            
            self.messages.append(message)
            logger.info(f"[{self.session_id}] 消息已添加到历史，当前历史长度: {len(self.messages)}")
            
            # 调用qwen-agent并流式返回
            logger.info(f"[{self.session_id}] 开始调用qwen-agent流式响应")
            response = []
            response_count = 0
            last_content_length = 0  # 跟踪上次发送的内容长度
            
            for resp in self.bot.run(self.messages):
                response = resp
                response_count += 1
                logger.debug(f"[{self.session_id}] 收到qwen-agent流式响应 #{response_count}")
                
                # 提取当前响应中的助手回复
                for msg in resp:
                    if msg.get('role') == 'assistant':
                        content = msg.get('content', '')
                        if content and len(content) > last_content_length:
                            # 只发送新增的内容部分
                            new_content = content[last_content_length:]
                            last_content_length = len(content)
                            yield {
                                'type': 'chunk',
                                'content': new_content,
                                'session_id': self.session_id
                            }
            
            logger.info(f"[{self.session_id}] qwen-agent流式调用完成，响应数量: {len(response)}")
            self.messages.extend(response)
            
            # 提取最后的助手回复
            assistant_reply = None
            for msg in reversed(response):
                if msg.get('role') == 'assistant':
                    assistant_reply = msg.get('content', '')
                    break
            
            # 发送完成信号
            yield {
                'type': 'complete',
                'success': True,
                'full_response': assistant_reply,
                'session_id': self.session_id,
                'message_count': len(self.messages)
            }
            
            logger.info(f"[{self.session_id}] 流式聊天处理成功完成")
            
        except Exception as e:
            logger.error(f"[{self.session_id}] 流式聊天处理失败: {str(e)}")
            yield {
                'type': 'error',
                'success': False,
                'error': str(e),
                'session_id': self.session_id
            }
    
    def get_history(self) -> List[Dict[str, Any]]:
        """获取会话历史"""
        return self.messages
    
    def clear_history(self):
        """清空会话历史"""
        self.messages = []
    
    def load_history(self, messages: List[Dict[str, Any]]):
        """加载历史消息"""
        self.messages = messages