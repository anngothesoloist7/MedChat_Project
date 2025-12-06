import json
from pathlib import Path

p = Path('/Users/VinUni Data Science/IntroToDataScience/Output_VN_Book_splitting/metadata.json')
obj = json.loads(p.read_text())

source = "Bệnh học nội khoa tập 1 YHN - Testyhoc.vn .pdf"

update = {
    "book_title": "Bệnh học Nội khoa - Tập 1",
    "edition": "4th Edition (ĐH Y Hà Nội)",
    "publish_year": "2020",
    "authors": [
        "GS.TS. Ngô Quý Châu (Chủ biên)",
        "Bộ môn Nội Tổng hợp - Đại học Y Hà Nội"
    ],
    "language": "Vietnamese",
    "specialty": "Internal Medicine",
    "document_type": "textbook"
}
count = 0
for item in obj:
    if item.get('source_file') == source or (isinstance(item.get('file_id'), str) and 'Harrisons Principles of Internal Medicine' in item.get('file_id')):
        # apply updates
        item.update(update)
        # ensure authors is exactly the list
        item['authors'] = update['authors']
        count += 1

p.write_text(json.dumps(obj, ensure_ascii=False, indent=4))
print(f'Updated {count} entries')
