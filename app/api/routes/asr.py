import os
import time
from typing import List, Union, Annotated

from whisper import tokenizer
from urllib.parse import quote
from fastapi import APIRouter, Query, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

from app.core.azure_asr import AzureClient, MS_LANGUAGES
from app.core.config import settings
from app.models import AzureASRData
from app.core.utils import load_audio

if settings.ASR_ENGINE == "faster_whisper":
    from app.core.faster_whisper_asr import transcribe, language_detection
else:
    from app.core.whisper_asr import transcribe, language_detection

LANGUAGE_CODES = sorted(list(tokenizer.LANGUAGES.keys()))

router = APIRouter()


@router.post("/azure-asr", response_model=List[AzureASRData])
async def azure_transcribe(
        file: UploadFile = File(...),
        languages: list = Query(..., description=f"语言列表; 参考：{MS_LANGUAGES}"),
        is_develop: bool = Query(False, description="是否为开发模式")
):
    if not file.filename.endswith(".wav"):
        raise HTTPException(status_code=400, detail="只支持wav音频格式")
    if not set(languages).issubset(MS_LANGUAGES):
        raise HTTPException(status_code=400, detail=f"不支持的语言: {languages}")

    wav_file = os.path.join(settings.OUTPUT_BASE_DIR, file.filename)
    with open(wav_file, "wb") as f:
        f.write(file.file.read())

    result = AzureClient().recognize_wav_stream(
        wav_file,
        languages,
        is_develop=is_develop
    )
    if not result:
        raise HTTPException(status_code=400, detail="azure_transcribe 发生异常，稍后再试。")

    return result


@router.post("/whisper-asr")
async def asr(
        audio_file: UploadFile = File(...),
        encode: bool = Query(default=True, description="Encode audio first through ffmpeg"),
        task: Union[str, None] = Query(default="transcribe", enum=["transcribe", "translate"]),
        language: Union[str, None] = Query(default=None, enum=LANGUAGE_CODES),
        initial_prompt: Union[str, None] = Query(default=None),
        vad_filter: Annotated[bool | None, Query(
            description="Enable the voice activity detection (VAD) to filter out parts of the audio without speech",
            include_in_schema=(True if settings.ASR_ENGINE == "faster_whisper" else False)
        )] = False,
        word_timestamps: bool = Query(default=False, description="Word level timestamps"),
        output: Union[str, None] = Query(default="txt", enum=["txt", "vtt", "srt", "tsv", "json"])
):
    start_time = time.time()
    result = transcribe(load_audio(audio_file.file, encode), task, language, initial_prompt, vad_filter,
                        word_timestamps, output)
    cost_time = time.time() - start_time
    return StreamingResponse(
        result,
        media_type="text/plain",
        headers={
            'Asr-Engine': settings.ASR_ENGINE,
            'Content-Disposition': f'attachment; filename="{quote(audio_file.filename)}.{output}"',
            'Asr-Cost-Time': f"{cost_time:.2f}s"
        }
    )


@router.post("/whisper-detect-language")
async def detect_language(
        audio_file: UploadFile = File(...),
        encode: bool = Query(default=True, description="Encode audio first through FFmpeg")
):
    stat_time = time.time()
    detected_lang_code = language_detection(load_audio(audio_file.file, encode))
    cost_time = time.time() - stat_time
    return {
        "detected_language": tokenizer.LANGUAGES[detected_lang_code],
        "language_code": detected_lang_code,
        "cost_time": f"{cost_time:.2f}s"
    }
