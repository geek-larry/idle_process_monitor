import psutil
import re
from src.utils.logger import logger
from src.config.user_config import user_config

class MatlabMonitor:
    def __init__(self):
        self.name = "matlab"
        self.process_name = "MATLAB.exe"
        self.enabled = user_config.get("matlab.monitor.enabled", False)  # 默认为关闭

    def is_matlab_running(self):
        """检查Matlab是否正在运行"""
        try:
            # 使用psutil检查Matlab进程是否存在
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] == 'MATLAB.exe':
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            return False
        except Exception as e:
            logger.error(f"Error checking if Matlab is running: {e}")
            return False

    def check_matlab_activity(self):
        """检查Matlab是否正在执行任务"""
        # 检查是否开启Matlab扩展监控
        if not self.enabled:
            logger.debug("Matlab extension monitor is disabled")
            return False
            
        if not self.is_matlab_running():
            return False

        # 只使用命令行的监控逻辑
        is_active = self._check_matlab_status_via_command()

        if is_active:
            logger.debug("Matlab is active via command line check")
            return True
        else:
            logger.debug("Matlab is idle via command line check")
            return False

    def _check_matlab_status_via_command(self):
        """通过命令行执行Matlab命令检查状态"""
        try:
            # 使用psutil获取Matlab进程的命令行参数
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    if proc.info['name'] == 'MATLAB.exe':
                        cmdline = proc.info.get('cmdline', [])
                        if cmdline:
                            # 将命令行参数列表转换为字符串
                            command_line = ' '.join(cmdline)
                            # 检查命令行参数中是否包含可能表示正在执行任务的标志
                            if ' -r ' in command_line or ' -batch ' in command_line:
                                return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception as e:
            logger.error(f"Error checking Matlab status via command: {e}")
        return False

# 全局Matlab监控实例
matlab_monitor = MatlabMonitor()
