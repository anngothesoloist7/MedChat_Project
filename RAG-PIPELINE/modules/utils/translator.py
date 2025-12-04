import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from google import genai
from google.genai import types
from tqdm import tqdm
from modules.config import Config

class Translator:
    def __init__(self):
        self.api_key = Config.GOOGLE_CHAT_API_KEY
        if not self.api_key: raise ValueError("GOOGLE_CHAT_API_KEY missing")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model = Config.GEMINI_TRANSLATOR_MODEL
        
        prompt_path = Config.PIPELINE_ROOT / "prompts" / "medical_info_translation_prompt.md"
        if not prompt_path.exists(): raise FileNotFoundError(f"Prompt not found: {prompt_path}")
        self.system_prompt = prompt_path.read_text(encoding="utf-8")

    def translate_pages(self, pages: list[dict], batch_size: int = 5) -> tuple[list[dict], str]:
        batches = [(i, pages[i : i + batch_size]) for i in range(0, len(pages), batch_size)]
        print(f"[INFO] Translating {len(pages)} pages in {len(batches)} batches...")
        
        results = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(self._process_batch, b[0], b[1]): b[0] for b in batches}
            for future in tqdm(as_completed(futures), total=len(batches), desc="Translating", unit="batch"):
                try: results.append(future.result())
                except Exception as e: print(f"\n[ERROR] Batch failed: {e}")

        results.sort(key=lambda x: x[0])
        full_translated_md = "\n\n".join([r[1] for r in results])
        
        new_pages = []
        for batch_idx, trans_text in results:
            new_pages.append({
                "page": pages[batch_idx]['page'],
                "content": trans_text,
                "images": []
            })
        return new_pages, full_translated_md

    def _process_batch(self, batch_index, batch_pages):
        batch_text = "\n\n".join([p['content'] for p in batch_pages])
        return batch_index, self.translate_content(batch_text)

    def translate_content(self, text: str) -> str:
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[types.Content(role="user", parts=[types.Part.from_text(text=text)])],
                    config=types.GenerateContentConfig(system_instruction=self.system_prompt, temperature=0.1)
                )
                return response.text
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait = 30 * (2 ** attempt)
                    tqdm.write(f"[WARN] Rate limit (Attempt {attempt+1}). Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"\n[ERROR] Translation failed: {e}")
                    return text
        return text

try:
    translator = Translator()
except Exception as e:
    print(f"[WARN] Translator init failed: {e}")
    translator = None
