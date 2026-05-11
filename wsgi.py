"""
伴读书童 - PythonAnywhere WSGI 入口文件
"""
import os
import sys

# 项目根目录
project_home = '/home/CBGoat/bandushutong'
if project_home not in sys.path:
    sys.path.insert(0, project_home)
    sys.path.insert(0, os.path.join(project_home, 'backend'))

from backend.main import app as application
