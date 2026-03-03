from flask import Flask, jsonify

app = Flask(__name__)

# 模拟进程配置数据
process_configs = [
    {
        "process_name": "chrome.exe",
        "cpu_threshold": 5.0,
        "memory_threshold": 1000.0,  # MB
        "io_threshold": 10.0,  # MB/s
        "network_threshold": 1.0,  # MB/s
        "idle_duration": 1800  # 30分钟，单位秒
    },
    {
        "process_name": "notepad.exe",
        "cpu_threshold": 1.0,
        "memory_threshold": 50.0,
        "io_threshold": 1.0,
        "network_threshold": 0.1,
        "idle_duration": 1800
    },
    {
        "process_name": "explorer.exe",
        "cpu_threshold": 10.0,
        "memory_threshold": 500.0,
        "io_threshold": 20.0,
        "network_threshold": 2.0,
        "idle_duration": 1800
    },
    {
        "process_name": "MATLAB.exe",
        "cpu_threshold": 5.0,
        "memory_threshold": 1000.0,
        "io_threshold": 10.0,
        "network_threshold": 1.0,
        "idle_duration": 1800
    }
]

@app.route('/api/process-configs', methods=['GET'])
def get_process_configs():
    return jsonify(process_configs)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)