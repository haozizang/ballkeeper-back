import os
import logging
from envs import ROOT_DIR
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlmodel import Session
from db.database import get_session
from utils import compress_image, get_img_path


logger = logging.getLogger("ballkeeper")

router = APIRouter()

@router.get('/ballkeeper/')
async def hello_world():
    return {'Hello': 'World'}

@router.get('/ballkeeper/get_app_info/')
async def get_app_info():
    return {'name': 'ballkeeper', 'logo_path': '/images/app/logo.png', 'version': '1.0.0'}

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
