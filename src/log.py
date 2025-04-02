import logging
import os
from datetime import datetime

def create_logger(name: str, log_dir: str, level: str = 'INFO') -> logging.Logger:
    """
    创建一个logger，支持同时输出到文件和控制台

    Args:
        name: logger名称
        log_dir: 日志文件保存目录
        level: 日志级别，默认INFO

    Returns:
        logging.Logger: 配置好的logger对象
    """
    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)

    # 创建logger
    logger = logging.getLogger(name)

    # 设置日志格式
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d:%(funcName)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 创建文件处理器
    log_file = os.path.join(log_dir, f'{name}_{datetime.now().strftime("%Y-%m-%d")}.log')
    file_handler = logging.FileHandler(log_file, encoding='utf8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 设置日志级别
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    logger.setLevel(level_map.get(level.upper(), logging.INFO))

    return logger
