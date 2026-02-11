FROM python:3.9-slim

# 设置环境变量：
# PYTHONUNBUFFERED=1 确保 Python 输出直接打印到终端（Docker logs），不被缓存
# PYTHONDONTWRITEBYTECODE=1 防止生成 .pyc 文件
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /mnt/locust

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码（利用 .dockerignore 排除无关文件）
COPY . .

# 暴露 Locust Web UI 端口 (8089) 和 Master-Worker 通信端口 (5557)
EXPOSE 8089 5557

# 设置入口点
# 可以在 K8s 或 Docker 命令中通过 args 覆盖，例如 ["--master"] 或 ["--worker"]
ENTRYPOINT ["locust"]
