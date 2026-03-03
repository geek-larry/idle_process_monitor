@echo off
:: 检查是否以管理员身份运行
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 请求管理员权限...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: 启动闲置进程监控器
echo 启动闲置进程监控器...
cd /d "%~dp0\.."
if exist "idle_process_monitor.exe" (
    start "Idle Process Monitor" "idle_process_monitor.exe"
) else if exist "main.py" (
    echo 未找到可执行文件，尝试直接运行Python脚本...
    python main.py
) else (
    echo 未找到 idle_process_monitor.exe 或 main.py，请先打包项目或确保Python环境已安装
    pause
)
echo 启动完成，监控器已在后台运行
