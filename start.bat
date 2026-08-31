@echo off
chcp 65001 >nul
setlocal

REM 项目根目录（脚本所在目录，末尾带反斜杠）
set "ROOT=%~dp0"
REM 后端 Python 虚拟环境
set "PY=C:\Users\24866\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

echo ==============================================
echo   RAG 知识库问答系统 - 一键启动
echo ==============================================
echo.

if not exist "%PY%" (
    echo [错误] 未找到 Python 虚拟环境：
    echo        %PY%
    echo 请先安装后端依赖，或修改本脚本中的 PY 变量指向正确的 python.exe
    echo.
    pause
    exit /b 1
)

echo [1/2] 启动后端服务  http://127.0.0.1:8000
start "RAG-Backend" cmd /k "chcp 65001 >nul && cd /d %ROOT%backend && %PY% -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo [2/2] 启动前端服务  http://localhost:5173
start "RAG-Frontend" cmd /k "chcp 65001 >nul && cd /d %ROOT%frontend && npm run dev"

echo.
echo 启动完成！请用浏览器打开：
echo     http://localhost:5173
echo.
echo 默认账号：admin      密码：123456
echo.
echo 提示：分别关闭 "RAG-Backend" 和 "RAG-Frontend" 窗口即可停止对应服务
echo 提示：若后端提示端口被占用，请先关闭已运行的后端窗口
echo.
pause