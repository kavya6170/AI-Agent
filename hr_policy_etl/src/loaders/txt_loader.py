import os

def load_txt(file_path: str, encoding: str = 'utf-8') -> str:
    """
    Load raw text from a .txt file.

    Args:
        file_path (str): The absolute path to the text file.
        encoding (str): Text encoding. Defaults to 'utf-8'.

    Returns:
        str: The raw content of the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a valid text file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    if not file_path.lower().endswith('.txt'):
        raise ValueError(f"Invalid file extension for TXT loader: {file_path}")

    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read().strip()
    except UnicodeDecodeError:
        # Fallback to latin-1 if utf-8 fails
        with open(file_path, 'r', encoding='latin-1') as f:
            return f.read().strip()
