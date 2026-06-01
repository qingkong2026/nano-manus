
import logging
import sys

from core.config import get_settings


def setup_logging():
    """
    配置项目的日志系统，涵盖日志等级、输出格式、输出渠道
    """

    # 1.获取项目配置
    settings = get_settings()

    # 2.获取根日志处理器
    root_logger = logging.getLogger()

    # 3.设置根日志处理器等级
    log_level = getattr(logging, settings.log_level)
    root_logger.setLevel(log_level)

    # 4.日志输出格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 5.日志输出渠道
    consol_handler = logging.StreamHandler(sys.stdout)
    consol_handler.setFormatter(formatter)
    consol_handler.setLevel(log_level)

    # 6.将日志处理器添加到根日志处理器中
    root_logger.addHandler(consol_handler)

    root_logger.info('Logging setup complete')












    