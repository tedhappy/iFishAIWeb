# Agent开发维护指南

本文档详细说明如何在IFishAI系统中新增和维护Agent，确保开发流程的标准化和可维护性。

## 📋 目录

- [系统架构概述](#系统架构概述)
- [新增Agent完整流程](#新增agent完整流程)
- [配置文件说明](#配置文件说明)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)
- [维护指南](#维护指南)

## 🏗️ 系统架构概述

### Agent面具生成流程
```
app/masks/cn.ts (源码定义)
       ↓
app/masks/build.ts (构建脚本)
       ↓
public/masks.json (生成文件)
       ↓
前端界面显示
```

### 相关文件结构
```
app/
├── masks/
│   ├── cn.ts              # 中文Agent面具定义
│   ├── build.ts           # 面具构建脚本
│   ├── index.ts           # 面具导出管理
│   └── typing.ts          # 类型定义
├── config/
│   └── suggested-questions.ts  # 推荐问题配置
└── components/
    ├── new-chat.tsx       # Agent选择界面
    └── mask.tsx           # 面具管理界面

public/
└── masks.json             # 生成的面具配置文件

flask_backend/
├── agents/                # 后端Agent实现
└── session_manager.py     # 会话管理
```

## 🚀 新增Agent完整流程

### 步骤1：定义Agent面具

编辑 `app/masks/cn.ts` 文件，在 `CN_MASKS` 数组中添加新的Agent配置：

```typescript
{
  avatar: "1f4ca",                    // emoji代码，用作头像
  name: "ChatBI",                     // Agent显示名称
  agentType: "chatbi",                // Agent类型标识（重要：用于路由）
  context: [                          // 预设对话上下文
    {
      id: "chatbi-0",
      role: "system",
      content: "我是ChatBI助手，专门用于数据分析和可视化...",
      date: ""
    },
    {
      id: "chatbi-1",
      role: "user", 
      content: "你能帮我分析数据吗？",
      date: ""
    },
    {
      id: "chatbi-2",
      role: "assistant",
      content: "当然可以！我可以帮您进行数据分析...",
      date: ""
    }
  ],
  modelConfig: {                      // 模型配置
    model: "qwen-turbo-latest",
    temperature: 0.3,                 // 根据Agent特性调整
    max_tokens: 2000,
    presence_penalty: 0,
    frequency_penalty: 0,
    sendMemory: true,
    historyMessageCount: 16,          // 根据需要调整
    compressMessageLengthThreshold: 1000
  },
  lang: "cn",
  builtin: true,
  createdAt: Date.now()               // 使用当前时间戳
}
```

### 步骤2：配置推荐问题

编辑 `app/config/suggested-questions.ts` 文件，添加Agent的推荐问题配置：

⚠️ **重要提醒**：推荐问题配置必须添加到 `AGENT_QUESTIONS_CONFIG` 数组中，而不是 `DEFAULT_QUESTIONS` 数组中！

```typescript
// 在 AGENT_QUESTIONS_CONFIG 数组中添加新的Agent配置
{
  agentType: "chatbi",
  name: "ChatBI",
  questions: [
    "帮我分析销售数据趋势",
    "生成用户行为分析报告", 
    "创建数据可视化图表"
  ],
  description: "专业的数据分析和可视化助手"
}
```

**配置位置说明**：
- `DEFAULT_QUESTIONS`：通用的默认推荐问题，适用于所有Agent
- `AGENT_QUESTIONS_CONFIG`：特定Agent的推荐问题配置，每个Agent一个配置对象
- 新增Agent的推荐问题必须添加到 `AGENT_QUESTIONS_CONFIG` 数组中
- **标准配置**：每个Agent必须配置恰好3个推荐问题

### 步骤3：构建面具配置

运行构建命令生成最新的面具配置文件：

```bash
npm run mask
```

这会执行 `app/masks/build.ts` 脚本，将源码中的面具定义写入到 `public/masks.json`。

### 步骤4：后端Agent实现

在 `flask_backend/agents/` 目录下创建对应的Agent实现文件：

```python
# flask_backend/agents/chatbi_agent.py
from .base_agent import BaseAgent
from qwen_agent.agents import Assistant
from typing import List, Dict, Any, Optional
from utils.logger import logger

class ChatBIAgent(BaseAgent):
    """ChatBI数据分析Agent"""
    
    def get_agent_name(self) -> str:
        """重写Agent名称"""
        return "ChatBI"
    
    def get_agent_description(self) -> str:
        """重写Agent描述"""
        return "专业的数据分析和可视化助手📊"
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """我是ChatBI数据分析助手，专门用于数据分析和可视化..."""
    
    def get_function_list(self) -> List[str]:
        """获取可用的工具函数列表"""
        return []  # 根据需要返回工具列表
    
    def get_mcp_config(self) -> Optional[Dict[str, Any]]:
        """重写MCP配置（可选）"""
        # 如果需要特定的MCP服务，在这里配置
        return None  # 使用默认配置
```

**⚠️ 重要提醒**：
1. **不要重写 `__init__` 方法**：BaseAgent需要特定的初始化参数
2. **必须实现抽象方法**：`get_system_prompt()` 和 `get_function_list()` 是必需的
3. **正确的导入语句**：包含必要的类型注解导入
4. **使用logger**：直接从 `utils.logger` 导入 `logger`，不需要 `get_logger()`

### 步骤5：注册Agent到会话管理器

编辑 `flask_backend/session_manager.py`，注册新的Agent：

```python
from agents.chatbi_agent import ChatBIAgent

# 在 _create_agent 方法中添加
def _create_agent(self, agent_type: str):
    if agent_type == "chatbi":
        return ChatBIAgent()
    # ... 其他Agent类型
```

### 步骤6：验证和测试

1. 启动开发服务器：`npm run dev`
2. 打开浏览器访问 `http://localhost:3000`
3. 在Agent选择页面验证新Agent是否正确显示
4. 测试Agent的对话功能是否正常

## 📝 配置文件说明

### Agent面具配置参数

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| avatar | string | emoji代码，用作Agent头像 | "1f4ca" |
| name | string | Agent显示名称 | "ChatBI" |
| agentType | string | Agent类型标识，用于后端路由 | "chatbi" |
| context | array | 预设对话上下文 | 见上方示例 |
| modelConfig | object | 模型配置参数 | 见下方详细说明 |
| lang | string | 语言标识 | "cn" |
| builtin | boolean | 是否为内置Agent | true |
| createdAt | number | 创建时间戳 | 1688899480510 |

### 模型配置参数

| 参数 | 类型 | 说明 | 推荐值 |
|------|------|------|--------|
| model | string | 使用的模型名称 | "qwen-turbo-latest" |
| temperature | number | 创造性程度 (0-1) | 分析类:0.3, 创意类:0.7-0.8 |
| max_tokens | number | 最大输出长度 | 2000 |
| historyMessageCount | number | 历史消息数量 | 8-16 |
| sendMemory | boolean | 是否发送历史记忆 | true |

## 💡 最佳实践

### 1. Agent命名规范
- **agentType**: 使用小写字母和下划线，如 `chatbi`, `text_to_image`
- **name**: 使用简洁明了的中文名称，如 "ChatBI", "AI文生图"
- **文件命名**: 使用 `{agent_type}_agent.py` 格式

### 2. 温度参数设置指南
- **分析类Agent** (如ChatBI): 0.1-0.3 (确保准确性)
- **对话类Agent** (如客服): 0.4-0.6 (平衡准确性和自然度)
- **创意类Agent** (如文生图): 0.7-0.9 (增强创造性)

### 3. 上下文设计原则
- 包含系统角色定义
- 提供典型用户问题示例
- 展示期望的回复风格
- 控制上下文长度，避免过长

### 4. 推荐问题设计
- **问题数量**：每个Agent必须提供**恰好3个**推荐问题（标准配置）
- **问题质量**：问题要具体且实用，体现Agent的核心功能
- **用户体验**：使用用户友好的语言，避免过于技术化的表述
- **功能覆盖**：3个问题应覆盖Agent的主要使用场景
- **完整性原则**：问题应该足够具体和完整，让AI能够在一次对话中给出有价值的完整答案，避免用户需要补充额外信息
- **具体化要求**：避免过于宽泛的问题，应包含具体的数量、范围、场景等限定条件
- **实用导向**：问题应直接指向用户的实际需求，提供可操作的建议或具体的解决方案

### 5. Agent类实现规范
- **继承方式**：直接继承BaseAgent，不要重写 `__init__` 方法
- **必需方法**：必须实现 `get_system_prompt()` 和 `get_function_list()` 抽象方法
- **可选重写**：可以重写 `get_agent_name()`、`get_agent_description()`、`get_mcp_config()` 等方法
- **类型注解**：使用正确的类型注解，如 `Optional[Dict[str, Any]]` 用于MCP配置
- **导入语句**：包含必要的导入语句，特别是类型注解相关的导入

### 6. MCP配置最佳实践
- **返回类型**：使用 `Optional[Dict[str, Any]]` 作为返回类型
- **配置结构**：遵循标准的MCP服务器配置格式
- **服务命名**：使用有意义的服务名称，便于识别和维护
- **URL配置**：确保MCP服务URL的正确性和可访问性

### 5. 推荐问题配置规范
- **配置位置**：必须添加到 `AGENT_QUESTIONS_CONFIG` 数组中
- **必要字段**：确保包含 `agentType`、`name`、`questions`、`description` 四个字段
- **问题数量**：每个Agent必须配置**恰好3个**推荐问题，不多不少
- **类型一致性**：`agentType` 必须与面具配置中的 `agentType` 完全一致
- **配置验证**：添加配置后立即运行 `npm run mask` 验证配置是否正确
- **避免重复**：不要在 `DEFAULT_QUESTIONS` 数组中添加特定Agent的配置
- **问题优化标准**：
  - 避免需要用户补充信息的开放性问题
  - 包含具体的数量指标（如"5个方法"、"3种类型"）
  - 明确指定范围和场景（如"适合初学者"、"200元预算"）
  - 提供完整的解决方案描述（如"包括步骤和示例"）

## ❓ 常见问题

### Q1: 新增Agent后在界面上看不到？
**A**: 检查以下步骤：
1. 确认已运行 `npm run mask` 构建命令
2. 检查 `public/masks.json` 是否包含新Agent
3. 刷新浏览器缓存
4. 检查控制台是否有错误信息

### Q2: Agent对话功能不正常？
**A**: 检查以下配置：
1. `agentType` 是否与后端注册的类型一致
2. 后端Agent类是否正确实现
3. 会话管理器是否正确注册Agent
4. 检查后端日志是否有错误

### Q2.1: 创建Agent时出现 "BaseAgent.__init__() missing required positional arguments" 错误？
**A**: 这是因为BaseAgent需要必需的初始化参数：
1. **错误原因**：BaseAgent的构造函数需要 `agent_id` 和 `user_id` 参数
2. **解决方案**：不要重写 `__init__` 方法，使用BaseAgent的标准初始化
3. **正确做法**：直接继承BaseAgent，重写必要的方法即可

**错误示例**（不要这样做）：
```python
class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__()  # 错误：缺少必需参数
        # ...
```

**正确示例**：
```python
class MyAgent(BaseAgent):
    """我的Agent"""
    
    def get_agent_name(self) -> str:
        return "我的Agent"
    
    def get_agent_description(self) -> str:
        return "Agent描述"
    
    # 其他必需方法...
```

### Q2.2: 出现 "Assistant.__init__() got an unexpected keyword argument 'mcp_config'" 错误？
**A**: 这是MCP配置传递方式的问题：
1. **错误原因**：Assistant类不直接接受 `mcp_config` 参数
2. **解决方案**：通过 `get_mcp_config()` 方法返回MCP配置
3. **系统处理**：BaseAgent会自动处理MCP配置的传递

**正确的MCP配置方式**：
```python
def get_mcp_config(self) -> Optional[Dict[str, Any]]:
    """重写MCP配置"""
    return {
        "mcpServers": {
            "服务名称": {
                "type": "sse",
                "url": "服务URL"
            }
        }
    }
```

### Q2.3: 如何验证Agent是否正确实现？
**A**: 使用以下测试方法验证Agent实现：

**基础测试**（在项目根目录下运行）：
```bash
# 进入Python环境
cd flask_backend
python -c "from agents.your_agent_name import YourAgentClass; agent = YourAgentClass(agent_id='test', user_id='test'); print('Agent名称:', agent.get_agent_name()); print('Agent描述:', agent.get_agent_description())"
```

**完整测试**：
```python
# 创建测试文件 test_agent.py
from agents.your_agent_name import YourAgentClass

def test_agent():
    try:
        # 创建Agent实例
        agent = YourAgentClass(agent_id="test_agent", user_id="test_user")
        
        # 测试基本方法
        print(f"Agent名称: {agent.get_agent_name()}")
        print(f"Agent描述: {agent.get_agent_description()}")
        print(f"系统提示词长度: {len(agent.get_system_prompt())}")
        print(f"工具列表: {agent.get_function_list()}")
        print(f"MCP配置: {agent.get_mcp_config()}")
        
        print("✅ Agent测试通过！")
        
    except Exception as e:
        print(f"❌ Agent测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_agent()
```

**常见测试错误和解决方案**：

**错误1**: `TypeError: BaseAgent.__init__() missing 2 required positional arguments: 'agent_id' and 'user_id'`
- **原因**：测试时没有提供必需的参数
- **解决**：测试时必须提供这两个参数
```python
# 正确的测试方式
agent = MyAgent(agent_id="test_agent", user_id="test_user")
print(agent.get_agent_name())
```

**错误2**: `TypeError: can't instantiate abstract class with abstract methods`
- **原因**：没有实现所有必需的抽象方法
- **解决**：确保实现了 `get_system_prompt()` 和 `get_function_list()` 方法

**错误3**: `TypeError: Assistant.__init__() got an unexpected keyword argument 'mcp_config'`
- **原因**：MCP配置传递方式不正确或BaseAgent内部处理有问题
- **解决**：检查 `get_mcp_config()` 方法的实现和返回类型，确保返回 `Optional[Dict[str, Any]]`

**错误4**: `ImportError` 或 `ModuleNotFoundError`
- **原因**：导入语句不正确或缺少必要的依赖
- **解决**：检查导入语句，确保所有必要的模块都已正确导入

**错误5**: `AttributeError: 'NoneType' object has no attribute`
- **原因**：某个方法返回了None而不是期望的类型
- **解决**：检查所有方法的返回值，确保类型正确

### Q3: 如何修改现有Agent？
**A**: 
1. 修改 `app/masks/cn.ts` 中的配置
2. 运行 `npm run mask` 重新构建
3. 如需修改后端逻辑，编辑对应的Agent实现文件
4. 重启开发服务器

### Q4: Agent推荐问题显示不正确或不显示？
**A**: 这是一个常见的配置错误，检查以下几点：
1. **配置位置错误**：确认推荐问题配置是否添加到了 `AGENT_QUESTIONS_CONFIG` 数组中，而不是 `DEFAULT_QUESTIONS` 数组中
2. **配置格式错误**：确认配置对象包含必要字段：`agentType`、`name`、`questions`、`description`
3. **agentType不匹配**：确认 `agentType` 与面具配置中的 `agentType` 完全一致
4. **重新构建**：修改配置后运行 `npm run mask` 重新构建
5. **清除缓存**：刷新浏览器缓存或硬刷新页面

**错误示例**（不要这样做）：
```typescript
// 错误：添加到 DEFAULT_QUESTIONS 数组中
DEFAULT_QUESTIONS.push({
  agentType: "chatbi",
  questions: [...]
});
```

**正确示例**：
```typescript
// 正确：添加到 AGENT_QUESTIONS_CONFIG 数组中
AGENT_QUESTIONS_CONFIG.push({
  agentType: "chatbi",
  name: "ChatBI",
  questions: [...],
  description: "..."
});
```

### Q5: 为什么推荐问题必须是3个？可以配置更多或更少吗？
**A**: 推荐问题数量标准化为3个是基于以下考虑：
1. **用户体验**：3个问题既能展示Agent核心功能，又不会让界面过于拥挤
2. **认知负荷**：用户可以快速浏览和选择，避免选择困难
3. **界面设计**：前端界面针对3个问题进行了优化布局
4. **维护一致性**：统一的数量标准便于维护和管理

如果确实需要更多问题，建议：
- 选择最具代表性的3个核心问题
- 将其他问题整合到Agent的系统提示中
- 通过对话引导用户了解更多功能

### Q8: Agent开发的完整最佳实践有哪些？
**A**: 遵循以下最佳实践可以避免大部分常见问题：

**1. 代码结构最佳实践**：
```python
from .base_agent import BaseAgent
from typing import List, Dict, Any, Optional
from utils.logger import logger

class MyAgent(BaseAgent):
    """Agent的简短描述"""
    
    def get_agent_name(self) -> str:
        """返回Agent显示名称"""
        return "我的Agent"
    
    def get_agent_description(self) -> str:
        """返回Agent描述，支持emoji"""
        return "专业的助手🤖"
    
    def get_system_prompt(self) -> str:
        """返回详细的系统提示词"""
        return """我是...
        
        我的专长包括：
        1. ...
        2. ...
        
        我会...
        """
    
    def get_function_list(self) -> List[str]:
        """返回工具函数列表"""
        return []  # 或返回具体的工具列表
    
    def get_mcp_config(self) -> Optional[Dict[str, Any]]:
        """返回MCP配置（可选）"""
        return None  # 或返回具体的MCP配置
```

**2. 系统提示词编写最佳实践**：
- **身份定位**：明确说明Agent的角色和专长
- **能力描述**：详细列出能提供的服务和功能
- **交互方式**：说明如何与用户互动
- **限制说明**：明确不能做什么
- **输出格式**：指定回答的格式和风格

**3. 推荐问题设计最佳实践**：
- **具体化**：避免"帮我分析一下"这样的泛泛问题
- **完整性**：问题应包含足够的上下文信息
- **实用性**：直接指向用户的实际需求
- **多样性**：覆盖Agent的不同使用场景

**4. 错误处理最佳实践**：
- **充分测试**：在集成前先进行单元测试
- **日志记录**：使用logger记录关键操作和错误
- **异常处理**：在关键方法中添加try-catch
- **类型检查**：使用类型注解提高代码质量

**5. 开发流程最佳实践**：
1. **规划阶段**：明确Agent的功能定位和目标用户
2. **设计阶段**：设计系统提示词和推荐问题
3. **实现阶段**：按照本文档的规范实现Agent类
4. **测试阶段**：使用本文档提供的测试方法验证实现
5. **集成阶段**：添加前端配置并注册到会话管理器
6. **验证阶段**：在完整系统中测试Agent功能
7. **优化阶段**：根据使用反馈优化提示词和功能

### Q6: 如何设计高质量的推荐问题？
**A**: 高质量推荐问题应遵循"一次性完整回答"原则：

**❌ 不好的问题示例**：
- "如何提高编程技能？" （过于宽泛，需要用户补充具体方向）
- "帮我分析数据" （缺少具体数据和分析目标）
- "推荐一些餐厅" （缺少地点、预算、场合等信息）

**✅ 优化后的问题示例**：
- "列出5个提高编程技能的具体实践项目，从简单到复杂逐步进阶"
- "请展示如何使用SQL分析电商平台各省份销售数据，包括查询语句和可视化图表示例"
- "推荐北京5家适合商务宴请的川菜餐厅，包括地址、人均消费、特色菜品和预订方式"

**优化要点**：
1. **具体数量**：明确指定需要的数量（如"5个方法"、"3种类型"）
2. **明确范围**：指定适用场景、预算、地点等限制条件
3. **完整描述**：说明期望的回答内容和格式
4. **实用导向**：直接解决用户的实际问题

### Q7: 如何删除Agent？
**A**:
1. 从 `app/masks/cn.ts` 中移除对应配置
2. 从 `app/config/suggested-questions.ts` 中移除相关配置
3. 运行 `npm run mask` 重新构建
4. 删除后端对应的Agent实现文件
5. 从会话管理器中移除注册

## 🔧 维护指南

### 定期维护任务

1. **检查Agent性能**
   - 监控响应时间
   - 检查错误率
   - 分析用户反馈

2. **更新推荐问题**
   - 根据用户使用情况调整
   - 添加新的热门问题
   - 移除过时的问题

3. **优化模型参数**
   - 根据实际效果调整temperature
   - 优化历史消息数量
   - 调整输出长度限制

### 版本控制建议

1. **提交规范**
   ```
   feat(agent): 新增ChatBI数据分析Agent
   fix(agent): 修复美食推荐Agent响应问题
   docs(agent): 更新Agent开发文档
   ```

2. **分支管理**
   - 为每个新Agent创建独立的feature分支
   - 完成测试后合并到主分支
   - 保持主分支的稳定性

### 监控和日志

1. **前端监控**
   - 使用 `app/utils/logger.ts` 记录关键操作
   - 监控Agent选择和切换事件
   - 记录用户交互数据

2. **后端监控**
   - 使用 `flask_backend/utils/logger.py` 记录处理过程
   - 监控Agent响应时间
   - 记录错误和异常情况

## 📚 相关资源

- [项目README](../README.md)
- [API文档](./api-documentation.md)
- [部署指南](./deployment-guide.md)
- [故障排除](./troubleshooting.md)

## 🔍 故障排除快速指南

### 常见错误速查表

| 错误类型 | 错误信息 | 解决方案 |
|---------|---------|----------|
| 初始化错误 | `missing required positional arguments` | 测试时提供 `agent_id` 和 `user_id` 参数 |
| 抽象方法错误 | `can't instantiate abstract class` | 实现 `get_system_prompt()` 和 `get_function_list()` 方法 |
| MCP配置错误 | `unexpected keyword argument 'mcp_config'` | 检查 `get_mcp_config()` 返回类型 |
| 导入错误 | `ModuleNotFoundError` | 检查导入路径和依赖安装 |
| 配置错误 | 推荐问题不显示 | 确认配置在 `AGENT_QUESTIONS_CONFIG` 中 |
| 界面错误 | Agent不显示 | 运行 `npm run mask` 重新构建 |

### 调试技巧

1. **使用日志调试**：
```python
from utils.logger import logger

class MyAgent(BaseAgent):
    def get_system_prompt(self) -> str:
        logger.info("正在获取系统提示词")
        prompt = "我是..."
        logger.debug(f"系统提示词长度: {len(prompt)}")
        return prompt
```

2. **分步测试**：
```python
# 测试Agent创建
try:
    agent = MyAgent(agent_id="test", user_id="test")
    print("✅ Agent创建成功")
except Exception as e:
    print(f"❌ Agent创建失败: {e}")
    
# 测试方法调用
try:
    name = agent.get_agent_name()
    print(f"✅ Agent名称: {name}")
except Exception as e:
    print(f"❌ 获取名称失败: {e}")
```

3. **配置验证**：
```bash
# 验证面具配置
cat public/masks.json | grep "agentType"

# 验证推荐问题配置
grep -n "agentType" app/config/suggested-questions.ts
```

## 📋 开发检查清单

### 新增Agent前检查
- [ ] 确定Agent的功能定位和目标用户
- [ ] 设计好系统提示词和推荐问题
- [ ] 确认 `agentType` 在系统中唯一
- [ ] 准备好Agent的头像emoji

### 实现阶段检查
- [ ] 正确继承BaseAgent，不重写 `__init__`
- [ ] 实现所有必需的抽象方法
- [ ] 使用正确的类型注解
- [ ] 添加适当的文档字符串
- [ ] 实现单元测试

### 配置阶段检查
- [ ] 在 `app/masks/cn.ts` 中添加面具配置
- [ ] 在 `AGENT_QUESTIONS_CONFIG` 中添加推荐问题（恰好3个）
- [ ] 运行 `npm run mask` 构建配置
- [ ] 在会话管理器中注册Agent

### 测试阶段检查
- [ ] 单元测试通过
- [ ] Agent在界面上正确显示
- [ ] 推荐问题正确显示
- [ ] 对话功能正常工作
- [ ] 错误处理正常

### 部署前检查
- [ ] 代码通过所有测试
- [ ] 文档更新完整
- [ ] 配置文件正确
- [ ] 性能测试通过

---

**最后更新**: 2024年12月
**维护者**: IFishAI开发团队

**更新记录**:
- 2024年12月: 新增推荐问题配置的详细说明和常见错误解决方案
- 强调了 `AGENT_QUESTIONS_CONFIG` 与 `DEFAULT_QUESTIONS` 的区别
- 添加了推荐问题配置规范和最佳实践
- 标准化推荐问题数量：每个Agent必须配置恰好3个推荐问题
- 优化推荐问题质量：实施"一次性完整回答"原则，避免用户需要补充信息
- 新增推荐问题设计指南：包含具体数量、明确范围、完整描述等优化要点
- 提供问题优化前后对比示例，帮助开发者设计高质量推荐问题
- 新增故障排除快速指南和开发检查清单
- 添加更多实用的错误处理和调试技巧
- 完善最佳实践建议，涵盖完整的开发流程

> 💡 **提示**: 本文档会随着系统更新而持续维护，建议定期查看最新版本。
> 
> ⚠️ **特别注意**: 
> - 配置推荐问题时，请务必将Agent配置添加到 `AGENT_QUESTIONS_CONFIG` 数组中，避免常见的配置位置错误
> - 每个Agent必须配置恰好3个推荐问题，这是系统的标准配置要求
> - 开发过程中遇到问题时，请先查阅故障排除快速指南，大部分常见问题都有对应的解决方案