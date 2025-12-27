import os
import pypdf
import pytesseract
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image

# Minimum text length per page to consider it "digital" rather than scanned
SCANNED_THRESHOLD_CHARS = 50

def load_pdf(file_path: str, ocr_fallback: bool = True) -> str:
    """
    Load raw text from a PDF file, using OCR as a fallback if scraping fails.

    Args:
        file_path (str): Absolute path to the PDF.
        ocr_fallback (bool): Whether to use OCR if direct extraction yields little text.

    Returns:
        str: extracted text.
    
    Raises:
        FileNotFoundError: If file not found.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    text_parts = []
    
    try:
        reader = pypdf.PdfReader(file_path)
        
        # Lightweight global check (optional optimization could go here, 
        # but simplistic per-page logic is safer for mixed documents).
        
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            
            if _needs_ocr(page_text) and ocr_fallback:
                # Perform OCR on this specific page
                try:
                    images = convert_from_path(
                        file_path, 
                        first_page=i+1, 
                        last_page=i+1,
                        dpi=300
                    )
                    if images:
                        ocr_text = pytesseract.image_to_string(images[0])
                        page_text = ocr_text
                except Exception as ocr_err:
                    # Log or silence OCR failure, fall back to whatever (empty) text we had or a placeholder
                    # For now we silence it to avoid crashing the whole pipeline on missing Poppler
                    # But in a real pipeline we might want to log this.
                    # Retaining original empty/scanty text is better than crashing.
                    pass
            
            if page_text:
                text_parts.append(page_text)
                
    except Exception as e:
        raise RuntimeError(f"Error processing PDF {file_path}: {str(e)}")

    return "\n".join(text_parts)

def _needs_ocr(text: str) -> bool:
    """
    Determine if a page text result implies a scanned page.
    Criteria: Empty or very few characters.
    """
    if not text:
        return True
    
    clean_text = text.strip()
    if len(clean_text) < SCANNED_THRESHOLD_CHARS:
        return True
        
    return False
