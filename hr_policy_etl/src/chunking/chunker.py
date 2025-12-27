import re
from typing import List

def chunk_text(
    text: str, 
    target_encoding_words: int = 500, 
    overlap_words: int = 50
) -> List[str]:
    """
    Chunk text by paragraphs, preserving structure.

    Args:
        text (str): Cleaned input text.
        target_encoding_words (int): Target word count per chunk.
        overlap_words (int): Overlap in words between chunks.

    Returns:
        List[str]: List of text chunks with paragraphs separated by double newlines.
    """
    if not text:
        return []

    # 1. Normalize and split into paragraphs
    original_paragraphs = [p for p in text.split('\n\n') if p.strip()]
    
    chunks = []
    current_chunk_paragraphs = []
    current_word_count = 0
    
    for paragraph in original_paragraphs:
        words_in_para = len(paragraph.split())
        
        # Check if adding this paragraph exceeds limit
        if current_word_count + words_in_para > target_encoding_words:
            
            # Scenario A: Current buffer has content.
            # If so, finalize it first, UNLESS the new paragraph fits better by itself 
            # (simple greedy approach: finalize current if full).
            
            if current_chunk_paragraphs:
                # 1. Finalize current chunk
                chunk_str = "\n\n".join(current_chunk_paragraphs)
                chunks.append(chunk_str)
                
                # 2. Prepare overlap for next chunk
                overlap_text = _get_tail_overlap(chunk_str, overlap_words)
                current_chunk_paragraphs = []
                current_word_count = 0
                
                if overlap_text:
                    current_chunk_paragraphs.append(overlap_text)
                    current_word_count += len(overlap_text.split())
            
            # Scenario B: The paragraph ITSELF is huge (> target)
            if words_in_para > target_encoding_words:
                # We must split this giant paragraph
                sub_chunks = _split_large_paragraph(paragraph, target_encoding_words, overlap_words)
                
                # If we have overlap buffer from previous chunk, prepend it to the first sub-chunk?
                # Simplify: Just append the overlap buffer to the first sub-chunk's text.
                if current_chunk_paragraphs:
                    # Merge overlap into first sub-chunk
                    sub_chunks[0] = current_chunk_paragraphs[0] + " " + sub_chunks[0]
                    current_chunk_paragraphs = []
                
                # Add all sub-chunks except potentially the last one 
                # (which we might want to keep open if it's small, but simpler to just finalize them all)
                # Let's finalize all but the last one to use as the base for next.
                
                # Actually, simpler: just add them all as chunks.
                # And set overlap from the LAST sub-chunk as the start of the next cycle.
                
                for i, sub in enumerate(sub_chunks):
                    if i == len(sub_chunks) - 1:
                        # This is the last piece of the giant paragraph.
                        # We use it as the start of the new buffer.
                        # Wait, is it a full chunk?
                        # _split_large_paragraph returns chunks of ~target size.
                        # So we should probably finalize it too, and take overlap from it.
                        chunks.append(sub)
                        overlap_text = _get_tail_overlap(sub, overlap_words)
                        if overlap_text:
                            current_chunk_paragraphs.append(overlap_text)
                            current_word_count = len(overlap_text.split())
                        else:
                            current_word_count = 0
                    else:
                        chunks.append(sub)
                
            else:
                # Paragraph fits in a new chunk (since we cleared buffer)
                current_chunk_paragraphs.append(paragraph)
                current_word_count += words_in_para
                
        else:
            # Paragraph fits in current chunk
            current_chunk_paragraphs.append(paragraph)
            current_word_count += words_in_para

    # Final flush
    if current_chunk_paragraphs:
        chunks.append("\n\n".join(current_chunk_paragraphs))

    return chunks

def _split_large_paragraph(text: str, target: int, overlap: int) -> List[str]:
    """
    Split a single large paragraph into multiple chunks based on sentences.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    sub_chunks = []
    current_sents = []
    current_count = 0
    
    for i, sent in enumerate(sentences):
        s_len = len(sent.split())
        
        if current_count + s_len > target:
            if current_sents:
                # Finalize sub-chunk
                chunk_str = " ".join(current_sents)
                sub_chunks.append(chunk_str)
                
                # Calculate overlap for next sub-chunk
                ov_text = _get_tail_overlap(chunk_str, overlap)
                current_sents = [ov_text] if ov_text else []
                current_count = len(ov_text.split()) if ov_text else 0
                
        current_sents.append(sent)
        current_count += s_len
        
    if current_sents:
        sub_chunks.append(" ".join(current_sents))
        
    return sub_chunks

def _get_tail_overlap(text: str, overlap_words: int) -> str:
    """
    Get the last N words from text, strictly limiting by word count.
    """
    if not text:
        return ""
    
    words = text.split()
    if len(words) <= overlap_words:
        return text
        
    return " ".join(words[-overlap_words:])
