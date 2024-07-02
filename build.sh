apt-get update && apt-get install -y ffmpeg \
    && apt-get clean && rm -rf /var/lib/apt/lists/*


# 安装 Python 依赖包，先升级 pip，然后安装所需的 Python 包
pip install --no-cache-dir --upgrade pip

pip install loguru fastapi uvicorn pydantic pydantic_settings ffmpeg-python faster_whisper openai-whisper
