"""Universal document parser for enterprise compliance pipelines.
Extracts clean text, section headings, bullet points, speaker notes, and slide hierarchies
from PDF, DOCX, PPTX, and plaintext files.
"""
import io
import os
import re
import logging
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".doc",
    ".pptx",
    ".ppt",
    ".txt",
    ".md",
    ".csv",
    ".json"
}

MAX_WORD_LIMIT = 25000


def validate_and_truncate_text(text: str, max_words: int = MAX_WORD_LIMIT) -> str:
    """Validate text length and safely truncate if exceeding context limit."""
    if not text:
        return ""
    words = text.split()
    if len(words) > max_words:
        truncated_words = words[:max_words]
        logger.warning(f"Extracted document text exceeded {max_words} words ({len(words)} words). Truncating.")
        return " ".join(truncated_words) + f"\n\n[Note: Document exceeded maximum limit of {max_words:,} words. Content was safely truncated for compliance analysis.]"
    return text


def extract_from_pdf(file_bytes: bytes, filename: str) -> str:
    """Extract text from PDF pages with clear delimiters and graceful scanned-page handling."""
    if not file_bytes:
        return ""

    file_stream = io.BytesIO(file_bytes)
    pages_text: List[str] = []

    # 1. Attempt extraction using pypdf
    try:
        import pypdf
        reader = pypdf.PdfReader(file_stream)
        if reader.is_encrypted:
            try:
                # Attempt default empty password decrypt
                reader.decrypt("")
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"The uploaded PDF '{filename}' is password-protected. Please remove password encryption before uploading."
                )

        for page_idx, page in enumerate(reader.pages, start=1):
            try:
                page_raw = page.extract_text() or ""
                page_clean = page_raw.strip()
                if page_clean:
                    pages_text.append(f"--- [Page {page_idx}] ---\n\n{page_clean}")
                else:
                    pages_text.append(f"--- [Page {page_idx}] ---\n\n[Empty or Scanned Page]")
            except Exception as page_err:
                logger.warning(f"Error reading page {page_idx} of '{filename}' via pypdf: {page_err}")
                pages_text.append(f"--- [Page {page_idx}] ---\n\n[Page Content Unreadable]")

        if pages_text:
            return "\n\n".join(pages_text).strip()

    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"pypdf extraction failed on '{filename}': {e}. Attempting fallback to pdfplumber.")

    # 2. Fallback extraction using pdfplumber
    try:
        import pdfplumber
        file_stream.seek(0)
        pages_text = []
        with pdfplumber.open(file_stream) as pdf:
            for page_idx, page in enumerate(pdf.pages, start=1):
                try:
                    page_raw = page.extract_text() or ""
                    page_clean = page_raw.strip()
                    if page_clean:
                        pages_text.append(f"--- [Page {page_idx}] ---\n\n{page_clean}")
                    else:
                        pages_text.append(f"--- [Page {page_idx}] ---\n\n[Empty or Scanned Page]")
                except Exception as p_err:
                    logger.warning(f"pdfplumber error on page {page_idx} of '{filename}': {p_err}")
                    pages_text.append(f"--- [Page {page_idx}] ---\n\n[Page Content Unreadable]")

        if pages_text:
            return "\n\n".join(pages_text).strip()
    except Exception as e:
        logger.error(f"pdfplumber fallback also failed on '{filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Corrupt or unreadable PDF file '{filename}': {str(e)}"
        )

    return "\n\n".join(pages_text).strip()


def extract_from_docx(file_bytes: bytes, filename: str) -> str:
    """Extract headings, paragraphs, and tables in document order from Word documents."""
    if not file_bytes:
        return ""

    file_stream = io.BytesIO(file_bytes)
    try:
        import docx
        doc = docx.Document(file_stream)
        elements: List[str] = []

        # Iterate through document body elements in chronological order
        for child in doc.element.body:
            tag = child.tag
            if tag.endswith("p"):
                # Paragraph element
                p = docx.text.paragraph.Paragraph(child, doc)
                text = p.text.strip()
                if text:
                    # Check if paragraph has heading style
                    style_name = p.style.name if (p.style and hasattr(p.style, "name")) else ""
                    if style_name and ("Heading" in style_name or "Title" in style_name):
                        elements.append(f"## {text}")
                    else:
                        elements.append(text)
            elif tag.endswith("tbl"):
                # Table element
                tbl = docx.table.Table(child, doc)
                table_rows = []
                for row in tbl.rows:
                    row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_cells:
                        # De-duplicate contiguous identical cells from column/row spans
                        unique_cells = []
                        for c in row_cells:
                            if not unique_cells or unique_cells[-1] != c:
                                unique_cells.append(c)
                        table_rows.append(" | ".join(unique_cells))
                if table_rows:
                    elements.append("\n".join(table_rows))

        if not elements:
            # Fallback to standard paragraphs if body iteration was empty
            for p in doc.paragraphs:
                t = p.text.strip()
                if t:
                    elements.append(t)

        return "\n\n".join(elements).strip()

    except Exception as e:
        err_msg = str(e)
        logger.error(f"Error parsing Word document '{filename}': {err_msg}")
        if "Package not found" in err_msg or file_bytes.startswith(b"\xd0\xcf\x11\xe0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Legacy binary Word file (.doc) is not supported directly. Please convert '{filename}' to modern Word format (.docx)."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Corrupt or unreadable Word document '{filename}': {err_msg}"
        )


def extract_from_pptx(file_bytes: bytes, filename: str) -> str:
    """Extract slide titles, bullet points, text frames, tables, and speaker notes from PowerPoint decks."""
    if not file_bytes:
        return ""

    file_stream = io.BytesIO(file_bytes)
    try:
        import pptx
        prs = pptx.Presentation(file_stream)
        slides_text: List[str] = []

        for slide_idx, slide in enumerate(prs.slides, start=1):
            # 1. Determine slide title
            slide_title = ""
            title_shape = None
            try:
                if slide.shapes.title and slide.shapes.title.text:
                    slide_title = slide.shapes.title.text.strip()
                    title_shape = slide.shapes.title
            except Exception:
                pass

            if not slide_title:
                # Search for first text frame that looks like a title
                for shape in slide.shapes:
                    if shape.has_text_frame and shape.text_frame.text.strip():
                        first_line = shape.text_frame.text.strip().split("\n")[0].strip()
                        if 0 < len(first_line) <= 100:
                            slide_title = first_line
                            title_shape = shape
                            break

            if not slide_title:
                slide_title = f"Slide {slide_idx}"

            slide_header = f"--- [Slide {slide_idx}: {slide_title}] ---"
            slide_content: List[str] = []

            # 2. Extract shape content (text frames, bullets, tables)
            for shape in slide.shapes:
                if shape == title_shape:
                    continue

                if shape.has_text_frame:
                    for p in shape.text_frame.paragraphs:
                        p_text = p.text.strip()
                        if p_text:
                            # Bullet indent formatting
                            indent = "  " * (p.level or 0)
                            slide_content.append(f"{indent}• {p_text}")

                elif shape.has_table:
                    table_rows = []
                    for row in shape.table.rows:
                        row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                        if row_cells:
                            table_rows.append(" | ".join(row_cells))
                    if table_rows:
                        slide_content.append("\n".join(table_rows))

            # 3. Extract speaker notes if present
            try:
                if slide.has_notes_slide and slide.notes_slide:
                    notes_tf = slide.notes_slide.notes_text_frame
                    if notes_tf and notes_tf.text.strip():
                        notes_clean = notes_tf.text.strip()
                        slide_content.append(f"[Speaker Notes]: {notes_clean}")
            except Exception as notes_err:
                logger.debug(f"Could not read speaker notes for slide {slide_idx}: {notes_err}")

            body_text = "\n\n".join(slide_content).strip()
            if body_text:
                slides_text.append(f"{slide_header}\n\n{body_text}")
            else:
                slides_text.append(f"{slide_header}\n\n[Visual or Empty Slide]")

        return "\n\n".join(slides_text).strip()

    except Exception as e:
        err_msg = str(e)
        logger.error(f"Error parsing PowerPoint presentation '{filename}': {err_msg}")
        if file_bytes.startswith(b"\xd0\xcf\x11\xe0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Legacy binary PowerPoint file (.ppt) is not supported directly. Please convert '{filename}' to modern presentation format (.pptx)."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Corrupt or unreadable PowerPoint presentation '{filename}': {err_msg}"
        )


def extract_from_plaintext(file_bytes: bytes, filename: str) -> str:
    """Decode plain text files using utf-8 with latin-1 fallback."""
    if not file_bytes:
        return ""
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return file_bytes.decode("latin-1", errors="replace")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to decode text file '{filename}': {str(e)}"
            )


def extract_text_from_upload(file_bytes: bytes, filename: str) -> str:
    """Unified entrypoint for extracting clean text, hierarchy, and metadata
    from enterprise uploads (PDF, DOCX, PPTX, TXT/MD/CSV/JSON).
    """
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty (0 bytes)."
        )

    clean_filename = (filename or "upload").strip()
    ext = os.path.splitext(clean_filename)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Please upload a PDF (.pdf), Word (.docx), PowerPoint (.pptx), or Text (.txt) file."
        )

    extracted_raw = ""

    if ext == ".pdf":
        extracted_raw = extract_from_pdf(file_bytes, clean_filename)
    elif ext in (".docx", ".doc"):
        extracted_raw = extract_from_docx(file_bytes, clean_filename)
    elif ext in (".pptx", ".ppt"):
        extracted_raw = extract_from_pptx(file_bytes, clean_filename)
    else:
        # Plain text formats: .txt, .md, .csv, .json
        extracted_raw = extract_from_plaintext(file_bytes, clean_filename)

    # Validate length and truncate safely if exceeding enterprise LLM context limit
    validated_text = validate_and_truncate_text(extracted_raw, max_words=MAX_WORD_LIMIT)

    if not validated_text.strip():
        logger.warning(f"File '{clean_filename}' parsed successfully but produced empty text.")
        return f"[Document '{clean_filename}' contained no readable text or consists entirely of images/scans.]"

    return validated_text.strip()
