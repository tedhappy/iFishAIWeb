from flask import Flask, request, jsonify
from flask_cors import CORS
from routes.agent_routes import agent_bp
from routes.auth_routes import auth_bp
from utils.session_manager import SessionManager
import os
import logging
import traceback
from dotenv import load_dotenv

# 加载.env文件
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置
app.config['ALIBABA_API_KEY'] = os.getenv('ALIBABA_API_KEY')
app.config['ENABLE_MCP'] = True  # 默认开启MCP功能

# 注册蓝图
app.register_blueprint(agent_bp, url_prefix='/flask/agent')
app.register_blueprint(auth_bp, url_prefix='/flask/auth')

# 配置日志
logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.DEBUG)

# 全局错误处理器
@app.errorhandler(500)
def internal_error(error):
    """处理500错误"""
    app.logger.error(f"Internal Server Error: {error}")
    app.logger.error(f"Traceback: {traceback.format_exc()}")
    return jsonify({
        'error': 'Internal Server Error',
        'message': str(error),
        'traceback': traceback.format_exc()
    }), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """处理所有未捕获的异常"""
    app.logger.error(f"Unhandled Exception: {e}")
    app.logger.error(f"Traceback: {traceback.format_exc()}")
    return jsonify({
        'error': 'Unhandled Exception',
        'message': str(e),
        'traceback': traceback.format_exc()
    }), 500

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