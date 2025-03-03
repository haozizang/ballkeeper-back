from sqlmodel import SQLModel, Session, create_engine
from envs import DATABASE_URL
import logging

# 创建数据库引擎
engine = create_engine(DATABASE_URL)

# 依赖项 - 获取数据库会话
def get_session():
    with Session(engine) as session:
        try:
            yield session
        except Exception as e:
            session.rollback()
            logging.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

# 初始化数据库
def init_db():
    """初始化数据库表结构"""
    SQLModel.metadata.create_all(engine)