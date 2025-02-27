'''
环境变量
'''

import os

# 数据库
DATABASE_URL = "sqlite:///ballkeeper.db"

# 图片
# parent dir
ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
IMG_DIR = os.path.join(ROOT_DIR, "images")

os.makedirs(IMG_DIR, exist_ok=True)