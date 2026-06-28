"""
Knowledge Base Builder for TOR Checklist System.

Reads sample TOR documents and sample TOR Checklists to build a structured
knowledge base that teaches the AI how to extract and format checklist items.
CRITICAL DESIGN: Strictly avoids injecting specific project names or sample text
into the prompt to guarantee zero leakage/hallucination of wrong project data.
"""
import os
import json
import pdfplumber
import openpyxl

# Flexible Root Path Detection
BASE_DIR = r'D:\CBD\TORChecklist' if os.path.exists(r'D:\CBD\TORChecklist') else os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SAMPLE_TOR_DIR = os.path.join(BASE_DIR, 'ตัวอย่าง TOR')
SAMPLE_CHECKLIST_DIR = os.path.join(BASE_DIR, 'ตัวอย่าง TOR Checklist')
CACHE_PATH = os.path.join(BASE_DIR, 'tor_knowledge_cache.json')

# In-memory cache to avoid rebuilding every request
_knowledge_cache = None


def _extract_pdf_text(pdf_path: str, max_pages: int = 5) -> str:
    """Extracts text from a PDF file (first N pages)."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:max_pages]:
                t = page.extract_text()
                if t and t.strip():
                    text += t + "\n"
    except Exception as e:
        print(f"[KnowledgeBase] Error reading PDF {pdf_path}: {e}")
    return text.strip()


def _extract_checklist_patterns(xlsx_path: str, max_rows: int = 500) -> list:
    """
    Reads a sample TOR Checklist Excel file and extracts row patterns
    showing how TOR requirements map to checklist columns.
    """
    patterns = []
    try:
        wb = openpyxl.load_workbook(xlsx_path)
        ws = wb.active

        header_row = None
        for r in range(1, min(ws.max_row + 1, 10)):
            for c in range(1, min(ws.max_column + 1, 12)):
                v = ws.cell(r, c).value
                if v and 'Status' in str(v):
                    header_row = r
                    break
            if header_row:
                break

        if not header_row:
            return patterns

        data_start = header_row + 1
        for r in range(data_start, min(data_start + max_rows, ws.max_row + 1)):
            row_data = {}
            col_names = ['Status', 'ลำดับ', 'หมวดหมู่หลัก', 'หัวข้อย่อย',
                         'ข้อกำหนด / รายละเอียด (Requirement / Details)',
                         'ชื่อเอกสารที่ใช้ยื่น', 'รายละเอียดที่ต้องระบุ',
                         'Comply?', 'หมายเหตุ (Remarks)']
            has_data = False
            for c_idx, col_name in enumerate(col_names, 1):
                v = ws.cell(r, c_idx).value
                if v is not None:
                    row_data[col_name] = str(v).strip()
                    if col_name not in ('Status', 'Comply?', 'หมายเหตุ (Remarks)') and str(v).strip():
                        has_data = True
                else:
                    row_data[col_name] = ''
            if has_data:
                patterns.append(row_data)

    except Exception as e:
        print(f"[KnowledgeBase] Error reading Checklist {xlsx_path}: {e}")
    return patterns


def _extract_section_headers(text: str) -> list:
    """
    Extracts common generic section headers from TOR documents.
    """
    import re
    headers = []
    patterns = [
        r'(?:^|\n)\s*[๐-๙\d]+[\.\)]\s*(.+)',
        r'(?:^|\n)\s*ข้อ\s*[๐-๙\d]+\s*(.+)',
        r'(?:^|\n)\s*หมวด(?:ที่)?\s*[๐-๙\d]+\s*(.+)',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for m in matches:
            clean = m.strip()[:60]
            # Ensure it looks like a generic header (e.g. ความเป็นมา, วัตถุประสงค์) and not a specific project sentence
            if clean and len(clean) > 3 and not any(kw in clean for kw in ['รฟม', 'โครงการ', 'งานจ้าง', 'บริษัท', 'กรม']):
                headers.append(clean)
    return list(dict.fromkeys(headers))[:20]


def build_tor_knowledge_base(force_rebuild: bool = False) -> dict:
    """
    Builds or loads the TOR Knowledge Base from sample files.
    """
    global _knowledge_cache

    if _knowledge_cache and not force_rebuild:
        return _knowledge_cache

    if not force_rebuild and os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, 'r', encoding='utf-8') as f:
                _knowledge_cache = json.load(f)
            print(f"[KnowledgeBase] Loaded cache from {CACHE_PATH}")
            return _knowledge_cache
        except Exception as e:
            print(f"[KnowledgeBase] Cache load failed: {e}, rebuilding...")

    print("[KnowledgeBase] Building Knowledge Base from sample files...")
    kb = {
        'tor_structures': [],
        'checklist_examples': [],
        'category_names': set(),
        'document_types': set()
    }

    if os.path.isdir(SAMPLE_TOR_DIR):
        for fname in sorted(os.listdir(SAMPLE_TOR_DIR)):
            if fname.lower().endswith('.pdf'):
                fpath = os.path.join(SAMPLE_TOR_DIR, fname)
                text = _extract_pdf_text(fpath, max_pages=5)
                if text:
                    headers = _extract_section_headers(text)
                    kb['tor_structures'].append({
                        'source': fname,
                        'sections': headers,
                        'sample_text': text[:500] # Kept minimal
                    })
                    print(f"  [TOR] {fname}: {len(headers)} sections extracted")
                else:
                    print(f"  [TOR] {fname}: scanned PDF")
    else:
        print(f"[KnowledgeBase] Sample TOR directory not found: {SAMPLE_TOR_DIR}")

    if os.path.isdir(SAMPLE_CHECKLIST_DIR):
        for fname in sorted(os.listdir(SAMPLE_CHECKLIST_DIR)):
            if fname.lower().endswith('.xlsx'):
                fpath = os.path.join(SAMPLE_CHECKLIST_DIR, fname)
                rows = _extract_checklist_patterns(fpath, max_rows=500)
                if rows:
                    kb['checklist_examples'].append({
                        'source': fname,
                        'rows': rows
                    })
                    for row in rows:
                        cat = row.get('หมวดหมู่หลัก', '')
                        if cat and len(cat) < 50:
                            kb['category_names'].add(cat)
                        doc = row.get('ชื่อเอกสารที่ใช้ยื่น', '')
                        if doc and len(doc) < 50:
                            kb['document_types'].add(doc)
                    print(f"  [Checklist] {fname}: {len(rows)} pattern rows extracted")
    else:
        print(f"[KnowledgeBase] Sample Checklist directory not found: {SAMPLE_CHECKLIST_DIR}")

    kb['category_names'] = sorted(list(kb['category_names']))
    kb['document_types'] = sorted(list(kb['document_types']))

    try:
        with open(CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(kb, f, ensure_ascii=False, indent=2)
        print(f"[KnowledgeBase] Saved cache to {CACHE_PATH}")
    except Exception as e:
        print(f"[KnowledgeBase] Failed to save cache: {e}")

    _knowledge_cache = kb
    return kb


def get_knowledge_prompt_section(kb: dict) -> str:
    """
    Converts the Knowledge Base into a concise prompt section.
    CRITICAL FIX: Fully strips any specific sample project sentences or headers
    to guarantee zero leakage/hallucination of wrong project data (e.g. รฟม).
    Injects only clean generic category names and document types.
    """
    sections = []

    # 1. Clean generic category names
    cats = [c for c in kb.get('category_names', []) if not any(kw in c for kw in ['รฟม', 'โครงการ', 'ประจำปี'])]
    if cats:
        sections.append(
            "หมวดหมู่หลัก (Main Categories) ที่ใช้จัดกลุ่มข้อกำหนด (กรุณาเลือกใช้ตามความเหมาะสมของเนื้อหาจริง):\n" +
            ", ".join(cats[:30])
        )

    # 2. Clean generic document types
    docs = [d for d in kb.get('document_types', []) if not any(kw in d for kw in ['รฟม', 'โครงการ'])]
    if docs:
        sections.append(
            "ชื่อเอกสารที่ใช้ยื่น (Document Types) ที่พบบ่อย (กรุณาเลือกใช้ตามความเหมาะสมของเนื้อหาจริง):\n" +
            ", ".join(docs[:30])
        )

    # 3. Strict instruction against hallucination
    sections.append(
        "กฎเหล็กสำคัญ: ข้อมูลด้านบนเป็นเพียงคลังคำศัพท์หมวดหมู่และชื่อเอกสารอ้างอิงเท่านั้น ห้ามสร้างข้อมูลสมมติหรือนำชื่อโครงการอื่นมาปะปนเด็ดขาด! ให้สกัดข้อกำหนดทั้งหมดจากเนื้อหาจริงของเอกสารที่ส่งมาในรอบนี้เท่านั้น"
    )

    return "\n\n".join(sections)


if __name__ == '__main__':
    kb = build_tor_knowledge_base(force_rebuild=True)
    print(f"\n=== Knowledge Base Summary ===")
    print(f"TOR structures: {len(kb['tor_structures'])} files")
    print(f"Checklist examples: {len(kb['checklist_examples'])} files")
    print(f"Category names: {len(kb['category_names'])}")
    print(f"Document types: {len(kb['document_types'])}")
    print(f"\n=== RAG Prompt Preview ===")
    print(get_knowledge_prompt_section(kb))
