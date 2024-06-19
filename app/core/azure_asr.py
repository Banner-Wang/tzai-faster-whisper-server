import io
import json
import time
from loguru import logger
import azure.cognitiveservices.speech as speechsdk

from app.core.config import settings

MS_LANGUAGES = {
    "ar-AE", "ar-BH", "ar-DZ", "ar-EG", "ar-IQ", "ar-JO", "ar-KW", "ar-LY", "ar-MA", "ar-OM", "ar-QA", "ar-SA", "ar-SY",
    "ar-YE", "bn-IN", "bg-BG", "ca-ES", "zh-CN", "zh-HK", "zh-TW", "hr-HR", "cs-CZ", "da-DK", "nl-NL", "en-AU", "en-CA",
    "en-GH", "en-HK", "en-IN", "en-IE", "en-KE", "en-NZ", "en-NG", "en-PH", "en-SG", "en-ZA", "en-TZ", "en-GB", "en-US",
    "et-EE", "fi-FI", "fr-CA", "fr-FR", "de-DE", "el-GR", "gu-IN", "he-IL", "hi-IN", "hu-HU", "id-ID", "ga-IE", "it-IT",
    "ja-JP", "kn-IN", "ml-IN", "ko-KR", "lv-LV", "lt-LT", "mt-MT", "mr-IN", "nb-NO", "pl-PL", "pt-BR", "pt-PT", "ro-RO",
    "ru-RU", "sk-SK", "sl-SI", "es-AR", "es-BO", "es-CL", "es-CO", "es-CR", "es-CU", "es-DO", "es-EC", "es-SV", "es-GQ",
    "es-GT", "es-HN", "es-MX", "es-NI", "es-PA", "es-PY", "es-PE", "es-PR", "es-ES", "es-UY", "es-US", "es-VE", "sv-SE",
    "ta-IN", "te-IN", "th-TH", "tr-TR", "uk-UA", "vi-VN",
}


class AzureClient:
    def __init__(self):
        self.subscription = settings.AZURE_SUBSCRIPTION
        self.region = settings.AZURE_REGION
        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.subscription,
            region=self.region
        )
        self.speech_config.output_format = speechsdk.OutputFormat.Detailed
        self.speech_config.request_word_level_timestamps()
        self.__final_info: list[dict] = []
        self.__done: bool = False

    @staticmethod
    def set_audio_config(wav_file, config_type):
        if config_type == "microphone":
            audio_config = speechsdk.AudioConfig(use_default_microphone=True)
        elif config_type == "file":
            audio_config = speechsdk.AudioConfig(filename=wav_file)
        elif config_type == "bytes":
            audio_bytes = wav_file.read()
            audio_stream = io.BytesIO(audio_bytes)
            # 创建SpeechSDK支持的PushStream
            push_stream = speechsdk.audio.PushAudioInputStream()
            # 将原始音频数据复制到PushStream
            push_stream.write(audio_stream.read())
            # 标记流结束
            push_stream.close()
            audio_config = speechsdk.AudioConfig(stream=push_stream)
        else:
            raise ValueError("config_type error, must [microphone, file, bytes]")
        return audio_config

    def set_speech_recognizer(self, audio_config, languages):
        if len(languages) > 1:
            self.speech_config.set_property(
                property_id=speechsdk.PropertyId.SpeechServiceConnection_LanguageIdMode,
                value='Continuous'
            )
            auto_lang_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(
                languages=languages
            )
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                auto_detect_source_language_config=auto_lang_config,
                audio_config=audio_config
            )
        elif len(languages) == 1:
            self.speech_config.speech_recognition_language = languages[0]
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
        else:
            raise ValueError("languages list must contain exactly 1 item or more than 1 item.")
        return speech_recognizer

    def recognize_wav_stream(self, wav_file, languages, config_type="file", is_develop=False):
        try:
            audio_config = self.set_audio_config(wav_file, config_type)
            speech_recognizer = self.set_speech_recognizer(audio_config, languages)
        except Exception as e:
            logger.error(f"AzureClient.recognize_wav_stream error: {e}")
            return self.__final_info

        def stop_cb(evt):
            speech_recognizer.stop_continuous_recognition()
            self.__done = True

        def recognizing_text(evt):
            auto_detect_source_language_result = speechsdk.AutoDetectSourceLanguageResult(evt.result)
            detected_language = auto_detect_source_language_result.language

        def store_text(evt):
            auto_detect_source_language_result = speechsdk.AutoDetectSourceLanguageResult(evt.result)
            detected_language = auto_detect_source_language_result.language

            json_result = evt.result.json

            if is_develop:
                best_or_lexical = json.loads(json_result).get('NBest')[0]
            else:
                best_or_lexical = json.loads(json_result).get('NBest')[0].get('Lexical')
            logger.debug(f'store_text: {best_or_lexical}, language:{detected_language}')

            self.__final_info.append(
                {
                    "text": best_or_lexical,
                    "language": detected_language
                }
            )

        # speech_recognizer.recognizing.connect(recognizing_text)
        speech_recognizer.recognized.connect(store_text)
        speech_recognizer.session_stopped.connect(stop_cb)
        speech_recognizer.canceled.connect(stop_cb)

        speech_recognizer.start_continuous_recognition()
        while not self.__done:
            time.sleep(.5)

        logger.info(f"final_info: {self.__final_info}")
        speech_recognizer.stop_continuous_recognition()
        return self.__final_info


if __name__ == '__main__':
    client = AzureClient()
    wav_file_path = r'D:\AIDatasets\hsbc_en_spanish_zh_yue_02.wav'
    language_list = ["zh-CN", "es-ES"]
    result = client.recognize_wav_stream(wav_file_path, language_list)
    print(result)
