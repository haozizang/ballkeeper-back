from typing import Optional
from fastapi import FastAPI, Depends, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from sqlmodel import Field, Session, SQLModel, create_engine, select
import logging
from enum import IntEnum
import os
import shutil

STATIC_URL_BASE = "/static"  # 开发环境

# 配置日志格式
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 数据库配置 - 使用 SQLite
DATABASE_URL = "sqlite:///ballkeeper.db"
engine = create_engine(DATABASE_URL)

# 定义状态码枚举
class StatusCode(IntEnum):
    SUCCESS = 0
    ERROR = 1
    USER_EXISTS = 2
    USER_NOT_FOUND = 3
    WRONG_PASSWORD = 4
    DB_ERROR = 5

    @classmethod
    def get_message(cls, code):
        messages = {
            cls.SUCCESS: "ok",
            cls.DB_ERROR: "数据库操作失败",
            cls.USER_EXISTS: "用户已存在",
            cls.USER_NOT_FOUND: "用户不存在",
            cls.WRONG_PASSWORD: "密码错误"
        }
        return messages.get(code, "未知错误")

# 统一的模型定义，同时用于 API 和数据库
class User(SQLModel, table=True):
    __tablename__ = "users"  # 显式定义表名
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password: str
    avatar_path: Optional[str] = None

# 创建数据库表
SQLModel.metadata.create_all(engine)

# 依赖项
def get_session():
    with Session(engine) as session:
        yield session

app = FastAPI()
app.mount("/static/avatars", StaticFiles(directory="avatars"), name="avatars")

@app.get('/ballkeeper/')
async def hello_world():
    return {'Hello': 'World'}

@app.post('/ballkeeper/register/')
async def register(user: User, session: Session = Depends(get_session)):
    try:
        user_exists = session.exec(select(User).where(User.username == user.username)).first()
        if user_exists:
            return {'msg': StatusCode.get_message(StatusCode.USER_EXISTS),
                   'code': StatusCode.USER_EXISTS}

        session.add(user)
        session.commit()
        session.refresh(user)
        return {'msg': StatusCode.get_message(StatusCode.SUCCESS),
                'code': StatusCode.SUCCESS,
                'data': {'username': user.username}}
    except Exception as e:
        session.rollback()
        logging.error(f"数据库操作错误: {e}")
        return {'msg': StatusCode.get_message(StatusCode.DB_ERROR),
                'code': StatusCode.DB_ERROR}

@app.post('/ballkeeper/upload_avatar/')
async def upload_avatar(avatar: UploadFile = File(...), username: str = Form(...), session: Session = Depends(get_session)):
    try:
        logging.info(f"DBG: username: {username} avatar: {avatar}")
        # 检查用户是否存在
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            return {
                'msg': StatusCode.get_message(StatusCode.USER_NOT_FOUND),
                'code': StatusCode.USER_NOT_FOUND
            }

        # 创建保存头像的目录
        avatar_dir = "avatars"
        if not os.path.exists(avatar_dir):
            os.makedirs(avatar_dir)

        # 生成文件名（使用用户名和原始文件扩展名）
        file_extension = os.path.splitext(avatar.filename)[1]
        avatar_path = f"{avatar_dir}/{username}{file_extension}"

        # 保存文件
        with open(avatar_path, "wb") as buffer:
            shutil.copyfileobj(avatar.file, buffer)

        # 更新用户的avatar_path
        user.avatar_path = avatar_path
        session.commit()

        avatar_url = f"{STATIC_URL_BASE}/avatars/{username}{file_extension}"

        return {
            'msg': StatusCode.get_message(StatusCode.SUCCESS),
            'code': StatusCode.SUCCESS,
            'data': {'avatar_url': avatar_url}
        }

    except Exception as e:
        session.rollback()
        logging.error(f"上传头像失败: {e}")
        return {
            'msg': StatusCode.get_message(StatusCode.DB_ERROR),
            'code': StatusCode.DB_ERROR
        }

@app.post('/ballkeeper/login/')
async def login(user: User, session: Session = Depends(get_session)):
    try:
        logging.debug(f"登录用户: {user}")
        user_exists = session.exec(select(User).where(User.username == user.username)).first()
        if not user_exists:
            return {'msg': StatusCode.get_message(StatusCode.USER_NOT_FOUND),
                   'code': StatusCode.USER_NOT_FOUND}

        if user_exists.password != user.password:
            return {'msg': StatusCode.get_message(StatusCode.WRONG_PASSWORD),
                   'code': StatusCode.WRONG_PASSWORD}

        return {'msg': StatusCode.get_message(StatusCode.SUCCESS),
                'code': StatusCode.SUCCESS,
                'data': {'username': user_exists.username}}
    except Exception as e:
        session.rollback()
        logging.error(f"数据库操作错误: {e}")
        return {'msg': StatusCode.get_message(StatusCode.DB_ERROR),
                'code': StatusCode.DB_ERROR}

@app.get('/items/{item_id}')
async def read_item(item_id: int, q: Optional[str] = None):
    return {'item_id': item_id, 'q': q}
