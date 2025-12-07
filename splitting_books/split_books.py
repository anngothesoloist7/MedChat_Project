import os
import fitz  # Đây là thư viện PyMuPDF
import json

# --- CẤU HÌNH ---
INPUT_FOLDER = "/Users/VinUni Data Science/IntroToDataScience/VNMedBooks"      # Thư mục chứa sách gốc
OUTPUT_FOLDER = "/Users/VinUni Data Science/IntroToDataScience/Output_VN_Book_splitting"   # Thư mục chứa sách đã cắt
PAGES_PER_FILE = 50             # Số trang mỗi file con

def split_pdfs():
    # Tạo thư mục output nếu chưa có
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    metadata_list = [] # Danh sách để lưu metadata tổng

    # Quét tất cả file PDF trong thư mục input
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith('.pdf')]
    
    print(f"Tìm thấy {len(files)} file sách. Bắt đầu xử lý...")

    for filename in files:
        file_path = os.path.join(INPUT_FOLDER, filename)
        doc = fitz.open(file_path) # Mở file sách
        total_pages = len(doc)
        book_name_clean = os.path.splitext(filename)[0] # Tên file không đuôi .pdf

        print(f"--> Đang cắt sách: {filename} ({total_pages} trang)")

        # Vòng lặp cắt file
        part_number = 1
        for start_page in range(0, total_pages, PAGES_PER_FILE):
            end_page = min(start_page + PAGES_PER_FILE, total_pages)
            
            # Tạo file PDF mới
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=start_page, to_page=end_page - 1)
            
            # Đặt tên file con: vidu_part_01.pdf
            new_filename = f"{book_name_clean}_part_{part_number:03d}.pdf"
            output_path = os.path.join(OUTPUT_FOLDER, new_filename)
            
            new_doc.save(output_path)
            new_doc.close()

            # Tự động tạo khung Metadata cho file này
            meta_entry = {
                # --- Định danh File (Tự động) ---
                "file_id": new_filename,          # Ví dụ: harrison_p01.pdf
                "source_file": filename,          # File gốc
                "part_number": part_number,
                "page_start": start_page + 1,
                "page_end": end_page,

                # --- Thông tin Sách (Điền 1 lần rồi copy cho các file cùng sách) ---
                "book_title": "",                 # VD: Harrison's Principles of Internal Medicine
                "edition": "",                    # VD: 21st Edition
                "publish_year": "",             # VD: 2022 (Dạng số nguyên để lọc > <)
                "authors": [],                    # VD: ["Loscalzo", "Fauci"] (Dạng List)
                "language": "Vietnamese",
                
                # --- Thông tin Ngữ cảnh (Quan trọng cho Hybrid Search) ---
                "specialty": "",                  # VD: Cardiology (Thay cho Subject/Category - dùng từ chuyên môn hơn)
                "document_type": "textbook",      # Để sau này mở rộng thêm "clinical_guideline", "paper"...
            }
            metadata_list.append(meta_entry)
            
            part_number += 1

        doc.close()

    # Lưu file metadata.json tổng vào cùng thư mục output
    metadata_path = os.path.join(OUTPUT_FOLDER, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata_list, f, ensure_ascii=False, indent=4)

    print(f"\nĐã xong! Kiểm tra folder '{OUTPUT_FOLDER}'.")
    print(f"Đã tạo file danh sách '{metadata_path}'.")

if __name__ == "__main__":
    split_pdfs()