# -*- coding: utf-8 -*-
"""
统一日志工具，为所有日志添加时间戳
"""

import logging
from datetime import datetime
from typing import Any


def get_timestamp() -> str:
    """获取格式化的当前时间"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class TimestampLogger:
    """带时间戳的日志记录器"""
    
    def __init__(self, name: str = __name__):
        self.logger = logging.getLogger(name)
        
        # 设置日志级别为DEBUG，确保所有级别的日志都能输出
        self.logger.setLevel(logging.DEBUG)
        
        # 如果logger还没有处理器，添加控制台处理器
        if not self.logger.handlers:
            # 创建控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            
            # 创建格式化器（不需要时间戳，因为我们在_log_with_timestamp中已经添加了）
            formatter = logging.Formatter('%(message)s')
            console_handler.setFormatter(formatter)
            
            # 添加处理器到logger
            self.logger.addHandler(console_handler)
            
            # 防止日志向上传播到根logger（避免重复输出）
            self.logger.propagate = False
    
    def _log_with_timestamp(self, level: int, *args: Any) -> None:
        """带时间戳的日志记录"""
        timestamp = get_timestamp()
        message = ' '.join(str(arg) for arg in args)
        self.logger.log(level, f"[{timestamp}] {message}")
    
    def debug(self, *args: Any) -> None:
        """调试日志"""
        self._log_with_timestamp(logging.DEBUG, *args)
    
    def info(self, *args: Any) -> None:
        """信息日志"""
        self._log_with_timestamp(logging.INFO, *args)
    
    def warning(self, *args: Any) -> None:
        """警告日志"""
        self._log_with_timestamp(logging.WARNING, *args)
    
    def error(self, *args: Any) -> None:
        """错误日志"""
        self._log_with_timestamp(logging.ERROR, *args)
    
    def critical(self, *args: Any) -> None:
        """严重错误日志"""
        self._log_with_timestamp(logging.CRITICAL, *args)


# 创建默认的日志实例
logger = TimestampLogger()

# 为了向后兼容，提供简单的函数接口
def log_with_time(*args: Any) -> None:
    """带时间戳的普通日志"""
    timestamp = get_timestamp()
    message = ' '.join(str(arg) for arg in args)
    print(f"[{timestamp}] {message}")

def error_with_time(*args: Any) -> None:
    """带时间戳的错误日志"""
    logger.error(*args)

def warn_with_time(*args: Any) -> None:
    """带时间戳的警告日志"""
    logger.warning(*args)

def info_with_time(*args: Any) -> None:
    """带时间戳的信息日志"""
    logger.info(*args)

def debug_with_time(*args: Any) -> None:
    """带时间戳的调试日志"""
    logger.debug(*args)

def get_logger(name: str = __name__) -> TimestampLogger:
    """获取带时间戳的日志记录器实例
    
    Args:
        name: 日志记录器名称，通常使用 __name__
        
    Returns:
        TimestampLogger: 带时间戳的日志记录器实例
    """
    return TimestampLogger(name)