# Reading Companion 应用 Docker 配置

FROM python:3.9-slim

# 配置国内 apt 源（完全覆盖默认配置）
RUN printf '%s\n' \
    'deb http://mirrors.tuna.tsinghua.edu.cn/debian/ trixie main contrib non-free' \
    'deb http://mirrors.tuna.tsinghua.edu.cn/debian/ trixie-updates main contrib non-free' \
    'deb http://mirrors.tuna.tsinghua.edu.cn/debian/ trixie-backports main contrib non-free' \
    'deb http://mirrors.tuna.tsinghua.edu.cn/debian-security/ trixie-security main contrib non-free' \
    > /etc/apt/sources.list && \
    rm -f /etc/apt/sources.list.d/*.list

# 安装 ffmpeg（用于音频合并）
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 安装依赖（已使用清华 pip 源）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/version || exit 1

# 启动命令：使用gunicorn运行Flask（main.py在backend目录）
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "600", "--access-logfile", "-", "--error-logfile", "-", "--chdir", "backend", "main:app"]
