from flask import Blueprint, request, jsonify
import uuid
import time
import threading
from utils.logger import logger

auth_bp = Blueprint('auth', __name__)

# 简单的用户会话存储（生产环境应使用数据库）
user_sessions = {}
_cleanup_thread = None
_stop_cleanup = False

def _start_session_cleanup():
    """启动会话清理线程"""
    global _cleanup_thread, _stop_cleanup
    
    def cleanup_expired_sessions():
        """清理过期会话的后台线程"""
        while not _stop_cleanup:
            try:
                current_time = time.time()
                expired_sessions = []
                
                for session_token, user_session in user_sessions.items():
                    if current_time - user_session['last_activity'] > 24 * 3600:  # 24小时过期
                        expired_sessions.append(session_token)
                
                for session_token in expired_sessions:
                    if session_token in user_sessions:
                        del user_sessions[session_token]
                
                if expired_sessions:
                    logger.info(f"清理了 {len(expired_sessions)} 个过期用户会话")
                
                # 每小时检查一次
                for _ in range(3600):
                    if _stop_cleanup:
                        break
                    time.sleep(1)
            except Exception as e:
                logger.error(f"用户会话清理线程异常: {str(e)}")
                time.sleep(300)  # 出错后等待5分钟再重试
    
    if not _cleanup_thread or not _cleanup_thread.is_alive():
        _stop_cleanup = False
        _cleanup_thread = threading.Thread(target=cleanup_expired_sessions, daemon=True)
        _cleanup_thread.start()
        logger.info("用户会话清理线程已启动")

# 启动清理线程
_start_session_cleanup()

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录/注册"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据格式错误'}), 400
    
    username = data.get('username')
    
    # 基本输入验证（移除严格长度限制）
    if username and not isinstance(username, str):
        return jsonify({'error': '用户名格式错误'}), 400
    
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
    if not data:
        return jsonify({'error': '请求数据格式错误'}), 400
    
    session_token = data.get('session_token')
    
    # 输入验证
    if not session_token or not isinstance(session_token, str):
        return jsonify({'error': '缺少有效的session_token参数'}), 400
    
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
    if not data:
        return jsonify({'error': '请求数据格式错误'}), 400
    
    session_token = data.get('session_token')
    
    # 输入验证
    if not session_token or not isinstance(session_token, str):
        return jsonify({'error': '缺少有效的session_token参数'}), 400
    
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