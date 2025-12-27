"""
HR Policy ETL Pipeline (Single File Version)
============================================
A simplified, standalone script for ingesting HR documents,
cleaning text, creating semantic chunks, and generating metadata.

Supported formats: .pdf, .docx, .txt
Capabilities:
- OCR fallback for scanned PDFs (requires tesseract and poppler)
- Paragraph-aware semantic chunking
- JSON output generation

Usage:
    python hr_policy_etl_single_file.py <path_to_document>
"""

import os
import sys
import re
import json
import uuid
import logging
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Optional

# Attempt to import required libraries
try:
    import pypdf
    from pdf2image import convert_from_path
    import pytesseract
    from docx import Document
except ImportError as e:
    print(f"CRITICAL: Missing dependency: {e}")
    print("Please install: pip install pypdf pdf2image pytesseract python-docx")
    sys.exit(1)

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
OUTPUT_DIR = "output_chunks"
MIN_CHUNK_SIZE = 50  # Minimum characters to keep a chunk
OCR_THRESHOLD_CHARS = 100  # If PDF extracts less than this, try OCR
MAX_CHUNK_WORDS = 500  # Max words per chunk before forced split
OVERLAP_WORDS = 50  # Words to overlap when splitting by size

def ensure_directories():
    """Ensure output directory exists."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def clean_text(text: str) -> str:
    """
    Normalize text: remove excessive whitespace, fix unicode, etc.
    """
    if not text:
        return ""
    
    # Replace non-breaking spaces and other common issues
    text = text.replace('\xa0', ' ').replace('\r', '\n')
    
    # Collapse multiple newlines to max 2 (preserve paragraph structure)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Collapse excessive spaces to single space
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Strip leading/trailing whitespace
    return text.strip()

def extract_from_pdf(file_path: str) -> str:
    """
    Extract text from PDF. Falls back to OCR if standard extraction yields little text.
    """
    logger.info(f"Processing PDF: {file_path}")
    text_content = []
    
    try:
        # Method 1: Standard Extraction
        with open(file_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
        
        full_text = "\n".join(text_content)
        
        # Method 2: Fallback to OCR if text is suspicious/scanned
        if len(full_text.strip()) < OCR_THRESHOLD_CHARS:
            logger.warning("Low text yield using standard extractor. Falling back to OCR (slow)...")
            try:
                images = convert_from_path(file_path)
                ocr_text = []
                for i, image in enumerate(images):
                    logger.info(f"OCRing page {i+1}/{len(images)}...")
                    page_str = pytesseract.image_to_string(image)
                    ocr_text.append(page_str)
                full_text = "\n".join(ocr_text)
            except Exception as ocr_err:
                logger.error(f"OCR Failed: {ocr_err}")
                logger.info("Returning whatever text was extracted standardly.")
                
        return full_text

    except Exception as e:
        logger.error(f"Error reading PDF: {e}")
        return ""

def extract_from_docx(file_path: str) -> str:
    """Extract text from DOCX using python-docx."""
    logger.info(f"Processing DOCX: {file_path}")
    try:
        doc = Document(file_path)
        # Join paragraphs with double newline to preserve structure
        text = "\n\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        return text
    except Exception as e:
        logger.error(f"Error reading DOCX: {e}")
        return ""

def extract_from_txt(file_path: str) -> str:
    """Extract text from TXT file."""
    logger.info(f"Processing TXT: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Fallback to latin-1 if utf-8 fails
        with open(file_path, 'r', encoding='latin-1') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading TXT: {e}")
        return ""

def ingest_document(file_path: str) -> str:
    """Dispatcher for document ingestion based on extension."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        return extract_from_pdf(file_path)
    elif ext == '.docx':
        return extract_from_docx(file_path)
    elif ext == '.txt':
        return extract_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

def semantic_chunking(text: str) -> List[str]:
    """
    Split text into semantic chunks based on paragraph structure.
    Enforces a MAX_CHUNK_WORDS limit with overlap to avoid monolithic chunks.
    """
    # Split by double newline (standard paragraph break)
    raw_paragraphs = text.split('\n\n')
    
    chunks = []
    current_chunk_words = []
    
    for para in raw_paragraphs:
        clean_para = para.strip()
        if not clean_para:
            continue
            
        para_words = clean_para.split()
        
        # If a single paragraph is huge (larger than MAX), we must split it internally
        while len(para_words) + len(current_chunk_words) > MAX_CHUNK_WORDS:
            # How much room is left in the current chunk?
            remaining_space = MAX_CHUNK_WORDS - len(current_chunk_words)
            
            # If we can fit the whole paragraph (we know we can't from while condition, 
            # but this handles the case where clean_chunk_words is empty and paragraph is HUGE)
            
            # Take what fits
            to_take = para_words[:remaining_space]
            
            # If current_chunk_words was empty and remaining_space is small/0? 
            # (Should rely on MAX_CHUNK_WORDS being > 0)
            
            # Add to current
            current_chunk_words.extend(to_take)
            
            # Finalize this full chunk
            chunks.append(" ".join(current_chunk_words))
            
            # Update para_words to be the rest
            para_words = para_words[remaining_space:]
            
            # Start new chunk with overlap from the JUST FINISHED chunk
            # The just finished chunk words are in the 'chunks' list string, or we can recover them.
            # Actually easier to keep a moving window.
            
            # Re-construct the tail for overlap
            # The tail is the last OVERLAP_WORDS of the chunk we just made
            previous_chunk_words = current_chunk_words
            overlap_start = max(0, len(previous_chunk_words) - OVERLAP_WORDS)
            current_chunk_words = previous_chunk_words[overlap_start:]
        
        # Add remaining paragraph words to current accumulation
        current_chunk_words.extend(para_words)

    # Append the last chunk
    if current_chunk_words:
        chunks.append(" ".join(current_chunk_words))
        
    return chunks

def generate_metadata(text_chunk: str, source_file: str, chunk_index: int) -> Dict:
    """Generate metadata for a specific chunk."""
    word_count = len(text_chunk.split())
    
    # Simple regex to try and find a Section Header (Capitalized words followed by newline?)
    # This is a basic heuristic
    possible_title = "Unknown"
    lines = text_chunk.split('\n')
    if lines and len(lines[0]) < 100 and lines[0][0].isupper():
        possible_title = lines[0].strip()

    metadata = {
        "chunk_id": str(uuid.uuid4()),
        "source_file": os.path.basename(source_file),
        "chunk_index": chunk_index,
        "word_count": word_count,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "inferred_title": possible_title,
        "char_count": len(text_chunk)
    }
    return metadata

def save_chunks(chunks: List[str], source_file: str):
    """Save processed chunks and metadata to JSON."""
    ensure_directories()
    
    base_name = os.path.splitext(os.path.basename(source_file))[0]
    output_data = []
    
    for i, chunk in enumerate(chunks):
        if len(chunk) < MIN_CHUNK_SIZE:
            continue
            
        meta = generate_metadata(chunk, source_file, i)
        
        # Create a unified record
        record = {
            "metadata": meta,
            "content": chunk
        }
        output_data.append(record)
    
    # Save as a single JSON array file for the document
    output_path = os.path.join(OUTPUT_DIR, f"{base_name}_processed.json")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Saved {len(output_data)} chunks to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="HR Policy ETL - Single File Processor")
    parser.add_argument("file_path", help="Path to the source document (PDF, DOCX, TXT)")
    
    args = parser.parse_args()
    
    logger.info("Starting ETL Pipeline...")
    
    try:
        # 1. Ingest
        raw_text = ingest_document(args.file_path)
        logger.info(f"Extracted {len(raw_text)} characters.")
        
        if not raw_text.strip():
            logger.warning("No text extracted. Exiting.")
            sys.exit(0)
            
        # 2. Clean
        cleaned_text = clean_text(raw_text)
        
        # 3. Chunk
        chunks = semantic_chunking(cleaned_text)
        logger.info(f"Generated {len(chunks)} semantic chunks.")
        
        # 4. Generate Metadata & Save
        save_chunks(chunks, args.file_path)
        
        logger.info("Pipeline completed successfully.")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
