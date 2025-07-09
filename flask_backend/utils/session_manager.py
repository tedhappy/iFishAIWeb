from typing import Dict, Optional
import json
import os
import logging
import threading
import time
from datetime import datetime
from agents.base_agent import BaseAgent
from agents.ticket_agent import TicketAgent
from agents.general_agent import GeneralAgent
from .logger import logger
# 导入其他Agent类...

class SessionManager:
    """会话管理器，负责Agent实例的创建和管理（线程安全）"""
    
    def __init__(self, session_file: str = "sessions.json", session_ttl: int = 7200):
        self.sessions: Dict[str, BaseAgent] = {}
        self.session_timestamps: Dict[str, float] = {}  # 会话时间戳
        self.session_file = session_file
        self.session_ttl = session_ttl  # 会话过期时间（秒），默认2小时
        self._lock = threading.RLock()  # 可重入锁，保证线程安全
        self.agent_types = {
            'ticket': TicketAgent,
            'general': GeneralAgent,  # 通用助手
            'image': None,  # 待实现
            'chatbi': None,  # 待实现
            'default': GeneralAgent  # 默认使用通用助手
        }
        # Logger已通过导入的logger模块统一管理
        self._cleanup_thread = None
        self._stop_cleanup = False
        self._load_sessions()
        self._start_cleanup_thread()
    
    def create_session(self, user_id: str, mask_id: str, agent_type: str = 'default', session_uuid: str = None, force_new: bool = False) -> str:
        """创建新的Agent会话（线程安全）"""
        with self._lock:
            # 如果提供了session_uuid，使用它来生成唯一的会话ID
            if session_uuid:
                session_id = f"{user_id}_{mask_id}_{agent_type}_{session_uuid}"
            else:
                # 兼容旧的会话ID格式
                session_id = f"{user_id}_{mask_id}_{agent_type}"
            
            # 如果force_new为True，强制创建新会话
            if force_new and session_id in self.sessions:
                # 为强制新建的会话添加时间戳后缀
                timestamp = str(int(time.time() * 1000))  # 毫秒级时间戳
                session_id = f"{session_id}_{timestamp}"
            
            # 如果会话已存在且不强制创建新会话，直接返回
            if session_id in self.sessions and not force_new:
                # 更新活跃时间
                self.session_timestamps[session_id] = time.time()
                # 立即保存更新的时间戳
                self._save_sessions()
                logger.info(f"会话已存在，返回现有会话: {session_id}")
                return session_id
            
            # 检查Agent类型是否支持
            if agent_type not in self.agent_types:
                raise ValueError(f"不支持的Agent类型: {agent_type}")
            
            # 创建新的Agent实例
            agent_class = self.agent_types[agent_type]
            agent = agent_class(agent_id=mask_id, user_id=user_id)
            
            # 存储会话
            self.sessions[session_id] = agent
            current_time = time.time()
            self.session_timestamps[session_id] = current_time
            
            # 保存会话到文件
            self._save_sessions()
            logger.info(f"创建新会话: {session_id}")
            
            return session_id
    
    def get_session(self, session_id: str) -> Optional[BaseAgent]:
        """获取Agent会话（线程安全，自动更新活跃时间）"""
        with self._lock:
            agent = self.sessions.get(session_id)
            if agent:
                # 更新会话活跃时间
                self.session_timestamps[session_id] = time.time()
            return agent
    
    def remove_session(self, session_id: str):
        """移除Agent会话（线程安全）"""
        with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                # 同时清理时间戳
                if session_id in self.session_timestamps:
                    del self.session_timestamps[session_id]
                # 保存会话到文件
                self._save_sessions()
                logger.info(f"移除会话: {session_id}")
            else:
                logger.warning(f"尝试移除不存在的会话: {session_id}")
    
    def get_user_sessions(self, user_id: str) -> Dict[str, BaseAgent]:
        """获取用户的所有会话（线程安全）"""
        with self._lock:
            user_sessions = {}
            for session_id, agent in self.sessions.items():
                if agent.user_id == user_id:
                    user_sessions[session_id] = agent
            return user_sessions
    
    def clear_user_sessions(self, user_id: str):
        """清空用户的所有会话（线程安全）"""
        with self._lock:
            sessions_to_remove = []
            for session_id, agent in self.sessions.items():
                if agent.user_id == user_id:
                    sessions_to_remove.append(session_id)
            
            for session_id in sessions_to_remove:
                del self.sessions[session_id]
                if session_id in self.session_timestamps:
                    del self.session_timestamps[session_id]
            
            if sessions_to_remove:
                self._save_sessions()
                logger.info(f"清空用户 {user_id} 的 {len(sessions_to_remove)} 个会话")
    
    def get_session_count(self) -> int:
        """获取当前会话总数（线程安全）"""
        with self._lock:
            return len(self.sessions)
    
    def register_agent_type(self, agent_type: str, agent_class):
        """注册新的Agent类型（线程安全）"""
        with self._lock:
            self.agent_types[agent_type] = agent_class
    
    def _load_sessions(self):
        """从文件加载会话信息（线程安全）"""
        with self._lock:
            try:
                if os.path.exists(self.session_file):
                    with open(self.session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                        
                    current_time = time.time()
                    for session_id, data in session_data.items():
                        try:
                            user_id = data.get('user_id')
                            mask_id = data.get('mask_id')
                            agent_type = data.get('agent_type', 'default')
                            
                            # 重新创建Agent实例
                            agent_class = self.agent_types.get(agent_type, self.agent_types['default'])
                            if agent_class:
                                agent = agent_class(agent_id=mask_id, user_id=user_id)
                                # 如果有历史消息，加载它们
                                if 'history' in data and hasattr(agent, 'load_history'):
                                    agent.load_history(data['history'])
                                self.sessions[session_id] = agent
                                # 初始化时间戳（使用保存的时间戳或当前时间）
                                self.session_timestamps[session_id] = data.get('timestamp', current_time)
                                logger.info(f"已恢复会话: {session_id}")
                        except Exception as e:
                            logger.error(f"恢复会话失败 {session_id}: {str(e)}")
                            
                    logger.info(f"已加载 {len(self.sessions)} 个会话")
            except Exception as e:
                logger.error(f"加载会话文件失败: {str(e)}")
    
    def _save_sessions(self):
        """保存会话信息到文件（线程安全）"""
        # 注意：此方法应该在已获得锁的情况下调用
        try:
            session_data = {}
            for session_id, agent in self.sessions.items():
                try:
                    # 提取会话基本信息
                    parts = session_id.split('_')
                    if len(parts) >= 3:
                        user_id = parts[0]
                        mask_id = parts[1]
                        agent_type = parts[2]
                    else:
                        user_id = getattr(agent, 'user_id', 'unknown')
                        mask_id = getattr(agent, 'agent_id', 'unknown')
                        agent_type = 'default'
                    
                    session_info = {
                        'user_id': user_id,
                        'mask_id': mask_id,
                        'agent_type': agent_type,
                        'timestamp': self.session_timestamps.get(session_id, time.time())
                    }
                    
                    # 保存历史消息（如果Agent支持）
                    if hasattr(agent, 'get_history'):
                        try:
                            session_info['history'] = agent.get_history()
                        except Exception as e:
                            logger.warning(f"获取会话历史失败 {session_id}: {str(e)}")
                    
                    session_data[session_id] = session_info
                except Exception as e:
                    logger.error(f"序列化会话失败 {session_id}: {str(e)}")
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"已保存 {len(session_data)} 个会话")
        except Exception as e:
            logger.error(f"保存会话文件失败: {str(e)}")
    
    def _start_cleanup_thread(self):
        """启动会话清理线程"""
        def cleanup_expired_sessions():
            """清理过期会话的后台线程"""
            while not self._stop_cleanup:
                try:
                    self._cleanup_expired_sessions()
                    # 每5分钟检查一次
                    for _ in range(300):  # 300秒 = 5分钟
                        if self._stop_cleanup:
                            break
                        time.sleep(1)
                except Exception as e:
                    logger.error(f"会话清理线程异常: {str(e)}")
                    time.sleep(60)  # 出错后等待1分钟再重试
        
        self._cleanup_thread = threading.Thread(target=cleanup_expired_sessions, daemon=True)
        self._cleanup_thread.start()
        logger.info("会话清理线程已启动")
    
    def _cleanup_expired_sessions(self):
        """清理过期的会话"""
        with self._lock:
            current_time = time.time()
            expired_sessions = []
            
            for session_id, timestamp in self.session_timestamps.items():
                if current_time - timestamp > self.session_ttl:
                    expired_sessions.append(session_id)
            
            if expired_sessions:
                for session_id in expired_sessions:
                    if session_id in self.sessions:
                        del self.sessions[session_id]
                    if session_id in self.session_timestamps:
                        del self.session_timestamps[session_id]
                
                # 保存更新后的会话
                self._save_sessions()
                logger.info(f"清理了 {len(expired_sessions)} 个过期会话")
    
    def touch_session(self, session_id: str):
        """更新会话活跃时间"""
        with self._lock:
            if session_id in self.sessions:
                self.session_timestamps[session_id] = time.time()
                # 立即保存更新的时间戳
                self._save_sessions()
                return True
            return False
    
    def get_session_info(self, session_id: str) -> Optional[dict]:
        """获取会话详细信息"""
        with self._lock:
            if session_id not in self.sessions:
                return None
            
            agent = self.sessions[session_id]
            timestamp = self.session_timestamps.get(session_id, 0)
            current_time = time.time()
            
            return {
                'session_id': session_id,
                'user_id': getattr(agent, 'user_id', 'unknown'),
                'agent_id': getattr(agent, 'agent_id', 'unknown'),
                'created_time': timestamp,
                'last_active': timestamp,
                'age_seconds': current_time - timestamp,
                'expires_in_seconds': max(0, self.session_ttl - (current_time - timestamp)),
                'is_expired': (current_time - timestamp) > self.session_ttl
            }
    
    def get_all_sessions_info(self) -> list:
        """获取所有会话的详细信息"""
        with self._lock:
            sessions_info = []
            for session_id in self.sessions.keys():
                info = self.get_session_info(session_id)
                if info:
                    sessions_info.append(info)
            return sessions_info
    
    def get_session_count(self) -> int:
        """获取当前活跃会话数量"""
        with self._lock:
            return len(self.sessions)
    
    def cleanup_user_expired_sessions(self, user_id: str) -> int:
        """清理指定用户的过期会话"""
        with self._lock:
            current_time = time.time()
            expired_sessions = []
            
            for session_id, agent in self.sessions.items():
                if (hasattr(agent, 'user_id') and agent.user_id == user_id and 
                    session_id in self.session_timestamps):
                    timestamp = self.session_timestamps[session_id]
                    if current_time - timestamp > self.session_ttl:
                        expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self.sessions[session_id]
                if session_id in self.session_timestamps:
                    del self.session_timestamps[session_id]
            
            if expired_sessions:
                self._save_sessions()
                logger.info(f"清理用户 {user_id} 的 {len(expired_sessions)} 个过期会话")
            
            return len(expired_sessions)
    
    def stop_cleanup_thread(self):
        """停止清理线程（用于应用关闭时）"""
        self._stop_cleanup = True
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
            logger.info("会话清理线程已停止")
    
    def chat_with_agent(self, session_id: str, message: str) -> str:
        """与Agent对话（线程安全）"""
        with self._lock:
            if session_id not in self.sessions:
                raise ValueError(f"会话不存在: {session_id}")
            
            agent = self.sessions[session_id]
            
            # 更新会话活跃时间
            self.session_timestamps[session_id] = time.time()
            
            try:
                response = agent.chat(message)
                # 对话成功后立即保存会话状态
                self._save_sessions()
                logger.info(f"会话 {session_id} 对话成功")
                return response
            except Exception as e:
                logger.error(f"会话 {session_id} 对话失败: {str(e)}")
                # 即使对话失败也保存时间戳更新
                self._save_sessions()
                raise
    
    def __del__(self):
        """析构函数，确保清理线程正确停止"""
        try:
            self.stop_cleanup_thread()
        except:
            pass