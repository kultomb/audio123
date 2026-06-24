import os, json
from pathlib import Path
from google import genai
from google.genai import types

json_path = 'C:/Users/CMD/Downloads/123.json'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = json_path
d = json.loads(Path(json_path).read_text(encoding='utf-8'))
c = genai.Client(vertexai=True, project=d['project_id'], location='us-central1')
cfg = types.GenerateContentConfig(max_output_tokens=10)

models = ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-1.5-pro-001', 'gemini-1.5-flash-001']
for m in models:
    try:
        r = c.models.generate_content(model=m, contents='Say hi', config=cfg)
        print(f'OK  : {m} -> {r.text.strip()}')
    except Exception as e:
        print(f'FAIL: {m} -> {str(e)[:120]}')
