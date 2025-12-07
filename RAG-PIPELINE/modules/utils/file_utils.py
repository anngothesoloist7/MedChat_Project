import os
import re
import requests
import gdown
import hashlib
import shutil
from urllib.parse import urlparse, unquote
from pathlib import Path
from pypdf import PdfReader

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
    """Sanitize filename and ensure it's not too long."""
    # Remove unwanted prefixes
    if filename.startswith("Bản sao của "): filename = filename[12:]
    elif filename.startswith("Copy of "): filename = filename[8:]
    
    # Remove invalid fs chars
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    filename = filename.strip()
    
    # Truncate if too long (max 100 chars for safety)
    if len(filename) > 100:
        base, ext = os.path.splitext(filename)
        filename = base[:95] + ext
        
    return filename

def download_file(url: str, output_dir: str = "downloads") -> str:
    os.makedirs(output_dir, exist_ok=True)
    
    if "drive.google.com" in url:
        print(f"[INFO] Downloading from Drive: {url}")
        try:
            # We don't know the filename yet, and gdown's fuzzy logic can return huge filenames.
            # Best strategy: Let gdown download to a temp name first, OR rely on it but handle the move carefully.
            # However, gdown with output=None writes to CWD using the remote name, which causes the crash.
            # Fix: Use a temporary safe output name, then rename it if we can extract proper name, 
            # or just use a generated name if the remote one is crazy.
            
            # Attempt to get name from ID or use generic
            file_id = None
            match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
            if match: file_id = match.group(1)
            else:
                 msg_match = re.search(r'id=([a-zA-Z0-9_-]+)', url)
                 if msg_match: file_id = msg_match.group(1)
            
            temp_name = f"gdown_temp_{file_id if file_id else hashlib.md5(url.encode()).hexdigest()}.pdf"
            temp_path = os.path.join(output_dir, temp_name)
            
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                print(f"[INFO] File already exists: {temp_path}. Skipping download.")
                return os.path.abspath(temp_path)
            
            # Tell gdown to download to this specific safe path
            downloaded_path = gdown.download(url, output=temp_path, quiet=False, fuzzy=True, use_cookies=False)
            
            # Try to rename using PDF metadata title if available
            renamed = False
            try:
                reader = PdfReader(downloaded_path)
                if reader.metadata and reader.metadata.title:
                    clean_title = clean_filename(reader.metadata.title)
                    if clean_title and len(clean_title) > 5: # Basic validity check
                        if not clean_title.lower().endswith(".pdf"): clean_title += ".pdf"
                        
                        new_path = os.path.join(output_dir, clean_title)
                        if new_path != downloaded_path:
                            # Handle collision
                            if os.path.exists(new_path):
                                 base, ext = os.path.splitext(clean_title)
                                 clean_title = f"{base}_{file_id[:8]}{ext}"
                                 new_path = os.path.join(output_dir, clean_title)
                            
                            os.rename(downloaded_path, new_path)
                            print(f"[INFO] Renamed (Metadata) {temp_name} -> {clean_title}")
                            downloaded_path = new_path
                            renamed = True
            except Exception as e:
                print(f"[WARN] Failed to rename based on metadata: {e}")

            # If metadata rename failed, try to get name from Drive page title
            if not renamed:
                try:
                    print(f"[INFO] Fetching Drive page title for {url}...")
                    page_resp = requests.get(url, timeout=10)
                    if page_resp.status_code == 200:
                        # Regex for <title>Filename - Google Drive</title>
                        # content="Basic Clinical Pharmacology, 14th Edition (Bertram G. Katzung) (z-lib.org).pdf - Google Drive"
                        # or <title>...
                        title_match = re.search(r'<title>(.*?) - Google Drive</title>', page_resp.text)
                        if title_match:
                            raw_name = title_match.group(1)
                            clean_name = clean_filename(raw_name)
                            if clean_name:
                                if not clean_name.lower().endswith(".pdf"): clean_name += ".pdf"
                                new_path = os.path.join(output_dir, clean_name)
                                
                                # Handle collision
                                if os.path.exists(new_path):
                                     base, ext = os.path.splitext(clean_name)
                                     clean_name = f"{base}_{file_id[:8]}{ext}"
                                     new_path = os.path.join(output_dir, clean_name)
                                
                                os.rename(downloaded_path, new_path)
                                print(f"[INFO] Renamed (Page Title) {temp_name} -> {clean_name}")
                                downloaded_path = new_path
                except Exception as ex:
                    print(f"[WARN] Failed to rename based on Drive page: {ex}")
            
            return os.path.abspath(downloaded_path)

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
