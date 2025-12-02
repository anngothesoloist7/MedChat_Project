import os
import sys

# Add project root to path BEFORE importing modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.utils.file_utils import resolve_pdf_path

def test_file_utils():
    # Test cases
    test_cases = [
        # 1. Local File (Assuming one exists, e.g., in database/splitted)
        # You might need to adjust this path to a real file for the test to pass
        os.path.join(os.getcwd(), "database", "splitted", "Basic  Clinical Pharmacology, 14th Edition (Bertram G. Katzung) (z-lib.org)(1-800).pdf"),
        
        # 2. Direct PDF URL (Example)
        "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        
        # 3. Google Drive Link (Public) - Replace with a real public link if you have one
        # "https://drive.google.com/file/d/YOUR_FILE_ID/view?usp=sharing" 
    ]

    print("Testing resolve_pdf_path...")

    for path in test_cases:
        print(f"\nProcessing: {path}")
        try:
            if not os.path.exists(path) and not path.startswith("http"):
                 print(f"[SKIP] Local file does not exist: {path}")
                 continue

            resolved_path = resolve_pdf_path(path, download_dir="test_downloads")
            print(f"[SUCCESS] Resolved to: {resolved_path}")
            
            # Verify file exists
            if os.path.exists(resolved_path):
                print(f"File exists. Size: {os.path.getsize(resolved_path)} bytes")
            else:
                print("[ERROR] Resolved path does not exist!")

        except Exception as e:
            print(f"[ERROR] Failed: {e}")

if __name__ == "__main__":
    # Add project root to path
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    test_file_utils()
