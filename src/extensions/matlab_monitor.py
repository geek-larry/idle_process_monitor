import psutil
import re
from src.utils.logger import logger

class MatlabMonitor:
    def __init__(self):
        self.name = "matlab"
        self.process_name = "MATLAB.exe"

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
        if not self.is_matlab_running():
            return False

        # 方法1：检查Matlab进程的CPU和内存使用情况
        cpu_usage = self._get_process_cpu_usage(self.process_name)
        memory_usage = self._get_process_memory_usage(self.process_name)

        # 方法2：尝试通过命令行执行Matlab命令检查状态
        is_active = self._check_matlab_status_via_command()

        # 综合判断：如果CPU使用率较高，或内存使用较大，或通过命令检查到活动，则认为Matlab处于活跃状态
        if cpu_usage > 10 or memory_usage > 500 or is_active:
            logger.debug(f"Matlab is active: CPU={cpu_usage:.2f}%, Memory={memory_usage:.2f}MB")
            return True
        else:
            logger.debug(f"Matlab is idle: CPU={cpu_usage:.2f}%, Memory={memory_usage:.2f}MB")
            return False

    def _get_process_cpu_usage(self, process_name):
        """获取进程的CPU使用率"""
        try:
            # 使用psutil获取进程的CPU使用率
            cpu_values = []
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] == process_name:
                        # 获取CPU使用率，使用较短的间隔以提高性能
                        cpu_percent = proc.cpu_percent(interval=0.05)
                        cpu_values.append(cpu_percent)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            if cpu_values:
                return sum(cpu_values) / len(cpu_values)
        except Exception as e:
            logger.error(f"Error getting CPU usage for {process_name}: {e}")
        return 0

    def _get_process_memory_usage(self, process_name):
        """获取进程的内存使用量（MB）"""
        try:
            # 使用psutil获取进程的内存使用量
            memory_values = []
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] == process_name:
                        # 获取内存使用情况，转换为MB
                        memory_info = proc.memory_info()
                        memory_values.append(memory_info.rss / 1024 / 1024)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            if memory_values:
                return sum(memory_values) / len(memory_values)
        except Exception as e:
            logger.error(f"Error getting memory usage for {process_name}: {e}")
        return 0

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
