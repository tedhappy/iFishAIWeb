from abc import ABC, abstractmethod
from typing import List, Dict, Any
import os
import dashscope
from qwen_agent.agents import Assistant
from utils.logger import logger
from utils.mcp_manager import mcp_manager

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
    
    def _init_agent(self) -> Assistant:
        """初始化具体的Agent实例
        
        默认实现，子类可以重写以自定义配置
        
        Returns:
            Assistant: 配置好的Assistant实例
        """
        logger.info(f"[{self.session_id}] 开始初始化Agent")
        
        # LLM配置
        llm_cfg = {
            'model': os.getenv('DEFAULT_MODEL', 'qwen-turbo-latest'),
            'api_key': os.getenv('ALIBABA_API_KEY'),
            'timeout': 30,
            'retry_count': 3,
        }
        
        logger.info(f"[{self.session_id}] LLM配置完成 - 模型: {llm_cfg['model']}, API密钥已配置: {bool(llm_cfg['api_key'])}")
        
        # 获取增强的工具列表
        enhanced_tools = self.get_enhanced_function_list()
        
        # 创建Assistant实例
        logger.info(f"[{self.session_id}] 开始创建Assistant实例")
        bot = Assistant(
            llm=llm_cfg,
            name=self.get_agent_name(),
            description=self.get_agent_description(),
            system_message=self.get_system_prompt(),
            function_list=enhanced_tools
        )
        
        logger.info(f"[{self.session_id}] Agent初始化成功")
        return bot
            
    
    def get_agent_name(self) -> str:
        """获取Agent名称，子类可重写"""
        return f"智能助手-{self.agent_id}"
    
    def get_agent_description(self) -> str:
        """获取Agent描述，子类可重写"""
        return "具备多种MCP工具能力的智能助手"
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        pass
    
    @abstractmethod
    def get_function_list(self) -> List[str]:
        """获取可用的工具函数列表"""
        pass
    
    def get_default_mcp_tools(self) -> List[Dict[str, Any]]:
        """获取默认的MCP工具配置
        
        通过MCP管理器的单例接口获取工具实例，利用内置的重复注册检查机制
        
        Returns:
            List[Dict[str, Any]]: MCP工具配置列表
        """
        # 检查MCP工具是否已预注册
        if not mcp_manager.is_initialized():
            logger.warning(f"[{self.session_id}] MCP工具尚未预注册")
            return []
        
        # 获取可用的工具名称
        available_tools = mcp_manager.get_available_tool_names()
        if not available_tools:
            logger.warning(f"[{self.session_id}] 没有可用的MCP工具")
            return []
        
        # 获取工具配置
        tool_configs = mcp_manager.get_mcp_tools()
        
        # 通过单例接口注册工具实例（内置重复检查，若已注册则直接返回成功）
        if mcp_manager.register_mcp_tools(available_tools, tool_configs):
            # 查询并返回已注册的工具实例
            registered_tools = mcp_manager.query_mcp_tools(available_tools)
            if registered_tools is not None:
                logger.debug(f"[{self.session_id}] 获取MCP工具实例成功: {available_tools}")
                return registered_tools
            else:
                logger.error(f"[{self.session_id}] 注册成功但查询失败")
                return tool_configs
        else:
            logger.error(f"[{self.session_id}] MCP工具实例注册失败")
            return []
    
    def get_enhanced_function_list(self) -> List[Dict[str, Any]]:
        """获取增强后的工具函数列表
        
        合并子类定义的工具和默认MCP工具，添加了工具去重逻辑和更好的错误处理
        
        Returns:
            List[Dict[str, Any]]: 完整的工具函数列表
        """
        logger.info(f"[{self.session_id}] 构建增强工具列表")
        
        # 获取子类定义的工具
        custom_tools = self.get_function_list()
        
        # 获取MCP工具
        mcp_tools = []
        try:
            if mcp_manager.is_initialized():
                mcp_tools = self.get_default_mcp_tools()
                logger.info(f"[{self.session_id}] 已加载 {len(mcp_tools)} 个MCP工具配置")
            else:
                logger.warning(f"[{self.session_id}] MCP管理器未初始化，跳过MCP工具加载")
        except Exception as e:
            logger.error(f"[{self.session_id}] 获取MCP工具失败: {e}")
            mcp_tools = []
        
        # 工具去重逻辑
        enhanced_tools = self._deduplicate_tools(custom_tools, mcp_tools)
        
        # 记录工具加载状态
        custom_count = len(custom_tools) if isinstance(custom_tools, list) else 0
        mcp_count = len(mcp_tools)
        total_count = len(enhanced_tools)
        
        logger.info(f"[{self.session_id}] 工具加载完成: 自定义工具 {custom_count} 个, MCP工具 {mcp_count} 个, 去重后总计 {total_count} 个")
        
        # 记录MCP工具状态
        if mcp_manager.is_initialized():
            try:
                config_count = mcp_manager.get_tools_count()
                instance_count = mcp_manager.get_registered_instances_count()
                logger.info(f"[{self.session_id}] MCP状态: {config_count} 个工具配置, {instance_count} 个已注册实例")
            except Exception as e:
                logger.debug(f"[{self.session_id}] 获取MCP状态信息失败: {e}")
        
        return enhanced_tools
    
    def _deduplicate_tools(self, custom_tools: List[Dict[str, Any]], mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """工具去重逻辑
        
        Args:
            custom_tools: 自定义工具列表
            mcp_tools: MCP工具列表
            
        Returns:
            List[Dict[str, Any]]: 去重后的工具列表
        """
        seen_tools = set()
        deduplicated_tools = []
        
        # 处理自定义工具
        if custom_tools and isinstance(custom_tools, list):
            # 首先添加自定义工具（优先级更高）
            for tool in custom_tools:
                tool_name = self._get_tool_name(tool)
                if tool_name and tool_name not in seen_tools:
                    seen_tools.add(tool_name)
                    deduplicated_tools.append(tool)
                elif tool_name:
                    logger.debug(f"[{self.session_id}] 跳过重复的自定义工具: {tool_name}")
        elif custom_tools:
            logger.warning(f"[{self.session_id}] 自定义工具格式不正确，跳过")
        
        # 然后添加MCP工具
        for tool in mcp_tools:
            tool_name = self._get_tool_name(tool)
            if tool_name and tool_name not in seen_tools:
                seen_tools.add(tool_name)
                deduplicated_tools.append(tool)
            elif tool_name:
                logger.debug(f"[{self.session_id}] 跳过重复的MCP工具: {tool_name}")
        
        return deduplicated_tools
    
    def _get_tool_name(self, tool: Dict[str, Any]) -> str:
        """从工具配置中提取工具名称
        
        Args:
            tool: 工具配置字典
            
        Returns:
            str: 工具名称，如果无法提取则返回空字符串
        """
        if not isinstance(tool, dict):
            return ''
        
        # 处理MCP工具格式
        if 'mcpServers' in tool:
            server_names = list(tool['mcpServers'].keys())
            return server_names[0] if server_names else ''
        
        # 处理其他工具格式
        return tool.get('name', tool.get('function_name', ''))
    
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