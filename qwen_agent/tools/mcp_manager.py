import asyncio
import json
import threading
import hashlib
from contextlib import AsyncExitStack
from typing import Dict, Optional, Union, List

from dotenv import load_dotenv

from qwen_agent.log import logger
from qwen_agent.tools.base import BaseTool, register_tool


# 全局锁，用于线程安全的单例管理
_global_lock = threading.RLock()


class MCPToolFactory:
    """MCP工具工厂类，用于依赖注入和实例管理"""
    
    @staticmethod
    def create_manager(config: Optional[Dict] = None) -> 'MCPManager':
        """创建或获取MCP管理器实例
        
        Args:
            config: 可选的配置字典，用于创建特定配置的实例
            
        Returns:
            MCPManager: MCP管理器实例
        """
        if config is None:
            return MCPManager.get_default_instance()
        else:
            config_hash = MCPManager._generate_config_hash(config)
            return MCPManager.get_instance(config_hash, config)


class MCPManager:
    # 类级别的实例存储，支持多个配置实例
    _instances: Dict[str, 'MCPManager'] = {}
    _default_instance: Optional['MCPManager'] = None
    _initialized_configs: Dict[str, List] = {}  # 缓存已初始化的工具列表
    
    def __init__(self, config_hash: str = 'default'):
        """私有构造函数，通过工厂方法创建实例"""
        if not hasattr(self, '_initialized'):
            load_dotenv()  # Load environment variables from .env file
            self.config_hash = config_hash
            self.clients: dict = {}
            self.exit_stack = AsyncExitStack()
            self.loop = asyncio.new_event_loop()
            self.loop_thread = threading.Thread(target=self.start_loop, daemon=True)
            self.loop_thread.start()
            self._initialized = True
            logger.info(f"MCP管理器实例已初始化: {config_hash}")
    
    @classmethod
    def get_default_instance(cls) -> 'MCPManager':
        """获取默认的单例实例"""
        with _global_lock:
            if cls._default_instance is None:
                cls._default_instance = cls('default')
            return cls._default_instance
    
    @classmethod
    def get_instance(cls, config_hash: str, config: Optional[Dict] = None) -> 'MCPManager':
        """获取指定配置的单例实例"""
        with _global_lock:
            if config_hash not in cls._instances:
                cls._instances[config_hash] = cls(config_hash)
            return cls._instances[config_hash]
    
    @staticmethod
    def _generate_config_hash(config: Dict) -> str:
        """生成配置的哈希值"""
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()[:16]
    
    @classmethod
    def reset_all_instances(cls):
        """重置所有实例（用于测试）"""
        with _global_lock:
            cls._instances.clear()
            cls._default_instance = None
            cls._initialized_configs.clear()
            logger.info("所有MCP管理器实例已重置")

    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def is_valid_mcp_servers(self, config: dict):
        """Example of mcp servers configuration:
        {
         "mcpServers": {
            "memory": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"]
            },
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/files"]
            }
         }
        }
        """

        # Check if the top-level key "mcpServers" exists and its value is a dictionary
        if not isinstance(config, dict) or 'mcpServers' not in config or not isinstance(config['mcpServers'], dict):
            return False
        mcp_servers = config['mcpServers']
        # Check each sub-item under "mcpServers"
        for key in mcp_servers:
            server = mcp_servers[key]
            # Each sub-item must be a dictionary
            if not isinstance(server, dict):
                return False
            if 'command' in server:
                # "command" must be a string
                if not isinstance(server['command'], str):
                    return False
                # "args" must be a list
                if 'args' not in server or not isinstance(server['args'], list):
                    return False
            if 'url' in server:
                # "url" must be a string
                if not isinstance(server['url'], str):
                    return False
                # "headers" must be a dictionary
                if 'headers' in server and not isinstance(server['headers'], dict):
                    return False
            # If the "env" key exists, it must be a dictionary
            if 'env' in server and not isinstance(server['env'], dict):
                return False
        return True

    def initConfig(self, config: Optional[Dict] = None):
        """初始化MCP配置，支持依赖注入和单例模式
        
        Args:
            config: 可选的配置字典，用于依赖注入
            
        Returns:
            List: 初始化的工具列表
        """
        if config is None:
            # 使用默认单例管理器
            manager = MCPManager.get_default_instance()
            return []
        
        # 生成配置哈希
        config_hash = self._generate_config_hash(config)
        
        # 检查是否已经初始化过相同配置
        with _global_lock:
            if config_hash in self._initialized_configs:
                logger.info(f'配置已初始化，返回缓存的工具列表: {config_hash}')
                return self._initialized_configs[config_hash]
        
        logger.info(f'开始初始化配置: {config_hash}')
        if not self.is_valid_mcp_servers(config):
            raise ValueError('Config format error')
        
        # Submit coroutine to the event loop and wait for the result
        future = asyncio.run_coroutine_threadsafe(self.init_config_async(config), self.loop)
        try:
            result = future.result()  # You can specify a timeout if desired
            
            # 缓存初始化结果
            with _global_lock:
                self._initialized_configs[config_hash] = result
            
            logger.info(f'配置初始化完成: {config_hash}, 工具数量: {len(result) if result else 0}')
            return result
        except Exception as e:
            logger.error(f'配置初始化失败: {e}')
            return None

    async def init_config_async(self, config: Dict):
        tools: list = []
        mcp_servers = config['mcpServers']
        logger.info(f'[MCP初始化] 开始初始化MCP服务器，服务器数量: {len(mcp_servers)}')
        
        for server_name in mcp_servers:
            logger.info(f'[MCP初始化] 正在连接MCP服务器: {server_name}')
            client = MCPClient()
            server = mcp_servers[server_name]
            await client.connection_server(self.exit_stack, server)  # Attempt to connect to the server
            self.clients[server_name] = client  # Add to clients dict after successful connection
            logger.info(f'[MCP初始化] MCP服务器连接成功: {server_name}, 可用工具数量: {len(client.tools) if client.tools else 0}')
            
            for tool in client.tools:
                """MCP tool example:
                {
                "name": "read_query",
                "description": "Execute a SELECT query on the SQLite database",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                        "type": "string",
                        "description": "SELECT SQL query to execute"
                        }
                    },
                    "required": ["query"]
                }
                """
                parameters = tool.inputSchema
                # The required field in inputSchema may be empty and needs to be initialized.
                if 'required' not in parameters:
                    parameters['required'] = []
                # Remove keys from parameters that do not conform to the standard OpenAI schema
                # Check if the required fields exist
                required_fields = {'type', 'properties', 'required'}
                missing_fields = required_fields - parameters.keys()
                if missing_fields:
                    raise ValueError(f'Missing required fields in schema: {missing_fields}')

                # Keep only the necessary fields
                cleaned_parameters = {
                    'type': parameters['type'],
                    'properties': parameters['properties'],
                    'required': parameters['required']
                }
                register_name = server_name + '-' + tool.name
                logger.info(f'[MCP初始化] 注册MCP工具: {register_name} (服务器: {server_name}, 工具: {tool.name})')
                agent_tool = self.create_tool_class(register_name, server_name, tool.name, tool.description,
                                                    cleaned_parameters)
                tools.append(agent_tool)
        
        logger.info(f'[MCP初始化] MCP工具初始化完成，总计注册工具数量: {len(tools)}')
        return tools

    def create_tool_class(self, register_name, server_name, tool_name, tool_desc, tool_parameters):
        # 捕获当前manager实例的引用
        manager_instance = self

        @register_tool(register_name)
        class ToolClass(BaseTool):
            description = tool_desc
            parameters = tool_parameters

            def call(self, params: Union[str, dict], **kwargs) -> str:
                import time
                import concurrent.futures
                
                tool_args = json.loads(params)
                logger.info(f'[MCP调用] 开始执行MCP工具 - 服务器: {server_name}, 工具: {tool_name}, 参数: {tool_args}')
                
                # 获取状态回调函数（如果提供）
                status_callback = kwargs.get('status_callback')
                
                # 发送工具调用开始状态
                if status_callback:
                    status_callback({
                        'type': 'tool_start',
                        'server_name': server_name,
                        'tool_name': tool_name,
                        'message': f'正在调用工具，请耐心等候 {server_name}-{tool_name}'
                    })
                
                # 使用捕获的manager实例而不是创建新实例
                client = manager_instance.clients[server_name]
                future = asyncio.run_coroutine_threadsafe(client.execute_function(tool_name, tool_args), manager_instance.loop)
                
                try:
                    # 设置30秒超时
                    result = future.result(timeout=30)
                    logger.info(f'[MCP调用] MCP工具执行成功 - 服务器: {server_name}, 工具: {tool_name}, 结果长度: {len(str(result)) if result else 0}')
                    
                    # 发送工具调用成功状态
                    if status_callback:
                        status_callback({
                            'type': 'tool_success',
                            'server_name': server_name,
                            'tool_name': tool_name,
                            'message': f'成功调用工具 {server_name}-{tool_name}'
                        })
                    
                    return result
                except concurrent.futures.TimeoutError:
                    logger.error(f'[MCP调用] MCP工具调用超时 - 服务器: {server_name}, 工具: {tool_name}')
                    
                    # 发送工具调用超时状态
                    if status_callback:
                        status_callback({
                            'type': 'tool_timeout',
                            'server_name': server_name,
                            'tool_name': tool_name,
                            'message': f'工具调用超时 {server_name}-{tool_name}，请稍后重试'
                        })
                    
                    # 尝试取消future
                    future.cancel()
                    return f'工具调用超时：{server_name}-{tool_name}，请稍后重试'
                except Exception as e:
                    logger.error(f'[MCP调用] MCP工具执行失败 - 服务器: {server_name}, 工具: {tool_name}, 错误: {e}')
                    
                    # 发送工具调用失败状态
                    if status_callback:
                        status_callback({
                            'type': 'tool_error',
                            'server_name': server_name,
                            'tool_name': tool_name,
                            'message': f'工具调用失败 {server_name}-{tool_name}: {str(e)}'
                        })
                    
                    return f'工具调用失败：{str(e)}'

        ToolClass.__name__ = f'{register_name}_Class'
        return ToolClass()

    async def clearup(self):
        await self.exit_stack.aclose()


class MCPClient:

    def __init__(self):
        from mcp import ClientSession

        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.tools: list = None

    async def connection_server(self, exit_stack, mcp_server):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from mcp.client.sse import sse_client
        """Connect to an MCP server and retrieve the available tools."""
        try:
            if 'url' in mcp_server:
                self._streams_context = sse_client(url=mcp_server.get('url'), headers=mcp_server.get('headers', {"Accept": "text/event-stream"}))
                streams = await self._streams_context.__aenter__()

                self._session_context = ClientSession(*streams)
                self.session: ClientSession = await self._session_context.__aenter__()
            else:
                server_params = StdioServerParameters(
                    command = mcp_server["command"],
                    args = mcp_server["args"],
                    env = mcp_server.get("env", None)
                )
                stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
                self.stdio, self.write = stdio_transport
                self.session = await exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

            await self.session.initialize()

            list_tools = await self.session.list_tools()
            self.tools = list_tools.tools
        except Exception as e:
            logger.info(f"Failed to connect to server: {e}")

    async def cleanup(self):
        """Properly clean up the session and streams"""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

    async def execute_function(self, tool_name, tool_args: dict):
        response = await self.session.call_tool(tool_name, tool_args)
        texts = []
        for content in response.content:
            if content.type == 'text':
                texts.append(content.text)
        if texts:
            return '\n\n'.join(texts)
        else:
            return 'execute error'
