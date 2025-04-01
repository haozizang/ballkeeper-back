import logging
from envs import ROOT_DIR
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session, select
from sqlalchemy.exc import SQLAlchemyError
from img_generator.img_gen import gen_txt_img
from db.models import User, UserBase, Activity, ActivityUser
from db.database import get_session
from utils import get_img_path

logger = logging.getLogger("ballkeeper")

router = APIRouter()

@router.post('/ballkeeper/create_activity/')
async def create_activity(activity: Activity, session: Session = Depends(get_session)):
    try:
        logger.debug(f"Creating activity: {activity}")
        # 检查用户是否存在
        user_exists = session.exec(select(User).where(User.id == activity.creator_id)).first()
        if not user_exists:
            raise HTTPException(
                status_code=409,
                detail="User does not exist"
            )

        # 生成默认头像
        if not activity.cover_path:
            img = gen_txt_img(activity.name)
            img_path = get_img_path("activity", ".png")
            abs_path = f"{ROOT_DIR}{img_path}"
            img.save(abs_path)
            activity.cover_path = img_path

        session.add(activity)
        session.commit()
        session.refresh(activity)
        return {'activity': activity}
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database operation error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        )

@router.get('/ballkeeper/get_activity/')
async def get_activity(activity_id: int, session: Session = Depends(get_session)):
    try:
        activity = session.exec(select(Activity).where(Activity.id == activity_id)).first()
        return {'activity': activity}
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database operation error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        )

@router.get('/ballkeeper/get_my_activities/')
async def get_my_activities(user_id: int, session: Session = Depends(get_session)):
    try:
        activities = session.exec(select(Activity).where(Activity.creator_id == user_id)).all()
        return {'activities': activities}
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database operation error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        )

@router.get('/ballkeeper/get_activities/')
async def get_activities(session: Session = Depends(get_session)):
    try:
        activities = session.exec(select(Activity)).all()
        return {'activities': activities}
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database operation error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        )

@router.get('/ballkeeper/get_act_users/')
async def get_act_users(act_id: int, session: Session = Depends(get_session)):
    try:
        act_users = session.exec(
            select(ActivityUser).where(
                ActivityUser.activity_id == act_id
            )
        ).all()

        logger.debug(f"DBG: 0 act_users: {act_users}")

        users = []
        for act_user in act_users:
            logger.debug(f"DBG: 1 act_user: {act_user}")
            user_exists = session.exec(select(User).where(User.id == act_user.user_id)).first()
            if not user_exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"User[{act_user.user_id}] for Activity[{act_id}] not exists"
                )
            users.append(UserBase.model_validate(user_exists))
        return {'users': users}
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database operation error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        )

@router.post('/ballkeeper/signup_act/')
async def signup_act(
    act_id: int = Body(...),
    user_id: int = Body(...),
    signup_type: int = Body(...),
    session: Session = Depends(get_session)):
    try:
        activity = session.exec(select(Activity).where(Activity.id == act_id)).first()
        return {'activity': activity}
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database operation error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        )