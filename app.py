import time
import json
import logging
import threading
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import psutil
import win32gui
import win32process

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('process_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessConfig:
    """进程配置信息数据类"""
    process_name: str
    cpu_threshold: float  # CPU使用率阈值（百分比）
    memory_threshold_mb: float  # 内存使用量阈值（MB）
    
    def __post_init__(self):
        """数据验证"""
        if self.cpu_threshold < 0:
            raise ValueError("CPU阈值不能为负数")
        if self.memory_threshold_mb < 0:
            raise ValueError("内存阈值不能为负数")


@dataclass
class ProcessState:
    """进程状态跟踪数据类"""
    process: Optional[psutil.Process] = None
    idle_start_time: Optional[datetime] = None
    idle_duration: timedelta = field(default_factory=timedelta)
    last_check_time: datetime = field(default_factory=datetime.now)
    
    def reset_idle_state(self):
        """重置空闲状态"""
        self.idle_start_time = None
        self.idle_duration = timedelta()
        self.last_check_time = datetime.now()
    
    def update_idle_duration(self):
        """更新空闲持续时间"""
        if self.idle_start_time:
            self.idle_duration = datetime.now() - self.idle_start_time
        else:
            self.idle_duration = timedelta()
        self.last_check_time = datetime.now()


class ConfigManager:
    """配置管理器：负责从服务端获取和缓存配置"""
    
    def __init__(self, config_url: str, cache_file: str = "process_config_cache.json"):
        """
        初始化配置管理器
        
        Args:
            config_url: 服务端配置接口URL
            cache_file: 本地缓存文件路径
        """
        self.config_url = config_url
        self.cache_file = cache_file
        self._configs: Dict[str, ProcessConfig] = {}
        self._last_fetch_time: Optional[datetime] = None
        self._config_lock = threading.Lock()
        
    def load_initial_config(self) -> None:
        """加载初始配置（从缓存或默认配置）"""
        try:
            # 尝试从本地缓存加载
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                self._load_config_from_dict(cached_data)
                logger.info(f"从缓存加载了 {len(self._configs)} 个进程配置")
        except (FileNotFoundError, json.JSONDecodeError):
            # 缓存文件不存在或格式错误，使用空配置
            self._configs = {}
            logger.info("未找到有效缓存，使用空配置初始化")
    
    def fetch_config_from_server(self) -> bool:
        """
        从服务端获取配置
        
        Returns:
            bool: 是否成功获取配置
        """
        try:
            response = requests.get(self.config_url, timeout=10)
            response.raise_for_status()
            
            config_data = response.json()
            with self._config_lock:
                self._load_config_from_dict(config_data)
            
            # 更新缓存
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            self._last_fetch_time = datetime.now()
            logger.info(f"从服务端成功获取 {len(self._configs)} 个进程配置")
            return True
            
        except requests.RequestException as e:
            logger.warning(f"从服务端获取配置失败: {e}")
            return False
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"配置数据格式错误: {e}")
            return False
    
    def _load_config_from_dict(self, config_dict: List[Dict]) -> None:
        """从字典加载配置到内部结构"""
        self._configs.clear()
        for item in config_dict:
            try:
                config = ProcessConfig(
                    process_name=item['process_name'],
                    cpu_threshold=float(item['cpu_threshold']),
                    memory_threshold_mb=float(item['memory_threshold'])
                )
                self._configs[config.process_name.lower()] = config
            except (KeyError, ValueError) as e:
                logger.error(f"解析配置项失败 {item}: {e}")
    
    def get_config(self, process_name: str) -> Optional[ProcessConfig]:
        """
        获取指定进程的配置
        
        Args:
            process_name: 进程名称
            
        Returns:
            ProcessConfig or None: 进程配置，不存在则返回None
        """
        return self._configs.get(process_name.lower())
    
    def get_all_configs(self) -> List[ProcessConfig]:
        """获取所有进程配置"""
        return list(self._configs.values())
    
    @property
    def has_configs(self) -> bool:
        """是否有配置"""
        return len(self._configs) > 0
    
    @property
    def last_fetch_time(self) -> Optional[datetime]:
        """最后获取配置的时间"""
        return self._last_fetch_time


class ProcessMonitor:
    """进程监控器：负责监控和判断进程状态"""
    
    def __init__(self, config_manager: ConfigManager, idle_threshold_minutes: int = 10):
        """
        初始化进程监控器
        
        Args:
            config_manager: 配置管理器实例
            idle_threshold_minutes: 空闲时间阈值（分钟）
        """
        self.config_manager = config_manager
        self.idle_threshold = timedelta(minutes=idle_threshold_minutes)
        self._process_states: Dict[str, ProcessState] = {}
        self._foreground_pid: Optional[int] = None
        self._monitor_lock = threading.Lock()
    
    def get_foreground_process_id(self) -> Optional[int]:
        """获取当前前台窗口的进程ID"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                return pid
        except Exception as e:
            logger.debug(f"获取前台窗口失败: {e}")
        return None
    
    def find_process_by_name(self, process_name: str) -> List[psutil.Process]:
        """
        根据进程名查找所有匹配的进程
        
        Args:
            process_name: 进程名称
            
        Returns:
            List[psutil.Process]: 匹配的进程列表
        """
        matching_processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                    matching_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            logger.debug(f"查找进程时发生异常: {e}")
        return matching_processes
    
    def check_process_idle(self, process: psutil.Process, config: ProcessConfig) -> bool:
        """
        检查进程是否处于空闲状态
        
        Args:
            process: 要检查的进程
            config: 进程配置
            
        Returns:
            bool: 是否空闲
        """
        try:
            # 获取CPU使用率（百分比）
            cpu_percent = process.cpu_percent(interval=0.1)
            
            # 获取内存使用量（MB）
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)  # 转换为MB
            
            # 检查是否为前台窗口
            is_foreground = False
            if self._foreground_pid:
                is_foreground = (process.pid == self._foreground_pid)
            
            # 判断是否满足空闲条件
            is_idle = (cpu_percent < config.cpu_threshold and 
                      memory_mb < config.memory_threshold_mb and 
                      not is_foreground)
            
            logger.info(f"进程 {process.name()}({process.pid}): "
                        f"CPU={cpu_percent:.1f}% (<{config.cpu_threshold}), "
                        f"内存={memory_mb:.1f}MB (<{config.memory_threshold_mb}), "
                        f"前台={is_foreground}, 空闲={is_idle}")
            
            return is_idle
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"检查进程状态失败: {e}")
            return False
    
    def terminate_process(self, process: psutil.Process) -> bool:
        """
        优雅终止进程
        
        Args:
            process: 要终止的进程
            
        Returns:
            bool: 是否成功终止
        """
        process_name = process.name()
        pid = process.pid
        
        try:
            logger.info(f"开始终止进程: {process_name}({pid})")
            
            # 尝试优雅终止
            process.terminate()
            
            # 等待进程结束（最多5秒）
            try:
                process.wait(timeout=5)
                logger.info(f"成功优雅终止进程: {process_name}({pid})")
                return True
            except psutil.TimeoutExpired:
                # 优雅终止超时，强制终止
                logger.warning(f"优雅终止超时，强制终止进程: {process_name}({pid})")
                process.kill()
                return True
                
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.error(f"终止进程失败 {process_name}({pid}): {e}")
            return False
    
    def monitor_cycle(self) -> None:
        """执行一次监控周期"""
        # 更新前台进程ID
        self._foreground_pid = self.get_foreground_process_id()
        
        # 如果没有配置，直接返回
        if not self.config_manager.has_configs:
            logger.debug("没有可用的进程配置，跳过监控周期")
            return
        
        # 获取所有配置的进程
        for config in self.config_manager.get_all_configs():
            self._monitor_process(config)
    
    def _monitor_process(self, config: ProcessConfig) -> None:
        """监控单个配置的进程"""
        process_name = config.process_name
        
        # 查找所有匹配的进程
        processes = self.find_process_by_name(process_name)
        
        if not processes:
            # 进程不存在，清理状态
            if process_name in self._process_states:
                del self._process_states[process_name]
            logger.debug(f"进程 {process_name} 未运行")
            return
        
        # 监控找到的每个进程实例
        for process in processes:
            pid_key = f"{process_name}_{process.pid}"
            
            # 检查进程是否空闲
            is_idle = self.check_process_idle(process, config)
            
            with self._monitor_lock:
                # 获取或创建进程状态
                if pid_key not in self._process_states:
                    self._process_states[pid_key] = ProcessState(process=process)
                
                state = self._process_states[pid_key]
                
                if is_idle:
                    # 进程空闲
                    if state.idle_start_time is None:
                        # 开始空闲计时
                        state.idle_start_time = datetime.now()
                        logger.info(f"进程 {process_name}({process.pid}) 开始空闲计时")
                    
                    state.update_idle_duration()
                    
                    # 检查是否达到终止条件
                    if state.idle_duration >= self.idle_threshold:
                        if self.terminate_process(process):
                            # 进程已终止，移除状态
                            del self._process_states[pid_key]
                else:
                    # 进程不空闲，重置状态
                    if state.idle_start_time is not None:
                        logger.info(f"进程 {process_name}({process.pid}) 结束空闲状态，"
                                  f"持续了 {state.idle_duration.total_seconds():.0f} 秒")
                    state.reset_idle_state()
    
    def cleanup_stale_states(self) -> None:
        """清理已不存在的进程的状态"""
        with self._monitor_lock:
            stale_keys = []
            for key, state in self._process_states.items():
                try:
                    # 检查进程是否还存在
                    if state.process and not state.process.is_running():
                        stale_keys.append(key)
                except psutil.NoSuchProcess:
                    stale_keys.append(key)
            
            for key in stale_keys:
                del self._process_states[key]
                logger.debug(f"清理已终止进程的状态: {key}")


class MonitorScheduler:
    """监控调度器：负责定时执行监控任务"""
    
    def __init__(self, 
                 config_manager: ConfigManager, 
                 monitor: ProcessMonitor,
                 check_interval: int = 5,
                 config_refresh_interval: int = 60):
        """
        初始化调度器
        
        Args:
            config_manager: 配置管理器
            monitor: 进程监控器
            check_interval: 监控检查间隔（秒）
            config_refresh_interval: 配置刷新间隔（秒）
        """
        self.config_manager = config_manager
        self.monitor = monitor
        self.check_interval = check_interval
        self.config_refresh_interval = config_refresh_interval
        
        self._running = False
        self._last_config_refresh = None
        self._scheduler_thread: Optional[threading.Thread] = None
    
    def start(self) -> None:
        """启动调度器"""
        if self._running:
            logger.warning("调度器已经在运行")
            return
        
        self._running = True
        
        # 加载初始配置
        self.config_manager.load_initial_config()
        
        # 启动调度线程
        self._scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._scheduler_thread.start()
        logger.info(f"进程监控调度器已启动，检查间隔: {self.check_interval}秒")
    
    def stop(self) -> None:
        """停止调度器"""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        logger.info("进程监控调度器已停止")
    
    def _run_scheduler(self) -> None:
        """调度器主循环"""
        while self._running:
            try:
                current_time = datetime.now()
                
                # 定期刷新配置
                if (self._last_config_refresh is None or 
                    (current_time - self._last_config_refresh).total_seconds() >= self.config_refresh_interval):
                    # self.config_manager.fetch_config_from_server()
                    self._last_config_refresh = current_time
                
                # 执行监控周期
                self.monitor.monitor_cycle()
                
                # 清理过期的进程状态
                self.monitor.cleanup_stale_states()
                
            except Exception as e:
                logger.error(f"调度器执行出错: {e}", exc_info=True)
            
            # 等待下一个周期
            time.sleep(self.check_interval)
    
    @property
    def is_running(self) -> bool:
        """调度器是否在运行"""
        return self._running


def main():
    """主函数：程序入口点"""
    # 配置参数（可根据需要调整为从配置文件或环境变量读取）
    CONFIG_URL = "http://your-server.com/api/process-configs"  # 替换为实际配置接口URL
    CHECK_INTERVAL = 5  # 监控检查间隔（秒）
    CONFIG_REFRESH_INTERVAL = 60  # 配置刷新间隔（秒）
    IDLE_THRESHOLD_MINUTES = 10  # 空闲时间阈值（分钟）
    
    logger.info("=== 进程智能监控客户端启动 ===")
    logger.info(f"配置URL: {CONFIG_URL}")
    logger.info(f"检查间隔: {CHECK_INTERVAL}秒")
    logger.info(f"配置刷新间隔: {CONFIG_REFRESH_INTERVAL}秒")
    logger.info(f"空闲阈值: {IDLE_THRESHOLD_MINUTES}分钟")
    
    try:
        # 初始化各组件
        config_manager = ConfigManager(CONFIG_URL)
        process_monitor = ProcessMonitor(config_manager, IDLE_THRESHOLD_MINUTES)
        scheduler = MonitorScheduler(
            config_manager=config_manager,
            monitor=process_monitor,
            check_interval=CHECK_INTERVAL,
            config_refresh_interval=CONFIG_REFRESH_INTERVAL
        )
        
        # 启动调度器
        scheduler.start()
        
        # 主线程等待（可按Ctrl+C停止）
        logger.info("监控已启动，按 Ctrl+C 停止...")
        while scheduler.is_running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("接收到停止信号")
    except Exception as e:
        logger.error(f"程序运行出错: {e}", exc_info=True)
    finally:
        if 'scheduler' in locals():
            scheduler.stop()
        logger.info("=== 进程智能监控客户端停止 ===")


if __name__ == "__main__":
    # 注意：运行前需要安装依赖
    # pip install psutil pywin32 requests
    
    # 创建示例配置文件（如果不存在）
    try:
        with open("process_config_cache.json", "r", encoding="utf-8") as f:
            json.load(f)
    except FileNotFoundError:
        # 创建默认配置示例
        default_config = [
            {
                "process_name": "msedge.exe",
                "cpu_threshold": 1.0,
                "memory_threshold": 1000.0
            }
        ]
        with open("process_config_cache.json", "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        logger.info("已创建示例配置文件 process_config_cache.json")
    
    main()