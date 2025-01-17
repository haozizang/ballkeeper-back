from typing import Optional
from fastapi import FastAPI, Depends
from sqlmodel import Field, Session, SQLModel, create_engine, select
import logging
from enum import IntEnum

logging.basicConfig(level=logging.DEBUG)

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

# 创建数据库表
SQLModel.metadata.create_all(engine)

# 依赖项
def get_session():
    with Session(engine) as session:
        yield session

app = FastAPI()

@app.get('/ballkeeper/')
async def hello_world():
    return {'Hello': 'World'}

@app.post('/ballkeeper/register/')
async def register(user: User, session: Session = Depends(get_session)):
    try:
        user_exists = session.exec(select(User).where(User.username == user.username)).first()
        if user_exists:
            return {'res': StatusCode.get_message(StatusCode.USER_EXISTS),
                   'code': StatusCode.USER_EXISTS}

        session.add(user)
        session.commit()
        session.refresh(user)
        return {'res': StatusCode.get_message(StatusCode.SUCCESS),
                'code': StatusCode.SUCCESS}
    except Exception as e:
        session.rollback()
        logging.error(f"数据库操作错误: {e}")
        return {'res': StatusCode.get_message(StatusCode.DB_ERROR),
                'code': StatusCode.DB_ERROR}

@app.post('/ballkeeper/login/')
async def login(user: User, session: Session = Depends(get_session)):
    try:
        user_exists = session.exec(select(User).where(User.username == user.username)).first()
        if not user_exists:
            return {'res': StatusCode.get_message(StatusCode.USER_NOT_FOUND),
                   'code': StatusCode.USER_NOT_FOUND}

        if user_exists.password != user.password:
            return {'res': StatusCode.get_message(StatusCode.WRONG_PASSWORD),
                   'code': StatusCode.WRONG_PASSWORD}

        return {'res': StatusCode.get_message(StatusCode.SUCCESS),
                'code': StatusCode.SUCCESS}
    except Exception as e:
        session.rollback()
        logging.error(f"数据库操作错误: {e}")
        return {'res': StatusCode.get_message(StatusCode.DB_ERROR),
                'code': StatusCode.DB_ERROR}

@app.get('/items/{item_id}')
async def read_item(item_id: int, q: Optional[str] = None):
    return {'item_id': item_id, 'q': q}
