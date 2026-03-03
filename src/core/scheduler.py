import time
import threading
from collections import deque
from src.config.config import config_manager
from src.core.monitor import monitor
from src.utils.logger import logger
from src.config.user_config import user_config
from src.extensions.matlab_monitor import matlab_monitor

class ProcessScheduler:
    def __init__(self):
        self.idle_times = {}  # 累积计时模式的闲置时间
        self.idle_windows = {}  # 滑动窗口模式的闲置状态队列
        self.running = False
        self.thread = None
        self.check_interval = user_config.get("check_interval", 10)  # 检查间隔，单位秒
        self.idle_detection_mode = user_config.get("idle.detection.mode", "cumulative")  # 空闲判定模式
        self.sliding_window_size = user_config.get("sliding.window.size", 180)  # 滑动窗口采样点数

    def start(self):
        """启动定时器"""
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        logger.info("Scheduler started")

    def stop(self):
        """停止定时器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Scheduler stopped")

    def _run(self):
        """定时器运行逻辑"""
        while self.running:
            try:
                self.check_processes()
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
            time.sleep(self.check_interval)

    def check_processes(self):
        """检查所有进程状态"""
        try:
            # 获取最新配置
            configs = config_manager.get_configs()
            
            if not configs:
                logger.warning("No process configs available")
                return
            
            for config in configs:
                process_name = config.process_name
                try:
                    # 检查是否为Matlab进程
                    is_active = False
                    process_exists = False
                    status = None
                    if process_name.lower() == "matlab.exe":
                        # 使用Matlab扩展监控
                        extension_active = matlab_monitor.check_matlab_activity()
                        process_exists = matlab_monitor.is_matlab_running()
                        
                        # 同时使用基础监控逻辑
                        status = monitor.get_process_group_status(process_name, config)
                        base_active = status.is_active if status else False
                        
                        # 合并判断：只要扩展监控或基础监控任一认为活跃，则认为Matlab活跃
                        is_active = extension_active or base_active
                        
                        if user_config.get("debug.enabled", False):
                            if is_active:
                                logger.debug(f"Matlab is active: Extension={extension_active}, Base={base_active}")
                                if status:
                                    logger.debug(f"Matlab base metrics: CPU={status.cpu_usage:.2f}%, Memory={status.memory_usage:.2f}MB, IO={status.io_usage:.2f}MB/s, Network={status.network_usage:.2f}MB/s, Foreground={status.is_foreground}")
                            else:
                                logger.debug(f"Matlab is idle: Extension={extension_active}, Base={base_active}")
                                if status:
                                    logger.debug(f"Matlab base metrics: CPU={status.cpu_usage:.2f}%, Memory={status.memory_usage:.2f}MB, IO={status.io_usage:.2f}MB/s, Network={status.network_usage:.2f}MB/s")
                    else:
                        # 使用默认监控逻辑
                        status = monitor.get_process_group_status(process_name, config)
                        if status:
                            process_exists = True
                            is_active = status.is_active
                            # 检查是否开启debug模式
                            if user_config.get("debug.enabled", False):
                                if is_active:
                                    logger.debug(f"Process {process_name} is active: CPU={status.cpu_usage:.2f}%, Memory={status.memory_usage:.2f}MB, IO={status.io_usage:.2f}MB/s, Network={status.network_usage:.2f}MB/s, Foreground={status.is_foreground}")
                                else:
                                    logger.debug(f"Process {process_name} is idle for {self.idle_times.get(process_name, 0)} seconds: CPU={status.cpu_usage:.2f}%, Memory={status.memory_usage:.2f}MB, IO={status.io_usage:.2f}MB/s, Network={status.network_usage:.2f}MB/s")
                    
                    if self.idle_detection_mode == "sliding_window":
                        # 滑动窗口模式
                        if process_name not in self.idle_windows:
                            # 初始化滑动窗口
                            self.idle_windows[process_name] = deque(maxlen=self.sliding_window_size)
                        
                        # 添加当前状态到滑动窗口（False表示活跃，True表示闲置）
                        self.idle_windows[process_name].append(not is_active)
                        
                        # 检查滑动窗口是否已满且所有状态都为闲置
                        if len(self.idle_windows[process_name]) == self.sliding_window_size and all(self.idle_windows[process_name]):
                            # 所有采样点都为闲置，判定为空闲
                            logger.info(f"Process {process_name} has been idle for {self.sliding_window_size * self.check_interval} seconds (sliding window), terminating...")
                            monitor.kill_processes(process_name)
                            # 重置滑动窗口
                            self.idle_windows[process_name] = deque(maxlen=self.sliding_window_size)
                        elif user_config.get("debug.enabled", False):
                            # 输出滑动窗口状态
                            idle_count = sum(self.idle_windows[process_name])
                            total_count = len(self.idle_windows[process_name])
                            logger.debug(f"Process {process_name} sliding window: {idle_count}/{total_count} idle")
                    else:
                        # 累积计时模式（默认）
                        if is_active:
                            # 进程活跃，重置闲置时间
                            self.idle_times[process_name] = 0
                        elif process_exists:
                            # 进程闲置，增加闲置时间
                            if process_name not in self.idle_times:
                                self.idle_times[process_name] = 0
                            self.idle_times[process_name] += self.check_interval
                            
                            # 检查是否超过闲置时间阈值
                            if self.idle_times[process_name] >= config.idle_duration:
                                logger.info(f"Process {process_name} has been idle for {self.idle_times[process_name]} seconds (cumulative), terminating...")
                                monitor.kill_processes(process_name)
                                # 重置闲置时间
                                self.idle_times[process_name] = 0
                    
                    # 进程不存在，重置闲置时间
                    if not process_exists:
                        if process_name in self.idle_times:
                            del self.idle_times[process_name]
                        if process_name in self.idle_windows:
                            del self.idle_windows[process_name]
                        logger.debug(f"Process {process_name} not found")
                except Exception as e:
                    logger.error(f"Error checking process {process_name}: {e}")
        except Exception as e:
            logger.error(f"Error in check_processes: {e}")

# 全局调度器实例
scheduler = ProcessScheduler()
