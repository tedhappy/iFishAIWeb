# MCP工具单例模式实现

## 概述

本项目为qwen-agent实现了一个线程安全的MCP（Model Context Protocol）工具单例模式，通过静态变量、全局锁和原子操作确保MCP工具实例的唯一性，避免重复注册和资源浪费。

## 核心特性

### 🔒 线程安全的单例模式
- 使用全局锁（`threading.RLock()`）确保线程安全
- 支持多线程环境下的并发访问
- 原子操作保证实例创建的一致性

### 🏭 工厂模式设计
- `MCPToolFactory`类提供统一的实例创建接口
- 支持依赖注入，可传入自定义配置
- 自动管理不同配置的实例

### 🔑 配置哈希机制
- 基于配置内容生成MD5哈希值
- 相同配置自动复用已有实例
- 支持配置内容的顺序无关性

### 💾 智能缓存系统
- 缓存已初始化的工具列表
- 避免重复初始化相同配置
- 提高性能和响应速度

### 🧪 测试友好
- 提供`reset_all_instances()`方法清理测试环境
- 支持隔离的测试用例
- 完整的单元测试覆盖

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    MCPToolFactory                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  create_manager(config=None)                        │    │
│  │  ├─ config is None → get_default_instance()         │    │
│  │  └─ config provided → get_instance(hash, config)    │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     MCPManager                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Class Variables:                                   │    │
│  │  ├─ _instances: Dict[str, MCPManager]               │    │
│  │  ├─ _default_instance: Optional[MCPManager]         │    │
│  │  └─ _initialized_configs: Dict[str, List]           │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Methods:                                           │    │
│  │  ├─ get_default_instance() → MCPManager             │    │
│  │  ├─ get_instance(hash, config) → MCPManager         │    │
│  │  ├─ initConfig(config) → List[Tools]                │    │
│  │  └─ reset_all_instances() → None                    │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Global Lock                               │
│              _global_lock = threading.RLock()              │
└─────────────────────────────────────────────────────────────┘
```

## 使用方法

### 1. 基本使用

```python
from qwen_agent.tools.mcp_manager import MCPManager, MCPToolFactory

# 方法1: 获取默认单例实例
manager = MCPManager.get_default_instance()

# 方法2: 通过工厂获取默认实例
manager = MCPToolFactory.create_manager()

# 方法3: 使用自定义配置
config = {
    "mcpServers": {
        "memory": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"]
        }
    }
}
manager = MCPToolFactory.create_manager(config)
```

### 2. 在Agent中使用

```python
from flask_backend.agents.base_agent import BaseAgent

class CustomAgent(BaseAgent):
    def get_mcp_config(self):
        """重写此方法提供自定义MCP配置"""
        return {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
                }
            }
        }
    
    def get_system_prompt(self):
        return "你是一个智能助手"
    
    def get_function_list(self):
        return []  # 使用MCP工具

# 创建Agent实例
agent = CustomAgent("agent1", "user1")
```

### 3. 直接初始化MCP工具

```python
# 配置MCP服务器
config = {
    "mcpServers": {
        "memory": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"]
        },
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        }
    }
}

# 获取管理器并初始化
manager = MCPToolFactory.create_manager(config)
tools = manager.initConfig(config)

print(f"初始化了 {len(tools)} 个MCP工具")
for tool in tools:
    print(f"- {tool.name}: {tool.description}")
```

## 核心组件

### MCPToolFactory
工厂类，提供统一的MCP管理器创建接口：
- `create_manager(config=None)`: 创建或获取MCP管理器实例

### MCPManager
单例管理器类，负责MCP工具的生命周期管理：
- `get_default_instance()`: 获取默认单例实例
- `get_instance(config_hash, config)`: 获取指定配置的实例
- `initConfig(config)`: 初始化MCP配置并返回工具列表
- `reset_all_instances()`: 重置所有实例（测试用）

### 线程安全机制
- 全局锁：`_global_lock = threading.RLock()`
- 原子操作：所有实例创建和访问都在锁保护下进行
- 线程安全的类变量管理

## 配置格式

MCP配置遵循标准格式：

```json
{
  "mcpServers": {
    "server_name": {
      "command": "npx",
      "args": ["-y", "package_name"],
      "env": {"ENV_VAR": "value"}  // 可选
    },
    "http_server": {
      "url": "http://localhost:8080/mcp",
      "headers": {"Authorization": "Bearer token"}  // 可选
    }
  }
}
```

## 测试

运行单例模式测试：

```bash
python test_mcp_singleton.py
```

测试覆盖：
- ✅ 基本单例模式
- ✅ 配置基础的实例管理
- ✅ 线程安全性
- ✅ 工厂模式
- ✅ 配置哈希机制
- ✅ 重置功能

运行使用示例：

```bash
python example_mcp_usage.py
```

## 最佳实践

### 1. 配置管理
```python
# 使用环境变量
config = {
    "mcpServers": {
        "memory": {
            "command": os.getenv("MCP_MEMORY_COMMAND", "npx"),
            "args": ["-y", os.getenv("MCP_MEMORY_PACKAGE", "@modelcontextprotocol/server-memory")]
        }
    }
}
```

### 2. 错误处理
```python
def safe_create_manager(config):
    try:
        return MCPToolFactory.create_manager(config)
    except Exception as e:
        logger.error(f"创建MCP管理器失败: {e}")
        # 降级到默认管理器
        return MCPManager.get_default_instance()
```

### 3. 测试隔离
```python
def test_something():
    # 测试前清理
    MCPManager.reset_all_instances()
    
    # 执行测试
    manager = MCPToolFactory.create_manager(test_config)
    # ... 测试逻辑
    
    # 测试后清理
    MCPManager.reset_all_instances()
```

## 性能优势

1. **避免重复连接**: 相同配置的MCP服务器只连接一次
2. **内存优化**: 单例模式减少内存占用
3. **缓存机制**: 已初始化的工具列表被缓存，避免重复初始化
4. **线程安全**: 多线程环境下的高效并发访问

## 兼容性

- ✅ 与现有qwen-agent代码完全兼容
- ✅ 支持所有现有的MCP配置格式
- ✅ 向后兼容，不影响现有功能
- ✅ 支持Python 3.7+

## 故障排除

### 常见问题

1. **MCP服务器连接失败**
   - 检查MCP服务器是否正在运行
   - 验证配置中的命令和参数是否正确
   - 查看日志获取详细错误信息

2. **工具重复注册警告**
   - 这是正常行为，单例模式会自动处理
   - 后注册的工具会覆盖先注册的同名工具

3. **线程安全问题**
   - 确保使用提供的工厂方法创建实例
   - 不要直接调用MCPManager构造函数

### 调试技巧

```python
# 查看当前实例状态
print(f"默认实例: {id(MCPManager.get_default_instance())}")
print(f"实例数量: {len(MCPManager._instances)}")
print(f"已初始化配置: {list(MCPManager._initialized_configs.keys())}")

# 重置环境进行调试
MCPManager.reset_all_instances()
```

## 更新日志

### v1.0.0 (2025-01-15)
- ✨ 实现线程安全的单例模式
- ✨ 添加MCPToolFactory工厂类
- ✨ 实现配置哈希机制
- ✨ 添加智能缓存系统
- ✨ 完整的测试覆盖
- 📚 详细的文档和示例

## 贡献

欢迎提交Issue和Pull Request来改进这个实现。请确保：
1. 添加适当的测试
2. 更新文档
3. 遵循现有的代码风格

## 许可证

本项目遵循与qwen-agent相同的许可证。