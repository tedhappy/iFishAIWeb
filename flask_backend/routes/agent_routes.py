from flask import Blueprint, request, jsonify, current_app
from utils.session_manager import SessionManager
from utils.logger import logger
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
    session_uuid = data.get('session_uuid')  # 新增session_uuid参数
    force_new = data.get('force_new', False)  # 新增force_new参数
    
    logger.info(f"初始化Agent会话 - user_id: {user_id}, mask_id: {mask_id}, agent_type: {agent_type}, session_uuid: {session_uuid}, force_new: {force_new}")
    
    if not mask_id:
        logger.error("缺少mask_id参数")
        return jsonify({'error': '缺少mask_id参数'}), 400
    
    try:
        session_id = session_manager.create_session(user_id, mask_id, agent_type, session_uuid, force_new)
        logger.info(f"会话创建成功 - session_id: {session_id}")
        return jsonify({
            'success': True,
            'session_id': session_id,
            'agent_type': agent_type,
            'user_id': user_id
        })
    except Exception as e:
        logger.error(f"创建会话失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/chat', methods=['POST'])
def chat_with_agent():
    """与Agent对话（流式响应）"""
    from flask import Response
    import json
    import time
    
    data = request.get_json()
    session_id = data.get('session_id')
    message = data.get('message')
    file_paths = data.get('file_paths', [])  # 修改为file_paths以匹配前端
    file_path = data.get('file_path')  # 保持向后兼容
    deep_thinking = data.get('deep_thinking', True)  # 新增深度思考模式参数，默认开启
    
    # 如果有file_paths就使用file_paths，否则使用file_path
    files = file_paths if file_paths else ([file_path] if file_path else [])
    
    logger.info(f"收到聊天请求 - session_id: {session_id}, message: {message[:50] if message else None}..., files: {files}")
    
    if not session_id or not message:
        logger.error(f"缺少必要参数 - session_id: {session_id}, message: {bool(message)}")
        return jsonify({'error': '缺少必要参数'}), 400
    
    agent = session_manager.get_session(session_id)
    logger.info(f"查找会话结果 - session_id: {session_id}, agent存在: {agent is not None}")
    logger.info(f"当前活跃会话数: {session_manager.get_session_count()}")
    logger.info(f"所有会话ID: {list(session_manager.sessions.keys())}")
    
    if not agent:
        logger.error(f"会话不存在 - session_id: {session_id}")
        return jsonify({'error': '会话不存在'}), 404
    
    def generate_stream():
        """生成流式响应"""
        try:
            # 使用Agent的流式聊天方法
            if files:
                # 如果有文件，需要特殊处理
                for chunk in agent.chat_stream(message, files[0], deep_thinking=deep_thinking):
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                # 手动更新会话时间戳并保存
                session_manager.touch_session(session_id)
            else:
                # 使用流式方法
                for chunk in agent.chat_stream(message, deep_thinking=deep_thinking):
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                # 更新会话时间戳
                session_manager.touch_session(session_id)
            
            # 发送结束标记
            yield f"data: {json.dumps({'type': 'done', 'success': True}, ensure_ascii=False)}\n\n"
            logger.info(f"流式聊天响应完成 - session_id: {session_id}")
            
        except Exception as e:
            logger.error(f"流式聊天处理失败 - session_id: {session_id}, error: {str(e)}")
            # 发送错误信息
            error_chunk = {
                'type': 'error',
                'success': False,
                'error': str(e)
            }
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
    
    # 返回流式响应
    return Response(
        generate_stream(),
        mimetype='text/plain',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'X-Accel-Buffering': 'no',  # 禁用 Nginx 缓冲
            'Transfer-Encoding': 'chunked',
        }
    )

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

@agent_bp.route('/session/<session_id>/status', methods=['GET'])
def check_session_status(session_id):
    """检查特定会话的状态"""
    logger.info(f"检查会话状态 - session_id: {session_id}")
    
    if not session_id:
        return jsonify({'error': '缺少session_id参数'}), 400
    
    try:
        agent = session_manager.get_session(session_id)
        if not agent:
            logger.info(f"会话不存在 - session_id: {session_id}")
            return jsonify({
                'success': False,
                'exists': False,
                'message': '会话不存在或已过期'
            }), 404
        
        # 更新会话的最后活跃时间
        session_manager.touch_session(session_id)
        
        logger.info(f"会话状态正常 - session_id: {session_id}")
        return jsonify({
            'success': True,
            'exists': True,
            'session_id': session_id,
            'agent_type': agent.agent_type if hasattr(agent, 'agent_type') else 'unknown',
            'message_count': len(agent.get_history()) if hasattr(agent, 'get_history') else 0
        })
    except Exception as e:
        logger.error(f"检查会话状态失败 - session_id: {session_id}, error: {str(e)}")
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

@agent_bp.route('/recover', methods=['POST'])
def recover_session():
    """尝试恢复会话（用于服务器重启后的会话恢复）"""
    data = request.get_json()
    user_id = data.get('user_id')
    mask_id = data.get('mask_id')
    agent_type = data.get('agent_type', 'default')
    session_id = data.get('session_id')  # 可选，如果提供则尝试恢复特定会话
    session_uuid = data.get('session_uuid')  # 新增：会话UUID参数
    
    logger.info(f"尝试恢复会话 - user_id: {user_id}, mask_id: {mask_id}, agent_type: {agent_type}, session_id: {session_id}, session_uuid: {session_uuid}")
    
    if not user_id or not mask_id:
        return jsonify({'error': '缺少必要参数 user_id 或 mask_id'}), 400
    
    try:
        # 如果提供了session_id，先检查是否已存在
        if session_id:
            existing_agent = session_manager.get_session(session_id)
            if existing_agent:
                logger.info(f"会话已存在，无需恢复 - session_id: {session_id}")
                return jsonify({
                    'success': True,
                    'session_id': session_id,
                    'message': '会话已存在',
                    'recovered': False
                })
        
        # 尝试创建新会话（如果持久化文件中有数据，会自动恢复）
        # 传递session_uuid参数以支持会话隔离
        new_session_id = session_manager.create_session(user_id, mask_id, agent_type, session_uuid=session_uuid)
        
        # 检查是否是恢复的会话还是新创建的会话
        is_recovered = session_id and new_session_id == session_id
        
        logger.info(f"会话恢复{'成功' if is_recovered else '失败，已创建新会话'} - session_id: {new_session_id}")
        
        return jsonify({
            'success': True,
            'session_id': new_session_id,
            'message': '会话恢复成功' if is_recovered else '已创建新会话',
            'recovered': is_recovered
        })
        
    except Exception as e:
        logger.error(f"会话恢复失败: {str(e)}")
        return jsonify({'error': f'会话恢复失败: {str(e)}'}), 500