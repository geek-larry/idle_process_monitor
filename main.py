import os
import sys
import threading
import signal
import time
from src.core.scheduler import scheduler
from src.utils.logger import logger

def start_flask_server():
    """启动Flask模拟服务端API"""
    try:
        from flask import Flask, jsonify
        import threading
        
        app = Flask(__name__)
        
        # 模拟进程配置数据
        process_configs = [
            {
                "process_name": "msedge.exe",
                "cpu_threshold": 5.0,
                "memory_threshold": 1500.0,
                "io_threshold": 10.0,
                "network_threshold": 1.0,
                "idle_duration": 1800,
                "termination_mode": "auto",
                "idle_detection_mode": "cumulative"
            },
            {
                "process_name": "bilibili.exe",
                "cpu_threshold": 3.0,
                "memory_threshold": 500.0,
                "io_threshold": 5.0,
                "network_threshold": 0.5,
                "idle_duration": 1800,
                "termination_mode": "confirm",
                "idle_detection_mode": "sliding_window",
                "sliding_window_size": 180,
                "sliding_window_idle_percentage": 90,
                "sliding_window_weighted": False
            },
            {
                "process_name": "EXCEL.EXE",
                "cpu_threshold": 2.0,
                "memory_threshold": 800.0,
                "io_threshold": 8.0,
                "network_threshold": 0.1,
                "idle_duration": 120,
                "termination_mode": "confirm",
                "idle_detection_mode": "sliding_window",
                "sliding_window_size": 12,
                "sliding_window_idle_percentage": 90,
                "sliding_window_weighted": False
            },
            {
                "process_name": "MATLAB.exe",
                "cpu_threshold": 5.0,
                "memory_threshold": 1000.0,
                "io_threshold": 10.0,
                "network_threshold": 1.0,
                "idle_duration": 1800,
                "termination_mode": "confirm",
                "idle_detection_mode": "sliding_window",
                "sliding_window_size": 180,
                "sliding_window_idle_percentage": 85,
                "sliding_window_weighted": True
            }
        ]
        
        @app.route('/api/process-configs', methods=['GET'])
        def get_process_configs():
            return jsonify(process_configs)
        
        # 在后台线程中运行Flask，避免窗口闪动
        def run_flask():
            app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
        
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        
    except Exception as e:
        logger.error(f"Error starting Flask server: {e}")

def signal_handler(sig, frame):
    """处理信号，优雅退出"""
    logger.info("Received interrupt signal, shutting down...")
    scheduler.stop()
    sys.exit(0)

def main():
    """主函数"""
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动Flask服务器线程
    flask_thread = threading.Thread(target=start_flask_server)
    flask_thread.daemon = True
    flask_thread.start()
    logger.info("Flask server started")
    
    # 等待Flask服务器启动
    time.sleep(2)
    
    # 启动调度器
    scheduler.start()
    
    # 主循环
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    # 添加src目录到Python路径
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
    main()
