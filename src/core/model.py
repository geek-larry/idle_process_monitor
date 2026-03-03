class ProcessConfig:
    def __init__(self, process_name, cpu_threshold, memory_threshold, io_threshold, network_threshold, idle_duration):
        self.process_name = process_name
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.io_threshold = io_threshold
        self.network_threshold = network_threshold
        self.idle_duration = idle_duration

    def to_dict(self):
        return {
            "process_name": self.process_name,
            "cpu_threshold": self.cpu_threshold,
            "memory_threshold": self.memory_threshold,
            "io_threshold": self.io_threshold,
            "network_threshold": self.network_threshold,
            "idle_duration": self.idle_duration
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            process_name=data.get("process_name"),
            cpu_threshold=data.get("cpu_threshold"),
            memory_threshold=data.get("memory_threshold"),
            io_threshold=data.get("io_threshold"),
            network_threshold=data.get("network_threshold"),
            idle_duration=data.get("idle_duration")
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