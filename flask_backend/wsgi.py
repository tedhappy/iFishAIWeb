#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI入口文件，用于Gunicorn部署
"""

import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 导入Flask应用
from app import app

# 设置应用实例
application = app

if __name__ == "__main__":
    application.run()