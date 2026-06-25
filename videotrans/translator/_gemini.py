import json
import logging
import os
import re,httpx
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.excepts import NO_RETRY_EXCEPT, TranslateSrtError, StopTask
from videotrans.configure.config import tr,settings,params,logger
from videotrans.translator._base import BaseTrans
from videotrans.util import tools
from google import genai
from google.genai import types,errors

@dataclass
class Gemini(BaseTrans):
    prompt: str = field(init=False)
    api_keys: List[str] = field(init=False, repr=False)  # Use repr=False for sensitive data

    def __post_init__(self):
        super().__post_init__()
        self.model_name = params.get("gemini_model",'gemini-2.5-flash')
        self.prompt_style = params.get("gemini_prompt_style", 'default')
        self.prompt = tools.get_prompt(ainame='gemini',aisendsrt=self.aisendsrt, style=self.prompt_style).replace('{lang}', self.target_language_name)
        self.api_keys = params.get('gemini_key', '').strip().split(',')
        # Vertex AI config
        self.auth_type = params.get('gemini_auth_type', 'api_key')
        if self.auth_type == 'vertex':
            json_path = params.get('gemini_vertex_json', '')
            if json_path and Path(json_path).exists():
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = json_path
            self.vertex_project = params.get('gemini_vertex_project', '')
            self.vertex_location = params.get('gemini_vertex_location', 'us-central1')


    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(max(3, int(settings.get('retry_nums', 3))))), wait=wait_fixed(3), before=before_log(logger, logging.INFO),after=after_log(logger, logging.INFO))
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = "\n".join([i.strip() for i in data]) if isinstance(data, list) else data
        api_key = self.api_keys.pop(0)
        self.api_keys.append(api_key)
        try:
            if self.auth_type == 'vertex':
                client = genai.Client(
                    vertexai=True,
                    project=self.vertex_project,
                    location=self.vertex_location,
                    http_options=types.HttpOptions(
                        client_args={'proxy': self.proxy_str, 'timeout': 120.0},
                        async_client_args={'proxy': self.proxy_str, 'timeout': 120.0},
                    )
                )
            else:
                client = genai.Client(
                    api_key=api_key,
                    http_options = types.HttpOptions(
                        client_args={'proxy': self.proxy_str, 'timeout': 120.0},
                        async_client_args={'proxy': self.proxy_str, 'timeout': 120.0},
                    )

                )
            model = params.get("gemini_model","gemini-2.5-flash")
            message=self.prompt.replace('{batch_input}', f'{text}')
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=message),
                    ],
                ),
            ]
            think_cfg=types.ThinkingConfig(
                        thinking_level="LOW",
                )
            if model.lower().startswith('gemini-2'):
                think_cfg=types.ThinkingConfig(
                        thinking_budget=0,
                    )
                
            generate_content_config = types.GenerateContentConfig(
                temperature=float(settings.get('aitrans_temperature',0.1)),
                max_output_tokens=int(params.get("gemini_maxtoken",65530)),
                safety_settings=[
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    )
                  ],

                thinking_config = think_cfg,
                system_instruction=[
                    types.Part.from_text(text='You are a top-tier Subtitle Translation Engine.'),
                ],
            )
            if model.startswith('gemini-1.') or model.startswith('gemini-2.0'):            
                generate_content_config = types.GenerateContentConfig()

            result = ""
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_content_config,
            ):
                result+=chunk.text if chunk.text else ""
                     
            logger.debug(f'{result=}')
            if not result:
                logger.warning(f'[gemini]请求失败 - empty response')
                raise TranslateSrtError(f"[Gemini]result is empty")
                
            # Strip thinking tags
            cleaned = re.sub(r'<think>.*?</think>', '', result, flags=re.I | re.S)
            match = re.search(r'<TRANSLATE_TEXT>(.*?)(?:</TRANSLATE_TEXT>|$)', cleaned, re.S | re.I)
            if match:
                return match.group(1)
            # Fallback: if result looks like plain SRT (starts with number),
            # return it directly instead of failing
            if re.search(r'^\d+\s*$', cleaned.strip(), re.M):
                logger.warning('[gemini] No TRANSLATE_TEXT tag found, using raw output as SRT')
                return cleaned.strip()
            logger.error(f'[gemini] No valid SRT found in response. Raw result (first 500 chars): {result[:500]}')
            raise TranslateSrtError(f"Gemini result is emtpy")
        except httpx.ConnectTimeout as e:
            raise StopTask(f' {tr("Unable to connect to remote API","Gemini AI")}\n{e}') from e
        except errors.APIError as e:
            logger.warning(f'{e=}')
            if e.code in [400,403,404,429,500]:
                raise StopTask(e.message)
            raise TranslateSrtError(e.message)

