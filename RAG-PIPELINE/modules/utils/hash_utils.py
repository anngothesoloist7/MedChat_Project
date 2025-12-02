import hashlib

def get_file_id(file_path: str) -> str:
    """
    Generate a SHA-256 hash for a file.
    
    Args:
        file_path: Path to the file.
        
    Returns:
        Hexadecimal digest of the SHA-256 hash.
    """
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(4096):
            hasher.update(chunk)
    return hasher.hexdigest()
