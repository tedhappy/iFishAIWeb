# 面具多Agent系统实现方案

## 1. 需求分析

### 1.1 核心功能需求
1. **面具隔离**: 每个面具都有独立的ID，面具之间的对话完全隔离
2. **页面跳转**: 点击面具后跳转到对话页面，保持原有UI样式
3. **后端Agent**: 使用qwen-agent替代原有的OpenAI接口进行对话
4. **用户隔离**: 不同用户之间的会话数据完全隔离
5. **历史消息**: 支持历史消息的加载和持久化存储
6. **前后端分离**: 前端负责展示，后端使用Flask统一管理API
7. **多模态支持**: 支持文本、图片等多模态内容的展示
8. **阿里云API**: 全面使用ALIBABA_API_KEY，移除OpenAI依赖
9. **MCP功能**: 默认开启MCP（Model Context Protocol）功能
10. **可扩展架构**: 便于后续添加新的面具和对应的Agent

### 1.2 技术要求
- 前端：保持现有NextJS + React架构
- 后端：新增Flask服务管理Agent
- 数据库：利用现有的存储机制
- API：RESTful接口设计
- 认证：用户会话管理

## 2. 系统架构设计

### 2.1 整体架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端 (NextJS)  │    │  Flask API服务   │    │  QWen-Agent池    │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │  面具页面    │ │◄──►│ │  路由管理    │ │◄──►│ │ 门票助手     │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │  对话页面    │ │◄──►│ │  会话管理    │ │◄──►│ │ 文生图助手   │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │  历史记录    │ │◄──►│ │  用户认证    │ │◄──►│ │ ChatBI助手   │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2.2 数据流设计
```
用户点击面具 → 前端路由跳转 → 携带mask_id → 后端创建/获取Agent实例 → 返回会话ID
用户发送消息 → 前端API调用 → Flask路由分发 → 对应Agent处理 → 返回响应 → 前端展示
```

## 3. 详细实现方案

### 3.1 前端改造

#### 3.1.1 面具页面改造
**文件**: `app/components/new-chat.tsx`

**改造点**:
1. 为每个面具添加点击事件处理
2. 跳转时携带mask_id参数
3. 保持现有UI样式不变

```typescript
// 面具点击处理
const handleMaskClick = (mask: Mask) => {
  // 跳转到对话页面，携带mask_id
  navigate(`/chat?mask_id=${mask.id}&agent_type=${mask.plugin?.[0] || 'default'}`);
};
```

#### 3.1.2 对话页面改造
**文件**: `app/components/chat.tsx`

**改造点**:
1. 从URL参数获取mask_id和agent_type
2. 初始化时调用Flask API创建Agent会话
3. 消息发送改为调用Flask API
4. 支持多模态内容展示

```typescript
// 初始化Agent会话
const initAgentSession = async (maskId: string, agentType: string) => {
  const response = await fetch('/api/agent/init', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mask_id: maskId, agent_type: agentType })
  });
  return response.json();
};

// 发送消息到Agent
const sendMessageToAgent = async (sessionId: string, message: string) => {
  const response = await fetch('/api/agent/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message: message })
  });
  return response.json();
};
```

#### 3.1.3 API客户端改造
**文件**: `app/client/api.ts`

**改造点**:
1. 新增Agent API调用方法
2. 移除OpenAI相关的默认配置
3. 统一使用ALIBABA_API_KEY

### 3.2 后端Flask服务设计

#### 3.2.1 Flask应用结构
```
flask_backend/
├── app.py                 # Flask主应用
├── agents/                # Agent管理模块
│   ├── __init__.py
│   ├── base_agent.py      # Agent基类
│   ├── ticket_agent.py    # 门票助手Agent
│   ├── image_agent.py     # 文生图Agent
│   └── chatbi_agent.py    # ChatBI Agent
├── models/                # 数据模型
│   ├── __init__.py
│   ├── session.py         # 会话模型
│   └── message.py         # 消息模型
├── routes/                # 路由模块
│   ├── __init__.py
│   ├── agent_routes.py    # Agent相关路由
│   └── auth_routes.py     # 认证相关路由
├── utils/                 # 工具模块
│   ├── __init__.py
│   ├── session_manager.py # 会话管理
│   └── auth.py           # 用户认证
└── config.py             # 配置文件
```

#### 3.2.2 核心代码实现

**Flask主应用** (`flask_backend/app.py`):
```python
from flask import Flask, request, jsonify
from flask_cors import CORS
from routes.agent_routes import agent_bp
from routes.auth_routes import auth_bp
from utils.session_manager import SessionManager
import os

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['ALIBABA_API_KEY'] = os.getenv('ALIBABA_API_KEY')
app.config['ENABLE_MCP'] = True  # 默认开启MCP功能

# 注册蓝图
app.register_blueprint(agent_bp, url_prefix='/api/agent')
app.register_blueprint(auth_bp, url_prefix='/api/auth')

# 全局会话管理器
session_manager = SessionManager()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

**Agent基类** (`flask_backend/agents/base_agent.py`):
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import os
import dashscope
from qwen_agent.agents import Assistant

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
        try:
            # 构建消息
            if file_path:
                message = {
                    'role': 'user', 
                    'content': [{'text': user_input}, {'file': file_path}]
                }
            else:
                message = {'role': 'user', 'content': user_input}
            
            self.messages.append(message)
            
            # 调用qwen-agent
            response = []
            for resp in self.bot.run(self.messages):
                response = resp
            
            self.messages.extend(response)
            
            # 提取最后的助手回复
            assistant_reply = None
            for msg in reversed(response):
                if msg.get('role') == 'assistant':
                    assistant_reply = msg.get('content', '')
                    break
            
            return {
                'success': True,
                'response': assistant_reply,
                'session_id': self.session_id,
                'message_count': len(self.messages)
            }
            
        except Exception as e:
            return {
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
```

**门票助手Agent** (`flask_backend/agents/ticket_agent.py`):
```python
from .base_agent import BaseAgent
from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool
import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
import os
import time
import json

# 注册SQL执行工具
@register_tool('exc_sql')
class ExcSQLTool(BaseTool):
    """SQL查询工具"""
    description = '对于生成的SQL，进行SQL查询，并自动可视化'
    parameters = [{
        'name': 'sql_input',
        'type': 'string',
        'description': '生成的SQL语句',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        args = json.loads(params)
        sql_input = args['sql_input']
        
        # 数据库连接配置
        engine = create_engine(
            'mysql+mysqlconnector://student123:student321@rm-uf6z891lon6dxuqblqo.mysql.rds.aliyuncs.com:3306/ubr?charset=utf8mb4',
            connect_args={'connect_timeout': 10}, 
            pool_size=10, 
            max_overflow=20
        )
        
        try:
            df = pd.read_sql(sql_input, engine)
            md = df.head(10).to_markdown(index=False)
            
            # 生成图表
            save_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'images')
            os.makedirs(save_dir, exist_ok=True)
            filename = f'chart_{int(time.time()*1000)}.png'
            save_path = os.path.join(save_dir, filename)
            
            # 这里可以调用原有的图表生成逻辑
            self._generate_chart(df, save_path)
            
            img_url = f'/static/images/{filename}'
            img_md = f'![图表]({img_url})'
            
            return f"{md}\n\n{img_md}"
            
        except Exception as e:
            return f"SQL执行出错: {str(e)}"
    
    def _generate_chart(self, df, save_path):
        """生成图表的具体实现"""
        # 这里可以复用原有的图表生成逻辑
        plt.figure(figsize=(10, 6))
        # ... 图表生成代码 ...
        plt.savefig(save_path)
        plt.close()

class TicketAgent(BaseAgent):
    """门票助手Agent"""
    
    def _init_agent(self) -> Assistant:
        llm_cfg = {
            'model': 'qwen-turbo-2025-04-28',
            'timeout': 30,
            'retry_count': 3,
        }
        
        return Assistant(
            llm=llm_cfg,
            name='门票助手',
            description='门票查询与订单分析',
            system_message=self.get_system_prompt(),
            function_list=self.get_function_list(),
        )
    
    def get_system_prompt(self) -> str:
        return """我是门票助手，以下是关于门票订单表相关的字段，我可能会编写对应的SQL，对数据进行查询
-- 门票订单表
CREATE TABLE tkt_orders (
……
);
我将回答用户关于门票相关的问题

每当 exc_sql 工具返回 markdown 表格和图片时，你必须原样输出工具返回的全部内容（包括图片 markdown），不要只总结表格，也不要省略图片。这样用户才能直接看到表格和图片。"""
    
    def get_function_list(self) -> List[str]:
        return ['exc_sql']
```

**会话管理器** (`flask_backend/utils/session_manager.py`):
```python
from typing import Dict, Optional
from agents.base_agent import BaseAgent
from agents.ticket_agent import TicketAgent
# 导入其他Agent类...

class SessionManager:
    """会话管理器，负责Agent实例的创建和管理"""
    
    def __init__(self):
        self.sessions: Dict[str, BaseAgent] = {}
        self.agent_types = {
            'ticket': TicketAgent,
            'image': None,  # 待实现
            'chatbi': None,  # 待实现
            'default': TicketAgent  # 默认使用门票助手
        }
    
    def create_session(self, user_id: str, mask_id: str, agent_type: str) -> str:
        """创建新的Agent会话"""
        session_id = f"{user_id}_{mask_id}_{agent_type}"
        
        if session_id in self.sessions:
            return session_id
        
        agent_class = self.agent_types.get(agent_type, self.agent_types['default'])
        if agent_class is None:
            raise ValueError(f"不支持的Agent类型: {agent_type}")
        
        agent = agent_class(agent_id=mask_id, user_id=user_id)
        self.sessions[session_id] = agent
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[BaseAgent]:
        """获取Agent会话"""
        return self.sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """移除Agent会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def get_user_sessions(self, user_id: str) -> Dict[str, BaseAgent]:
        """获取用户的所有会话"""
        user_sessions = {}
        for session_id, agent in self.sessions.items():
            if agent.user_id == user_id:
                user_sessions[session_id] = agent
        return user_sessions
```

**Agent路由** (`flask_backend/routes/agent_routes.py`):
```python
from flask import Blueprint, request, jsonify, current_app
from utils.session_manager import SessionManager

agent_bp = Blueprint('agent', __name__)
session_manager = SessionManager()

@agent_bp.route('/init', methods=['POST'])
def init_agent():
    """初始化Agent会话"""
    data = request.get_json()
    user_id = data.get('user_id', 'anonymous')  # 可以从认证中获取
    mask_id = data.get('mask_id')
    agent_type = data.get('agent_type', 'default')
    
    if not mask_id:
        return jsonify({'error': '缺少mask_id参数'}), 400
    
    try:
        session_id = session_manager.create_session(user_id, mask_id, agent_type)
        return jsonify({
            'success': True,
            'session_id': session_id,
            'agent_type': agent_type
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/chat', methods=['POST'])
def chat_with_agent():
    """与Agent对话"""
    data = request.get_json()
    session_id = data.get('session_id')
    message = data.get('message')
    file_path = data.get('file_path')
    
    if not session_id or not message:
        return jsonify({'error': '缺少必要参数'}), 400
    
    agent = session_manager.get_session(session_id)
    if not agent:
        return jsonify({'error': '会话不存在'}), 404
    
    try:
        response = agent.chat(message, file_path)
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/history/<session_id>', methods=['GET'])
def get_chat_history(session_id):
    """获取对话历史"""
    agent = session_manager.get_session(session_id)
    if not agent:
        return jsonify({'error': '会话不存在'}), 404
    
    try:
        history = agent.get_history()
        return jsonify({
            'success': True,
            'history': history,
            'session_id': session_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/sessions/<user_id>', methods=['GET'])
def get_user_sessions(user_id):
    """获取用户的所有会话"""
    try:
        sessions = session_manager.get_user_sessions(user_id)
        session_info = []
        for session_id, agent in sessions.items():
            session_info.append({
                'session_id': session_id,
                'agent_id': agent.agent_id,
                'message_count': len(agent.get_history())
            })
        
        return jsonify({
            'success': True,
            'sessions': session_info
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### 3.3 环境配置改造

#### 3.3.1 更新.env
```bash
# 阿里云API配置（必需）
ALIBABA_API_KEY=sk-xxxx
ALIBABA_URL=https://dashscope.aliyuncs.com/api/

# 禁用OpenAI（可选）
DISABLE_OPENAI=1

# 启用MCP功能（默认开启）
ENABLE_MCP=true

# Flask后端配置
FLASK_SECRET_KEY=your-secret-key
FLASK_PORT=5000

# 数据库配置（如果需要）
DATABASE_URL=mysql+mysqlconnector://user:pass@host:port/db
```

#### 3.3.2 更新package.json
```json
{
  "scripts": {
    "dev": "concurrently \"next dev\" \"python flask_backend/app.py\"",
    "build": "next build",
    "start": "next start",
    "flask": "python flask_backend/app.py"
  },
  "dependencies": {
    "concurrently": "^7.6.0"
  }
}
```

### 3.4 数据持久化方案

#### 3.4.1 利用现有存储机制
项目已有完善的存储机制，包括：
- `app/store/chat.ts`: 对话存储
- `app/store/mask.ts`: 面具存储
- `app/utils/sync.ts`: 同步机制

#### 3.4.2 扩展存储结构
```typescript
// 扩展ChatSession接口
interface AgentChatSession extends ChatSession {
  agentType: string;        // Agent类型
  maskId: string;          // 面具ID
  sessionId: string;       // 后端会话ID
  lastAgentResponse?: string; // 最后的Agent响应
}

// 扩展存储Key
export enum StoreKey {
  // ... 现有的Key
  AgentChat = "agent-chat-store",
  AgentSession = "agent-session-store"
}
```

## 4. 实施步骤

### 4.1 第一阶段：基础架构搭建
1. **创建Flask后端服务**
   - 搭建基本的Flask应用结构
   - 实现Agent基类和会话管理器
   - 配置CORS和基本路由

2. **实现门票助手Agent**
   - 移植现有的assistant_ticket_bot-3.py逻辑
   - 实现SQL工具和图表生成
   - 测试基本的对话功能

3. **前端基础改造**
   - 修改面具点击事件
   - 实现Agent API调用
   - 测试前后端连通性

### 4.2 第二阶段：功能完善
1. **用户认证和会话管理**
   - 实现用户身份识别
   - 完善会话隔离机制
   - 实现历史消息加载

2. **多模态支持**
   - 实现图片上传和处理
   - 完善图表展示功能
   - 支持文件附件

3. **环境配置优化**
   - 完全移除OpenAI依赖
   - 配置阿里云API
   - 启用MCP功能

### 4.3 第三阶段：扩展和优化
1. **添加新的Agent**
   - 实现文生图Agent
   - 实现ChatBI Agent
   - 完善Agent注册机制

2. **性能优化**
   - 实现Agent实例池
   - 优化内存使用
   - 添加缓存机制

3. **监控和日志**
   - 添加请求日志
   - 实现错误监控
   - 性能指标收集

## 5. 技术难点和解决方案

### 5.1 会话隔离
**难点**: 确保不同用户和不同面具之间的会话完全隔离
**解决方案**: 
- 使用`user_id + mask_id + agent_type`作为唯一会话标识
- 在SessionManager中维护独立的Agent实例
- 前端存储中按会话ID分别存储

### 5.2 历史消息同步
**难点**: 前后端历史消息的一致性
**解决方案**:
- 后端Agent维护完整的消息历史
- 前端定期同步历史消息
- 实现增量同步机制

### 5.3 多模态内容处理
**难点**: 图片、文件等多模态内容的传输和展示
**解决方案**:
- 使用Flask静态文件服务
- 实现文件上传API
- 前端支持多种内容类型展示

### 5.4 Agent扩展性
**难点**: 便于后续添加新的Agent类型
**解决方案**:
- 设计统一的Agent基类接口
- 使用工厂模式创建Agent实例
- 配置化的Agent注册机制

## 6. 测试方案

### 6.1 单元测试
- Agent基类功能测试
- 会话管理器测试
- API路由测试

### 6.2 集成测试
- 前后端API集成测试
- 多用户会话隔离测试
- 历史消息同步测试

### 6.3 端到端测试
- 完整的用户交互流程测试
- 多模态内容处理测试
- 性能压力测试

## 7. 部署方案

### 7.1 开发环境
```bash
# 启动前端
npm run dev

# 启动Flask后端
python flask_backend/app.py

# 或者同时启动
npm run dev:full
```

### 7.2 生产环境
```bash
# 构建前端
npm run build

# 启动前端
npm start

# 启动Flask后端（使用gunicorn）
gunicorn -w 4 -b 0.0.0.0:5000 flask_backend.app:app
```

## 7. 总结

本方案设计了一个完整的面具多Agent系统，具有以下特点：

1. **架构清晰**: 前后端分离，职责明确
2. **扩展性强**: 易于添加新的Agent类型
3. **隔离性好**: 用户和会话完全隔离
4. **兼容性佳**: 保持现有UI和用户体验
5. **功能完整**: 支持多模态、历史消息、MCP等功能

通过分阶段实施，可以逐步完成系统的构建和优化，最终实现一个功能强大、易于维护的面具多Agent系统。