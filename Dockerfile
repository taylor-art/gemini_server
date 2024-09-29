# 使用 Python 3.10 的基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制 requirements.txt 文件并安装依赖
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件到工作目录
COPY . .

# 创建日志目录
RUN mkdir -p /var/log/myapp

# 设置环境变量
ENV LOG_FILE=/var/log/myapp/app.log

# 启动 Flask 应用
CMD ["python", "main.py"]