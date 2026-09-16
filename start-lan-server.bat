@echo off
rem NRI 情报地球 - 局域网预览服务（默认端口 8731）
cd /d %~dp0
echo NRI 情报地球: http://localhost:8731/index.html  （局域网同事用 http://<本机IP>:8731/index.html）
python server.py 8731
pause
