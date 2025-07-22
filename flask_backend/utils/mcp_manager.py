"""MCP工具管理器

这个模块提供了一个单例模式的MCP管理器，支持按需注册和查询MCP工具实例。
Agent在创建时先查询所需MCP工具是否已注册，如果已注册则直接返回实例，
如果未注册则进行注册。在应用启动时会预注册常用的MCP工具。
"""

import threading
from typing import Dict, List, Optional, Any, Union
from qwen_agent.tools.base import BaseTool
import logging
import hashlib
import json

logger = logging.getLogger(__name__)

class MCPManager:
    """MCP工具管理器 - 单例模式
    
    支持按需注册和查询MCP工具实例，Agent创建时先查询再注册
    在应用启动时预注册常用的MCP工具
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
                    # MCP工具实例注册表：key为工具配置的hash，value为工具实例
                    self._registered_tools: Dict[str, List[Dict[str, Any]]] = {}
                    # MCP工具配置缓存：key为工具名称，value为配置
                    self._tool_configs: Dict[str, Dict[str, Any]] = {}
                    # 预注册状态
                    self._pre_registered = False
                    self._load_error = None
                    MCPManager._initialized = True
    
    def _generate_config_hash(self, config: Dict[str, Any]) -> str:
        """生成配置的哈希值，用于标识唯一的MCP工具配置
        
        Args:
            config: MCP工具配置
            
        Returns:
            str: 配置的哈希值
        """
        # 将配置转换为标准化的JSON字符串，然后生成哈希
        config_str = json.dumps(config, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(config_str.encode('utf-8')).hexdigest()
    
    def get_default_mcp_config(self) -> List[Dict[str, Any]]:
        """获取默认MCP配置
        
        Returns:
            List[Dict[str, Any]]: MCP配置列表
        """
        # 只保留高德地图、tavily和12306三个重要工具
        return [{
            "mcpServers": {
                "amap-maps": {
                    "command": "npx",
                    "args": [
                        "-y",
                        "@amap/amap-maps-mcp-server"
                    ],
                    "env": {
                        "AMAP_MAPS_API_KEY": "1b53684eb64e583bae01afcc981b477a"
                    }
                },
                # "bing-cn-mcp-server": {
                #     "type": "sse",
                #     "url": "https://mcp.api-inference.modelscope.net/b9870e09875547/sse"
                # },
                # "fetch": {
                #     "type": "sse",
                #     "url": "https://mcp.api-inference.modelscope.net/d0d14b5f47b345/sse"
                # },
                # "12306-mcp": {
                #     "type": "sse",
                #     "url": "https://mcp.api-inference.modelscope.net/df74994c8c5b46/sse"
                # },
                "tavily-mcp": {
                    "command": "npx",
                    "args": ["-y", "tavily-mcp@0.1.4"],
                    "env": {
                        "TAVILY_API_KEY": "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"
                    },
                    "disabled": False,
                    "autoApprove": []
                }
                # "MiniMax-MCP": {
                #     "type": "sse",
                #     "url": "https://mcp.api-inference.modelscope.net/237368dc90a642/sse"
                # }
            }
        }]
    
    def pre_register_default_tools(self, force_reload: bool = False) -> bool:
        """预注册默认的MCP工具
        
        在应用启动时调用，预注册常用的MCP工具配置
        
        Args:
            force_reload: 是否强制重新加载
            
        Returns:
            bool: 预注册是否成功
        """
        if self._pre_registered and not force_reload:
            logger.info("默认MCP工具已经预注册，跳过重复注册")
            return True
            
        try:
            logger.info("开始预注册默认MCP工具...")
            
            # 获取默认配置并预注册
            default_configs = self.get_default_mcp_config()
            
            registered_count = 0
            for config in default_configs:
                if 'mcpServers' in config:
                    for tool_name, tool_config in config['mcpServers'].items():
                        # 缓存工具配置
                        self._tool_configs[tool_name] = tool_config
                        registered_count += 1
                        logger.debug(f"预注册MCP工具配置: {tool_name}")
            
            self._pre_registered = True
            self._load_error = None
            
            logger.info(f"默认MCP工具预注册成功，注册了 {registered_count} 个工具配置")
            return True
            
        except Exception as e:
            self._load_error = str(e)
            logger.error(f"默认MCP工具预注册失败: {e}")
            return False
    
    def query_mcp_tools(self, tool_names: List[str]) -> Optional[List[Dict[str, Any]]]:
        """查询已注册的MCP工具实例（线程安全）
        
        通过全局锁确保查询操作的原子性，支持单例模式的并发访问
        
        Args:
            tool_names: 需要查询的工具名称列表
            
        Returns:
            Optional[List[Dict[str, Any]]]: 如果所有工具都已注册，返回工具实例列表；否则返回None
        """
        logger.info(f"[MCP查询] 开始查询MCP工具实例: {tool_names}")
        
        # 使用全局锁确保线程安全的查询操作
        with self._lock:
            try:
                # 生成查询配置的哈希
                query_config = {"mcpServers": {}}
                for tool_name in tool_names:
                    if tool_name not in self._tool_configs:
                        logger.info(f"[MCP查询] 工具 {tool_name} 未在配置中找到")
                        return None
                    query_config["mcpServers"][tool_name] = self._tool_configs[tool_name]
                
                config_hash = self._generate_config_hash(query_config)
                
                # 原子操作：检查是否已注册
                if config_hash in self._registered_tools:
                    logger.info(f"[MCP查询] 找到已注册的MCP工具实例: {tool_names}")
                    return self._registered_tools[config_hash]
                
                logger.info(f"[MCP查询] MCP工具实例未注册: {tool_names}")
                return None
                
            except Exception as e:
                logger.error(f"[MCP查询] 查询MCP工具实例失败: {e}")
                return None
    
    def register_mcp_tools(self, tool_names: List[str], tool_instances: List[Dict[str, Any]]) -> bool:
        """注册MCP工具实例（单例模式，线程安全）
        
        通过全局锁和原子操作判断是否已初始化，若已注册则直接返回True，
        若未注册则执行注册逻辑，确保同一配置只注册一次。
        
        Args:
            tool_names: 工具名称列表
            tool_instances: 工具实例列表
            
        Returns:
            bool: 注册是否成功
        """
        logger.info(f"[MCP注册] 开始注册MCP工具实例: {tool_names}")
        
        # 使用全局锁确保线程安全
        with self._lock:
            try:
                # 验证工具名称是否都在配置中
                for tool_name in tool_names:
                    if tool_name not in self._tool_configs:
                        logger.error(f"[MCP注册] 工具 {tool_name} 未在预注册配置中找到")
                        return False
                
                # 生成配置哈希
                config = {"mcpServers": {}}
                for tool_name in tool_names:
                    config["mcpServers"][tool_name] = self._tool_configs[tool_name]
                
                config_hash = self._generate_config_hash(config)
                
                # 原子操作：检查是否已注册（单例模式核心逻辑）
                if config_hash in self._registered_tools:
                    logger.info(f"[MCP注册] MCP工具实例已存在，跳过重复注册: {tool_names}")
                    return True
                
                # 执行注册逻辑
                self._registered_tools[config_hash] = tool_instances
                
                logger.info(f"[MCP注册] 成功注册MCP工具实例: {tool_names}")
                return True
                
            except Exception as e:
                logger.error(f"[MCP注册] 注册MCP工具实例失败: {e}")
                return False
    
    def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """获取已初始化的MCP工具配置
        
        Returns:
            List[Dict[str, Any]]: 全局共享的MCP工具配置列表
        """
        if not self._pre_registered:
            logger.warning("MCP工具尚未初始化，返回空列表")
            return []
        
        return self.get_default_mcp_config()
    
    def is_initialized(self) -> bool:
        """检查MCP工具是否已初始化
        
        Returns:
            bool: 是否已初始化
        """
        return self._pre_registered
    
    def get_load_error(self) -> Optional[str]:
        """获取加载错误信息
        
        Returns:
            Optional[str]: 错误信息，如果没有错误则返回None
        """
        return self._load_error
    
    def get_tools_count(self) -> int:
        """获取MCP工具数量
        
        Returns:
            int: MCP工具数量
        """
        if not self._pre_registered:
            return 0
        
        return len(self._tool_configs)
    
    def get_available_tool_names(self) -> List[str]:
        """获取所有可用的MCP工具名称
        
        Returns:
            List[str]: 可用的工具名称列表
        """
        return list(self._tool_configs.keys())
    
    def get_registered_instances_count(self) -> int:
        """获取已注册的工具实例数量
        
        Returns:
            int: 已注册的工具实例数量
        """
        return len(self._registered_tools)
    
    def get_tool_config(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """获取指定工具的配置
        
        Args:
            tool_name: 工具名称
            
        Returns:
            Optional[Dict[str, Any]]: 工具配置，如果不存在则返回None
        """
        return self._tool_configs.get(tool_name)
    
    def reset(self):
        """重置MCP管理器状态（主要用于测试）
        """
        with self._lock:
            self._registered_tools = {}
            self._tool_configs = {}
            self._pre_registered = False
            self._load_error = None
            logger.info("MCP管理器状态已重置")

# 全局MCP管理器实例
mcp_manager = MCPManager()