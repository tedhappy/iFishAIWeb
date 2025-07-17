from .base_agent import BaseAgent
from qwen_agent.agents import Assistant
from typing import List, Dict, Any, Optional
from utils.logger import logger

class TrainTicketAgent(BaseAgent):
    """火车票查询助手Agent"""
    
    def get_agent_name(self) -> str:
        """重写Agent名称"""
        return '火车票查询助手'
    
    def get_agent_description(self) -> str:
        """重写Agent描述"""
        return '专业的火车票查询助手🚄，基于12306官方数据，为您提供准确可靠的火车出行信息！'
    
    def get_mcp_config(self) -> Optional[Dict[str, Any]]:
        """重写MCP配置，指定使用12306火车票查询MCP工具
        
        Returns:
            Dict[str, Any]: 包含12306-mcp工具的MCP配置
        """
        return {
            "mcpServers": {
                "12306-mcp": {
                    "type": "sse",
                    "url": "https://mcp.api-inference.modelscope.net/df74994c8c5b46/sse"
                }
            }
        }
    
    def get_system_prompt(self) -> str:
        return """嗨！我是您的专业火车票查询助手🚄，基于12306官方数据为您提供准确可靠的火车出行服务！

**我的查询能力：**
• 🚄 **车次查询**：查询指定线路的所有车次信息
• 🎫 **余票查询**：实时查询车票余量和座位类型
• 💰 **票价查询**：查询不同座位等级的票价信息
• 🚉 **车站信息**：查询车站详细信息和停靠车次
• ⏰ **时刻表查询**：查询列车详细时刻表和停站信息
• 📍 **正晚点信息**：查询列车运行状态和延误情况

**支持的查询类型：**
- **高铁/动车**：G字头、D字头列车
- **普速列车**：K字头、T字头、Z字头等
- **城际列车**：C字头列车
- **临客列车**：L字头临时加开列车

**查询建议：**
1. 🗓️ **提前规划**：建议提前查询，特别是节假日期间
2. 📍 **准确地名**：使用准确的城市或车站名称
3. 🕐 **灵活时间**：可以查询前后几天的车次对比
4. 💺 **多种选择**：对比不同车次的时间和价格

**使用示例：**
- "查询明天北京到上海的高铁票"
- "G1次列车的详细时刻表"
- "北京南站今天有哪些车次"
- "查询广州到深圳的城际列车票价"
- "K1次列车现在晚点了吗？"

我会利用12306官方数据接口，为您提供最准确、最及时的火车票信息。让我们开始您的火车出行查询吧！🌟"""
    
    def get_function_list(self) -> List[str]:
        return []