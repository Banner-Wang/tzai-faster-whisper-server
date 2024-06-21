import os
import time
from typing import List, Union, Annotated

from whisper import tokenizer
from urllib.parse import quote
from fastapi import APIRouter, Query, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.utils import load_audio
from app.core.faster_whisper_asr import transcribe, language_detection

LANGUAGE_CODES = sorted(list(tokenizer.LANGUAGES.keys()))
ASR_ENGINE = "faster_whisper"

router = APIRouter()


@router.post("/transcribe")
async def asr(
        audio_file: UploadFile = File(...),
        encode: bool = Query(default=True, description="Encode audio first through ffmpeg"),
        task: Union[str, None] = Query(default="transcribe", enum=["transcribe", "translate"]),
        language: Union[str, None] = Query(default=None, enum=LANGUAGE_CODES),
        initial_prompt: Union[str, None] = Query(default=None),
        vad_filter: Annotated[bool | None, Query(
            description="Enable the voice activity detection (VAD) to filter out parts of the audio without speech",
            include_in_schema=(True if ASR_ENGINE == "faster_whisper" else False)
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
            'Asr-Engine': ASR_ENGINE,
            'Content-Disposition': f'attachment; filename="{quote(audio_file.filename)}.{output}"',
            'Asr-Cost-Time': f"{cost_time:.2f}s"
        }
    )


@router.post("/detect-language")
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
