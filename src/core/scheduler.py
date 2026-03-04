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
                        # 检查Matlab是否运行
                        process_exists = matlab_monitor.is_matlab_running()
                        
                        if not process_exists:
                            # 进程未开启
                            is_active = False
                        else:
                            # 进程开启，使用Matlab扩展监控
                            extension_active = matlab_monitor.check_matlab_activity()
                            
                            # 同时使用基础监控逻辑
                            status = monitor.get_process_group_status(process_name, config)
                            base_active = status.is_active if status else False
                            
                            # 合并判断：只要扩展监控或基础监控任一认为活跃，则认为Matlab活跃
                            is_active = extension_active or base_active
                            
                            if user_config.get("debug.enabled", False):
                                # 只打印一条详细日志
                                log_message = f"Matlab status: {'Active' if is_active else 'Idle'}"
                                if status:
                                    log_message += f" | Base metrics: CPU={status.cpu_usage:.2f}%, Memory={status.memory_usage:.2f}MB, IO={status.io_usage:.2f}MB/s, Network={status.network_usage:.2f}MB/s, Foreground={status.is_foreground}"
                                # 添加扩展监控状态
                                log_message += f" | Extension monitor: {'Active' if extension_active else 'Idle'}"
                                logger.debug(log_message)
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
                                    # 获取进程的闲置检测模式
                                    idle_detection_mode = config.idle_detection_mode or "cumulative"
                                    if idle_detection_mode == "sliding_window":
                                        # 滑动窗口模式，显示窗口状态
                                        window_size = config.sliding_window_size or 180
                                        if process_name in self.idle_windows:
                                            window = self.idle_windows[process_name]
                                            if window:
                                                # 计算当前窗口的闲置比例
                                                idle_count = sum(is_idle for is_idle, _ in window)
                                                idle_percentage = (idle_count / len(window)) * 100
                                                # 检查窗口是否填满
                                                if len(window) < window_size:
                                                    # 窗口未填满，显示填充进度
                                                    logger.debug(f"Process {process_name} sliding window: {idle_count}/{len(window)} idle (filling: {len(window)}/{window_size} checks): CPU={status.cpu_usage:.2f}%, Memory={status.memory_usage:.2f}MB, IO={status.io_usage:.2f}MB/s, Network={status.network_usage:.2f}MB/s")
                                                else:
                                                    # 窗口已填满，显示闲置比例
                                                    logger.debug(f"Process {process_name} sliding window: {idle_percentage:.1f}% idle ({len(window)}/{window_size} checks): CPU={status.cpu_usage:.2f}%, Memory={status.memory_usage:.2f}MB, IO={status.io_usage:.2f}MB/s, Network={status.network_usage:.2f}MB/s")
                                            else:
                                                logger.debug(f"Process {process_name} sliding window: initializing: CPU={status.cpu_usage:.2f}%, Memory={status.memory_usage:.2f}MB, IO={status.io_usage:.2f}MB/s, Network={status.network_usage:.2f}MB/s")
                                    else:
                                        # 累积计时模式，显示空闲时长
                                        logger.debug(f"Process {process_name} is idle for {self.idle_times.get(process_name, 0)} seconds: CPU={status.cpu_usage:.2f}%, Memory={status.memory_usage:.2f}MB, IO={status.io_usage:.2f}MB/s, Network={status.network_usage:.2f}MB/s")
                    
                    # 获取进程的闲置检测模式
                    idle_detection_mode = config.idle_detection_mode or "cumulative"
                    
                    if idle_detection_mode == "sliding_window":
                        # 滑动窗口模式
                        if process_name not in self.idle_windows:
                            # 初始化滑动窗口
                            window_size = config.sliding_window_size or 180
                            self.idle_windows[process_name] = deque(maxlen=window_size)
                        
                        # 添加当前状态到滑动窗口（存储是否闲置和是否为前台窗口活跃）
                        is_foreground = status.is_foreground if status else False
                        self.idle_windows[process_name].append((not is_active, is_foreground))
                        
                        # 获取滑动窗口配置
                        window_size = config.sliding_window_size or 180
                        idle_percentage_threshold = config.sliding_window_idle_percentage or 90
                        use_weighted = config.sliding_window_weighted or False
                        
                        # 检查滑动窗口是否已满
                        if len(self.idle_windows[process_name]) == window_size:
                            try:
                                # 检查是否有前台窗口活跃
                                has_foreground_active = any(foreground for _, foreground in self.idle_windows[process_name])
                                
                                if has_foreground_active:
                                    # 如果有前台窗口活跃，直接判定为活跃
                                    if user_config.get("debug.enabled", False):
                                        # 计算前台活跃的位置
                                        foreground_positions = [i for i, (_, foreground) in enumerate(self.idle_windows[process_name]) if foreground]
                                        if foreground_positions:
                                            # 找到最近的前台活跃位置
                                            last_foreground_idx = max(foreground_positions)
                                            # 计算前台活跃后的闲置状态
                                            idle_after_foreground = sum(is_idle for is_idle, _ in list(self.idle_windows[process_name])[last_foreground_idx+1:])
                                            total_after_foreground = len(self.idle_windows[process_name]) - last_foreground_idx - 1
                                            logger.debug(f"Process {process_name} has foreground activity at check {last_foreground_idx+1}/{window_size}, resetting idle calculation: {idle_after_foreground}/{total_after_foreground} idle since last foreground activity")
                                        else:
                                            logger.debug(f"Process {process_name} has foreground activity, marked as active")
                                else:
                                    # 没有前台窗口活跃，使用滑动窗口判定
                                    if use_weighted:
                                        # 加权滑动窗口
                                        idle_count = 0
                                        total_weight = 0
                                        
                                        for i, (is_idle, _) in enumerate(self.idle_windows[process_name]):
                                            # 计算权重：最近的状态权重更高
                                            weight = (i + 1) / window_size
                                            if is_idle:
                                                idle_count += weight
                                            total_weight += weight
                                        
                                        idle_percentage = (idle_count / total_weight) * 100
                                    else:
                                        # 普通滑动窗口
                                        idle_count = sum(is_idle for is_idle, _ in self.idle_windows[process_name])
                                        idle_percentage = (idle_count / window_size) * 100
                                    
                                    # 检查闲置比例是否达到阈值
                                    if idle_percentage >= idle_percentage_threshold:
                                        # 闲置比例达到阈值，判定为空闲
                                        logger.info(f"Process {process_name} has been {idle_percentage:.1f}% idle for {window_size * self.check_interval} seconds ({'weighted ' if use_weighted else ''}sliding window), terminating...")
                                        # 检查终止模式
                                        if config.termination_mode == "confirm":
                                            # 显示确认对话框
                                            if monitor.show_termination_confirmation(process_name):
                                                monitor.kill_processes(process_name)
                                                logger.info(f"User confirmed termination of {process_name}")
                                            else:
                                                logger.info(f"User cancelled termination of {process_name}")
                                        else:
                                            # 自动终止
                                            monitor.kill_processes(process_name)
                                        # 重置滑动窗口
                                        self.idle_windows[process_name] = deque(maxlen=window_size)
                                    elif user_config.get("debug.enabled", False):
                                        # 输出滑动窗口状态
                                        logger.debug(f"Process {process_name} sliding window: {idle_percentage:.1f}% idle ({'weighted' if use_weighted else 'normal'})")
                            except Exception as e:
                                logger.error(f"Error in sliding window calculation for {process_name}: {e}")
                                # 重置滑动窗口，避免异常导致的状态错误
                                self.idle_windows[process_name] = deque(maxlen=window_size)
                    else:
                        # 累积计时模式
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
                                # 检查终止模式
                                if config.termination_mode == "confirm":
                                    # 显示确认对话框
                                    if monitor.show_termination_confirmation(process_name):
                                        monitor.kill_processes(process_name)
                                        logger.info(f"User confirmed termination of {process_name}")
                                    else:
                                        logger.info(f"User cancelled termination of {process_name}")
                                else:
                                    # 自动终止
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
