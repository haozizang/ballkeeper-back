import os
import logging
from envs import ROOT_DIR
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy.exc import SQLAlchemyError
from img_generator.img_gen import gen_txt_img
from db.models import User
from db.database import get_session
from utils import get_img_path

logger = logging.getLogger("ballkeeper")

router = APIRouter()

@router.post('/ballkeeper/register/')
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

@router.post('/ballkeeper/login/')
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
