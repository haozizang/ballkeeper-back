from typing import Optional
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy.exc import SQLAlchemyError
import logging
from enum import IntEnum
import os
import shutil
from datetime import datetime

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

# 添加用户-球队关联表模型
class UserTeam(SQLModel, table=True):
    __tablename__ = "user_team"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    team_id: int = Field(foreign_key="teams.id")
    follow_time: datetime = Field(default_factory=datetime.utcnow)
    role: str = Field(default="member")  # 可以是 "creator", "admin", "member" 等

# 修改 User 模型，移除 team_id 字段
class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password: str
    avatar_path: Optional[str] = None

# 添加 Team 模型
class Team(SQLModel, table=True):
    __tablename__ = "teams"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(unique=True, index=True)
    category_id: int
    is_public: bool = Field(default=True)
    mobile: str
    name: str
    content: Optional[str] = None
    # creator_id: int = Field(foreign_key="users.id")
    creator_id: int = Field(index=True)
    logo_url: Optional[str] = None

    def __str__(self):
        return f"Team(id={self.id}, title='{self.title}')"

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
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise HTTPException(
                status_code=401,
                detail="用户不存在"
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

        # 创建用户-球队关联记录,设置创建者角色
        user_team = UserTeam(
            user_id=user.id,
            team_id=team.id,
            role="creator"  # 设置为创建者角色
        )
        session.add(user_team)
        session.commit()

        logging.error(f"创建团队成功: {team}")

        return {'team': team}
    except SQLAlchemyError as e:
        session.rollback()
        # 检查是否是唯一约束违反错误
        logging.error(f"caught SQLAlchemyError: {e}")
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(
                status_code=409,  # Conflict
                detail="球队名称已存在"
            )
        logging.error(f"创建团队失败: {e}")
        raise HTTPException(
            status_code=500,
            detail="创建团队失败"
        )

'''
单个参数时, 需要 embed=True 来强制使用 JSON 对象格式
多个参数时, FastAPI 自动使用 JSON 对象格式，不需要 embed=True
'''
@app.post('/ballkeeper/get_team_list/')
async def get_team_list(
    username: str = Body(...),
    keyword: str = Body(...),
    limit: int = Body(...),
    offset: int = Body(...),
    session: Session = Depends(get_session)
):
    try:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise HTTPException(
                status_code=401,
                detail="用户不存在"
            )

        # 构建基础查询
        query = (
            select(Team, UserTeam.follow_time, UserTeam.role)
            .join(UserTeam)
            .where(UserTeam.user_id == user.id)
        )

        # 添加标题搜索条件（如果keyword不为空）
        if keyword.strip():
            query = query.where(Team.title.contains(keyword))

        # 获取总记录数
        total_count = len(session.exec(query).all())

        # 添加分页(SELECT columns FROM table LIMIT [number_of_rows] OFFSET [number_of_rows_to_skip];)
        query = query.offset(offset).limit(limit)

        # 执行查询
        results = session.exec(query).all()

        # 构造返回数据
        team_list = [
            {
                **dict(team),
                "follow_time": follow_time.isoformat(),
                "role": role
            }
            for team, follow_time, role in results
        ]

        return {'total': total_count, 'team_list': team_list, 'offset': offset, 'limit': limit}

    except SQLAlchemyError as e:
        session.rollback()
        logging.error(f"获取球队列表失败: {e}")
        raise HTTPException(
            status_code=500,
            detail="获取球队列表失败"
        )

@app.post('/ballkeeper/follow_team/')
async def follow_team(
    username: str = Body(...),
    team_id: int = Body(...),
    session: Session = Depends(get_session)
):
    try:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")

        team = session.exec(select(Team).where(Team.id == team_id)).first()
        if not team:
            raise HTTPException(status_code=404, detail="球队不存在")

        # 检查是否已经加入
        existing = session.exec(
            select(UserTeam).where(
                UserTeam.user_id == user.id,
                UserTeam.team_id == team_id
            )
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="已经加入该球队")

        # 创建新的关联记录
        user_team = UserTeam(
            user_id=user.id,
            team_id=team_id,
            role="member"
        )
        session.add(user_team)
        session.commit()

        return team

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logging.error(f"加入球队失败: {e}")
        raise HTTPException(status_code=500, detail="加入球队失败")
