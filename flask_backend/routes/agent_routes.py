from flask import Blueprint, request, jsonify, current_app
from utils.logger import logger
import uuid

agent_bp = Blueprint('agent', __name__)

# 获取全局会话管理器的辅助函数
def get_session_manager():
    """获取全局会话管理器实例"""
    return current_app.session_manager

@agent_bp.route('/init', methods=['POST'])
def init_agent():
    """初始化Agent会话"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据格式错误'}), 400
    
    user_id = data.get('user_id', str(uuid.uuid4()))  # 如果没有用户ID，生成一个
    mask_id = data.get('mask_id')
    agent_type = data.get('agent_type', 'default')
    session_uuid = data.get('session_uuid')  # 新增session_uuid参数
    force_new = data.get('force_new', False)  # 新增force_new参数
    
    # 验证前日志：记录接收到的参数
    logger.info(f"[/init] 验证前参数检查 - user_id: {user_id} (类型: {type(user_id).__name__}), mask_id: {mask_id} (类型: {type(mask_id).__name__}), agent_type: {agent_type} (类型: {type(agent_type).__name__}), session_uuid: {session_uuid} (类型: {type(session_uuid).__name__}), force_new: {force_new} (类型: {type(force_new).__name__})")
    
    # 基本输入验证（移除严格长度限制）
    # mask_id可以是字符串或数字，统一转换为字符串
    if mask_id is not None:
        if isinstance(mask_id, (str, int, float)):
            mask_id = str(mask_id)
            logger.info(f"[/init] mask_id已转换为字符串: {mask_id}")
        else:
            logger.error(f"[/init] 验证失败 - mask_id类型错误: {type(mask_id).__name__}, 值: {mask_id}")
            return jsonify({'error': 'mask_id必须是字符串或数字'}), 400
    if user_id and not isinstance(user_id, str):
        logger.error(f"[/init] 验证失败 - user_id类型错误: {type(user_id).__name__}, 值: {user_id}")
        return jsonify({'error': 'user_id必须是字符串'}), 400
    
    logger.info(f"[/init] 参数验证通过")

    logger.info(f"初始化Agent会话 - user_id: {user_id}, mask_id: {mask_id}, agent_type: {agent_type}, session_uuid: {session_uuid}, force_new: {force_new}")
    
    try:
        session_id = get_session_manager().create_session(user_id, mask_id, agent_type, session_uuid, force_new)
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
    if not data:
        return jsonify({'error': '请求数据格式错误'}), 400
    
    session_id = data.get('session_id')
    message = data.get('message')
    file_paths = data.get('file_paths', [])  # 修改为file_paths以匹配前端
    file_path = data.get('file_path')  # 保持向后兼容
    deep_thinking = data.get('deep_thinking', True)  # 新增深度思考模式参数，默认开启
    
    # 验证前日志：记录接收到的参数
    logger.info(f"[/chat] 验证前参数检查 - session_id: {session_id} (类型: {type(session_id).__name__}), message: {message[:50] if message else None}... (类型: {type(message).__name__}), file_paths: {file_paths} (类型: {type(file_paths).__name__}), file_path: {file_path} (类型: {type(file_path).__name__}), deep_thinking: {deep_thinking} (类型: {type(deep_thinking).__name__})")
    
    # 基本输入验证（移除严格长度限制）
    if not session_id or not isinstance(session_id, str):
        logger.error(f"[/chat] 验证失败 - session_id无效: {session_id} (类型: {type(session_id).__name__})")
        return jsonify({'error': '缺少有效的session_id参数'}), 400
    if not message or not isinstance(message, str):
        logger.error(f"[/chat] 验证失败 - message无效: {message} (类型: {type(message).__name__})")
        return jsonify({'error': '缺少有效的message参数'}), 400
    
    logger.info(f"[/chat] 参数验证通过")
    
    # 如果有file_paths就使用file_paths，否则使用file_path
    files = file_paths if file_paths else ([file_path] if file_path else [])
    
    logger.info(f"收到聊天请求 - session_id: {session_id}, message: {message[:50] if message else None}..., files: {files}")
    
    if not session_id or not message:
        logger.error(f"缺少必要参数 - session_id: {session_id}, message: {bool(message)}")
        return jsonify({'error': '缺少必要参数'}), 400
    
    # 在请求上下文中获取会话管理器和agent实例
    session_mgr = get_session_manager()
    agent = session_mgr.get_session(session_id)
    logger.info(f"查找会话结果 - session_id: {session_id}, agent存在: {agent is not None}")
    logger.info(f"当前活跃会话数: {session_mgr.get_session_count()}")
    logger.info(f"所有会话ID: {list(session_mgr.sessions.keys())}")
    
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
                session_mgr.touch_session(session_id)
            else:
                # 使用流式方法
                for chunk in agent.chat_stream(message, deep_thinking=deep_thinking):
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                # 更新会话时间戳
                session_mgr.touch_session(session_id)
            
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
    # 验证前日志：记录接收到的参数
    logger.info(f"[/history] 验证前参数检查 - session_id: {session_id} (类型: {type(session_id).__name__})")
    
    agent = get_session_manager().get_session(session_id)
    if not agent:
        logger.error(f"[/history] 验证失败 - 会话不存在: {session_id}")
        return jsonify({'error': '会话不存在'}), 404
    
    logger.info(f"[/history] 参数验证通过")
    
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
    # 验证前日志：记录接收到的参数
    logger.info(f"[/sessions] 验证前参数检查 - user_id: {user_id} (类型: {type(user_id).__name__})")
    
    # 基本输入验证（移除严格长度限制）
    if not user_id or not isinstance(user_id, str):
        logger.error(f"[/sessions] 验证失败 - user_id无效: {user_id} (类型: {type(user_id).__name__})")
        return jsonify({'error': '无效的user_id参数'}), 400
    
    logger.info(f"[/sessions] 参数验证通过")
    
    try:
        sessions = get_session_manager().get_user_sessions(user_id)
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
    # 验证前日志：记录接收到的参数
    logger.info(f"[/clear] 验证前参数检查 - session_id: {session_id} (类型: {type(session_id).__name__})")
    
    agent = get_session_manager().get_session(session_id)
    if not agent:
        logger.error(f"[/clear] 验证失败 - 会话不存在: {session_id}")
        return jsonify({'error': '会话不存在'}), 404
    
    logger.info(f"[/clear] 参数验证通过")
    
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
    # 验证前日志：记录接收到的参数
    logger.info(f"[/remove] 验证前参数检查 - session_id: {session_id} (类型: {type(session_id).__name__})")
    
    logger.info(f"[/remove] 参数验证通过")
    
    try:
        get_session_manager().remove_session(session_id)
        return jsonify({
            'success': True,
            'message': '会话已移除'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/status', methods=['GET'])
def get_status():
    """获取系统状态"""
    # 验证前日志：记录接收到的参数
    logger.info(f"[/status] 验证前参数检查 - 无需参数验证")
    
    logger.info(f"[/status] 参数验证通过")
    
    try:
        return jsonify({
            'success': True,
            'session_count': get_session_manager().get_session_count(),
            'supported_agents': list(get_session_manager().agent_types.keys()),
            'alibaba_api_configured': bool(current_app.config.get('ALIBABA_API_KEY')),
            'mcp_enabled': current_app.config.get('ENABLE_MCP', False)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/session/<session_id>/status', methods=['GET'])
def check_session_status(session_id):
    """检查特定会话的状态"""
    # 验证前日志：记录接收到的参数
    logger.info(f"[/session/status] 验证前参数检查 - session_id: {session_id} (类型: {type(session_id).__name__})")
    
    if not session_id:
        logger.error(f"[/session/status] 验证失败 - session_id为空: {session_id}")
        return jsonify({'error': '缺少session_id参数'}), 400
    
    logger.info(f"[/session/status] 参数验证通过")
    
    try:
        agent = get_session_manager().get_session(session_id)
        if not agent:
            logger.info(f"会话不存在 - session_id: {session_id}")
            return jsonify({
                'success': False,
                'exists': False,
                'message': '会话不存在或已过期'
            }), 404
        
        # 更新会话的最后活跃时间
        get_session_manager().touch_session(session_id)
        
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
    if not data:
        return jsonify({'error': '请求数据格式错误'}), 400
    
    session_id = data.get('session_id')
    messages = data.get('messages', [])
    
    # 验证前日志：记录接收到的参数
    logger.info(f"[/load_history] 验证前参数检查 - session_id: {session_id} (类型: {type(session_id).__name__}), messages: {len(messages) if isinstance(messages, list) else 'N/A'}条消息 (类型: {type(messages).__name__})")
    
    # 基本输入验证（移除严格长度限制）
    if not session_id or not isinstance(session_id, str):
        logger.error(f"[/load_history] 验证失败 - session_id无效: {session_id} (类型: {type(session_id).__name__})")
        return jsonify({'error': '缺少有效的session_id参数'}), 400
    if not isinstance(messages, list):
        logger.error(f"[/load_history] 验证失败 - messages类型错误: {type(messages).__name__}, 值: {messages}")
        return jsonify({'error': 'messages参数必须是数组'}), 400
    
    logger.info(f"[/load_history] 参数验证通过")
    
    agent = get_session_manager().get_session(session_id)
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
    if not data:
        return jsonify({'error': '请求数据格式错误'}), 400
    
    user_id = data.get('user_id')
    mask_id = data.get('mask_id')
    agent_type = data.get('agent_type', 'default')
    session_id = data.get('session_id')  # 可选，如果提供则尝试恢复特定会话
    session_uuid = data.get('session_uuid')  # 新增：会话UUID参数
    
    # 验证前日志：记录接收到的参数
    logger.info(f"[/recover] 验证前参数检查 - user_id: {user_id} (类型: {type(user_id).__name__}), mask_id: {mask_id} (类型: {type(mask_id).__name__}), agent_type: {agent_type} (类型: {type(agent_type).__name__}), session_id: {session_id} (类型: {type(session_id).__name__}), session_uuid: {session_uuid} (类型: {type(session_uuid).__name__})")
    
    # 基本输入验证（移除严格长度限制）
    if not user_id or not isinstance(user_id, str):
        logger.error(f"[/recover] 验证失败 - user_id无效: {user_id} (类型: {type(user_id).__name__})")
        return jsonify({'error': '缺少有效的user_id参数'}), 400
    # mask_id可以是字符串或数字，统一转换为字符串
    if mask_id is not None:
        if isinstance(mask_id, (str, int, float)):
            mask_id = str(mask_id)
            logger.info(f"[/recover] mask_id已转换为字符串: {mask_id}")
        else:
            logger.error(f"[/recover] 验证失败 - mask_id类型错误: {type(mask_id).__name__}, 值: {mask_id}")
            return jsonify({'error': 'mask_id必须是字符串或数字'}), 400
    else:
        logger.error(f"[/recover] 验证失败 - mask_id为空: {mask_id}")
        return jsonify({'error': '缺少有效的mask_id参数'}), 400
    if session_id and not isinstance(session_id, str):
        logger.error(f"[/recover] 验证失败 - session_id类型错误: {session_id} (类型: {type(session_id).__name__})")
        return jsonify({'error': 'session_id参数无效'}), 400
    
    logger.info(f"[/recover] 参数验证通过")
    
    logger.info(f"尝试恢复会话 - user_id: {user_id}, mask_id: {mask_id}, agent_type: {agent_type}, session_id: {session_id}, session_uuid: {session_uuid}")
    
    try:
        # 如果提供了session_id，先检查是否已存在
        if session_id:
            existing_agent = get_session_manager().get_session(session_id)
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
        new_session_id = get_session_manager().create_session(user_id, mask_id, agent_type, session_uuid=session_uuid)
        
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