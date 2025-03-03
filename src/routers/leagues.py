import logging
from envs import ROOT_DIR
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session, select
from sqlalchemy.exc import SQLAlchemyError
from img_generator.img_gen import gen_txt_img
from db.models import User, League, UserLeague
from db.database import get_session
from utils import get_img_path


logger = logging.getLogger("ballkeeper")

router = APIRouter()

@router.post('/ballkeeper/create_league/')
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

@router.get('/ballkeeper/get_league/')
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

@router.get('/ballkeeper/get_leagues/')
async def get_leagues(limit : int = 10, offset : int = 0, session: Session = Depends(get_session)):
    try:
        leagues = session.exec(select(League).offset(offset).limit(limit)).all()
        return {'leagues': leagues, 'offset': offset, 'limit': limit}
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Failed to get league list: {e}")
        raise HTTPException(status_code=500, detail="Failed to get league list")

@router.get('/ballkeeper/get_my_leagues/')
async def get_my_leagues(username : str, limit : int = 10, offset : int = 0, session: Session = Depends(get_session)):
    try:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise HTTPException(status_code=401, detail="User does not exist")

        leagues = session.exec(select(League).where(League.creator_id == user.id).offset(offset).limit(limit)).all()
        return {'leagues': leagues, 'offset': offset, 'limit': limit}
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Failed to get league list: {e}")
        raise HTTPException(status_code=500, detail="Failed to get league list")
