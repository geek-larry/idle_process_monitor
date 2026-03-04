import psutil
import time
import win32gui
import win32process
import ctypes
from src.core.model import ProcessStatus
from src.utils.logger import logger
from src.config.user_config import user_config

class ProcessMonitor:
    def __init__(self):
        self.process_cache = {}
        self.cache_expiry = user_config.get("process_cache_expiry", 5)  # 进程信息缓存时间，单位秒
        self.last_cache_time = 0
        self.last_foreground_check_time = 0
        self.foreground_check_interval = 1  # 前台窗口检查间隔，单位秒
        self.foreground_pid = None
        self.last_confirmation_time = {}  # 记录每个进程的上次弹窗时间，避免频繁弹窗
        self.confirmation_cooldown = 60  # 弹窗冷却时间，单位秒

    def get_processes_by_name(self, process_name):
        """根据进程名称获取所有进程，使用缓存提高性能"""
        current_time = psutil.time.time()
        if current_time - self.last_cache_time > self.cache_expiry:
            # 缓存过期，重新获取
            self.process_cache = {}
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = proc.info['name']
                    if name not in self.process_cache:
                        self.process_cache[name] = []
                    self.process_cache[name].append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            self.last_cache_time = current_time
        
        return self.process_cache.get(process_name, [])

    def is_process_in_foreground(self, process_id):
        """判断进程是否在前台窗口"""
        try:
            # 直接获取前台窗口，不使用时间戳检查频率
            # 获取当前前台窗口句柄
            foreground_window = win32gui.GetForegroundWindow()
            if foreground_window:
                # 获取前台窗口所属的进程ID
                _, foreground_pid = win32process.GetWindowThreadProcessId(foreground_window)
                return foreground_pid == process_id
        except Exception as e:
            logger.error(f"Error checking if process is in foreground: {e}")
        return False

    def show_termination_confirmation(self, process_name):
        """显示终止进程确认对话框"""
        try:
            # 检查冷却时间，避免频繁弹窗
            current_time = time.time()
            if process_name in self.last_confirmation_time:
                if current_time - self.last_confirmation_time[process_name] < self.confirmation_cooldown:
                    logger.info(f"Skipping confirmation for {process_name} due to cooldown")
                    return False
            
            # 导入必要的Windows API常量
            MB_YESNO = 4
            MB_SYSTEMMODAL = 4096
            MB_SETFOREGROUND = 65536
            MB_TOPMOST = 0x40000
            IDYES = 6  # 是按钮的ID
            IDNO = 7   # 否按钮的ID
            IDTIMEOUT = 32000  # 超时返回值
            
            # 定义MessageBoxTimeout函数
            user32 = ctypes.WinDLL('user32', use_last_error=True)
            MessageBoxTimeout = user32.MessageBoxTimeoutW
            MessageBoxTimeout.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
            MessageBoxTimeout.restype = ctypes.c_int
            
            # 显示带超时的消息框
            result = MessageBoxTimeout(
                0,  # 父窗口句柄
                f"进程 {process_name} 已闲置超过阈值，是否终止？\n\n" +
                f"如果您不操作，将在10秒后自动取消。",  # 消息内容
                "进程闲置提醒",  # 标题
                MB_YESNO | MB_SYSTEMMODAL | MB_SETFOREGROUND | MB_TOPMOST,  # 样式
                0,  # 图标（0表示无图标）
                10000  # 超时时间（毫秒）
            )
            
            # 更新上次弹窗时间
            self.last_confirmation_time[process_name] = current_time
            
            # 检查结果
            if result == IDYES:
                logger.info(f"User confirmed termination of {process_name}")
                return True
            elif result == IDTIMEOUT:
                logger.info(f"Confirmation dialog timed out for {process_name}")
                return False
            else:
                logger.info(f"User cancelled termination of {process_name}")
                return False
        except Exception as e:
            logger.error(f"Error showing confirmation dialog: {e}")
            return False

    def get_process_group_status(self, process_name, config):
        """获取进程组的聚合状态"""
        processes = self.get_processes_by_name(process_name)
        if not processes:
            return None

        # 聚合指标
        total_cpu = 0
        total_memory = 0
        is_foreground = False

        # 获取IO计数器初始值
        io_counters = psutil.disk_io_counters()
        net_io_counters = psutil.net_io_counters()

        # 等待一小段时间以获取IO和网络使用情况
        psutil.time.sleep(0.05)  # 减少等待时间，提高性能

        # 获取IO计数器新值
        new_io_counters = psutil.disk_io_counters()
        new_net_io_counters = psutil.net_io_counters()

        # 计算IO和网络使用情况
        io_read_speed = (new_io_counters.read_bytes - io_counters.read_bytes) / 1024 / 1024 / 0.05  # MB/s
        io_write_speed = (new_io_counters.write_bytes - io_counters.write_bytes) / 1024 / 1024 / 0.05  # MB/s
        net_sent_speed = (new_net_io_counters.bytes_sent - net_io_counters.bytes_sent) / 1024 / 1024 / 0.05  # MB/s
        net_recv_speed = (new_net_io_counters.bytes_recv - net_io_counters.bytes_recv) / 1024 / 1024 / 0.05  # MB/s

        # 限制同时获取CPU使用率的进程数量，避免资源消耗过大
        max_processes = user_config.get("max_processes_per_check", 10)
        processes_to_check = processes[:max_processes]
        
        for proc in processes_to_check:
            try:
                # 获取CPU使用率
                cpu_percent = proc.cpu_percent(interval=0.05)  # 减少间隔，提高性能
                total_cpu += cpu_percent

                # 获取内存使用情况
                memory_info = proc.memory_info()
                total_memory += memory_info.rss / 1024 / 1024  # MB

                # 检查是否在前台
                if not is_foreground and self.is_process_in_foreground(proc.pid):
                    is_foreground = True

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        # 计算平均或总使用率
        avg_cpu = total_cpu / len(processes_to_check) if processes_to_check else 0
        total_io = io_read_speed + io_write_speed
        total_network = net_sent_speed + net_recv_speed

        # 判断是否活跃
        is_active = False
        if is_foreground:
            is_active = True
        elif avg_cpu > config.cpu_threshold:
            is_active = True
        elif total_memory > config.memory_threshold:
            is_active = True
        elif total_io > config.io_threshold:
            is_active = True
        elif total_network > config.network_threshold:
            is_active = True

        return ProcessStatus(
            process_name=process_name,
            is_active=is_active,
            cpu_usage=avg_cpu,
            memory_usage=total_memory,
            io_usage=total_io,
            network_usage=total_network,
            is_foreground=is_foreground
        )

    def kill_processes(self, process_name):
        """优雅终止进程"""
        processes = self.get_processes_by_name(process_name)
        for proc in processes:
            try:
                proc.terminate()
                # 等待进程终止
                proc.wait(timeout=5)
                logger.info(f"Terminated process {process_name} (PID: {proc.pid})")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                try:
                    proc.kill()
                    logger.warning(f"Killed process {process_name} (PID: {proc.pid})")
                except Exception as e:
                    logger.error(f"Error terminating process {process_name} (PID: {proc.pid}): {e}")

# 全局监控实例
monitor = ProcessMonitor()
