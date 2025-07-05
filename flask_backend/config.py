import os
from typing import Dict, Any

class Config:
    """Flask应用配置类"""
    
    # 基础配置
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # API配置
    ALIBABA_API_KEY = os.getenv('ALIBABA_API_KEY', '')
    ALIBABA_URL = os.getenv('ALIBABA_URL', 'https://dashscope.aliyuncs.com/api/')
    
    # MCP配置
    ENABLE_MCP = os.getenv('ENABLE_MCP', 'true').lower() == 'true'
    
    # 数据库配置
    DATABASE_URL = os.getenv('DATABASE_URL', 'mysql+mysqlconnector://student123:student321@rm-uf6z891lon6dxuqblqo.mysql.rds.aliyuncs.com:3306/ubr?charset=utf8mb4')
    
    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'xlsx'}
    
    # 静态文件配置
    STATIC_FOLDER = os.path.join(os.path.dirname(__file__), 'static')
    
    # Agent配置
    DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', 'qwen-turbo-2025-04-28')
    MODEL_TIMEOUT = int(os.getenv('MODEL_TIMEOUT', '30'))
    MODEL_RETRY_COUNT = int(os.getenv('MODEL_RETRY_COUNT', '3'))
    
    # 会话配置
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '86400'))  # 24小时
    MAX_SESSIONS_PER_USER = int(os.getenv('MAX_SESSIONS_PER_USER', '10'))
    
    # CORS配置
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    
    @classmethod
    def get_llm_config(cls) -> Dict[str, Any]:
        """获取LLM配置"""
        return {
            'model': cls.DEFAULT_MODEL,
            'timeout': cls.MODEL_TIMEOUT,
            'retry_count': cls.MODEL_RETRY_COUNT,
            'api_key': cls.ALIBABA_API_KEY
        }
    
    @classmethod
    def validate_config(cls) -> bool:
        """验证配置是否完整"""
        required_configs = [
            'ALIBABA_API_KEY'
        ]
        
        for config in required_configs:
            if not getattr(cls, config):
                print(f"警告: 缺少必要配置 {config}")
                return False
        
        return True

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    
class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    
class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True

# 配置映射
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name: str = None) -> Config:
    """获取配置类"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')
    
    return config_map.get(config_name, DevelopmentConfig)