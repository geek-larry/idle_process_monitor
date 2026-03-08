import logging
import os
import sys
import datetime
from src.config.user_config import user_config

class Logger:
    def __init__(self, log_dir="logs", log_level=None, keep_days=None):
        # 获取当前可执行文件所在目录
        if getattr(sys, 'frozen', False):
            # 打包为exe时的路径
            base_dir = os.path.dirname(sys.executable)
        else:
            # 开发环境时的路径
            base_dir = os.path.dirname(os.path.abspath(__file__))
            # 向上两级到项目根目录
            base_dir = os.path.join(base_dir, "..", "..")
        
        self.log_dir = os.path.join(base_dir, log_dir)
        # 从用户配置获取日志级别
        if log_level is None:
            log_level_str = user_config.get("log_level", "INFO")
            log_level = getattr(logging, log_level_str.upper(), logging.INFO)
        self.log_level = log_level
        # 从用户配置获取日志保留天数
        self.keep_days = keep_days if keep_days is not None else user_config.get("log_keep_days", 7)
        self._logger = None
        self.setup_logger()
        self.cleanup_old_logs()

    def setup_logger(self):
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(self.log_dir, f"app_{today}.log")

        self._logger = logging.getLogger("IdleProcessMonitor")
        self._logger.setLevel(self.log_level)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        if not self._logger.handlers:
            self._logger.addHandler(file_handler)
            self._logger.addHandler(console_handler)

    def cleanup_old_logs(self):
        if not os.path.exists(self.log_dir):
            return

        today = datetime.datetime.now()
        for filename in os.listdir(self.log_dir):
            if filename.startswith("app_") and filename.endswith(".log"):
                try:
                    date_str = filename.split("_")[1].split(".")[0]
                    log_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                    if (today - log_date).days > self.keep_days:
                        os.remove(os.path.join(self.log_dir, filename))
                except Exception as e:
                    print(f"Error cleaning up old log file {filename}: {e}")

    def debug(self, message):
        if self._logger:
            self._logger.debug(message)

    def info(self, message):
        if self._logger:
            self._logger.info(message)

    def warning(self, message):
        if self._logger:
            self._logger.warning(message)

    def error(self, message):
        if self._logger:
            self._logger.error(message)

    def critical(self, message):
        if self._logger:
            self._logger.critical(message)

# 全局日志实例
logger = Logger()
