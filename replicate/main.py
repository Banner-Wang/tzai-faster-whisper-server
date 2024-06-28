import argparse
import time

from predict import *

parser = argparse.ArgumentParser(description="Automatic Speech Recognition")
parser.add_argument(
    "--file-name",
    required=True,
    type=str,
    help="Path or URL to the audio file to be transcribed.",
)


class AsrPredictor(Predictor):
    def asr(
            self,
            audio: Path,
            encode: bool = True,
            task: str = "transcribe",
            language: str = None,
            initial_prompt: str = None,
            vad_filter: bool = True,
            word_timestamps: bool = False,
            output: str = "json"
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


if __name__ == '__main__':
    args = parser.parse_args()

    predictor = AsrPredictor()
    start_time = time.time()
    predictor.setup()
    setup_time = time.time()
    result = predictor.asr(
        audio=args.file_name
    )
    print(result)
