from typing import Dict, Optional
from agents.base_agent import BaseAgent
from agents.ticket_agent import TicketAgent
# 导入其他Agent类...

class SessionManager:
    """会话管理器，负责Agent实例的创建和管理"""
    
    def __init__(self):
        self.sessions: Dict[str, BaseAgent] = {}
        self.agent_types = {
            'ticket': TicketAgent,
            'image': None,  # 待实现
            'chatbi': None,  # 待实现
            'default': TicketAgent  # 默认使用门票助手
        }
    
    def create_session(self, user_id: str, mask_id: str, agent_type: str) -> str:
        """创建新的Agent会话"""
        session_id = f"{user_id}_{mask_id}_{agent_type}"
        
        if session_id in self.sessions:
            return session_id
        
        agent_class = self.agent_types.get(agent_type, self.agent_types['default'])
        if agent_class is None:
            raise ValueError(f"不支持的Agent类型: {agent_type}")
        
        agent = agent_class(agent_id=mask_id, user_id=user_id)
        self.sessions[session_id] = agent
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[BaseAgent]:
        """获取Agent会话"""
        return self.sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """移除Agent会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def get_user_sessions(self, user_id: str) -> Dict[str, BaseAgent]:
        """获取用户的所有会话"""
        user_sessions = {}
        for session_id, agent in self.sessions.items():
            if agent.user_id == user_id:
                user_sessions[session_id] = agent
        return user_sessions
    
    def clear_user_sessions(self, user_id: str):
        """清空用户的所有会话"""
        sessions_to_remove = []
        for session_id, agent in self.sessions.items():
            if agent.user_id == user_id:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.sessions[session_id]
    
    def get_session_count(self) -> int:
        """获取当前会话总数"""
        return len(self.sessions)
    
    def register_agent_type(self, agent_type: str, agent_class):
        """注册新的Agent类型"""
        self.agent_types[agent_type] = agent_class