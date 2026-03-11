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
        self.last_cache_time = 0
        self.last_foreground_check_time = 0
        self.foreground_check_interval = 1  # 前台窗口检查间隔，单位秒
        self.foreground_pid = None
        self.last_confirmation_time = {}  # 记录每个进程的上次弹窗时间，避免频繁弹窗
        self.confirmation_cooldown = 60  # 弹窗冷却时间，单位秒
        self.last_io_check_time = 0  # 上次IO检查时间
        self.io_check_interval = 2  # IO检查间隔，单位秒
        self.last_io_counters = None  # 上次IO计数器值
        self.last_net_counters = None  # 上次网络计数器值

    def get_processes_by_name(self, process_name):
        """根据进程名称获取所有进程"""
        # 每次都重新获取进程信息
        processes = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] == process_name:
                    processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return processes

    def is_process_in_foreground(self, process_id):
        """判断进程是否在前台窗口"""
        try:
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
            IDTIMEOUT = 32000  # 超时返回值
            
            # 定义MessageBoxTimeout函数
            user32 = ctypes.WinDLL('user32', use_last_error=True)
            message_box_timeout = user32.MessageBoxTimeoutW
            message_box_timeout.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
            message_box_timeout.restype = ctypes.c_int
            
            # 显示带超时的消息框
            result = message_box_timeout(
                0,  # 父窗口句柄
                "进程 {} 已闲置超过阈值，是否终止？\n\n如果您不操作，将在10秒后自动取消。".format(process_name),  # 消息内容
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
        total_io = 0
        total_network = 0


        
        # 计算IO和网络使用情况（使用缓存，减少频繁检查）
        current_time = psutil.time.time()
        if current_time - self.last_io_check_time > self.io_check_interval:
            # 获取IO计数器初始值
            io_counters = psutil.disk_io_counters()
            net_io_counters = psutil.net_io_counters()

            # 等待一小段时间以获取IO和网络使用情况
            psutil.time.sleep(0.01)  # 进一步减少等待时间

            # 获取IO计数器新值
            new_io_counters = psutil.disk_io_counters()
            new_net_io_counters = psutil.net_io_counters()

            # 计算IO和网络使用情况
            io_read_speed = (new_io_counters.read_bytes - io_counters.read_bytes) / 1024 / 1024 / 0.01  # MB/s
            io_write_speed = (new_io_counters.write_bytes - io_counters.write_bytes) / 1024 / 1024 / 0.01  # MB/s
            net_sent_speed = (new_net_io_counters.bytes_sent - net_io_counters.bytes_sent) / 1024 / 1024 / 0.01  # MB/s
            net_recv_speed = (new_net_io_counters.bytes_recv - net_io_counters.bytes_recv) / 1024 / 1024 / 0.01  # MB/s

            total_io = io_read_speed + io_write_speed
            total_network = net_sent_speed + net_recv_speed

            # 更新缓存
            self.last_io_check_time = current_time
            self.last_io_counters = (io_counters, new_io_counters)
            self.last_net_counters = (net_io_counters, new_net_io_counters)
        else:
            # 使用缓存的IO和网络数据
            if self.last_io_counters and self.last_net_counters:
                io_counters, new_io_counters = self.last_io_counters
                net_io_counters, new_net_counters = self.last_net_counters
                
                # 计算IO和网络使用情况
                io_read_speed = (new_io_counters.read_bytes - io_counters.read_bytes) / 1024 / 1024 / 0.01  # MB/s
                io_write_speed = (new_io_counters.write_bytes - io_counters.write_bytes) / 1024 / 1024 / 0.01  # MB/s
                net_sent_speed = (new_net_counters.bytes_sent - net_io_counters.bytes_sent) / 1024 / 1024 / 0.01  # MB/s
                net_recv_speed = (new_net_counters.bytes_recv - net_io_counters.bytes_recv) / 1024 / 1024 / 0.01  # MB/s

                total_io = io_read_speed + io_write_speed
                total_network = net_sent_speed + net_recv_speed

        for proc in processes:
            try:
                # 获取CPU使用率（使用interval=0，避免阻塞）
                cpu_percent = proc.cpu_percent(interval=0)  # 使用interval=0，基于上次调用的结果
                total_cpu += cpu_percent

                # 获取内存使用情况
                memory_info = proc.memory_info()
                total_memory += memory_info.rss / 1024 / 1024  # MB

                # 检查是否在前台
                if not is_foreground and self.is_process_in_foreground(proc.pid):
                    is_foreground = True

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # 计算平均或总使用率
        avg_cpu = total_cpu / len(processes) if processes else 0

        # 判断是否活跃
        is_active = is_foreground or \
                    avg_cpu > config.cpu_threshold or \
                    total_memory > config.memory_threshold or \
                    total_io > config.io_threshold or \
                    total_network > config.network_threshold

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
