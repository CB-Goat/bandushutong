"""
伴读书童 - PythonAnywhere WSGI 入口文件
"""
import os
import sys

# 项目根目录（在 PythonAnywhere 上修改为实际路径）
project_home = '/home/你的用户名/bandushutong'
if project_home not in sys.path:
    sys.path.insert(0, project_home)
    sys.path.insert(0, os.path.join(project_home, 'backend'))

from backend.main import app as application
