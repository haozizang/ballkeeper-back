import os
import logging
from envs import ROOT_DIR
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Body
from sqlmodel import Session, select
from sqlalchemy.exc import SQLAlchemyError
from img_generator.img_gen import gen_txt_img
from db.models import User, Team, UserTeam, League, UserLeague
from db.database import get_session
from utils import compress_image, get_img_path


logger = logging.getLogger("ballkeeper")

router = APIRouter()

@router.post('/ballkeeper/upload_image/')
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

@router.post('/ballkeeper/create_team/')
async def create_team(
    username: str = Body(...),
    name: str = Body(...),
    category_id: int = Body(...),
    is_public: bool = Body(...),
    mobile: str = Body(...),
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
            name=name,
            category_id=category_id,
            is_public=is_public,
            mobile=mobile,
            content=content,
            creator_id=user.id
        )

        if not team.logo_path:
            img = gen_txt_img(name)
            img_path = get_img_path("team", ".png")
            abs_path = f"{ROOT_DIR}{img_path}"
            img.save(abs_path)
            team.logo_path = img_path

        session.add(team)
        session.commit()
        session.refresh(team)

        user.team_id = team.id
        session.add(user)
        session.commit()

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

@router.post('/ballkeeper/get_team/')
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
@router.post('/ballkeeper/get_team_list/')
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
            query = query.where(Team.name.contains(keyword))

        # 直接添加分页并执行查询 - 完全移除计数部分
        results = session.exec(query.offset(offset).limit(limit)).all()

        # 构造返回数据
        team_list = [
            {
                **dict(team),
                "follow_time": follow_time.isoformat(),
                "role": role
            }
            for team, follow_time, role in results
        ]

        # 简化的响应，不包含总数
        return {'team_list': team_list, 'offset': offset, 'limit': limit}

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Failed to get team list: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get team list"
        )

@router.post('/ballkeeper/follow_team/')
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
