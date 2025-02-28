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
from utils import path_from_dir, strfnow, compress_image, get_img_path


app = FastAPI()

# 添加调试中间件
@app.middleware("http")
async def log_request_details(request, call_next):
    # 打印请求方法和URL
    logger.debug(f"请求方法: {request.method}")
    logger.debug(f"请求URL: {request.url}")

    # 打印请求头
    logger.debug("请求头:")
    for header, value in request.headers.items():
        logger.debug(f"{header}: {value}")

    # 打印请求体 (如果是POST/PUT请求)
    if request.method in ["POST", "PUT"]:
        try:
            body = await request.body()
            logger.debug(f"请求体decode: {body.decode()[:100]}")
        except Exception as e:
            logger.debug(f"无法读取请求体: {e}")

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
                detail="用户已存在"
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
        logger.error(f"数据库操作错误: {e}")
        raise HTTPException(
            status_code=500,
            detail="数据库操作失败"
        )

@app.post('/ballkeeper/upload_image/')
async def upload_image(image_type: str=Form(...), image: UploadFile = File(...), session: Session = Depends(get_session)):
    logger.info(f"DBG: image_type: {image_type}")
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
        logger.info(f"DBG: save compressed image to {abs_path}")
        with open(abs_path, "wb") as f:
            f.write(compressed_img)

        # 构造返回URL

        return {
            'img_path': img_path
        }
    except Exception as e:
        session.rollback()
        logger.error(f"上传图片失败: {e}")
        raise HTTPException(
            status_code=500,
            detail="上传图片失败"
        )

@app.post('/ballkeeper/login/')
async def login(user: User, session: Session = Depends(get_session)):
    try:
        logger.debug(f"登录用户: {user}")
        user = session.exec(select(User).where(User.username == user.username)).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="用户不存在"
            )

        if user.password != user.password:
            raise HTTPException(
                status_code=401,
                detail="密码错误"
            )

        return {'username': user.username, 'avatar_path': user.avatar_path}
    except Exception as e:
        session.rollback()
        logger.error(f"数据库操作错误: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"登录失败: {e}"
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
        logger.error(f"创建团队成功: {team}")

        return {'team': team}
    except SQLAlchemyError as e:
        session.rollback()
        # 检查是否是唯一约束违反错误
        logger.error(f"caught SQLAlchemyError: {e}")
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(
                status_code=409,  # Conflict
                detail="球队名称已存在"
            )
        logger.error(f"创建团队失败: {e}")
        raise HTTPException(status_code=500, detail="创建团队失败")

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
            raise HTTPException(status_code=404, detail="球队不存在")

        return {'team': team}
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"获取球队(id={team_id})失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取球队(id={team_id})失败")

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
        logger.error(f"获取球队列表失败: {e}")
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
        logger.error(f"加入球队失败: {e}")
        raise HTTPException(status_code=500, detail="加入球队失败")

@app.post('/ballkeeper/create_league/')
async def create_league(
    creator: str = Body(...),
    name: str = Body(...),
    league_type_ind: int = Body(...),
    mobile: str = Body(...),
    content: Optional[str] = Body(None),
    session: Session = Depends(get_session)
):
    try:
        user = session.exec(select(User).where(User.username == creator)).first()
        if not user:
            raise HTTPException(
                status_code=401,
                detail="用户不存在"
            )

        # 创建新联赛
        league = League(
            name=name,
            league_type_ind=league_type_ind,
            mobile=mobile,
            content=content,
            creator_id=user.id
        )

        img = gen_txt_img(name)
        img_path = f"{ROOT_DIR}/images/{strfnow()}.png"
        img.save(img_path)
        league.logo_path = img_path

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
        logger.info(f"创建联赛成功: {league}")

        return {'league': league}
    except SQLAlchemyError as e:
        session.rollback()
        # 检查是否是唯一约束违反错误
        logger.error(f"caught SQLAlchemyError: {e}")
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(
                status_code=409,  # Conflict
                detail="联赛名称已存在"
            )
        logger.error(f"创建联赛失败: {e}")
        raise HTTPException(status_code=500, detail="创建联赛失败")