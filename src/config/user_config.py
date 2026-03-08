from src.config.config_loader import config_loader

class UserConfig:
    def __init__(self):
        # 当前没有需要初始化的成员变量，保留空实现以备后续扩展
        pass

    def get(self, key, default=None):
        """获取配置值"""
        # 从config.properties文件中读取配置
        config_map = {
            "api_url": lambda: config_loader.get("api.url", default or "http://127.0.0.1:5000/api/process-configs"),
            "cache_duration": lambda: config_loader.get_int("config.cache.duration", default or 300),
            "check_interval": lambda: config_loader.get_int("check.interval", default or 10),
            "log_level": lambda: config_loader.get("log.level", default or "INFO"),
            "log_keep_days": lambda: config_loader.get_int("log.keep.days", default or 7),
            "max_processes_per_check": lambda: config_loader.get_int("max.processes.per.check", default or 10),
            "process_cache_expiry": lambda: config_loader.get_int("process.cache.expiry", default or 5),
            "debug.enabled": lambda: config_loader.get_boolean("debug.enabled", default or False),
        }
        return config_map.get(key, lambda: default)()

    def set(self, key, value):
        """设置配置值（预留接口，实际配置通过修改config.properties文件）"""
        pass

# 全局用户配置实例
user_config = UserConfig()
