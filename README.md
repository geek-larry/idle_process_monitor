# 闲置进程监控器 (Idle Process Monitor)

## 项目简介

闲置进程监控器是一个Python项目，用于监控软件进程是否闲置，并在进程闲置超过设定时间后进行优雅释放。项目通过Flask框架模拟服务端API提供进程配置信息，基于psutil和pywin32库实现进程监控和前台窗口判断。

## 功能特点

- 从服务端API获取进程配置信息，支持配置缓存，减少API调用频率
- 支持配置CPU使用率、内存占用量、IO指标、网络指标阈值
- 基于进程组的聚合判断（处理同名多进程情况）
- 前台窗口状态判断
- 可配置的检查间隔（默认10秒）
- 闲置持续时间超过设定阈值（默认30分钟）时进行进程优雅释放
- 每日生成一个日志文件，最多保留7天
- 支持打包为exe文件，包含自启动脚本
- 提供用户配置文件，允许自定义设置
- 加强了异常处理和容错机制，提高程序稳定性
- 优化了性能，减少了资源消耗

## 项目结构

```
idle_process_monitor/
├── src/               # 源代码目录
│   ├── api/          # API相关代码
│   │   └── app.py    # Flask模拟服务端API
│   ├── core/         # 核心功能代码
│   │   ├── model.py  # 模型类
│   │   ├── monitor.py# 进程监控逻辑
│   │   └── scheduler.py # 定时器逻辑
│   ├── config/       # 配置相关代码
│   │   ├── config.py # 配置管理
│   │   └── user_config.py # 用户配置
│   └── utils/        # 工具类
│       └── logger.py # 日志处理
├── scripts/          # 脚本目录
│   └── startup_script.bat # 自启动脚本
├── logs/             # 日志目录
├── tests/            # 测试目录
├── main.py           # 主入口文件
├── requirements.txt  # 依赖配置
├── .gitignore        # Git忽略文件
├── README.md         # 项目说明
└── user_config.json  # 用户配置文件（自动生成）
```

## 安装步骤

1. 克隆项目到本地
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 运行主程序：
   ```bash
   python main.py
   ```

## 配置说明

### 进程配置

进程配置信息通过Flask模拟服务端API提供，默认配置包含以下进程：

- chrome.exe：CPU阈值5.0%，内存阈值1000MB，IO阈值10MB/s，网络阈值1.0MB/s
- notepad.exe：CPU阈值1.0%，内存阈值50MB，IO阈值1.0MB/s，网络阈值0.1MB/s
- explorer.exe：CPU阈值10.0%，内存阈值500MB，IO阈值20MB/s，网络阈值2.0MB/s

### 用户配置

用户可以通过修改`user_config.json`文件来自定义设置：

- `api_url`：API地址，默认http://127.0.0.1:5000/api/process-configs
- `cache_duration`：配置缓存时间，单位秒，默认300
- `check_interval`：检查间隔，单位秒，默认10
- `log_level`：日志级别，可选DEBUG, INFO, WARNING, ERROR, CRITICAL，默认INFO
- `log_keep_days`：日志保留天数，默认7
- `max_processes_per_check`：每次检查的最大进程数，默认10
- `process_cache_expiry`：进程信息缓存时间，单位秒，默认5

## 打包为EXE

### 步骤1：安装PyInstaller
```bash
pip install pyinstaller
```

### 步骤2：执行打包命令
```bash
pyinstaller --onefile --noconsole --name idle_process_monitor main.py
```

**参数说明**：
- `--onefile`：将所有依赖打包为单个exe文件
- `--noconsole`：不显示命令行窗口（实现无cmd窗口启动）
- `--name`：指定生成的exe文件名
- `main.py`：主入口文件路径

### 步骤3：复制配置文件
将配置文件复制到生成的exe文件所在目录：
```bash
copy config.properties dist\config.properties
```

### 步骤4：运行生成的exe文件
双击`dist`目录中的`idle_process_monitor.exe`文件即可启动，此时不会显示cmd窗口。

### 注意事项
1. **权限问题**：由于程序需要终止进程，运行时可能需要管理员权限。可以在快捷方式中设置"以管理员身份运行"。
2. **路径问题**：确保所有相对路径都能正确解析，特别是配置文件、日志目录等。
3. **测试**：打包后应在目标环境中测试，确保所有功能正常。

## 自启动设置

1. 将生成的exe文件复制到合适位置
2. 创建快捷方式到启动文件夹：
   - 按下Win+R，输入`shell:startup`
   - 将快捷方式粘贴到打开的文件夹中
3. 设置快捷方式以管理员身份运行：
   - 右键快捷方式，选择"属性"
   - 点击"高级"按钮
   - 勾选"以管理员身份运行"

或者使用项目提供的自启动脚本：

```bash
scripts\startup_script.bat
```

## 日志管理

- 日志文件存储在`logs`目录下
- 每日生成一个日志文件，格式为`app_YYYY-MM-DD.log`
- 最多保留7天的日志文件（可通过用户配置修改）
- 日志级别可在`user_config.json`中调整

## 性能优化

1. **进程信息缓存**：使用缓存减少进程遍历频率
2. **配置缓存**：减少API调用频率，提高响应速度
3. **限制进程检查数量**：每次检查最多处理10个进程，避免资源消耗过大
4. **优化IO和网络监控**：减少采样时间，提高性能
5. **异常处理**：加强异常捕获和处理，提高程序稳定性

## 注意事项

- 运行时需要管理员权限，以便能够终止进程
- 模拟服务端API默认运行在http://127.0.0.1:5000
- 首次运行时会从API获取配置并保存到本地config.json文件
- 当API不可用时，会使用本地缓存的配置
- 日志文件会自动清理，最多保留7天的日志
