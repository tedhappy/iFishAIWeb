from flask import Blueprint, request, jsonify
import uuid
import time

auth_bp = Blueprint('auth', __name__)

# 简单的用户会话存储（生产环境应使用数据库）
user_sessions = {}

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录/注册"""
    data = request.get_json()
    username = data.get('username')
    
    if not username:
        # 如果没有用户名，生成匿名用户
        user_id = f"anonymous_{str(uuid.uuid4())[:8]}"
        username = f"匿名用户_{user_id[-8:]}"
    else:
        # 简单的用户ID生成（实际应用中应该有更复杂的认证逻辑）
        user_id = f"user_{hash(username) % 100000}"
    
    # 创建会话
    session_token = str(uuid.uuid4())
    user_sessions[session_token] = {
        'user_id': user_id,
        'username': username,
        'login_time': time.time(),
        'last_activity': time.time()
    }
    
    return jsonify({
        'success': True,
        'user_id': user_id,
        'username': username,
        'session_token': session_token
    })

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """用户登出"""
    data = request.get_json()
    session_token = data.get('session_token')
    
    if session_token and session_token in user_sessions:
        del user_sessions[session_token]
        return jsonify({
            'success': True,
            'message': '登出成功'
        })
    
    return jsonify({
        'success': False,
        'message': '无效的会话'
    }), 400

@auth_bp.route('/verify', methods=['POST'])
def verify_session():
    """验证会话有效性"""
    data = request.get_json()
    session_token = data.get('session_token')
    
    if not session_token or session_token not in user_sessions:
        return jsonify({
            'success': False,
            'message': '会话无效或已过期'
        }), 401
    
    user_session = user_sessions[session_token]
    
    # 检查会话是否过期（24小时）
    if time.time() - user_session['last_activity'] > 24 * 3600:
        del user_sessions[session_token]
        return jsonify({
            'success': False,
            'message': '会话已过期'
        }), 401
    
    # 更新最后活动时间
    user_session['last_activity'] = time.time()
    
    return jsonify({
        'success': True,
        'user_id': user_session['user_id'],
        'username': user_session['username']
    })

@auth_bp.route('/user_info/<session_token>', methods=['GET'])
def get_user_info(session_token):
    """获取用户信息"""
    if not session_token or session_token not in user_sessions:
        return jsonify({
            'success': False,
            'message': '会话无效'
        }), 401
    
    user_session = user_sessions[session_token]
    
    return jsonify({
        'success': True,
        'user_id': user_session['user_id'],
        'username': user_session['username'],
        'login_time': user_session['login_time'],
        'last_activity': user_session['last_activity']
    })

@auth_bp.route('/sessions', methods=['GET'])
def get_active_sessions():
    """获取活跃会话数量（管理接口）"""
    current_time = time.time()
    active_sessions = 0
    
    for session_token, user_session in user_sessions.items():
        if current_time - user_session['last_activity'] <= 24 * 3600:
            active_sessions += 1
    
    return jsonify({
        'success': True,
        'active_sessions': active_sessions,
        'total_sessions': len(user_sessions)
    })