import sys
import os

# 添加main.py所在目录到 Python 路径
sys.path.append(os.path.dirname(__file__))

from envs import ROOT_DIR, IMG_DIR
from log import create_logger

logger = create_logger(name="ballkeeper", level="debug", log_dir=f"{ROOT_DIR}/logs")

from typing import Optional
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from sqlalchemy.exc import SQLAlchemyError
from img_generator.img_gen import gen_txt_img
from models import User, Team, UserTeam, League, UserLeague, get_session
from utils import path_from_dir, compress_image, get_img_path

app = FastAPI()

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
            logger.debug(f"Request body decode: {body.decode()[:100]}")
        except Exception as e:
            logger.debug(f"Could not read request body: {e}")

    # 继续处理请求
    response = await call_next(request)
    return response

app.mount('/images', StaticFiles(directory=IMG_DIR), name="images")

@app.get('/ballkeeper/')
async def hello_world():
    return {'Hello': 'World'}

@app.get('/ballkeeper/get_app_info/')
async def get_app_info():
    return {'name': 'ballkeeper', 'logo_path': '/images/app/logo.png', 'version': '1.0.0'}

@app.post('/ballkeeper/register/')
async def register(user: User, session: Session = Depends(get_session)):
    try:
        # 检查用户是否存在
        user_exists = session.exec(select(User).where(User.username == user.username)).first()
        if user_exists:
            raise HTTPException(
                status_code=409,
                detail="User already exists"
            )

        # 生成默认头像
        if not user.avatar_path:
            img = gen_txt_img(user.username)
            img_path = get_img_path("avatar", ".png")
            abs_path = f"{ROOT_DIR}{img_path}"
            img.save(abs_path)
            user.avatar_path = img_path

        session.add(user)
        session.commit()
        session.refresh(user)
        return {'user': user}
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database operation error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        )

@app.post('/ballkeeper/upload_image/')
async def upload_image(image_type: str=Form(...), image: UploadFile = File(...), session: Session = Depends(get_session)):
    logger.info(f"DEBUG: image_type: {image_type}")
    try:
        # 读取上传文件内容
        contents = await image.read()

        # 获取文件扩展名
        ext = os.path.splitext(image.filename)[1].lower()

        # 生成文件名和路径
        img_path = get_img_path(image_type, ext)
        abs_path = f"{ROOT_DIR}{img_path}"

        # 压缩图片
        compressed_img = compress_image(contents, ext)

        # 保存压缩后的图片
        logger.info(f"DEBUG: save compressed image to {abs_path}")
        with open(abs_path, "wb") as f:
            f.write(compressed_img)

        # 构造返回URL

        return {
            'img_path': img_path
        }
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to upload image: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to upload image"
        )

@app.post('/ballkeeper/login/')
async def login(user: User, session: Session = Depends(get_session)):
    try:
        logger.debug(f"Login user: {user}")
        user = session.exec(select(User).where(User.username == user.username)).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User does not exist"
            )

        if user.password != user.password:
            raise HTTPException(
                status_code=401,
                detail="Incorrect password"
            )

        return {'username': user.username, 'avatar_path': user.avatar_path}
    except Exception as e:
        session.rollback()
        logger.error(f"Database operation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {e}"
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
                detail="User does not exist"
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

        img = gen_txt_img(title)
        img_path = f"{path_from_dir(TEAM_LOGO_DIR)}/{title}.png"
        img.save(f".{img_path}")
        team.logo_path = img_path

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
        logger.info(f"Team created successfully: {team}")

        return {'team': team}
    except SQLAlchemyError as e:
        session.rollback()
        # 检查是否是唯一约束违反错误
        logger.error(f"Caught SQLAlchemyError: {e}")
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(
                status_code=409,  # Conflict
                detail="Team name already exists"
            )
        logger.error(f"Failed to create team: {e}")
        raise HTTPException(status_code=500, detail="Failed to create team")

@app.post('/ballkeeper/get_team/')
async def get_team(team_id: int = Body(..., embed=True), session: Session = Depends(get_session)):
    try:
        # 构建基础查询
        query = (
            select(Team)
            .where(Team.id == team_id)
        )

        # 执行查询
        team = session.exec(query).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team does not exist")

        return {'team': team}
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Failed to get team(id={team_id}): {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get team(id={team_id})")

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
                detail="User does not exist"
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
        logger.error(f"Failed to get team list: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get team list"
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
            raise HTTPException(status_code=401, detail="User does not exist")

        team = session.exec(select(Team).where(Team.id == team_id)).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team does not exist")

        # 检查是否已经加入
        existing = session.exec(
            select(UserTeam).where(
                UserTeam.user_id == user.id,
                UserTeam.team_id == team_id
            )
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="Already joined this team")

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
        logger.error(f"Failed to join team: {e}")
        raise HTTPException(status_code=500, detail="Failed to join team")

@app.post('/ballkeeper/create_league/')
async def create_league(
    creator: str = Body(...),
    name: str = Body(...),
    league_type_ind: int = Body(...),
    mobile: str = Body(...),
    content: Optional[str] = Body(None),
    cover_path: Optional[str] = Body(None),
    session: Session = Depends(get_session)
):
    try:
        user = session.exec(select(User).where(User.username == creator)).first()
        if not user:
            raise HTTPException(
                status_code=401,
                detail="User does not exist"
            )

        # 创建新联赛
        league = League(
            name=name,
            league_type_ind=league_type_ind,
            mobile=mobile,
            content=content,
            creator_id=user.id,
            cover_path=cover_path
        )

        if not league.cover_path:
            img = gen_txt_img(name, (100, 100))
            img_path = get_img_path("league", ".png")
            abs_path = f"{ROOT_DIR}{img_path}"
            img.save(abs_path)
            league.cover_path = img_path

        session.add(league)
        session.commit()
        session.refresh(league)

        # 创建用户-联赛关联记录,设置创建者角色
        user_league = UserLeague(
            user_id=user.id,
            league_id=league.id,
            role="creator"  # 设置为创建者角色
        )
        session.add(user_league)
        session.commit()
        logger.info(f"League created successfully: {league}")

        return {'league': league}
    except SQLAlchemyError as e:
        session.rollback()
        # 检查是否是唯一约束违反错误
        logger.error(f"Caught SQLAlchemyError: {e}")
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(
                status_code=409,  # Conflict
                detail="League name already exists"
            )
        logger.error(f"Failed to create league: {e}")
        raise HTTPException(status_code=500, detail="Failed to create league")

@app.get('/ballkeeper/get_league/')
async def get_league(league_id: int, session: Session = Depends(get_session)):
    try:
        logger.debug(f"Fetching league")
        league = session.exec(select(League).where(League.id == league_id)).first()
        if not league:
            raise HTTPException(
                status_code=401,
                detail="League does not exist"
            )

        return {'league': league}
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Failed to get league: {e}")
        raise HTTPException(status_code=500, detail="Failed to get league")

@app.get('/ballkeeper/get_league_list/')
async def get_league_list(session: Session = Depends(get_session)):
    try:
        leagues = session.exec(select(League)).all()
        return {'leagues': leagues}
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Failed to get league list: {e}")
        raise HTTPException(status_code=500, detail="Failed to get league list")
