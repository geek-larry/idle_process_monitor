import os
import sys
import configparser

class ConfigLoader:
    def __init__(self, config_file="config.properties"):
        # 获取当前可执行文件所在目录
        if getattr(sys, 'frozen', False):
            # 打包为exe时的路径
            base_dir = os.path.dirname(sys.executable)
        else:
            # 开发环境时的路径
            base_dir = os.path.dirname(os.path.abspath(__file__))
            # 向上两级到项目根目录
            base_dir = os.path.join(base_dir, "..", "..")
        
        self.config_file = os.path.join(base_dir, config_file)
        self.config = configparser.ConfigParser()
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            # 使用utf-8编码读取配置文件
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config.read_file(f)

    def get(self, key, default=None, section="DEFAULT"):
        """获取配置值"""
        if section in self.config and key in self.config[section]:
            return self.config[section][key]
        return default

    def get_boolean(self, key, default=False, section="DEFAULT"):
        """获取布尔类型配置值"""
        if section in self.config and key in self.config[section]:
            return self.config[section].getboolean(key)
        return default

    def get_int(self, key, default=0, section="DEFAULT"):
        """获取整数类型配置值"""
        if section in self.config and key in self.config[section]:
            try:
                return self.config[section].getint(key)
            except ValueError:
                pass
        return default

    def get_float(self, key, default=0.0, section="DEFAULT"):
        """获取浮点数类型配置值"""
        if section in self.config and key in self.config[section]:
            try:
                return self.config[section].getfloat(key)
            except ValueError:
                pass
        return default

# 全局配置加载器实例
config_loader = ConfigLoader()
