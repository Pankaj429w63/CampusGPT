import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.config import settings

class DocumentChunk:
    def __init__(self, text: str, metadata: Dict[str, Any]):
        self.text = text
        self.metadata = metadata

def clean_text(text: str) -> str:
    # Normalize excessive whitespaces and lines
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

HEADING_PATTERN = re.compile(
    r'^(?:'
    r'#+\s*(.+)|'  # Markdown heading: # Title
    r'(Department\s+of\s+[A-Za-z0-9&/,\- ()]+)|'  # Department of ...
    r'([0-9]+\.\s+[A-Z][A-Za-z0-9&/,\- ()]+(?::|\b))|'  # 1. Attendance Policy:
    r'(Faculty\s+Profile(?:\s+[A-Za-z0-9&/,\- ()]+)?)|'  # Faculty Profile ...
    r'(Curriculum\s+(?:Structure|Overview|Scheme))|'  # Curriculum Structure
    r'(Syllabus\s+for\s+[A-Za-z0-9&/,\- ()]+)|'  # Syllabus for ...
    r'([A-Z][A-Za-z0-9&/,\- ]{3,50}:)$'  # Title:
    r')',
    re.IGNORECASE
)

def extract_heading_from_line(line: str) -> Optional[str]:
    s = line.strip()
    if not s or len(s) > 100:
        return None
    m = HEADING_PATTERN.match(s)
    if m:
        h = m.group(0).strip()
        h = re.sub(r'^#+\s*', '', h).strip()
        return h
    return None

def split_text_into_chunks(
    text: str,
    chunk_size: int = settings.CHUNK_SIZE,
    chunk_overlap: int = settings.CHUNK_OVERLAP
) -> List[str]:
    text = clean_text(text)
    if not text:
        return []
    
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        
        # If we are not at the end of text, attempt to break at sentence or newline
        if end < len(text):
            break_pt = -1
            # Look for paragraph break
            p_break = text.rfind('\n\n', start + chunk_size // 2, end)
            if p_break != -1:
                break_pt = p_break + 2
            else:
                # Look for sentence break (. ! ?)
                for punct in ['. ', '.\n', '? ', '!\n']:
                    s_break = text.rfind(punct, start + chunk_size // 2, end)
                    if s_break != -1:
                        break_pt = max(break_pt, s_break + len(punct))
            
            if break_pt != -1:
                end = break_pt
            else:
                # Fallback: look for space
                sp_break = text.rfind(' ', start + chunk_size // 2, end)
                if sp_break != -1:
                    end = sp_break + 1

        chunk_str = text[start:end].strip()
        if chunk_str:
            chunks.append(chunk_str)
        
        # Advance with overlap
        start = max(start + 1, end - chunk_overlap)
        if end >= len(text):
            break
            
    return chunks

def load_pdf(file_path: Path) -> List[Dict[str, Any]]:
    import pypdf
    pages_data = []
    reader = pypdf.PdfReader(str(file_path))
    for idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages_data.append({
                "page": idx + 1,
                "text": text
            })
    return pages_data

def load_docx(file_path: Path) -> List[Dict[str, Any]]:
    import docx
    doc = docx.Document(str(file_path))
    full_text = []
    for para in doc.paragraphs:
        if para.text.strip():
            full_text.append(para.text)
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                full_text.append(row_text)
                
    content = "\n\n".join(full_text)
    if not content.strip():
        return []
    return [{"page": 1, "text": content}]

def load_txt_or_md(file_path: Path) -> List[Dict[str, Any]]:
    # Try utf-8 then fallback to latin-1
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = file_path.read_text(encoding="latin-1", errors="ignore")
        
    if not content.strip():
        return []
    return [{"page": 1, "text": content}]

def process_file_into_chunks(
    file_path: Path,
    base_dir: Optional[Path] = None,
    department: Optional[str] = None
) -> List[DocumentChunk]:
    ext = file_path.suffix.lower()
    raw_pages = []
    
    if ext == ".pdf":
        raw_pages = load_pdf(file_path)
    elif ext in [".docx", ".doc"]:
        raw_pages = load_docx(file_path)
    elif ext in [".txt", ".md", ".markdown"]:
        raw_pages = load_txt_or_md(file_path)
    else:
        return []
        
    # Determine department and relative path if not explicitly provided
    if department is None:
        if base_dir is not None:
            try:
                rel = file_path.relative_to(base_dir)
                department = rel.parts[0] if len(rel.parts) > 1 else "general"
            except ValueError:
                department = "general"
        else:
            department = "general"

    if base_dir is not None:
        try:
            rel_path = str(file_path.relative_to(base_dir)).replace("\\", "/")
        except ValueError:
            rel_path = file_path.name
    else:
        rel_path = file_path.name

    all_chunks = []
    chunk_index = 0
    current_section = ""

    for page_item in raw_pages:
        page_num = page_item["page"]
        text_content = page_item["text"]

        # Split page content into section blocks when a new heading line appears
        lines = text_content.split("\n")
        section_blocks = []
        current_block_lines = []
        active_heading = current_section

        for line in lines:
            detected = extract_heading_from_line(line)
            if detected:
                if current_block_lines:
                    section_blocks.append((active_heading, "\n".join(current_block_lines)))
                    current_block_lines = []
                active_heading = detected
            current_block_lines.append(line)

        if current_block_lines:
            section_blocks.append((active_heading, "\n".join(current_block_lines)))

        for block_heading, block_text in section_blocks:
            current_section = block_heading
            splits = split_text_into_chunks(block_text)
            for split in splits:
                metadata = {
                    "department": department,
                    "section": current_section,
                    "document": file_path.name,
                    "relative_path": rel_path,
                    "file_path": str(file_path.resolve()),
                    "page": page_num,
                    "chunk_index": chunk_index,
                    "char_length": len(split)
                }
                all_chunks.append(DocumentChunk(text=split, metadata=metadata))
                chunk_index += 1
            
    return all_chunks

