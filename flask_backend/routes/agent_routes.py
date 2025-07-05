from flask import Blueprint, request, jsonify, current_app
from utils.session_manager import SessionManager
import uuid

agent_bp = Blueprint('agent', __name__)
session_manager = SessionManager()

@agent_bp.route('/init', methods=['POST'])
def init_agent():
    """初始化Agent会话"""
    data = request.get_json()
    user_id = data.get('user_id', str(uuid.uuid4()))  # 如果没有用户ID，生成一个
    mask_id = data.get('mask_id')
    agent_type = data.get('agent_type', 'default')
    
    if not mask_id:
        return jsonify({'error': '缺少mask_id参数'}), 400
    
    try:
        session_id = session_manager.create_session(user_id, mask_id, agent_type)
        return jsonify({
            'success': True,
            'session_id': session_id,
            'agent_type': agent_type,
            'user_id': user_id
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
                'message_count': len(agent.get_history()),
                'agent_type': session_id.split('_')[-1] if '_' in session_id else 'unknown'
            })
        
        return jsonify({
            'success': True,
            'sessions': session_info
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/clear/<session_id>', methods=['POST'])
def clear_session_history(session_id):
    """清空会话历史"""
    agent = session_manager.get_session(session_id)
    if not agent:
        return jsonify({'error': '会话不存在'}), 404
    
    try:
        agent.clear_history()
        return jsonify({
            'success': True,
            'message': '会话历史已清空'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/remove/<session_id>', methods=['DELETE'])
def remove_session(session_id):
    """移除会话"""
    try:
        session_manager.remove_session(session_id)
        return jsonify({
            'success': True,
            'message': '会话已移除'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/status', methods=['GET'])
def get_status():
    """获取系统状态"""
    try:
        return jsonify({
            'success': True,
            'session_count': session_manager.get_session_count(),
            'supported_agents': list(session_manager.agent_types.keys()),
            'alibaba_api_configured': bool(current_app.config.get('ALIBABA_API_KEY')),
            'mcp_enabled': current_app.config.get('ENABLE_MCP', False)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/load_history', methods=['POST'])
def load_history():
    """加载历史消息到会话"""
    data = request.get_json()
    session_id = data.get('session_id')
    messages = data.get('messages', [])
    
    if not session_id:
        return jsonify({'error': '缺少session_id参数'}), 400
    
    agent = session_manager.get_session(session_id)
    if not agent:
        return jsonify({'error': '会话不存在'}), 404
    
    try:
        agent.load_history(messages)
        return jsonify({
            'success': True,
            'message': f'已加载{len(messages)}条历史消息'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500