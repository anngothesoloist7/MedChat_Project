import os
import sys
import time
from dotenv import load_dotenv
from mistralai import Mistral, DocumentURLChunk

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

import base64
import io
import json
from PIL import Image
from mistralai import TextChunk, ImageURLChunk

def generate_image_description(image_base64: str, client) -> dict:
    """
    Generate a detailed description of an image using Mistral.
    """
    try:
        # Decode the base64 image to get dimensions
        # Check if the base64 string has a data URI prefix (e.g., "data:image/jpeg;base64,")
        if "base64," in image_base64:
            image_base64 = image_base64.split("base64,")[1]
            
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))
        width, height = image.size

        # Create a prompt text
        prompt_text = "Describe this image in detail. Include what type of image it is (chart, graph, photograph, diagram, etc.), what it depicts, and any key elements. Also provide structured metadata about the image content."

        # Generate a description using Mistral
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[
                {
                    "role": "user",
                    "content": [
                        TextChunk(text=prompt_text),
                        ImageURLChunk(image_url=f"data:image/png;base64,{image_base64}")
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        content = response.choices[0].message.content
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            # Fallback if JSON is malformed but contains dict-like string
            print(f"[WARN] Malformed JSON from vision model: {content[:50]}...")
            return {
                "description": content[:200] + "...",
                "metadata": {"type": "Unknown", "dimensions": f"{width}x{height}"}
            }

        # Ensure metadata exists
        if "metadata" not in result:
            result["metadata"] = {}
        if "dimensions" not in result["metadata"]:
            result["metadata"]["dimensions"] = f"{width}x{height}"
            
        return result

    except Exception as e:
        print(f"[ERROR] generating image description: {e}")
        return {
            "description": "Image description unavailable due to error.",
            "metadata": {"error": str(e)}
        }

def test_mistral_ocr_full():
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        print("Error: MISTRAL_API_KEY not found in environment variables.")
        return

    # Path to the real splitted data
    pdf_path = os.path.join(
        os.getcwd(), 
        "database", 
        "splitted", 
        "Basic  Clinical Pharmacology, 14th Edition (Bertram G. Katzung) (z-lib.org)(1-800).pdf"
    )

    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        return

    print(f"Starting OCR parsing for: {pdf_path}")
    print("Using direct MistralAI client to ensure all pages are processed...")

    try:
        client = Mistral(api_key=api_key)

        # 1. Upload File
        print("Uploading file to Mistral...")
        with open(pdf_path, "rb") as f:
            uploaded_file = client.files.upload(
                file={"file_name": os.path.basename(pdf_path), "content": f}, 
                purpose="ocr"
            )
        file_id = uploaded_file.id
        print(f"File uploaded. ID: {file_id}")

        # 2. Get Signed URL
        signed_url = client.files.get_signed_url(file_id=file_id).url

        # 3. Process with OCR
        print("Sending OCR request (this may take time for 800 pages)...")
        start_time = time.time()
        
        ocr_response = client.ocr.process(
            document=DocumentURLChunk(document_url=signed_url),
            model="mistral-ocr-latest",
            include_image_base64=True
        )
        
        duration = time.time() - start_time
        print(f"OCR request completed in {duration:.2f} seconds.")

        # 4. Construct Output
        print(f"Processing {len(ocr_response.pages)} pages from response...")
        
        full_markdown_parts = []
        json_pages = []
        
        # Limit image processing for testing to avoid huge costs/time? 
        # The user asked for "real splitted data", so we should probably try to do it, 
        # but maybe warn or only do it for a subset if it's too many.
        # For now, I will process ALL images as requested, but print progress.
        
        total_images = sum(len(p.images) for p in ocr_response.pages)
        print(f"Found {total_images} images across the document. Generating descriptions...")
        
        image_count = 0
        
        for i, page in enumerate(ocr_response.pages):
            md = page.markdown
            
            # Process images in this page
            for img in page.images:
                image_count += 1
                print(f"Processing image {image_count}/{total_images}...")
                
                desc_data = generate_image_description(img.image_base64, client)
                
                # Format the replacement string
                description = desc_data.get("description", "No description")
                replacement = f"![{description}]({img.id})\n"
                replacement += f"*Image Description: {description}*\n\n"
                
                if "metadata" in desc_data and desc_data["metadata"]:
                    replacement += "**Image Metadata:**\n"
                    for k, v in desc_data["metadata"].items():
                        replacement += f"- {k}: {v}\n"
                    replacement += "\n"
                
                # Replace the placeholder in markdown
                # The placeholder is usually ![id](id)
                md = md.replace(f"![{img.id}]({img.id})", replacement)

            full_markdown_parts.append(md)
            
            # JSON Output Structure
            json_pages.append({
                "page": i + 1,
                "content": md,
                "images": [img.id for img in page.images] 
            })

            if (i + 1) % 10 == 0:
                print(f"Processed {i + 1} pages...")

        full_markdown = "\n\n".join(full_markdown_parts)

        # 5. Save Markdown Output
        output_md_path = os.path.join(os.path.dirname(__file__), "mistral_ocr_output.md")
        with open(output_md_path, "w", encoding="utf-8") as f:
            f.write(full_markdown)
        
        # 6. Save JSON Output
        output_json_path = os.path.join(os.path.dirname(__file__), "mistral_ocr_output.json")
        import json
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(json_pages, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully parsed PDF.")
        print(f"Markdown saved to: {output_md_path}")
        print(f"JSON saved to: {output_json_path}")
        print(f"Total content length: {len(full_markdown)} characters")
        
        # Cleanup
        try:
            client.files.delete(file_id=file_id)
            print("Temporary file deleted from Mistral.")
        except Exception as cleanup_err:
            print(f"Warning: Failed to delete file {file_id}: {cleanup_err}")

    except Exception as e:
        print(f"An error occurred during OCR parsing: {e}")

if __name__ == "__main__":
    test_mistral_ocr_full()
