'''
环境变量
'''

import os

# 数据库
DATABASE_URL = "sqlite:///ballkeeper.db"

# 图片
ROOT_DIR = ".."
AVATAR_DIR = f"{ROOT_DIR}/images/avatar"
TEAM_LOGO_DIR = f"{ROOT_DIR}/images/team_logo"
APP_DIR = f"{ROOT_DIR}/images/app"

os.makedirs(f"{AVATAR_DIR}", exist_ok=True)
os.makedirs(f"{TEAM_LOGO_DIR}", exist_ok=True)
os.makedirs(f"{APP_DIR}", exist_ok=True)