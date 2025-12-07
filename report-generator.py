# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "markdown",
#     "xhtml2pdf",
# ]
# ///

import argparse
import sys
import markdown
from xhtml2pdf import pisa

def convert_md_to_pdf(input_file, output_file):
    try:
        # Read the markdown file
        with open(input_file, 'r', encoding='utf-8') as f:
            text = f.read()

        # Convert markdown to HTML
        # 'extra' extension includes tables, fenced code blocks, etc.
        html_body = markdown.markdown(text, extensions=['extra', 'codehilite', 'toc'])

        # Create a complete HTML document with some basic styling
        html_doc = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Report</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    font-size: 11pt;
                    line-height: 1.6;
                    margin: 20px;
                    color: #333;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    color: #2c3e50;
                    margin-top: 1.5em;
                    margin-bottom: 0.5em;
                }}
                h1 {{ font-size: 24pt; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
                h2 {{ font-size: 18pt; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
                h3 {{ font-size: 14pt; }}
                
                code {{
                    background-color: #f5f5f5;
                    padding: 2px 5px;
                    border-radius: 3px;
                    font-family: Consolas, monospace;
                    font-size: 0.9em;
                }}
                pre {{
                    background-color: #f8f8f8;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    padding: 15px;
                    overflow-x: auto;
                }}
                pre code {{
                    background-color: transparent;
                    padding: 0;
                }}
                
                blockquote {{
                    border-left: 4px solid #ddd;
                    margin: 0;
                    padding-left: 15px;
                    color: #777;
                }}
                
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 20px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 10px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                    font-weight: bold;
                }}
                tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                
                img {{
                    max-width: 100%;
                    height: auto;
                }}
                
                a {{
                    color: #3498db;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            {html_body}
        </body>
        </html>
        """

        # Generate PDF
        print(f"Generating PDF: {output_file}...")
        
        with open(output_file, "w+b") as result_file:
            pisa_status = pisa.CreatePDF(
                html_doc,                # the HTML to convert
                dest=result_file         # file handle to receive result
            )

        if pisa_status.err:
            print(f"Error generating PDF: {pisa_status.err}", file=sys.stderr)
            sys.exit(1)
            
        print("Done!")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Convert Markdown file to PDF')
    parser.add_argument('input_file', help='Path to the input Markdown file')
    parser.add_argument('output_file', help='Path to the output PDF file (e.g., report.pdf)')
    
    args = parser.parse_args()
    
    convert_md_to_pdf(args.input_file, args.output_file)

if __name__ == '__main__':
    main()
