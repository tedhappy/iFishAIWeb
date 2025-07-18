import copy
from typing import Dict, Iterator, List, Literal, Optional, Union

from qwen_agent import Agent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import DEFAULT_SYSTEM_MESSAGE, FUNCTION, Message
from qwen_agent.memory import Memory
from qwen_agent.settings import MAX_LLM_CALL_PER_RUN
from qwen_agent.tools import BaseTool
from qwen_agent.utils.utils import extract_files_from_messages


class FnCallAgent(Agent):
    """This is a widely applicable function call agent integrated with llm and tool use ability."""

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 files: Optional[List[str]] = None,
                 **kwargs):
        """Initialization the agent.

        Args:
            function_list: One list of tool name, tool configuration or Tool object,
              such as 'code_interpreter', {'name': 'code_interpreter', 'timeout': 10}, or CodeInterpreter().
            llm: The LLM model configuration or LLM model object.
              Set the configuration as {'model': '', 'api_key': '', 'model_server': ''}.
            system_message: The specified system message for LLM chat.
            name: The name of this agent.
            description: The description of this agent, which will be used for multi_agent.
            files: A file url list. The initialized files for the agent.
        """
        super().__init__(function_list=function_list,
                         llm=llm,
                         system_message=system_message,
                         name=name,
                         description=description,
                         **kwargs)

        if not hasattr(self, 'mem'):
            # Default to use Memory to manage files
            if 'qwq' in self.llm.model.lower() or 'qvq' in self.llm.model.lower():
                if 'dashscope' in self.llm.model_type:
                    mem_llm = {
                        'model': 'qwen-turbo-latest',
                        'model_type': 'qwen_dashscope',
                        'generate_cfg': {
                            'max_input_tokens': 30000
                        }
                    }
                else:
                    mem_llm = None
            else:
                mem_llm = self.llm
            self.mem = Memory(llm=mem_llm, files=files, **kwargs)

    def _run(self, messages: List[Message], lang: Literal['en', 'zh'] = 'en', **kwargs) -> Iterator[List[Message]]:
        messages = copy.deepcopy(messages)
        num_llm_calls_available = MAX_LLM_CALL_PER_RUN
        response = []
        
        # 重置立即工具调用标记（每次新的_run调用都重置）
        self._immediate_tool_called = False
        
        # 检查是否有新的用户消息，如果有则立即尝试调用MCP工具
        if messages and messages[-1].role == 'user':
            mcp_tool_used = self._try_call_mcp_tools_immediately(messages, response, **kwargs)
            if mcp_tool_used:
                yield response
        
        while True and num_llm_calls_available > 0:
            num_llm_calls_available -= 1

            extra_generate_cfg = {'lang': lang}
            if kwargs.get('seed') is not None:
                extra_generate_cfg['seed'] = kwargs['seed']
            output_stream = self._call_llm(messages=messages,
                                           functions=[func.function for func in self.function_map.values()],
                                           extra_generate_cfg=extra_generate_cfg)
            output: List[Message] = []
            for output in output_stream:
                if output:
                    yield response + output
            if output:
                response.extend(output)
                messages.extend(output)
                used_any_tool = False
                for out in output:
                    use_tool, tool_name, tool_args, _ = self._detect_tool(out)
                    if use_tool:
                        # 检查是否是已经在立即调用阶段调用过的工具，避免重复调用
                        if hasattr(self, '_immediate_tool_called') and self._immediate_tool_called:
                            # 检查最近的消息中是否已经有相同工具的调用结果
                            recent_tool_calls = [msg for msg in messages[-5:] if msg.role == FUNCTION and msg.name == tool_name]
                            if recent_tool_calls:
                                # 跳过重复的工具调用
                                continue
                        
                        tool_result = self._call_tool(tool_name, tool_args, messages=messages, **kwargs)
                        fn_msg = Message(
                            role=FUNCTION,
                            name=tool_name,
                            content=tool_result,
                        )
                        messages.append(fn_msg)
                        response.append(fn_msg)
                        yield response
                        used_any_tool = True
                if not used_any_tool:
                    break
        yield response

    def _try_call_mcp_tools_immediately(self, messages: List[Message], response: List[Message], **kwargs) -> bool:
        """立即尝试调用MCP工具，使用LLM智能判断是否需要调用特定工具"""
        if not messages or messages[-1].role != 'user':
            return False
            
        user_message = messages[-1].content
        if not user_message:
            return False
            
        # 检查是否已经调用过工具（避免重复调用）
        if hasattr(self, '_immediate_tool_called') and self._immediate_tool_called:
            return False
            
        # 检查是否有MCP工具可用
        mcp_tools = [name for name in self.function_map.keys() if '-' in name]  # MCP工具通常包含连字符
        if not mcp_tools:
            return False
            
        # 构建工具描述信息供LLM判断
        tool_descriptions = []
        for tool_name in mcp_tools:
            if tool_name in self.function_map:
                func_info = self.function_map[tool_name].function
                description = func_info.get('description', '无描述')
                tool_descriptions.append(f"- {tool_name}: {description}")
        
        if not tool_descriptions:
            return False
            
        # 使用LLM判断是否需要立即调用工具
        judgment_prompt = f"""用户问题：{user_message}

可用的MCP工具：
{chr(10).join(tool_descriptions)}

请判断是否需要立即调用工具来获取信息以更好地回答用户问题。如果需要，可以选择1-3个最相关的工具。

请按以下格式回答：
如果需要调用工具：CALL_TOOLS: 工具名称1,工具名称2,工具名称3
如果不需要调用工具：NO_TOOL

只回答格式化的结果，不要其他解释。"""
        
        try:
            # 创建判断消息
            judgment_messages = [
                Message(role='system', content='你是一个工具调用判断助手，根据用户问题和可用工具，判断是否需要立即调用工具。'),
                Message(role='user', content=judgment_prompt)
            ]
            
            # 调用LLM进行判断
            judgment_result = ''
            for output in self._call_llm(messages=judgment_messages, functions=[], extra_generate_cfg={'max_tokens': 50}):
                if output and len(output) > 0:
                    judgment_result = output[-1].content
                    break
            
            # 解析LLM的判断结果
            if not judgment_result or 'NO_TOOL' in judgment_result:
                return False
                
            if 'CALL_TOOLS:' in judgment_result:
                tool_names_str = judgment_result.split('CALL_TOOLS:')[1].strip()
                tool_names = [name.strip() for name in tool_names_str.split(',') if name.strip()]
                
                # 验证工具名称是否有效，过滤无效工具
                valid_tool_names = []
                for tool_name in tool_names:
                    if tool_name in self.function_map and tool_name in mcp_tools:
                        valid_tool_names.append(tool_name)
                
                if not valid_tool_names:
                    return False
                
                # 标记已调用工具，避免重复调用
                self._immediate_tool_called = True
                
                # 记录成功调用的工具数量
                successful_calls = 0
                
                # 依次调用每个工具
                for tool_name in valid_tool_names:
                    try:
                        # 构造工具参数（根据工具类型智能构造）
                        tool_args = self._construct_tool_args(tool_name, user_message)
                        
                        # 发送工具调用状态消息
                        status_msg = Message(
                            role='assistant',
                            content='',
                            extra={
                                'type': 'tool_status',
                                'tool_status': {
                                    'type': 'calling',
                                    'message': f'正在调用工具 {tool_name}...',
                                    'tool_name': tool_name,
                                    'server_name': tool_name.split('-')[0] if '-' in tool_name else ''
                                }
                            }
                        )
                        response.append(status_msg)
                        
                        # 调用工具
                        tool_result = self._call_tool(tool_name, tool_args, messages=messages, **kwargs)
                        
                        # 发送工具调用完成状态消息
                        success_msg = Message(
                            role='assistant',
                            content='',
                            extra={
                                'type': 'tool_status',
                                'tool_status': {
                                    'type': 'success',
                                    'message': f'成功调用工具 {tool_name}',
                                    'tool_name': tool_name,
                                    'server_name': tool_name.split('-')[0] if '-' in tool_name else ''
                                }
                            }
                        )
                        response.append(success_msg)
                        
                        # 添加工具结果消息
                        fn_msg = Message(
                            role=FUNCTION,
                            name=tool_name,
                            content=tool_result,
                        )
                        messages.append(fn_msg)
                        response.append(fn_msg)
                        successful_calls += 1
                        
                    except Exception as e:
                        # 发送工具调用失败状态消息
                        error_msg = Message(
                            role='assistant',
                            content='',
                            extra={
                                'type': 'tool_status',
                                'tool_status': {
                                    'type': 'error',
                                    'message': f'工具调用失败: {str(e)}',
                                    'tool_name': tool_name,
                                    'server_name': tool_name.split('-')[0] if '-' in tool_name else ''
                                }
                            }
                        )
                        response.append(error_msg)
                        # 继续调用下一个工具，不因为一个工具失败而停止
                        continue
                
                # 如果至少有一个工具调用成功，返回True
                return successful_calls > 0
                    
        except Exception as e:
            # LLM判断失败，静默处理
            return False
            
        return False
    
    def _construct_tool_args(self, tool_name: str, user_message: str) -> dict:
        """根据工具类型和用户消息智能构造工具参数"""
        tool_name_lower = tool_name.lower()
        
        # 搜索类工具
        if any(keyword in tool_name_lower for keyword in ['search', 'bing', 'tavily']):
            return {'query': user_message}
        
        # 12306火车票工具
        elif '12306' in tool_name_lower:
            if 'get-tickets' in tool_name_lower:
                # 尝试从用户消息中提取出发地和目的地
                # 这里可以进一步优化，使用更复杂的NLP解析
                return {'from_station': '', 'to_station': '', 'train_date': ''}
            else:
                return {'query': user_message}
        
        # 地图类工具
        elif any(keyword in tool_name_lower for keyword in ['map', 'amap']):
            return {'query': user_message}
        
        # 图像生成工具
        elif 'image' in tool_name_lower or 'generate' in tool_name_lower:
            return {'prompt': user_message}
        
        # 默认参数
        else:
            return {'query': user_message}

    def _call_tool(self, tool_name: str, tool_args: Union[str, dict] = '{}', **kwargs) -> str:
        if tool_name not in self.function_map:
            return f'Tool {tool_name} does not exists.'
        # Temporary plan: Check if it is necessary to transfer files to the tool
        # Todo: This should be changed to parameter passing, and the file URL should be determined by the model
        if self.function_map[tool_name].file_access:
            assert 'messages' in kwargs
            files = extract_files_from_messages(kwargs['messages'], include_images=True) + self.mem.system_files
            return super()._call_tool(tool_name, tool_args, files=files, **kwargs)
        else:
            return super()._call_tool(tool_name, tool_args, **kwargs)
