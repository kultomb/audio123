import json
import logging
import mimetypes
import os
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Union, Dict, List

from google import genai
from google.api_core.exceptions import Unauthorized
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import params, logger, settings
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.tts._base import BaseTTS


@dataclass
class GEMINITTS(BaseTTS):

    def _get_rate_extra(self):
        """Trả về extra args cho ffmpeg atempo filter dựa trên self.rate.
        Gemini TTS không hỗ trợ tham số tốc độ trực tiếp, nên dùng hậu xử lý ffmpeg."""
        speed = self.get_speed()
        if speed == 1.0:
            return None
        # atempo giới hạn [0.5, 2.0], cần chia nhỏ nếu vượt quá
        atempo_list = []
        factor = speed
        while factor > 2.0:
            atempo_list.append("atempo=2.0")
            factor /= 2.0
        while factor < 0.5:
            atempo_list.append("atempo=0.5")
            factor /= 0.5
        atempo_list.append(f"atempo={factor:.2f}")
        filter_str = ",".join(atempo_list)
        return ["-filter:a", filter_str]

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        role = data_item['role']
        try:
            self.generate_tts_segment(data_item['text'], role, params.get('gemini_ttsmodel',''),
                                      data_item['filename'] + '.wav')
        except Unauthorized as e:
            raise StopTask(e.message)
        # Áp dụng tốc độ đọc (rate) bằng ffmpeg atempo filter nếu rate != +0%
        self.convert_to_wav(data_item['filename'] + '.wav', data_item['filename'],
                            extra=self._get_rate_extra())

    def generate_tts_segment(self, text, voice, model, file_name):
        def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
            parameters = parse_audio_mime_type(mime_type)
            bits_per_sample = parameters["bits_per_sample"]
            sample_rate = parameters["rate"]
            num_channels = 1
            data_size = len(audio_data)
            bytes_per_sample = bits_per_sample // 8
            block_align = num_channels * bytes_per_sample
            byte_rate = sample_rate * block_align
            chunk_size = 36 + data_size  # 36 bytes for header fields before data chunk size

            # http://soundfile.sapp.org/doc/WaveFormat/

            header = struct.pack(
                "<4sI4s4sIHHIIHH4sI",
                b"RIFF",  # ChunkID
                chunk_size,  # ChunkSize (total file size - 8 bytes)
                b"WAVE",  # Format
                b"fmt ",  # Subchunk1ID
                16,  # Subchunk1Size (16 for PCM)
                1,  # AudioFormat (1 for PCM)
                num_channels,  # NumChannels
                sample_rate,  # SampleRate
                byte_rate,  # ByteRate
                block_align,  # BlockAlign
                bits_per_sample,  # BitsPerSample
                b"data",  # Subchunk2ID
                data_size  # Subchunk2Size (size of audio data)
            )
            return header + audio_data

        def parse_audio_mime_type(mime_type: str):
            """Parses bits per sample and rate from an audio MIME type string.

            Assumes bits per sample is encoded like "L16" and rate as "rate=xxxxx".

            Args:
                mime_type: The audio MIME type string (e.g., "audio/L16;rate=24000").

            Returns:
                A dictionary with "bits_per_sample" and "rate" keys. Values will be
                integers if found, otherwise None.
            """
            bits_per_sample = 16
            rate = 24000

            # Extract rate from parameters
            parts = mime_type.split(";")
            for param in parts:  # Skip the main type part
                param = param.strip()
                if param.lower().startswith("rate="):
                    try:
                        rate_str = param.split("=", 1)[1]
                        rate = int(rate_str)
                    except (ValueError, IndexError,TypeError):
                        # Handle cases like "rate=" with no value or non-integer value
                        pass  # Keep rate as default
                elif param.startswith("audio/L"):
                    try:
                        bits_per_sample = int(param.split("L", 1)[1])
                    except (ValueError, IndexError,TypeError):
                        pass  # Keep bits_per_sample as default if conversion fails

            return {"bits_per_sample": bits_per_sample, "rate": rate}

        def save_binary_file(file_name, data):
            with open(file_name, "wb") as f:
                f.write(data)

        # Vertex AI support
        auth_type = params.get('gemini_auth_type', 'api_key')
        if auth_type == 'vertex':
            json_path = params.get('gemini_vertex_json', '')
            if json_path and Path(json_path).exists():
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = json_path
            client = genai.Client(
                vertexai=True,
                project=params.get('gemini_vertex_project', ''),
                location=params.get('gemini_vertex_location', 'us-central1'),
                http_options=types.HttpOptions(
                    client_args={'proxy': self.proxy_str, 'timeout': 120.0},
                    async_client_args={'proxy': self.proxy_str, 'timeout': 120.0},
                )
            )
        else:
            client = genai.Client(
                api_key=params.get('gemini_key', ''),
                http_options=types.HttpOptions(
                    client_args={'proxy': self.proxy_str, 'timeout': 120.0},
                    async_client_args={'proxy': self.proxy_str, 'timeout': 120.0},
                )
            )

        # Gemini TTS có giới hạn độ dài text, cắt bớt nếu quá dài để tránh mất audio
        max_tts_chars = 1500
        if len(text) > max_tts_chars:
            logger.warning(f'[Gemini TTS] Text too long ({len(text)} chars), truncating to {max_tts_chars}')
            text = text[:max_tts_chars].rsplit(' ', 1)[0]  # cắt tại từ cuối cùng

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=text),
                ],
            ),
        ]
        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            response_modalities=[
                "audio",
            ],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice
                    )
                )
            ),
        )
        # Retry loop: Gemini đôi khi từ chối tạo audio (safety filter), thử lại tối đa 3 lần
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            audio_chunks = []
            mime_type = None
            for chunk in client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=generate_content_config,
            ):
                if (
                        chunk.candidates is None
                        or chunk.candidates[0].content is None
                        or chunk.candidates[0].content.parts is None
                ):
                    continue
                if chunk.candidates[0].content.parts[0].inline_data:
                    inline_data = chunk.candidates[0].content.parts[0].inline_data
                    mime_type = inline_data.mime_type
                    audio_chunks.append(inline_data.data)

            if audio_chunks:
                audio_data = b''.join(audio_chunks)
                file_extension = mimetypes.guess_extension(mime_type) if mime_type else None
                if file_extension is None:
                    audio_data = convert_to_wav(audio_data, mime_type or 'audio/L16;rate=24000')
                save_binary_file(file_name, audio_data)
                return  # thành công, thoát

            logger.warning(f'[Gemini TTS] Attempt {attempt}/{max_retries}: no audio returned for text: {text[:100]}...')
            if attempt < max_retries:
                import time
                time.sleep(1)  # đợi 1 giây trước khi thử lại

        raise Exception(f"Gemini TTS returned empty audio after {max_retries} attempts for text: {text[:100]}...")