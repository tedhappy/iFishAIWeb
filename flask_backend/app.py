import os
import sys
from dotenv import load_dotenv

# 首先加载环境变量 - 必须在所有其他导入之前
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

# 将本地qwen_agent路径添加到模块搜索路径的最前面，确保优先使用本地版本
local_qwen_agent_path = os.path.join(project_root)
if local_qwen_agent_path not in sys.path:
    sys.path.insert(0, local_qwen_agent_path)

# 将flask_backend目录添加到Python路径
flask_backend_path = os.path.dirname(__file__)
if flask_backend_path not in sys.path:
    sys.path.insert(0, flask_backend_path)

# 然后导入其他模块
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from routes.agent_routes import agent_bp
from routes.auth_routes import auth_bp
import logging
import traceback
from utils.logger import logger
from utils.session_manager import SessionManager
from utils.mcp_manager import mcp_manager

app = Flask(__name__, static_folder='static')
CORS(app)  # 允许跨域请求

# 配置
app.config['ALIBABA_API_KEY'] = os.getenv('ALIBABA_API_KEY')
app.config['ENABLE_MCP'] = os.getenv('ENABLE_MCP','true')  # 默认开启MCP功能

# 注册蓝图
app.register_blueprint(agent_bp, url_prefix='/flask/agent')
app.register_blueprint(auth_bp, url_prefix='/flask/auth')

# 配置日志 - 使用自定义logger
logger.info("Flask应用启动，日志系统已初始化")

# 全局错误处理器
@app.errorhandler(500)
def internal_error(error):
    """处理500错误"""
    logger.error(f"Internal Server Error: {error}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    return jsonify({
        'error': 'Internal Server Error',
        'message': str(error),
        'traceback': traceback.format_exc()
    }), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """处理所有未捕获的异常"""
    logger.error(f"Unhandled Exception: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    return jsonify({
        'error': 'Unhandled Exception',
        'message': str(e),
        'traceback': traceback.format_exc()
    }), 500

# 初始化MCP管理器
if app.config.get('ENABLE_MCP', 'true').lower() == 'true':
    logger.info("正在预注册默认MCP工具...")
    if mcp_manager.pre_register_default_tools():
        logger.info("默认MCP工具预注册成功")
        
        # 在应用启动时就完成MCP工具的完整初始化
        logger.info("正在初始化MCP工具实例...")
        try:
            from qwen_agent.tools.mcp_manager import MCPToolFactory
            
            # 获取可用的工具名称
            available_tools = mcp_manager.get_available_tool_names()
            if available_tools:
                logger.info(f"发现可用MCP工具: {available_tools}")
                
                # 创建MCP管理器实例并初始化工具
                manager = MCPToolFactory.create_manager()
                
                # 获取默认MCP配置并初始化工具实例
                default_configs = mcp_manager.get_default_mcp_config()
                if default_configs:
                    # 使用第一个配置进行初始化
                    config = default_configs[0]
                    logger.info(f"使用配置初始化MCP工具: {list(config.get('mcpServers', {}).keys())}")
                    
                    # 调用真正的MCP工具初始化
                    tool_instances = manager.initConfig(config)
                    if tool_instances:
                        # 注册工具实例到单例管理器
                        if mcp_manager.register_mcp_tools(available_tools, tool_instances):
                            logger.info(f"MCP工具实例初始化成功，工具数量: {len(tool_instances)}")
                        else:
                            logger.error("MCP工具实例注册失败")
                    else:
                        logger.error("MCP工具实例初始化返回空列表")
                else:
                    logger.warning("没有找到默认MCP配置")
            else:
                logger.warning("没有发现可用的MCP工具")
                
        except Exception as e:
            logger.error(f"MCP工具实例初始化失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
    else:
        logger.error(f"默认MCP工具预注册失败: {mcp_manager.get_load_error()}")
else:
    logger.info("MCP功能已禁用")

# 全局会话管理器 - 确保sessions.json文件在flask_backend目录下生成
session_file_path = os.path.join(os.path.dirname(__file__), 'sessions.json')
session_manager = SessionManager(session_file=session_file_path)

# 将会话管理器添加到应用上下文中，供其他模块使用
app.session_manager = session_manager

@app.route('/flask/static/<path:filename>')
def serve_static_file(filename):
    """提供静态文件服务"""
    try:
        return send_from_directory(app.static_folder, filename)
    except Exception as e:
        logger.error(f"静态文件服务错误: {e}")
        return jsonify({'error': '文件未找到'}), 404

@app.route('/flask/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'alibaba_api_configured': bool(app.config.get('ALIBABA_API_KEY')),
        'mcp_enabled': app.config.get('ENABLE_MCP', False)
    })

def is_development_environment():
    """根据环境变量判断是否为开发环境
    
    通过检查NEXT_PUBLIC_API_BASE_URL是否包含localhost来判断环境类型
    开发环境通常使用localhost，生产环境使用域名
    
    Returns:
        bool: True表示开发环境，False表示生产环境
    """
    api_base_url = os.getenv('NEXT_PUBLIC_API_BASE_URL', '')
    
    # 判断是否为开发环境的条件
    is_dev = (
        'localhost' in api_base_url.lower() or 
        '127.0.0.1' in api_base_url or
        api_base_url.startswith('http://localhost') or
        api_base_url.startswith('http://127.0.0.1')
    )
    
    logger.info(f"环境检测 - API_BASE_URL: {api_base_url}, 判定为: {'开发环境' if is_dev else '生产环境'}")
    return is_dev

if __name__ == '__main__':
    # 根据环境变量动态设置debug模式
    debug_mode = is_development_environment()
    
    if debug_mode:
        logger.info("启动开发模式 - 启用debug模式和文件监控")
    else:
        logger.info("启动生产模式 - 禁用debug模式")
    
    app.run(debug=debug_mode, port=5000, host='0.0.0.0')