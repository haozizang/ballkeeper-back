import sys
import os

# NOTE: 此行代码应在所有导入之前: 添加main所在目录到Python路径
sys.path.append(os.path.dirname(__file__))

from envs import ROOT_DIR, IMG_DIR
from log import create_logger

logger = create_logger(name="ballkeeper", level="debug", log_dir=f"{ROOT_DIR}/logs")

from db.database import init_db
from db.models import *

# 初始化数据库,创建数据库表
init_db()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers import users, teams, leagues, activities, others

app = FastAPI()
app.include_router(users.router)
app.include_router(teams.router)
app.include_router(leagues.router)
app.include_router(activities.router)
app.include_router(others.router)

# 添加调试中间件
@app.middleware("http")
async def log_request_details(request, call_next):
    # 打印请求方法和URL
    logger.debug(f"Request method: {request.method}")
    logger.debug(f"Request URL: {request.url}")

    '''
    # 打印请求头
    logger.debug("Request headers:")
    for header, value in request.headers.items():
        logger.debug(f"{header}: {value}")
    '''

    # 打印请求体 (如果是POST/PUT请求)
    if request.method in ["POST", "PUT"]:
        try:
            body = await request.body()
            logger.debug(f"Request body decode: {body.decode()}")
        except Exception as e:
            logger.debug(f"Could not read request body: {e}")

    # 继续处理请求
    response = await call_next(request)
    return response

app.mount('/images', StaticFiles(directory=IMG_DIR), name="images")
