import logging
from envs import ROOT_DIR
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session, select
from sqlalchemy.exc import SQLAlchemyError
from img_generator.img_gen import gen_txt_img
from db.models import User, UserBase, Activity, ActivityUser, Team
from db.database import get_session
from utils import get_img_path
from constants import SignupType

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
        attend_users = []
        pending_users = []
        absent_users = []
        for act_user in act_users:
            user_exists = session.exec(select(User).where(User.id == act_user.user_id)).first()
            if not user_exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"User[{act_user.user_id}] for Activity[{act_id}] not exists"
                )
            if act_user.signup_type == SignupType.ATTENDING:
                attend_users.append(UserBase.model_validate(user_exists))
            elif act_user.signup_type == SignupType.PENDING:
                pending_users.append(UserBase.model_validate(user_exists))
            elif act_user.signup_type == SignupType.ABSENT:
                absent_users.append(UserBase.model_validate(user_exists))
        return {'attend_users': attend_users, 'pending_users': pending_users, 'absent_users': absent_users}
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f'DB error: {str(e)}'
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=f'DB error: {str(e)}')

@router.get('/ballkeeper/get_activity/')
async def get_activity(activity_id: int, session: Session = Depends(get_session)):
    try:
        activity = session.exec(select(Activity).where(Activity.id == activity_id)).first()
        # get activity users info
        act_users = await get_act_users(activity_id, session)
        logger.debug(f"users for activity[{activity_id}]: {act_users}")

        act_creator = session.exec(select(User).where(User.id == activity.creator_id)).first() if activity.creator_id else None
        logger.debug(f"creator for activity[{activity_id}]: {act_creator}")

        act_team = session.exec(select(Team).where(Team.id == activity.team_id)).first() if activity.team_id != 0 else None
        logger.debug(f"team for activity[{activity_id}]: {act_team}")

        return {'activity': activity, **act_users, 'creator': UserBase.model_validate(act_creator), 'team': act_team}
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f'DB error: {str(e)}'
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.post('/ballkeeper/signup_act/')
async def signup_act(
    act_id: int = Body(...),
    user_id: int = Body(...),
    signup_type: int = Body(...),
    session: Session = Depends(get_session)):
    try:
        activity = session.exec(select(Activity).where(Activity.id == act_id)).first()
        if not activity:
            raise HTTPException(
                status_code=404,
                detail=f"Activity[{act_id}] not exists"
            )
        # check user_id is valid
        user = session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User[{user_id}] not exists"
            )
        # create activityUser
        activity_user = ActivityUser(
            activity_id=act_id,
            user_id=user_id,
            signup_type=signup_type
        )
        session.add(activity_user)
        session.commit()
        session.refresh(activity_user)
        session.refresh(user)
        return {'activity_user': activity_user, 'user': user}
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f'DB error: {str(e)}'
        logger.error(error_msg)
        if 'unique constraint' in error_msg.lower():
            raise HTTPException(status_code=409, detail=f'User[{user_id}] already signed up for activity[{act_id}]')
        raise HTTPException(status_code=500, detail=error_msg)