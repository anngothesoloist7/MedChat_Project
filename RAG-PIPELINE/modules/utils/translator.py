import os
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

class Translator:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_CHAT_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_CHAT_API_KEY is missing in .env")
        
        self.client = genai.Client(api_key=self.api_key)
        # Load model from env, default to gemini-2.0-flash-exp
        self.model = os.getenv("GEMINI_TRANSLATOR_MODEL", "gemini-2.5-flash") 
        
        prompt_path = Path(os.getcwd()) / "prompts" / "medical_info_translation_prompt.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Translation prompt not found at {prompt_path}")
            
        self.system_prompt = prompt_path.read_text(encoding="utf-8")

    def translate_pages(self, pages: list[dict], batch_size: int = 5) -> tuple[list[dict], str]:
        """
        Translates a list of pages (from pages.json) in batches using parallel processing.
        Returns: (translated_pages_list, full_translated_markdown)
        """
        import time
        import sys
        import threading
        import itertools
        from concurrent.futures import ThreadPoolExecutor, as_completed

        translated_pages = [None] * len(pages)
        
        # Helper to translate a single batch
        def process_batch(batch_index, batch_pages):
            batch_text = "\n\n".join([p['content'] for p in batch_pages])
            translated_text = self.translate_content(batch_text)
            
            # We need to split the translated text back into pages roughly
            # Since exact page mapping is hard after translation, we will assign the 
            # whole translated batch text to the first page of the batch and leave others empty
            # or just return the text to be re-chunked later. 
            # Better approach for RAG: Keep the structure simple.
            
            # For this implementation, we will return the translated text and the indices it covers
            return batch_index, translated_text

        # Create batches
        batches = []
        for i in range(0, len(pages), batch_size):
            batches.append((i, pages[i : i + batch_size]))

        print(f"[INFO] Translating {len(pages)} pages in {len(batches)} batches (Parallel)...")
        
        results = []
        from tqdm import tqdm
        
        with ThreadPoolExecutor(max_workers=3) as executor: # Limit workers to avoid rate limits
            futures = {executor.submit(process_batch, b[0], b[1]): b[0] for b in batches}
            
            # Use tqdm to show progress bar
            for future in tqdm(as_completed(futures), total=len(batches), desc="Translating Batches", unit="batch"):
                try:
                    batch_idx, trans_text = future.result()
                    results.append((batch_idx, trans_text))
                except Exception as e:
                    print(f"\n[ERROR] Batch translation failed: {e}")

        # Sort results by batch index to maintain order
        results.sort(key=lambda x: x[0])
        
        # Reconstruct full markdown
        full_translated_md = "\n\n".join([r[1] for r in results])
        
        # Reconstruct pages list (simplified: we map translated batches back to the original page structure)
        # Note: Exact page-to-page correspondence is lost, but order is preserved.
        # We will create a new list of pages where each entry corresponds to a batch.
        new_pages = []
        for batch_idx, trans_text in results:
            # Find original page numbers for this batch
            start_page_idx = batch_idx
            original_page_num = pages[start_page_idx]['page']
            
            new_pages.append({
                "page": original_page_num, # Start page of the batch
                "content": trans_text,
                "images": [] # Images are hard to map back without complex logic
            })

        return new_pages, full_translated_md

    def translate_content(self, text: str) -> str:
        """
        Translates the given text using Gemini with the medical translation prompt.
        Handles rate limits (429) with exponential backoff and shows dynamic progress.
        """
        import time
        import sys
        import threading
        import itertools

        max_retries = 5
        
        for attempt in range(max_retries):
            process_start = time.time()

            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=text)]
                        )
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_prompt,
                        temperature=0.1, # Low temperature as requested
                        tools=[] # No external tools
                    )
                )
                total_time = time.time() - process_start
                print(f"[INFO] Translation Done in {total_time:.1f}s") 
                # Commented out to avoid spamming logs in parallel mode
                return response.text
            except Exception as e:
                # Check for 429 Resource Exhausted
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait_time = 30 * (2 ** attempt) # 30s, 60s, 120s...
                    # Use tqdm.write to avoid breaking the progress bar
                    from tqdm import tqdm
                    tqdm.write(f"[WARN] Translation rate limit hit (Attempt {attempt+1}/{max_retries}). Retrying in {wait_time}s...")
                    
                    # Dynamic countdown
                    for remaining in range(wait_time, 0, -1):
                        # Simple sleep for now to keep tqdm clean, or use a separate progress bar if really needed
                        # But printing countdown inside a tqdm loop is messy.
                        time.sleep(1)
                else:
                    print(f"\n[ERROR] Translation failed: {e}")
                    return text # Non-retriable error, return original
        
        print("\n[ERROR] Translation failed after max retries.")
        return text

# Global instance
try:
    translator = Translator()
except Exception as e:
    print(f"[WARN] Translator init failed: {e}")
    translator = None
