apt-get update && apt-get install -y ffmpeg jq file \
    && apt-get clean && rm -rf /var/lib/apt/lists/*


# 安装 Python 依赖包，先升级 pip，然后安装所需的 Python 包
/opt/python3/bin/pip3 install --no-cache-dir --upgrade pip

/opt/python3/bin/pip3 install loguru fastapi uvicorn pydantic pydantic_settings ffmpeg-python faster_whisper openai-whisper
