from datetime import datetime
from PIL import Image
import io
import logging

logger = logging.getLogger("ballkeeper")

# NOTE: dir[`images/avatar/`] => path[`/images/avatar/`]
def path_from_dir(dir):
    return f"/{dir}"

def strfnow():
    return datetime.now().strftime("%Y%m%d%H%M%S%f")

def compress_image(image_data: bytes, file_extension: str, max_size: int = 100 * 1024) -> bytes:
    """
    压缩图片至指定大小以内

    Args:
        image_data: 原始图片数据
        file_extension: 文件扩展名（带.）如.jpg、.png
        max_size: 最大文件大小（字节），默认100KB

    Returns:
        bytes: 压缩后的图片数据
    """
    img_len = len(image_data)
    # 如果原始图片已经小于最大尺寸，直接返回
    if img_len <= max_size:
        logger.info(f"image size[{img_len}] <= {max_size}, return")
        return image_data

    logger.info(f"image size[{img_len}] > {max_size}, compressing...")

    # 打开图片
    img = Image.open(io.BytesIO(image_data))

    # 根据不同格式使用不同压缩方法
    output = io.BytesIO()
    file_extension = file_extension.lower()

    if file_extension in ['.jpg', '.jpeg']:
        # JPEG压缩：调整质量
        quality = 90
        while quality > 10:
            output.seek(0)
            output.truncate(0)
            img.save(output, format='JPEG', quality=quality)
            if output.tell() <= max_size:
                break
            quality -= 10

    elif file_extension == '.png':
        # PNG压缩：转换为RGB模式（移除透明通道）并调整大小
        if img.mode == 'RGBA':
            img = img.convert('RGB')

        # 保持宽高比调整大小
        width, height = img.size
        ratio = min(1.0, max_size / len(image_data))
        new_width = int(width * ratio)
        new_height = int(height * ratio)

        img = img.resize((new_width, new_height), Image.LANCZOS)
        img.save(output, format='PNG', optimize=True)

    else:
        # 其他格式，简单调整大小
        width, height = img.size
        ratio = min(1.0, max_size / len(image_data))
        new_width = int(width * ratio)
        new_height = int(height * ratio)

        img = img.resize((new_width, new_height), Image.LANCZOS)
        img.save(output, format=file_extension[1:].upper())

    # 获取压缩后的图片数据
    compressed_data = output.getvalue()
    logger.info(f"compressed size: {len(compressed_data)/1024:.2f}KB")

    return compressed_data
