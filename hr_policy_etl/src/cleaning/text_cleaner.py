import re

def clean_text(text: str) -> str:
    """
    Orchestrate the text cleaning process.
    
    Args:
        text (str): Raw extracted text.
        
    Returns:
        str: Cleaned text.
    """
    if not text:
        return ""
        
    text = normalize_whitespace(text)
    text = remove_noise_lines(text)
    text = normalize_characters(text)
    
    return text.strip()

def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace while preserving paragraph boundaries.
    1. Replace non-breaking spaces with normal spaces.
    2. Normalize line breaks (Windows/Mac to Unix).
    3. Collapse multiple spaces into one.
    4. Collapse >2 newlines into 2 (paragraph breaks).
    """
    # Replace non-breaking space
    text = text.replace('\xa0', ' ')
    
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Collapse multiple internal spaces mostly for single-line cleanliness,
    # but be careful not to merge words across line breaks prematurely.
    # Strategy: Split by line, clean each line, join back.
    
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.split('\n')]
    
    # Re-join with newlines
    text = '\n'.join(lines)
    
    # Collapse multiple newlines (paragraph boundaries)
    # 3 or more newlines become 2 (standard paragraph break)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text

def remove_noise_lines(text: str) -> str:
    """
    Remove headers, footers, page numbers, and likely garbage lines.
    Strategy: Filter out lines that match specific patterns.
    """
    lines = text.split('\n')
    cleaned_lines = []
    
    # Regex patterns for common noise
    # Page X of Y, Page X, just numbers
    page_patterns = [
        r'^\s*page\s+\d+\s*$', 
        r'^\s*page\s+\d+\s+of\s+\d+\s*$',
        r'^\s*\d+\s*$'
    ]
    
    for line in lines:
        is_noise = False
        
        # Check against patterns
        for pattern in page_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                is_noise = True
                break
        
        # Skip very short lines that might be noise/artifacts (heuristic)
        # But keep them if they might be bullet points or short headings? 
        # Requirement says "Clean doc extraction", so be conservative.
        # We'll stick to strict pattern matching for now to avoid data loss.
        
        if not is_noise:
            cleaned_lines.append(line)
            
    return '\n'.join(cleaned_lines)

def normalize_characters(text: str) -> str:
    """
    Normalize quotes, dashes, and bullet points.
    """
    # Smart quotes removal
    text = text.replace('“', '"').replace('”', '"').replace("‘", "'").replace("’", "'")
    
    # Common bullet points to standard dash
    text = text.replace('•', '-').replace('●', '-')
    
    return text
