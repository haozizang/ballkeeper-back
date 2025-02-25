from PIL import Image, ImageDraw, ImageFont
import random
import os
import time
import secrets

def get_system_font():
    """获取系统中文字体"""
    # 常见的中文字体路径
    font_paths = [
        '/usr/share/fonts/wqy-microhei/wqy-microhei.ttc',    # 文泉驿微米黑
        '/usr/share/fonts/zihun/zihun-xingmouhei.ttf',       # 字魂-星眸黑
        # '/usr/share/fonts/zihun/zihun-youlongzhuanti.ttf',   # 字魂-游龙篆体
        '/usr/share/fonts/chinese/TrueType/uming.ttc',       # uming字体
        '/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc',        # 文泉驿正黑
        '/usr/share/fonts/dejavu/DejaVuSans.ttf',            # DejaVu字体
    ]

    # 遍历查找可用字体
    for font_path in font_paths:
        if os.path.exists(font_path):
            return font_path

    return None

def get_contrast_color(bg_color):
    """根据背景色生成对比度高的前景色"""
    # 计算背景色的亮度
    brightness = (bg_color[0] * 299 + bg_color[1] * 587 + bg_color[2] * 114) / 1000
    # 如果背景偏亮，返回黑色；如果背景偏暗，返回白色
    return (0, 0, 0) if brightness > 128 else (255, 255, 255)

def gen_txt_img(text, size=(50, 50)):
    # 使用时间戳和随机数组合作为种子
    random.seed(int(time.time() * 1000) + secrets.randbelow(1000000))
    
    # 使用 secrets 模块生成更随机的颜色
    color1 = (
        secrets.randbelow(151) + 50,  # 50-200 范围
        secrets.randbelow(151) + 50,
        secrets.randbelow(151) + 50
    )
    
    color2 = (
        secrets.randbelow(151) + 50,
        secrets.randbelow(151) + 50,
        secrets.randbelow(151) + 50
    )

    # 创建新图片
    img = Image.new('RGB', size)
    draw = ImageDraw.Draw(img)
    
    # 创建渐变背景
    for y in range(size[1]):
        ratio = y / size[1]
        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        draw.line([(0, y), (size[0], y)], fill=(r, g, b))
    
    # 获取中间位置的背景色，用于决定文字颜色
    mid_y = size[1] // 2
    mid_color = (
        int(color1[0] * 0.5 + color2[0] * 0.5),
        int(color1[1] * 0.5 + color2[1] * 0.5),
        int(color1[2] * 0.5 + color2[2] * 0.5)
    )
    
    # 获取与背景对比度高的文字颜色
    text_color = get_contrast_color(mid_color)
    
    # 获取系统字体
    font_path = get_system_font()
    if font_path:
        # 根据文本长度动态调整初始字体大小
        initial_size = size[0] // (len(text) if len(text) > 2 else 2)  # 文字越长，初始字体越小
        font_size = initial_size
        font = ImageFont.truetype(font_path, font_size)
        
        # 获取文字大小
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # 调整字体大小直到文字适合图片（宽度不超过70%）
        max_width = size[0] * 0.8
        max_height = size[1] * 0.8
        
        if text_width > max_width or text_height > max_height:
            # 如果初始大小太大，就逐步缩小
            while text_width > max_width or text_height > max_height:
                font_size = int(font_size * 0.9)  # 每次缩小10%
                if font_size < 8:  # 设置最小字体大小
                    font_size = 8
                    break
                font = ImageFont.truetype(font_path, font_size)
                text_bbox = draw.textbbox((0, 0), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
        else:
            # 如果初始大小太小，就逐步放大
            while text_width < max_width and text_height < max_height:
                font_size += 1
                font = ImageFont.truetype(font_path, font_size)
                text_bbox = draw.textbbox((0, 0), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
            # 回退一个字号确保不超出
            font_size -= 1
            font = ImageFont.truetype(font_path, font_size)
    else:
        # 如果没找到中文字体，使用默认字体
        font = ImageFont.load_default()
    
    # 获取最终文字大小
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    # 修改计算居中位置的方式
    x = (size[0] - text_width) // 2
    # 考虑文字的基线偏移
    y = (size[1] - text_height) // 2 - text_bbox[1]  # 减去基线偏移量

    # 绘制文字
    draw.text((x, y), text, fill=text_color, font=font)
    
    return img

# 使用示例
if __name__ == "__main__":
    for text in ["aa", "bf", 's']:
        avatar = gen_txt_img(text)
        avatar.save(f"{text}.png")
