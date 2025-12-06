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

def clean_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters."""
    # Remove "Copy of" prefix often added by Drive
    if filename.startswith("Bản sao của "): filename = filename[12:]
    elif filename.startswith("Copy of "): filename = filename[8:]
    
    # Remove invalid fs chars
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    return filename.strip()

def download_file(url: str, output_dir: str = "downloads") -> str:
    os.makedirs(output_dir, exist_ok=True)
    
    if "drive.google.com" in url:
        print(f"[INFO] Downloading from Drive: {url}")
        try:
            # gdown with output=None will download to CWD using the original filename
            downloaded_path = gdown.download(url, output=None, quiet=False, fuzzy=True, use_cookies=False)
            if not downloaded_path: raise Exception("gdown failed to return a path.")
            
            # Get the filename gdown determined
            original_fname = os.path.basename(downloaded_path)
            cleaned_fname = clean_filename(original_fname)
            
            final_path = os.path.join(output_dir, cleaned_fname)
            
            # Move from CWD to output_dir
            # If downloaded_path is already absolute/relative to CWD, move it.
            if os.path.abspath(downloaded_path) != os.path.abspath(final_path):
                shutil.move(downloaded_path, final_path)
                
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
                
            # No random IDs, just clean the name
            cleaned_fname = clean_filename(fname)
            if not cleaned_fname.lower().endswith('.pdf'):
                cleaned_fname += '.pdf'

            final_path = os.path.join(output_dir, cleaned_fname)
            
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
