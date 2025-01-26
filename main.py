from typing import Optional
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy.exc import SQLAlchemyError
import logging
from enum import IntEnum
import os
import shutil

STATIC_URL_BASE = "/static"
AVATAR_DIR = "images/avatar"
TEAM_LOGO_DIR = "images/team_logo"

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
    team_id: Optional[int] = Field(default=None)

# 添加 Team 模型
class Team(SQLModel, table=True):
    __tablename__ = "teams"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    category_id: int
    is_public: bool = Field(default=True)
    mobile: str
    name: str
    content: Optional[str] = None
    creator_id: int = Field(foreign_key="users.id")
    logo_path: Optional[str] = None

# 创建数据库表
SQLModel.metadata.create_all(engine)

# 依赖项
def get_session():
    with Session(engine) as session:
        yield session

app = FastAPI()

# 添加调试中间件
@app.middleware("http")
async def log_request_details(request, call_next):
    # 打印请求方法和URL
    logging.debug(f"请求方法: {request.method}")
    logging.debug(f"请求URL: {request.url}")

    # 打印请求头
    logging.debug("请求头:")
    for header, value in request.headers.items():
        logging.debug(f"    {header}: {value}")

    # 打印请求体 (如果是POST/PUT请求)
    if request.method in ["POST", "PUT"]:
        try:
            body = await request.body()
            logging.debug(f"请求体: {body}")
            logging.debug(f"请求体decode: {body.decode()}")
        except Exception as e:
            logging.debug(f"无法读取请求体: {e}")

    # 继续处理请求
    response = await call_next(request)
    return response

os.makedirs(f"{AVATAR_DIR}", exist_ok=True)
os.makedirs(f"{TEAM_LOGO_DIR}", exist_ok=True)
app.mount(f"{STATIC_URL_BASE}/avatar", StaticFiles(directory=f"{AVATAR_DIR}"), name="avatar")
app.mount(f"{STATIC_URL_BASE}/team_logo", StaticFiles(directory=f"{TEAM_LOGO_DIR}"), name="team_logo")

@app.get('/ballkeeper/')
async def hello_world():
    return {'Hello': 'World'}

@app.post('/ballkeeper/register/')
async def register(user: User, session: Session = Depends(get_session)):
    try:
        # 检查用户是否存在
        user_exists = session.exec(select(User).where(User.username == user.username)).first()
        if user_exists:
            raise HTTPException(
                status_code=409,
                detail="用户已存在"
            )

        session.add(user)
        session.commit()
        session.refresh(user)
        return {'username': user.username}
    except SQLAlchemyError as e:
        session.rollback()
        logging.error(f"数据库操作错误: {e}")
        raise HTTPException(
            status_code=500,
            detail="数据库操作失败"
        )

@app.post('/ballkeeper/upload_image/')
async def upload_image(username: str=Form(...), image_name: str=Form(...), image_type: str=Form(...), image: UploadFile = File(...), session: Session = Depends(get_session)):
    logging.info(f"DBG: username: {username} image_name: {image_name} image: {image}")
    try:
        if image_type == "avatar":
            user = session.exec(select(User).where(User.username == username)).first()
            if not user:
                raise HTTPException(
                    status_code=404,
                    detail="用户不存在"
                )

            # 生成文件名（使用用户名和原始文件扩展名）
            file_extension = os.path.splitext(image.filename)[1]
            avatar_path = f"{AVATAR_DIR}/{image_name}{file_extension}"

            # 保存文件
            with open(avatar_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)

            # 更新用户的avatar_path
            user.avatar_path = avatar_path
            session.commit()

            avatar_url = f"{STATIC_URL_BASE}/avatar/{image_name}{file_extension}"
            return {'avatar_url': avatar_url}
        elif image_type == "team_logo":
            user = session.exec(select(User).where(User.username == username)).first()
            if not user:
                raise HTTPException(
                    status_code=404,
                    detail="用户不存在"
                )
            team_id = user.team_id
            if not team_id:
                raise HTTPException(
                    status_code=404,
                    detail="用户没有团队"
                )

            team_logo_path = f"{TEAM_LOGO_DIR}/{image_name}{file_extension}"
            with open(team_logo_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            return {'team_logo_url': team_logo_path}
    except Exception as e:
        session.rollback()
        logging.error(f"上传头像失败: {e}")
        raise HTTPException(
            status_code=500,
            detail="上传头像失败"
        )

@app.post('/ballkeeper/login/')
async def login(user: User, session: Session = Depends(get_session)):
    try:
        logging.debug(f"登录用户: {user}")
        user_exists = session.exec(select(User).where(User.username == user.username)).first()
        if not user_exists:
            raise HTTPException(
                status_code=404,
                detail="用户不存在"
            )

        if user_exists.password != user.password:
            raise HTTPException(
                status_code=401,
                detail="密码错误"
            )

        return {'username': user_exists.username}
    except Exception as e:
        session.rollback()
        logging.error(f"数据库操作错误: {e}")
        raise HTTPException(
            status_code=500,
            detail="数据库操作失败"
        )

@app.get('/items/{item_id}')
async def read_item(item_id: int, q: Optional[str] = None):
    return {'item_id': item_id, 'q': q}

@app.post('/ballkeeper/create_team/')
async def create_team(
    username: str = Body(...),
    title: str = Body(...),
    category_id: int = Body(...),
    is_public: bool = Body(...),
    mobile: str = Body(...),
    name: str = Body(...),
    content: Optional[str] = Body(None),
    session: Session = Depends(get_session)
):
    try:
        # 从请求头获取用户信息（假设已经实现了认证机制）
        # TODO: 实现proper的用户认证
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise HTTPException(
                status_code=401,
                detail="用户未登录"
            )

        # 创建新团队
        team = Team(
            title=title,
            category_id=category_id,
            is_public=is_public,
            mobile=mobile,
            name=name,
            content=content,
            creator_id=user.id
        )

        session.add(team)
        session.commit()
        session.refresh(team)

        # 更新用户的 team_id
        user.team_id = team.id
        session.commit()

        return team.id

    except SQLAlchemyError as e:
        session.rollback()
        logging.error(f"创建团队失败: {e}")
        raise HTTPException(
            status_code=500,
            detail="创建团队失败"
        )
