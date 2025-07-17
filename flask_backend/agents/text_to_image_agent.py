from .base_agent import BaseAgent
from qwen_agent.agents import Assistant
from typing import List, Dict, Any, Optional
from utils.logger import logger



class TextToImageAgent(BaseAgent):
    """AI文生图助手Agent"""
    
    def get_agent_name(self) -> str:
        """重写Agent名称"""
        return 'AI文生图助手'
    
    def get_agent_description(self) -> str:
        """重写Agent描述"""
        return '创意无限的AI绘画师小鱼🐟，能根据你的文字描述生成精美图像，让想象变成现实！'
    
    def get_mcp_config(self) -> Optional[Dict[str, Any]]:
        """重写MCP配置，指定使用文生图相关的MCP工具
        
        Returns:
            Dict[str, Any]: 包含ModelScope和MiniMax文生图工具的MCP配置
        """
        return {
            "mcpServers": {
                "ModelScope-Image-Generation-MCP": {
                    "type": "sse",
                    "url": "https://mcp.api-inference.modelscope.net/eef5f8c388d047/sse"
                },
                "MiniMax-MCP": {
                    "type": "sse",
                    "url": "https://mcp.api-inference.modelscope.net/237368dc90a642/sse"
                }
            }
        }
    
    def get_system_prompt(self) -> str:
        return """嗨！我是你的专业AI文生图助手小鱼🐟，专门帮你把文字变成精美的图像！🎨

**我的创作能力：**
• 🖼️ **多平台支持**：集成ModelScope和MiniMax两大AI图像生成平台
• 🎯 **精准理解**：准确理解你的描述，生成符合预期的图像
• ✨ **智能优化**：自动选择最适合的生成模型和参数
• 📐 **多尺寸支持**：支持不同比例和分辨率的图像生成
• 🎭 **风格丰富**：写实、动漫、艺术、抽象等多种风格
• 🔄 **快速生成**：利用云端GPU加速，快速出图

**支持的生成平台：**
- **ModelScope平台**：阿里达摩院开源模型，支持多种AIGC模型
- **MiniMax平台**：专业的AI内容生成服务，图像质量优秀

**使用建议：**
1. 📝 **详细描述**：越具体的描述，生成效果越好
2. 🎨 **指定风格**：可以要求特定的艺术风格或画风
3. 📏 **说明用途**：告诉我图片的用途，我会选择合适的尺寸
4. 🔄 **多次尝试**：不同平台可能有不同效果，可以尝试多个

**示例用法：**
- "帮我生成一张写实风格的夕阳海滩图片"
- "画一个动漫风格的可爱猫咪，要有大眼睛"
- "创作一幅中国山水画风格的风景图"
- "生成一个科幻风格的未来城市场景"

我会根据你的需求，智能选择最适合的AI模型来为你生成图像。让我们开始创作吧！🌟"""
    
    def get_function_list(self) -> List[str]:
        return []