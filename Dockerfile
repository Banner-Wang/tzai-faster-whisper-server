# 使用官方的 Python 3.10 Slim 镜像作为基础镜像
FROM python:3.10-slim-bookworm

# 设置环境变量，指定用户的主目录和更新 PATH 环境变量
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# 切换到 root 用户
USER root

RUN apt-get update && apt-get install -y ffmpeg \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR $HOME/app

# 安装 Python 依赖包，先升级 pip，然后安装所需的 Python 包
RUN pip install --no-cache-dir --upgrade pip && \
    pip install loguru fastapi uvicorn pydantic pydantic_settings ffmpeg-python faster_whisper openai-whisper

# 复制应用代码到容器内，并将所有权设置为 root
COPY --chown=root . $HOME/app

ENV LD_LIBRARY_PATH /usr/local/lib/python3.10/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]