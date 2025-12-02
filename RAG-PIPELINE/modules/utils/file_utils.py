import os
import re
import requests
import gdown
from urllib.parse import urlparse, unquote

def is_url(path: str) -> bool:
    """Check if the path is a valid URL."""
    try:
        result = urlparse(path)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def get_filename_from_cd(cd):
    """Get filename from content-disposition header."""
    if not cd:
        return None
    fname = re.findall('filename=(.+)', cd)
    if len(fname) == 0:
        return None
    return fname[0].strip().strip('"')

def shorten_filename(filename: str, file_id: str = "0000", max_length: int = 100) -> str:
    """
    Consistently shorten filename using intelligent algorithm.
    """
    # Remove "Bản sao của " prefix
    if filename.startswith("Bản sao của "):
        filename = filename[12:]
    
    # Remove invalid characters first
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    
    name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
    ext = '.pdf' # Force PDF extension as we expect PDFs
    
    # Split by common delimiters
    parts = name_without_ext.replace(' -- ', '|').split('|')
    
    if len(parts) > 0:
        title = parts[0].strip()
        
        # Extract year (4 digits)
        year = None
        for part in parts:
            for word in part.strip().split():
                clean_word = word.strip('(),')
                if len(clean_word) == 4 and clean_word.isdigit():
                    year = clean_word
                    break
            if year:
                break
        
        # Extract edition number
        edition = None
        for part in parts:
            part_lower = part.lower().strip()
            if any(word.rstrip('stndrh,').isdigit() for word in part.split()):
                for word in part.split():
                    if word.rstrip('stndrh,').isdigit():
                        edition = word.rstrip('stndrh,')
                        break
            elif 'edition' in part_lower:
                if 'twentieth' in part_lower:
                    edition = '20th'
                elif 'eleventh' in part_lower:
                    edition = '11th'
                elif 'fourteenth' in part_lower:
                    edition = '14th'
                elif 'thirteenth' in part_lower:
                    edition = '13th'
            if edition:
                break
        
        # Build shortened name
        short_parts = [title[:60].rsplit(' ', 1)[0] if len(title) > 60 else title]
        if edition:
            short_parts.append(f"{edition}ed")
        if year:
            short_parts.append(year)
        
        base_short_name = ' '.join(short_parts)
        
        # Always append short hash for uniqueness (last 4 chars of file_id)
        short_hash = file_id[-4:]
        suffix = f" {short_hash}"
        
        # Calculate available length for base name
        # max_length - ext - suffix
        available_length = max_length - len(ext) - len(suffix)
        
        if len(base_short_name) > available_length:
            base_short_name = base_short_name[:available_length].rsplit(' ', 1)[0]
        
        return f"{base_short_name}{suffix}{ext}"
    
    # Fallback if parsing fails
    return f"{file_id}{ext}"

def download_file(url: str, output_dir: str = "downloads") -> str:
    """
    Download a file from a URL (direct link or Google Drive).
    
    Args:
        url: The URL to download from.
        output_dir: The directory to save the downloaded file.
        
    Returns:
        The absolute path to the downloaded file.
        
    Raises:
        Exception: If download fails or Google Drive file is not accessible.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Handle Google Drive Links
    if "drive.google.com" in url:
        print(f"[INFO] Detected Google Drive URL: {url}")
        try:
            # gdown handles the extraction of file ID and download
            # fuzzy=True helps with extracting ID from various URL formats
            output_path = gdown.download(url, output=None, quiet=False, fuzzy=True, use_cookies=False)
            
            if not output_path:
                 raise Exception("gdown failed to download. File might be private or invalid.")
            
            # Sanitize and move
            original_filename = os.path.basename(output_path)
            # Use file ID from URL if possible, or random hash
            import hashlib
            file_id = hashlib.md5(url.encode()).hexdigest()[:8]
            
            filename = shorten_filename(original_filename, file_id=file_id)
            final_path = os.path.join(output_dir, filename)
            
            # If gdown downloaded to a different name/location, move it
            if os.path.abspath(output_path) != os.path.abspath(final_path):
                # If target exists, maybe we should overwrite or skip? 
                # For now, overwrite
                if os.path.exists(final_path):
                    os.remove(final_path)
                os.rename(output_path, final_path)
                
            return os.path.abspath(final_path)
            
        except Exception as e:
            error_msg = str(e)
            if "Permission denied" in error_msg or "Access denied" in error_msg:
                raise Exception(f"Cannot access Google Drive file. Please ensure 'Anyone with the link' has 'Viewer' access. Error: {e}")
            raise Exception(f"Failed to download from Google Drive: {e}")

    # 2. Handle Direct URLs
    else:
        print(f"[INFO] Downloading from URL: {url}")
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Try to get filename from header
            filename = get_filename_from_cd(response.headers.get('content-disposition'))
            
            # Fallback to URL path
            if not filename:
                parsed_url = urlparse(url)
                filename = os.path.basename(unquote(parsed_url.path))
            
            # Fallback if still empty
            if not filename:
                filename = "downloaded_file.pdf"
                
            # Sanitize
            import hashlib
            file_id = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = shorten_filename(filename, file_id=file_id)
            
            final_path = os.path.join(output_dir, filename)
            
            with open(final_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
            return os.path.abspath(final_path)
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to download file from URL: {e}")

def list_google_drive_folder(url: str) -> list[dict]:
    """
    List files in a Google Drive folder without downloading them.
    Returns a list of dicts: {'name': str, 'url': str}
    """
    print(f"[INFO] Listing Google Drive folder: {url}")
    captured_files = []
    
    # Mock function to replace download
    def mock_download(url, output, quiet=False, fuzzy=False, use_cookies=False, **kwargs):
        import os
        filename = os.path.basename(output) if output else "Unknown"
        captured_files.append({'name': filename, 'url': url})
        return output

    try:
        import gdown.download_folder
        
        # Save original
        original_download = gdown.download_folder.download
        
        # Monkey-patch the one used inside download_folder
        gdown.download_folder.download = mock_download
        
        # Create dummy dir to satisfy any existence checks
        import shutil
        dummy_dir = "dummy_list_dir"
        if os.path.exists(dummy_dir):
            shutil.rmtree(dummy_dir)
        os.makedirs(dummy_dir, exist_ok=True)
        
        # Call download_folder
        gdown.download_folder.download_folder(url, output=dummy_dir, quiet=True, use_cookies=False)
        
        # Filter for PDFs
        pdf_files = [f for f in captured_files if f['name'].lower().endswith('.pdf')]
        
        # Remove duplicates
        unique_files = []
        seen_urls = set()
        for f in pdf_files:
            if f['url'] not in seen_urls:
                unique_files.append(f)
                seen_urls.add(f['url'])
                
        return unique_files

    except Exception as e:
        print(f"[ERROR] Failed to list GDrive folder: {e}")
        return []
    finally:
        # Restore original
        if 'gdown.download_folder' in locals() and 'original_download' in locals():
            gdown.download_folder.download = original_download
        
        # Cleanup dummy dir
        if os.path.exists("dummy_list_dir"):
            try: shutil.rmtree("dummy_list_dir")
            except: pass

def download_google_drive_file(file_url: str, output_dir: str) -> str:
    """Downloads a single file from GDrive."""
    return download_file(file_url, output_dir)

def resolve_pdf_path(input_path: str, download_dir: str = "RAG-PIPELINE/database/raw") -> str:
    """
    Resolve the PDF path. If it's a URL, download it. If it's a local path, verify it exists.
    
    Args:
        input_path: Local path or URL.
        download_dir: Directory to save downloaded files.
        
    Returns:
        Absolute path to the PDF file.
    """
    # Check if it's a URL
    if is_url(input_path):
        # Ensure download dir is absolute
        if not os.path.isabs(download_dir):
            download_dir = os.path.join(os.getcwd(), download_dir)
            
        print(f"[INFO] Input is a URL. Attempting to download to {download_dir}...")
        return download_file(input_path, download_dir)
    
    # Handle Local Path
    else:
        # Expand user (~) and resolve absolute path
        local_path = os.path.abspath(os.path.expanduser(input_path))
        
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")
            
        if not os.path.isfile(local_path):
             raise IsADirectoryError(f"Path is a directory, not a file: {local_path}")
             
        return local_path
