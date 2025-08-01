from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
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
        self.bot = self._init_agent(enable_thinking=True)
        # 标记当前思考模式状态
        self.bot._thinking_enabled = True
    
    def _init_agent(self, enable_thinking: bool = True) -> Assistant:
        """初始化具体的Agent实例
        
        默认实现，子类可以重写以自定义配置
        
        Args:
            enable_thinking: 是否启用思考模式，默认为True
            
        Returns:
            Assistant: 配置好的Assistant实例
        """
        logger.info(f"[{self.session_id}] 开始初始化Agent，思考模式: {enable_thinking}")
        
        # LLM配置
        llm_cfg = {
            'model': os.getenv('DEFAULT_MODEL', 'qwen-turbo-latest'),
            'api_key': os.getenv('ALIBABA_API_KEY'),
            'timeout': 30,
            'retry_count': 3,
            # 动态配置思考模式
            'generate_cfg': {
                'enable_thinking': enable_thinking,  # 根据参数动态启用Qwen3的思考模式
                'max_tokens': 32000,  # 设置最大输出token数量为32000（接近模型最大限制）
            }
        }
        
        logger.info(f"[{self.session_id}] LLM配置完成 - 模型: {llm_cfg['model']}, API密钥已配置: {bool(llm_cfg['api_key'])}, 最大输出token: {llm_cfg['generate_cfg']['max_tokens']}")
        
        # 获取增强的工具列表
        enhanced_tools = self.get_enhanced_function_list()
        
        # 获取MCP配置
        mcp_config = self.get_mcp_config()
        
        # 创建Assistant实例
        logger.info(f"[{self.session_id}] 开始创建Assistant实例")
        bot = Assistant(
            llm=llm_cfg,
            name=self.get_agent_name(),
            description=self.get_agent_description(),
            system_message=self.get_system_prompt(),
            function_list=enhanced_tools,
            mcp_config=mcp_config
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
    
    def get_mcp_config(self) -> Optional[Dict[str, Any]]:
        """获取MCP配置，子类可重写以提供自定义配置
        
        Returns:
            Optional[Dict[str, Any]]: MCP配置字典，None表示使用全局默认配置
        """
        return None
    
    def get_default_mcp_tools(self) -> List[Dict[str, Any]]:
        """获取默认的MCP工具配置
        
        直接使用已经在应用启动时初始化好的MCP工具实例
        
        Returns:
            List[Dict[str, Any]]: MCP工具配置列表
        """
        logger.info(f"[{self.session_id}] [MCP工具获取] 开始获取已初始化的MCP工具")
        
        try:
            # 检查MCP工具是否已预注册
            if not mcp_manager.is_initialized():
                logger.warning(f"[{self.session_id}] [MCP工具获取] MCP工具尚未预注册")
                return []
            
            # 获取可用的工具名称
            available_tools = mcp_manager.get_available_tool_names()
            if not available_tools:
                logger.warning(f"[{self.session_id}] [MCP工具获取] 没有可用的MCP工具")
                return []
            
            logger.info(f"[{self.session_id}] [MCP工具获取] 发现可用工具: {available_tools}")
            
            # 直接查询已注册的工具实例（应该在应用启动时已经初始化）
            registered_tools = mcp_manager.query_mcp_tools(available_tools)
            if registered_tools is not None:
                logger.info(f"[{self.session_id}] [MCP工具获取] 获取已初始化的MCP工具实例成功，数量: {len(registered_tools)}")
                return registered_tools
            else:
                logger.warning(f"[{self.session_id}] [MCP工具获取] 工具实例尚未初始化，返回配置")
                # 如果实例还没有初始化，返回配置（向后兼容）
                tool_configs = mcp_manager.get_mcp_tools()
                logger.info(f"[{self.session_id}] [MCP工具获取] 返回工具配置，数量: {len(tool_configs)}")
                return tool_configs
                
        except Exception as e:
            logger.error(f"[{self.session_id}] [MCP工具获取] 获取MCP工具失败: {e}")
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
            tool: 工具配置字典或工具实例
            
        Returns:
            str: 工具名称，如果无法提取则返回空字符串
        """
        # 处理MCP工具实例（通过register_tool装饰器创建的工具类）
        if hasattr(tool, '__class__') and hasattr(tool.__class__, '__name__'):
            class_name = tool.__class__.__name__
            # MCP工具类名格式通常是 '{register_name}_Class'
            if class_name.endswith('_Class'):
                return class_name[:-6]  # 移除 '_Class' 后缀
            # 如果工具有name属性，优先使用
            if hasattr(tool, 'name'):
                return getattr(tool, 'name')
            return class_name
        
        # 处理字典格式的工具配置
        if isinstance(tool, dict):
            # 处理MCP工具配置格式
            if 'mcpServers' in tool:
                server_names = list(tool['mcpServers'].keys())
                return server_names[0] if server_names else ''
            
            # 处理其他工具格式
            return tool.get('name', tool.get('function_name', ''))
        
        return ''
    
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
            logger.info(f"[{self.session_id}] 开始调用qwen-agent，当前可用工具数量: {len(self.bot.function_list) if hasattr(self.bot, 'function_list') else 0}")
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
    
    def chat_stream(self, user_input: str, file_path: str = None, deep_thinking: bool = True):
        """处理用户输入并返回流式响应"""
        logger.info(f"[{self.session_id}] 开始处理流式聊天请求 - 输入长度: {len(user_input)}, 文件: {file_path}, 深度思考: {deep_thinking}")
        
        # 创建工具状态回调函数
        def tool_status_callback(status_info):
            """工具调用状态回调函数"""
            try:
                yield {
                    "type": "tool_status",
                    "tool_status": status_info['type'],
                    "content": status_info['message'],
                    "server_name": status_info.get('server_name', ''),
                    "tool_name": status_info.get('tool_name', ''),
                    "session_id": self.session_id
                }
            except Exception as e:
                logger.error(f"[{self.session_id}] 工具状态回调失败: {str(e)}")
        
        try:
            # 如果当前Agent的思考模式设置与请求不匹配，重新初始化Agent
            current_thinking_enabled = getattr(self.bot, '_thinking_enabled', True)
            if current_thinking_enabled != deep_thinking:
                logger.info(f"[{self.session_id}] 思考模式设置变更，重新初始化Agent: {current_thinking_enabled} -> {deep_thinking}")
                # 保存当前消息历史
                current_messages = self.messages.copy()
                # 重新初始化Agent
                self.bot = self._init_agent(enable_thinking=deep_thinking)
                # 标记当前思考模式状态
                self.bot._thinking_enabled = deep_thinking
                # 恢复消息历史
                self.messages = current_messages
            
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
            
            # 设置工具调用状态回调
            self._tool_status_generator = None
            
            # 调用qwen-agent并流式返回
            logger.info(f"[{self.session_id}] 开始调用qwen-agent流式响应，当前可用工具数量: {len(self.bot.function_list) if hasattr(self.bot, 'function_list') else 0}")
            response = []
            response_count = 0
            last_content_length = 0  # 跟踪上次发送的内容长度
            last_reasoning_length = 0  # 跟踪上次发送的思考内容长度
            
            # 为当前agent实例创建独立的工具调用包装，避免全局状态污染
            original_function_map = getattr(self.bot, 'function_map', {})
            self._original_tool_calls = {}  # 保存原始的工具调用方法
            
            for func_name, func_obj in original_function_map.items():
                if hasattr(func_obj, 'call'):
                    # 保存原始的call方法，以便后续恢复
                    if not hasattr(func_obj, '_original_call'):
                        func_obj._original_call = func_obj.call
                    
                    # 为当前session创建独立的包装函数
                    current_session_id = self.session_id
                    current_handle_method = self._handle_tool_status
                    
                    def create_wrapped_call(original_func, session_id, handle_method):
                        def wrapped_call(*args, **kwargs):
                            # 添加状态回调到kwargs，确保回调指向正确的agent实例
                            kwargs['status_callback'] = lambda status: handle_method(status)
                            return original_func(*args, **kwargs)
                        return wrapped_call
                    
                    # 为当前实例创建包装后的调用方法
                    func_obj.call = create_wrapped_call(func_obj._original_call, current_session_id, current_handle_method)
            
            # 初始化立即发送标志
            self._immediate_tool_status = False
            
            for resp in self.bot.run(self.messages):
                response = resp
                response_count += 1
                # logger.debug(f"[{self.session_id}] 收到qwen-agent流式响应 #{response_count}")
                
                # 优先检查是否有工具状态需要立即发送
                if hasattr(self, '_immediate_tool_status') and self._immediate_tool_status:
                    if hasattr(self, '_pending_tool_status') and self._pending_tool_status:
                        for status in self._pending_tool_status:
                            yield status
                            # 立即刷新输出缓冲区
                            import sys
                            sys.stdout.flush()
                        self._pending_tool_status = []
                    self._immediate_tool_status = False
                
                # 检查是否有其他工具状态需要发送
                if hasattr(self, '_pending_tool_status') and self._pending_tool_status:
                    for status in self._pending_tool_status:
                        yield status
                        # 立即刷新输出缓冲区
                        import sys
                        sys.stdout.flush()
                    self._pending_tool_status = []
                
                # 提取当前响应中的助手回复
                for msg in resp:
                    if msg.get('role') == 'assistant':
                        # 检查是否有工具状态信息在extra字段中
                        extra = msg.get('extra', {})
                        if extra and extra.get('type') == 'tool_status':
                            # 处理工具状态信息
                            tool_status_info = extra.get('tool_status', {})
                            yield {
                                "type": "tool_status",
                                "tool_status": tool_status_info.get('type', 'unknown'),
                                "content": tool_status_info.get('message', ''),
                                "server_name": tool_status_info.get('server_name', ''),
                                "tool_name": tool_status_info.get('tool_name', ''),
                                "session_id": self.session_id
                            }
                            continue
                        
                        # 处理思考内容（reasoning_content）- 仅在深度思考模式开启时输出
                        if deep_thinking:
                            reasoning_content = msg.get('reasoning_content', '')
                            if reasoning_content and len(reasoning_content) > last_reasoning_length:
                                # 只发送新增的思考内容部分
                                new_reasoning = reasoning_content[last_reasoning_length:]
                                last_reasoning_length = len(reasoning_content)
                                yield {
                                    "type": "chunk",
                                    "content": new_reasoning,
                                    "is_thinking": True,
                                    "session_id": self.session_id
                                }
                        
                        # 处理正常回复内容
                        content = msg.get('content', '')
                        if content and len(content) > last_content_length:
                            # 只发送新增的内容部分
                            new_content = content[last_content_length:]
                            last_content_length = len(content)
                            yield {
                                "type": "chunk",
                                "content": new_content,
                                "is_thinking": False,
                                "session_id": self.session_id
                            }
            
            # 检查最后是否还有工具状态需要发送
            if hasattr(self, '_pending_tool_status'):
                for status in self._pending_tool_status:
                    yield status
                self._pending_tool_status = []
            
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
        finally:
            # 恢复工具的原始调用方法，避免影响其他agent实例
            original_function_map = getattr(self.bot, 'function_map', {})
            for func_name, func_obj in original_function_map.items():
                if hasattr(func_obj, '_original_call'):
                    func_obj.call = func_obj._original_call
            logger.debug(f"[{self.session_id}] 已恢复工具原始调用方法")
    
    def _handle_tool_status(self, status_info):
        """处理工具调用状态"""
        if not hasattr(self, '_pending_tool_status'):
            self._pending_tool_status = []
        
        tool_status_msg = {
            "type": "tool_status",
            "tool_status": status_info['type'],
            "content": status_info['message'],
            "server_name": status_info.get('server_name', ''),
            "tool_name": status_info.get('tool_name', ''),
            "session_id": self.session_id
        }
        
        self._pending_tool_status.append(tool_status_msg)
        
        # 检查工具完成状态，如果包含图表信息则发送chart消息
        # 支持多种完成状态类型：completed, success, tool_success
        if status_info['type'] in ['completed', 'success', 'tool_success'] and 'result' in status_info:
            logger.info(f"[{self.session_id}] [图表检测] 工具完成，检查结果中是否包含图表: {status_info['result'][:200]}...")
            chart_info = self._extract_chart_info(status_info['result'])
            if chart_info:
                chart_msg = {
                    "type": "chart",
                    "chart_url": chart_info['url'],
                    "alt_text": chart_info['alt'],
                    "session_id": self.session_id
                }
                self._pending_tool_status.append(chart_msg)
                logger.info(f"[{self.session_id}] [图表检测] 检测到图表，已添加chart消息: URL={chart_info['url']}, Alt={chart_info['alt']}")
            else:
                logger.info(f"[{self.session_id}] [图表检测] 工具结果中未检测到图表")
        
        # 设置立即发送标志
        self._immediate_tool_status = True
        logger.info(f"[{self.session_id}] 工具状态: {status_info['message']}")
    
    def get_history(self) -> List[Dict[str, Any]]:
        """获取会话历史"""
        return self.messages
    
    def clear_history(self):
        """清空会话历史"""
        self.messages = []
    
    def load_history(self, messages: List[Dict[str, Any]]):
        """加载历史消息"""
        self.messages = messages
    
    def _extract_chart_info(self, result_text: str) -> dict:
        """从工具返回结果中提取图表信息
        
        Args:
            result_text: 工具返回的结果文本
            
        Returns:
            dict: 图表信息字典，包含url、alt、markdown字段，如果没有图表则返回None
        """
        import re
        
        # 匹配Markdown格式的图片：![alt](url)
        pattern = r'!\[([^\]]*?)\]\(([^\)]+?)\)'
        matches = re.findall(pattern, result_text)
        
        if matches:
            # 取第一个匹配的图片
            alt_text, img_url = matches[0]
            
            # 检查是否是本地生成的图表（包含/flask/static/images/路径）
            if '/flask/static/images/' in img_url:
                return {
                    "url": img_url,
                    "alt": alt_text or "图表",
                    "markdown": f"![{alt_text}]({img_url})"
                }
        
        return None
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return self.system_prompt if hasattr(self, 'system_prompt') else ''