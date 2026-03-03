from src.config.config_loader import config_loader

class UserConfig:
    def __init__(self):
        pass

    def get(self, key, default=None):
        """获取配置值"""
        # 从config.properties文件中读取配置
        if key == "api_url":
            return config_loader.get("api.url", default or "http://127.0.0.1:5000/api/process-configs")
        elif key == "cache_duration":
            return config_loader.get_int("config.cache.duration", default or 300)
        elif key == "check_interval":
            return config_loader.get_int("check.interval", default or 10)
        elif key == "log_level":
            return config_loader.get("log.level", default or "INFO")
        elif key == "log_keep_days":
            return config_loader.get_int("log.keep.days", default or 7)
        elif key == "max_processes_per_check":
            return config_loader.get_int("max.processes.per.check", default or 10)
        elif key == "process_cache_expiry":
            return config_loader.get_int("process.cache.expiry", default or 5)
        elif key == "debug.enabled":
            return config_loader.get_boolean("debug.enabled", default or False)
        return default

    def set(self, key, value):
        """设置配置值（预留接口，实际配置通过修改config.properties文件）"""
        pass

# 全局用户配置实例
user_config = UserConfig()
