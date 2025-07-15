import os
from dotenv import load_dotenv

# 首先加载环境变量 - 必须在所有其他导入之前
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

# 然后导入其他模块
from flask import Flask, request, jsonify
from flask_cors import CORS
from routes.agent_routes import agent_bp
from routes.auth_routes import auth_bp
import logging
import traceback
from utils.logger import logger
from utils.session_manager import SessionManager
from utils.mcp_manager import mcp_manager

app = Flask(__name__)
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
    logger.info("正在初始化MCP工具管理器...")
    if mcp_manager.initialize_mcp_tools():
        logger.info("MCP工具管理器初始化成功")
    else:
        logger.error(f"MCP工具管理器初始化失败: {mcp_manager.get_load_error()}")
else:
    logger.info("MCP功能已禁用")

# 全局会话管理器
session_manager = SessionManager()

@app.route('/flask/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'alibaba_api_configured': bool(app.config.get('ALIBABA_API_KEY')),
        'mcp_enabled': app.config.get('ENABLE_MCP', False)
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')