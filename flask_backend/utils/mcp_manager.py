"""MCP工具管理器

这个模块提供了一个单例模式的MCP管理器，确保MCP工具只初始化一次，
避免多个agent实例重复注册导致的冲突问题。
"""

import threading
from typing import Dict, List, Optional, Any
from qwen_agent.tools.base import BaseTool
import logging

logger = logging.getLogger(__name__)

class MCPManager:
    """MCP工具管理器 - 单例模式
    
    确保MCP工具只初始化一次，避免重复注册问题
    支持基于用户ID和会话ID的工具名称区分
    """
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MCPManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._mcp_tools: List[Dict[str, Any]] = []
                    self._is_loaded = False
                    self._load_error = None
                    self._registered_tools: Dict[str, str] = {}  # 记录已注册的工具名称和对应的会话ID
                    self._session_tools: Dict[str, List[str]] = {}  # 记录每个会话的工具列表
                    MCPManager._initialized = True
    
    def get_default_mcp_config(self) -> List[Dict[str, Any]]:
        """获取默认MCP配置
        
        基于assistant_bot.py中的配置，提供标准的MCP服务器配置
        只保留高德地图和tavily这两个重要的MCP工具
        
        Returns:
            List[Dict[str, Any]]: MCP配置列表
        """
        # 只保留高德地图和tavily两个重要工具
        return [{
            "mcpServers": {
                "amap-maps": {
                    "type": "sse",
                    "url": "https://mcp.api-inference.modelscope.net/acbe007a6c2c40/sse"
                },
                "tavily-mcp": {
                    "type": "sse",
                    "url": "https://mcp.api-inference.modelscope.net/7214e0e509b141/sse"
                }
            }
        }]
    
    def get_full_mcp_config(self) -> List[Dict[str, Any]]:
        """获取完整MCP配置
        
        包含所有可用的MCP服务器
        
        Returns:
            List[Dict[str, Any]]: 完整MCP配置列表
        """
        return [{
            "mcpServers": {
                "amap-maps": {
                    "type": "sse",
                    "url": "https://mcp.api-inference.modelscope.net/acbe007a6c2c40/sse"
                },
                "fetch": {
                    "type": "sse",
                    "url": "https://mcp.api-inference.modelscope.net/d0d14b5f47b345/sse"
                },
                "bing-cn-mcp-server": {
                    "type": "sse",
                    "url": "https://mcp.api-inference.modelscope.net/be9ed9ccc46848/sse"
                },
                "12306-mcp": {
                    "type": "sse",
                    "url": "https://mcp.api-inference.modelscope.net/df74994c8c5b46/sse"
                },
                "tavily-mcp": {
                    "type": "sse",
                    "url": "https://mcp.api-inference.modelscope.net/7214e0e509b141/sse"
                }
            }
        }]
    
    def initialize_mcp_tools(self, custom_config: Optional[List[Dict[str, Any]]] = None, force_reload: bool = False) -> bool:
        """初始化MCP工具
        
        Args:
            custom_config: 自定义MCP配置，如果为None则使用默认配置
            force_reload: 是否强制重新加载
            
        Returns:
            bool: 初始化是否成功
        """
        if self._is_loaded and not force_reload:
            logger.info("MCP工具已经初始化，跳过重复初始化")
            return True
            
        try:
            logger.info("开始初始化MCP工具配置...")
            
            # 使用自定义配置或默认配置
            config = custom_config if custom_config is not None else self.get_default_mcp_config()
            
            # 存储配置
            self._mcp_tools = config
            self._is_loaded = True
            self._load_error = None
            
            logger.info(f"MCP工具配置初始化成功，加载了 {len(config)} 个配置")
            
            # 记录配置详情
            for i, tool_config in enumerate(config):
                if 'mcpServers' in tool_config:
                    server_count = len(tool_config['mcpServers'])
                    logger.info(f"配置组 {i+1}: 包含 {server_count} 个MCP服务器")
            
            return True
            
        except Exception as e:
            self._load_error = str(e)
            logger.error(f"MCP工具初始化失败: {e}")
            return False
    
    def get_mcp_tools(self, session_id: str = None) -> List[Dict[str, Any]]:
        """获取已初始化的MCP工具配置
        
        Args:
            session_id: 会话ID，用于生成唯一的工具名称
        
        Returns:
            List[Dict[str, Any]]: MCP工具配置列表
        """
        if not self._is_loaded:
            logger.warning("MCP工具尚未初始化，返回空列表")
            return []
        
        # 如果提供了session_id，为工具名称添加会话标识
        if session_id:
            return self._get_session_specific_tools(session_id)
        
        return self._mcp_tools.copy()
    
    def is_initialized(self) -> bool:
        """检查MCP工具是否已初始化
        
        Returns:
            bool: 是否已初始化
        """
        return self._is_loaded
    
    def get_load_error(self) -> Optional[str]:
        """获取加载错误信息
        
        Returns:
            Optional[str]: 错误信息，如果没有错误则返回None
        """
        return self._load_error
    
    def _get_session_specific_tools(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话特定的MCP工具配置
        
        为每个会话生成唯一的工具名称，避免重复注册
        
        Args:
            session_id: 会话ID
            
        Returns:
            List[Dict[str, Any]]: 会话特定的MCP工具配置列表
        """
        session_tools = []
        
        for tool_config in self._mcp_tools:
            if 'mcpServers' in tool_config:
                session_config = {'mcpServers': {}}
                
                for server_name, server_config in tool_config['mcpServers'].items():
                    # 为工具名称添加会话标识，确保唯一性
                    unique_server_name = f"{server_name}_{session_id}"
                    
                    # 检查是否已经注册过
                    if unique_server_name not in self._registered_tools:
                        session_config['mcpServers'][unique_server_name] = server_config.copy()
                        self._registered_tools[unique_server_name] = session_id
                        
                        # 记录会话工具
                        if session_id not in self._session_tools:
                            self._session_tools[session_id] = []
                        self._session_tools[session_id].append(unique_server_name)
                        
                        logger.info(f"为会话 {session_id} 注册工具: {unique_server_name}")
                    else:
                        logger.debug(f"工具 {unique_server_name} 已存在，跳过注册")
                
                if session_config['mcpServers']:
                    session_tools.append(session_config)
        
        return session_tools
    
    def is_tool_registered(self, tool_name: str, session_id: str = None) -> bool:
        """检查工具是否已注册
        
        Args:
            tool_name: 工具名称
            session_id: 会话ID（可选）
            
        Returns:
            bool: 工具是否已注册
        """
        if session_id:
            unique_tool_name = f"{tool_name}_{session_id}"
            return unique_tool_name in self._registered_tools
        return tool_name in self._registered_tools
    
    def unregister_session_tools(self, session_id: str):
        """注销会话的所有工具
        
        Args:
            session_id: 会话ID
        """
        with self._lock:
            if session_id in self._session_tools:
                tools_to_remove = self._session_tools[session_id]
                for tool_name in tools_to_remove:
                    if tool_name in self._registered_tools:
                        del self._registered_tools[tool_name]
                        logger.info(f"注销工具: {tool_name}")
                
                del self._session_tools[session_id]
                logger.info(f"已注销会话 {session_id} 的所有工具")
    
    def get_registered_tools_count(self) -> int:
        """获取已注册工具数量
        
        Returns:
            int: 已注册工具数量
        """
        return len(self._registered_tools)
    
    def get_session_tools_count(self, session_id: str) -> int:
        """获取指定会话的工具数量
        
        Args:
            session_id: 会话ID
            
        Returns:
            int: 会话工具数量
        """
        return len(self._session_tools.get(session_id, []))
    
    def reset(self):
        """重置MCP管理器状态（主要用于测试）
        """
        with self._lock:
            self._mcp_tools = []
            self._is_loaded = False
            self._load_error = None
            self._registered_tools = {}
            self._session_tools = {}
            logger.info("MCP管理器状态已重置")

# 全局MCP管理器实例
mcp_manager = MCPManager()