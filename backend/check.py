import requests
import os
from dotenv import load_dotenv

load_dotenv()

res = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={os.getenv('GEMINI_API_KEY')}")
models = [m['name'] for m in res.json()['models'] if 'embedContent' in m.get('supportedGenerationMethods', [])]
print(models)