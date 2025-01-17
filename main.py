from typing import Optional
from fastapi import FastAPI, Depends
from sqlmodel import Field, Session, SQLModel, create_engine, select
import logging

logging.basicConfig(level=logging.DEBUG)

# 数据库配置 - 使用 SQLite
DATABASE_URL = "sqlite:///ballkeeper.db"
engine = create_engine(DATABASE_URL)

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
        logging.debug(f"user: {user}")
        session.add(user)
        session.commit()
        session.refresh(user)
        return {'res': 'ok', 'code': 0}
    except Exception as e:
        session.rollback()
        logging.error(f"数据库操作错误: {e}")
        return {'res': '数据库操作失败', 'code': 1}

@app.post('/ballkeeper/login/')
async def login(user: User, session: Session = Depends(get_session)):
    try:
        logging.debug(f"user: {user}")
        # check if user exists
        user_exists = session.exec(select(User).where(User.username == user.username)).first()
        logging.debug(f"user_exists: {user_exists}")
        if not user_exists:
            return {'res': '用户不存在', 'code': 1}
        # check if password is correct
        if user_exists.password != user.password:
            return {'res': '密码错误', 'code': 1}
        return {'res': 'ok', 'code': 0}
    except Exception as e:
        session.rollback()
        logging.error(f"数据库操作错误: {e}")
        return {'res': '数据库操作失败', 'code': 1}

@app.get('/items/{item_id}')
async def read_item(item_id: int, q: Optional[str] = None):
    return {'item_id': item_id, 'q': q}
