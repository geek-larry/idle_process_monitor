class ProcessConfig:
    def __init__(self, process_name, cpu_threshold, memory_threshold, io_threshold, network_threshold, idle_duration, 
                 termination_mode="auto", idle_detection_mode="cumulative", 
                 sliding_window_size=180, sliding_window_idle_percentage=90, sliding_window_weighted=False):
        """初始化进程配置
        
        Args:
            process_name: 进程名称
            cpu_threshold: CPU使用率阈值
            memory_threshold: 内存使用阈值
            io_threshold: IO使用阈值
            network_threshold: 网络使用阈值
            idle_duration: 闲置时长阈值
            termination_mode: 终止模式 (auto: 自动终止, confirm: 确认后终止)
            idle_detection_mode: 闲置检测模式 (cumulative: 累积计时, sliding_window: 滑动窗口)
            sliding_window_size: 滑动窗口大小
            sliding_window_idle_percentage: 闲置百分比阈值
            sliding_window_weighted: 是否使用加权滑动窗口
        """
        self.process_name = process_name
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.io_threshold = io_threshold
        self.network_threshold = network_threshold
        self.idle_duration = idle_duration
        self.termination_mode = termination_mode
        self.idle_detection_mode = idle_detection_mode
        self.sliding_window_size = sliding_window_size
        self.sliding_window_idle_percentage = sliding_window_idle_percentage
        self.sliding_window_weighted = sliding_window_weighted

    def to_dict(self):
        """转换为字典"""
        return {
            "process_name": self.process_name,
            "cpu_threshold": self.cpu_threshold,
            "memory_threshold": self.memory_threshold,
            "io_threshold": self.io_threshold,
            "network_threshold": self.network_threshold,
            "idle_duration": self.idle_duration,
            "termination_mode": self.termination_mode,
            "idle_detection_mode": self.idle_detection_mode,
            "sliding_window_size": self.sliding_window_size,
            "sliding_window_idle_percentage": self.sliding_window_idle_percentage,
            "sliding_window_weighted": self.sliding_window_weighted
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建实例"""
        return cls(
            process_name=data.get("process_name"),
            cpu_threshold=data.get("cpu_threshold"),
            memory_threshold=data.get("memory_threshold"),
            io_threshold=data.get("io_threshold"),
            network_threshold=data.get("network_threshold"),
            idle_duration=data.get("idle_duration"),
            termination_mode=data.get("termination_mode", "auto"),
            idle_detection_mode=data.get("idle_detection_mode", "cumulative"),
            sliding_window_size=data.get("sliding_window_size", 180),
            sliding_window_idle_percentage=data.get("sliding_window_idle_percentage", 90),
            sliding_window_weighted=data.get("sliding_window_weighted", False)
        )

class ProcessStatus:
    def __init__(self, process_name, is_active, cpu_usage, memory_usage, io_usage, network_usage, is_foreground):
        self.process_name = process_name
        self.is_active = is_active
        self.cpu_usage = cpu_usage
        self.memory_usage = memory_usage
        self.io_usage = io_usage
        self.network_usage = network_usage
        self.is_foreground = is_foreground