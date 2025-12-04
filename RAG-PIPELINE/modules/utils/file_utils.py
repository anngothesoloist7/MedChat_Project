import os
import re
import requests
import gdown
import hashlib
import shutil
from urllib.parse import urlparse, unquote
from pathlib import Path

def is_url(path: str) -> bool:
    try:
        result = urlparse(path)
        return all([result.scheme, result.netloc])
    except ValueError: return False

def get_filename_from_cd(cd):
    if not cd: return None
    fname = re.findall('filename=(.+)', cd)
    return fname[0].strip().strip('"') if fname else None

def shorten_filename(filename: str, file_id: str = "0000", max_length: int = 100) -> str:
    if filename.startswith("Bản sao của "): filename = filename[12:]
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
    ext = '.pdf'
    
    parts = name_without_ext.replace(' -- ', '|').split('|')
    if parts:
        title = parts[0].strip()
        year, edition = None, None
        
        for part in parts:
            for word in part.strip().split():
                clean = word.strip('(),')
                if len(clean) == 4 and clean.isdigit():
                    year = clean; break
            if year: break
            
        for part in parts:
            part_lower = part.lower().strip()
            if any(w.rstrip('stndrh,').isdigit() for w in part.split()):
                for w in part.split():
                    if w.rstrip('stndrh,').isdigit(): edition = w.rstrip('stndrh,'); break
            elif 'edition' in part_lower:
                if 'twentieth' in part_lower: edition = '20th'
                elif 'eleventh' in part_lower: edition = '11th'
                elif 'fourteenth' in part_lower: edition = '14th'
                elif 'thirteenth' in part_lower: edition = '13th'
            if edition: break
        
        short_parts = [title[:60].rsplit(' ', 1)[0] if len(title) > 60 else title]
        if edition: short_parts.append(f"{edition}ed")
        if year: short_parts.append(year)
        
        base = ' '.join(short_parts)
        suffix = f" {file_id[-4:]}"
        avail = max_length - len(ext) - len(suffix)
        if len(base) > avail: base = base[:avail].rsplit(' ', 1)[0]
        return f"{base}{suffix}{ext}"
    
    return f"{file_id}{ext}"

def download_file(url: str, output_dir: str = "downloads") -> str:
    os.makedirs(output_dir, exist_ok=True)
    
    if "drive.google.com" in url:
        print(f"[INFO] Downloading from Drive: {url}")
        try:
            file_id = hashlib.md5(url.encode()).hexdigest()[:8]
            temp_path = os.path.join(output_dir, f"temp_{file_id}.pdf")
            
            out = gdown.download(url, output=temp_path, quiet=False, fuzzy=True, use_cookies=False)
            if not out: raise Exception("gdown failed.")
            
            original = f"document_{file_id}.pdf"
            try:
                from pypdf import PdfReader
                reader = PdfReader(out)
                if reader.metadata and reader.metadata.title:
                    t = reader.metadata.title.strip()
                    if t: original = f"{t}.pdf"
            except Exception as e: print(f"[WARN] Metadata error: {e}")

            final_path = os.path.join(output_dir, shorten_filename(original, file_id=file_id))
            if os.path.abspath(out) != os.path.abspath(final_path):
                if os.path.exists(final_path): os.remove(final_path)
                os.rename(out, final_path)
            return os.path.abspath(final_path)
            
        except Exception as e:
            if "Permission denied" in str(e): raise Exception(f"Drive Access Denied: {e}")
            raise Exception(f"Drive Download Failed: {e}")

    else:
        print(f"[INFO] Downloading URL: {url}")
        try:
            res = requests.get(url, stream=True, timeout=30)
            res.raise_for_status()
            
            fname = get_filename_from_cd(res.headers.get('content-disposition'))
            if not fname:
                parsed = urlparse(url)
                fname = os.path.basename(unquote(parsed.path)) or "downloaded_file.pdf"
                
            file_id = hashlib.md5(url.encode()).hexdigest()[:8]
            final_path = os.path.join(output_dir, shorten_filename(fname, file_id=file_id))
            
            with open(final_path, 'wb') as f:
                for chunk in res.iter_content(chunk_size=8192):
                    if chunk: f.write(chunk)
            return os.path.abspath(final_path)
        except Exception as e: raise Exception(f"URL Download Failed: {e}")

def list_google_drive_folder(url: str) -> list[dict]:
    print(f"[INFO] Listing Drive folder: {url}")
    captured = []
    
    def mock_download(url, output, **kwargs):
        captured.append({'name': os.path.basename(output) if output else "Unknown", 'url': url})
        return output

    try:
        import gdown.download_folder
        orig = gdown.download_folder.download
        gdown.download_folder.download = mock_download
        
        dummy = "dummy_list_dir"
        if os.path.exists(dummy): shutil.rmtree(dummy)
        os.makedirs(dummy, exist_ok=True)
        
        gdown.download_folder.download_folder(url, output=dummy, quiet=True, use_cookies=False)
        
        unique = []
        seen = set()
        for f in [x for x in captured if x['name'].lower().endswith('.pdf')]:
            if f['url'] not in seen:
                unique.append(f)
                seen.add(f['url'])
        return unique

    except Exception as e:
        print(f"[ERROR] List folder failed: {e}")
        return []
    finally:
        if 'gdown.download_folder' in locals() and 'orig' in locals():
            gdown.download_folder.download = orig
        if os.path.exists("dummy_list_dir"): shutil.rmtree("dummy_list_dir", ignore_errors=True)

def download_google_drive_file(file_url: str, output_dir: str) -> str:
    return download_file(file_url, output_dir)

def resolve_pdf_path(input_path: str, download_dir: str = "RAG-PIPELINE/database/raw") -> str:
    if is_url(input_path):
        if not os.path.isabs(download_dir): download_dir = os.path.join(os.getcwd(), download_dir)
        print(f"[INFO] Downloading to {download_dir}...")
        return download_file(input_path, download_dir)
    else:
        local = os.path.abspath(os.path.expanduser(input_path))
        if not os.path.exists(local): raise FileNotFoundError(f"File not found: {local}")
        if not os.path.isfile(local): raise IsADirectoryError(f"Not a file: {local}")
        return local
