import os
import json
import time

import ffmpeg
import numpy as np
from io import StringIO
from typing import Union, BinaryIO, TextIO, Any

from whisper import tokenizer
from whisper.utils import format_timestamp
from faster_whisper import WhisperModel
from faster_whisper.utils import format_timestamp
from cog import BasePredictor, Input, Path

model_name = "large-v3"
model_path = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
SAMPLE_RATE = 16000
LANGUAGE_CODES = sorted(list(tokenizer.LANGUAGES.keys()))


class ResultWriter:
    extension: str

    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def __call__(self, result: dict, audio_path: str):
        audio_basename = os.path.basename(audio_path)
        output_path = os.path.join(self.output_dir, audio_basename + "." + self.extension)

        with open(output_path, "w", encoding="utf-8") as f:
            self.write_result(result, file=f)

    def write_result(self, result: dict, file: TextIO):
        raise NotImplementedError


class WriteTXT(ResultWriter):
    extension: str = "txt"

    def write_result(self, result: dict, file: TextIO):
        for segment in result["segments"]:
            print(segment.text.strip(), file=file, flush=True)


class WriteVTT(ResultWriter):
    extension: str = "vtt"

    def write_result(self, result: dict, file: TextIO):
        print("WEBVTT\n", file=file)
        for segment in result["segments"]:
            print(
                f"{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}\n"
                f"{segment.text.strip().replace('-->', '->')}\n",
                file=file,
                flush=True,
            )


class WriteSRT(ResultWriter):
    extension: str = "srt"

    def write_result(self, result: dict, file: TextIO):
        for i, segment in enumerate(result["segments"], start=1):
            # write srt lines
            print(
                f"{i}\n"
                f"{format_timestamp(segment.start, always_include_hours=True, decimal_marker=',')} --> "
                f"{format_timestamp(segment.end, always_include_hours=True, decimal_marker=',')}\n"
                f"{segment.text.strip().replace('-->', '->')}\n",
                file=file,
                flush=True,
            )


class WriteTSV(ResultWriter):
    """
    Write a transcript to a file in TSV (tab-separated values) format containing lines like:
    <start time in integer milliseconds>\t<end time in integer milliseconds>\t<transcript text>

    Using integer milliseconds as start and end times means there's no chance of interference from
    an environment setting a language encoding that causes the decimal in a floating point number
    to appear as a comma; also is faster and more efficient to parse & store, e.g., in C++.
    """
    extension: str = "tsv"

    def write_result(self, result: dict, file: TextIO):
        print("start", "end", "text", sep="\t", file=file)
        for segment in result["segments"]:
            print(round(1000 * segment.start), file=file, end="\t")
            print(round(1000 * segment.end), file=file, end="\t")
            print(segment.text.strip().replace("\t", " "), file=file, flush=True)


class WriteJSON(ResultWriter):
    extension: str = "json"

    def write_result(self, result: dict, file: TextIO):
        json.dump(result, file)


def load_audio(file: bytes, encode=True, sr: int = SAMPLE_RATE):
    """
    Open an audio file object and read as mono waveform, resampling as necessary.
    Modified from https://github.com/openai/whisper/blob/main/whisper/audio.py to accept a file object
    Parameters
    ----------
    file: BinaryIO
        The audio file like object
    encode: Boolean
        If true, encode audio stream to WAV before sending to whisper
    sr: int
        The sample rate to resample the audio if necessary
    Returns
    -------
    A NumPy array containing the audio waveform, in float32 dtype.
    """

    if encode:
        try:
            # This launches a subprocess to decode audio while down-mixing and resampling as necessary.
            # Requires the ffmpeg CLI and `ffmpeg-python` package to be installed.
            out, _ = (
                ffmpeg.input("pipe:", threads=0)
                .output("-", format="s16le", acodec="pcm_s16le", ac=1, ar=sr)
                .run(cmd="ffmpeg", capture_stdout=True, capture_stderr=True, input=file)
            )
        except ffmpeg.Error as e:
            raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e
    else:
        out = file.read()

    return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0


def write_result(
        result: dict, file: BinaryIO, output: Union[str, None]
):
    if output == "srt":
        WriteSRT(ResultWriter).write_result(result, file=file)
    elif output == "vtt":
        WriteVTT(ResultWriter).write_result(result, file=file)
    elif output == "tsv":
        WriteTSV(ResultWriter).write_result(result, file=file)
    elif output == "json":
        WriteJSON(ResultWriter).write_result(result, file=file)
    elif output == "txt":
        WriteTXT(ResultWriter).write_result(result, file=file)
    else:
        return 'Please select an output method!'


class Predictor(BasePredictor):
    def setup(self):
        device = "cuda"
        model_quantization = "float16"
        setup_time = time.time()
        self.model = WhisperModel(
            model_size_or_path=model_name,
            device=device,
            compute_type=model_quantization,
            download_root=model_path
        )
        self.setup_cost_time = time.time() - setup_time

    def predict(
            self,
            audio: Path = Input(
                description="Audio file"
            ),
            encode: bool = Input(
                default=True,
                description="Encode audio first through FFmpeg",
            ),
            task: str = Input(
                default="transcribe",
                choices=["transcribe", "translate"],
                description="Whether to perform X->English translation (translate) or English->X (transcribe)",
            ),
            language: str = Input(
                default=None,
                choices=LANGUAGE_CODES,
                description="The language spoken in the audio, if known. "
                            "Supports: " + ", ".join(LANGUAGE_CODES),
            ),
            initial_prompt: str = Input(
                default=None,
                description="Optional text to provide context for the speech recognition.",
            ),
            vad_filter: bool = Input(
                default=True,
                description="Enable the voice activity detection (VAD) to filter out parts of the audio without speech",
            ),
            word_timestamps: bool = Input(
                default=False,
                description="Word level timestamps",
            ),
            output: str = Input(
                default="txt",
                choices=["txt", "vtt", "srt", "tsv", "json"],
                description="Output format",
            )
    ) -> Any:
        with open(audio, 'rb') as f:
            audio_data = f.read()
            audio = load_audio(audio_data, encode)

        options_dict = {"task": task}

        if language:
            options_dict["language"] = language
        if initial_prompt:
            options_dict["initial_prompt"] = initial_prompt
        if vad_filter:
            options_dict["vad_filter"] = True
        if word_timestamps:
            options_dict["word_timestamps"] = True

        segments = []
        text = ""
        transcribe_start_time = time.time()
        segment_generator, info = self.model.transcribe(audio, beam_size=5, **options_dict)
        transcribe_cost_time = time.time() - transcribe_start_time
        for segment in segment_generator:
            segments.append(segment)
            text = text + segment.text
        result = {
            "language": options_dict.get("language", info.language),
            "segments": segments,
            "text": text,
            "setup_cost_time": self.setup_cost_time,
            "transcribe_cost_time": transcribe_cost_time
        }

        output_file = StringIO()
        write_result(result, output_file, output)
        output_file.seek(0)

        return output_file.read()
