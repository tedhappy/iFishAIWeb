# 小鱼AI - 基于Qwen-Agent的智能对话平台

小鱼AI是一个基于Qwen-Agent框架开发的多功能智能对话平台，集成了多种AI模型、专业Agent助手、数据分析工具和MCP工具生态，为用户提供全方位的AI服务体验。

## ✨ 核心特性

### 🤖 多模型AI支持
- **主流AI模型集成**：支持OpenAI GPT系列、Claude、Gemini、文心一言、通义千问、智谱AI等20+主流AI模型
- **多平台兼容**：兼容阿里云、百度、腾讯、字节跳动、月之暗面、科大讯飞、DeepSeek等AI服务平台
- **视觉模型支持**：支持GPT-4V、Claude Vision等多模态AI模型
- **实时语音对话**：集成语音识别和TTS功能，支持实时语音交互

### 🎯 专业Agent助手
- **通用助手**：智能聊天、问题解答、创意写作、编程帮助等全能服务
- **股票分析师**：专业的股票数据分析和投资建议
- **美食推荐师**：个性化美食推荐和餐厅查找
- **火车票查询助手**：实时火车票查询和出行规划
- **算命先生**：传统文化娱乐服务
- **可扩展架构**：支持自定义Agent开发

### 🛠️ 强大的工具生态
- **MCP协议支持**：兼容Model Context Protocol，支持丰富的第三方工具
- **内置工具集**：
  - 🗺️ 高德地图导航和位置查询
  - 🌐 网页内容抓取和解析
  - 🔍 实时搜索引擎集成
  - 🚄 12306火车票查询
  - ⏰ 时间和日期处理工具
- **数据可视化**：支持图表生成和数据分析展示

### 🏢 企业级功能
- **会话管理**：支持多会话并发，会话持久化存储
- **用户认证**：完整的用户管理和权限控制系统
- **API接口**：RESTful API设计，支持第三方集成
- **配置灵活**：丰富的环境变量配置选项
- **日志监控**：完善的日志记录和错误追踪

### 🌐 跨平台支持
- **Web应用**：基于Next.js的现代化Web界面
- **桌面应用**：支持Tauri打包的跨平台桌面应用
- **移动端适配**：响应式设计，完美适配移动设备
- **容器化部署**：支持Docker容器化部署

## 🏗️ 技术架构

### 前端技术栈
- **框架**：Next.js 14 + React 18
- **语言**：TypeScript
- **样式**：Sass + CSS Modules
- **状态管理**：Zustand
- **UI组件**：自定义组件库
- **桌面应用**：Tauri 2.x

### 后端技术栈
- **框架**：Flask + Python
- **AI引擎**：Qwen-Agent框架
- **协议支持**：MCP (Model Context Protocol)
- **数据存储**：JSON文件存储（支持扩展数据库）
- **API设计**：RESTful API

### 核心依赖
- `@modelcontextprotocol/sdk`：MCP协议支持
- `qwen-agent`：AI Agent框架
- `axios`：HTTP客户端
- `mermaid`：图表渲染
- `react-markdown`：Markdown渲染

## 🚀 快速开始

### 环境要求
- Node.js 18+
- Python 3.8+
- Yarn 或 npm

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd IFishAIWeb
```

2. **安装前端依赖**
```bash
yarn install
# 或
npm install
```

3. **安装后端依赖**
```bash
cd flask_backend
pip install -r requirements.txt
```

4. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，配置API密钥
```

5. **启动开发服务器**
```bash
# 启动前端
yarn dev

# 启动后端（新终端）
cd flask_backend
python app.py
```

### 环境变量配置

```env
# AI模型API配置
ALIBABA_API_KEY=your_alibaba_api_key

# MCP功能配置
ENABLE_MCP=true

# 应用配置
NEXT_PUBLIC_API_BASE_URL=http://localhost:5000
```

## 📦 部署方案

### Docker部署
```bash
# 构建镜像
docker build -t ifishai .

# 运行容器
docker run -p 3000:3000 -p 5000:5000 ifishai
```

### 宝塔面板部署
1. 上传项目文件到服务器
2. 配置Node.js和Python环境
3. 设置反向代理
4. 配置SSL证书

### 桌面应用打包
```bash
# 开发模式
yarn app:dev

# 构建桌面应用
yarn app:build
```

## 🔧 开发指南

### TypeScript编译检查

在开发过程中，可以使用以下命令检查TypeScript编译错误：

```bash
# 检查TypeScript编译错误（不生成输出文件）
npx tsc --noEmit
```

该命令会检查整个项目的TypeScript代码，报告类型错误和编译问题，但不会生成JavaScript文件。这对于在开发过程中快速发现和修复类型相关的问题非常有用。

### 自定义Agent开发

1. **创建Agent类**
```python
from agents.base_agent import BaseAgent

class CustomAgent(BaseAgent):
    def get_agent_name(self) -> str:
        return "自定义助手"
    
    def get_agent_description(self) -> str:
        return "这是一个自定义的AI助手"
    
    def get_system_prompt(self) -> str:
        return "你的系统提示词"
```

2. **注册Agent**
在 `session_manager.py` 中添加Agent类型映射

### MCP工具集成

1. **配置MCP服务器**
2. **注册工具到管理器**
3. **在Agent中调用工具**

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request来帮助改进项目！

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- GitHub Issues
- 项目讨论区

---

**小鱼AI** - 让AI更智能，让交互更自然 🐟✨