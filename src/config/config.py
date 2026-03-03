import json
import requests
import os
import sys
import time
from src.core.model import ProcessConfig
from src.utils.logger import logger
from src.config.user_config import user_config

# 获取当前可执行文件所在目录
if getattr(sys, 'frozen', False):
    # 打包为exe时的路径
    base_dir = os.path.dirname(sys.executable)
else:
    # 开发环境时的路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # 向上两级到项目根目录
    base_dir = os.path.join(base_dir, "..", "..")

CONFIG_FILE = os.path.join(base_dir, "config.json")
API_URL = user_config.get("api_url", "http://127.0.0.1:5000/api/process-configs")
CACHE_DURATION = user_config.get("cache_duration", 300)  # 配置缓存时间，单位秒

class ConfigManager:
    def __init__(self):
        self.configs = []
        self.last_update_time = 0

    def get_configs(self):
        """获取配置，优先使用缓存"""
        current_time = time.time()
        if current_time - self.last_update_time > CACHE_DURATION:
            # 缓存过期，重新获取
            configs = self._get_configs_from_api()
            if configs:
                self.configs = configs
                self.last_update_time = current_time
                logger.info("Config cache updated")
            else:
                # API获取失败，使用本地文件
                configs = self._get_configs_from_file()
                if configs:
                    self.configs = configs
                    logger.warning("Using config from file due to API failure")
        return self.configs

    def _get_configs_from_api(self):
        """从API获取配置"""
        try:
            response = requests.get(API_URL, timeout=5)
            if response.status_code == 200:
                config_data = response.json()
                configs = [ProcessConfig.from_dict(data) for data in config_data]
                self._save_configs_to_file(configs)
                return configs
            else:
                logger.error(f"Failed to get configs from API: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting configs from API: {e}")
            return []

    def _save_configs_to_file(self, configs):
        """保存配置到文件"""
        try:
            config_data = [config.to_dict() for config in configs]
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving configs to file: {e}")

    def _get_configs_from_file(self):
        """从文件获取配置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config_data = json.load(f)
                    return [ProcessConfig.from_dict(data) for data in config_data]
            else:
                return []
        except Exception as e:
            logger.error(f"Error getting configs from file: {e}")
            return []

    def get_process_config(self, process_name):
        """根据进程名称获取配置"""
        configs = self.get_configs()
        for config in configs:
            if config.process_name == process_name:
                return config
        return None

# 全局配置管理器实例
config_manager = ConfigManager()
