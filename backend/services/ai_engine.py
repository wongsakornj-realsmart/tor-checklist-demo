"""
AI Engine for TOR Checklist System.

Uses OpenTyphoon AI with Dynamic RAG (Knowledge Base) and AI Critic (Self-Correction)
to extract structured checklist items from TOR documents.

Architecture:
  1. Metadata Extraction (dedicated small AI call + robust text fallback)
  2. Chunked Checklist Extraction (split document into sections, call AI per chunk without dummy JSON examples)
  3. Bulletproof Hallucination/Gibberish Filtering (_is_valid_tor_item)
  4. AI Critic Self-Correction Loop
  5. Natural Hierarchical Sorting (ensures perfect sequential numbering e.g. 5, 6, 7, 10)
  6. Final Polish (guarantees 'ชื่อเอกสารที่ใช้ยื่น' and 'รายละเอียดที่ต้องระบุ' are populated 100%)
"""
import os
import json
import re
import math
from openai import OpenAI

from backend.services.knowledge_base import build_tor_knowledge_base, get_knowledge_prompt_section
from backend.services.ai_critic import evaluate_and_correct_checklist

# OpenTyphoon AI Configuration
TYPHOON_API_KEY = os.getenv("TYPHOON_API_KEY", "sk-Rmn1bvzNfpruBxlQWH9umkZRPPFTWbU4OtMtczKRUsGxnWmG")
TYPHOON_BASE_URL = "https://api.opentyphoon.ai/v1"

client = OpenAI(
    api_key=TYPHOON_API_KEY,
    base_url=TYPHOON_BASE_URL
)

# Chunk size for splitting long documents (chars per chunk)
CHUNK_SIZE = 12000
CHUNK_OVERLAP = 500


def _get_target_models() -> list:
    """Get list of available models, with dynamic discovery."""
    target_models = [
        "typhoon-v2.5-30b-a3b-instruct",
        "typhoon-v2.1-12b-instruct",
        "typhoon-v2-70b-instruct",
        "typhoon-v2-8b-instruct",
        "typhoon-v1.5x-70b-instruct",
        "typhoon-v1.5-instruct"
    ]
    try:
        available_models = [m.id for m in client.models.list().data]
        print(f"[AI Engine] Discovered models: {available_models}")
        instruct_models = [m for m in available_models if 'instruct' in m.lower()]
        if instruct_models:
            target_models = instruct_models + target_models
    except Exception as e:
        print(f"[AI Engine] Model discovery failed: {e}")
    return target_models


def _call_ai(system_prompt: str, user_content: str, max_tokens: int = 4096) -> str:
    """Makes an AI call with model fallback. Returns raw response text or None."""
    target_models = _get_target_models()
    for model_name in target_models:
        for mt in [max_tokens, max_tokens // 2]:
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=0.15,
                    max_tokens=mt
                )
                text = response.choices[0].message.content.strip()
                if text:
                    return text
            except Exception as e:
                print(f"[AI Engine] {model_name} (max_tokens={mt}) failed: {e}")
                continue
    return None


def _is_valid_tor_item(item: dict) -> bool:
    """
    Bulletproof validation filter to detect and destroy AI hallucination / gibberish.
    Checks 'หมวดหมู่หลัก' and 'ข้อกำหนด / รายละเอียด (Requirement / Details)'.
    """
    cat = str(item.get('หมวดหมู่หลัก', '')).strip()
    req = str(item.get('ข้อกำหนด / รายละเอียด (Requirement / Details)', '')).strip()
    combined = f"{cat} {req}"

    if not cat and not req:
        return False

    # 1. Check for repeating character glitches (e.g. PPPPPPPPPP, FFFFFFFF, dddddd)
    if re.search(r'([A-Za-z0-9])\1{4,}', combined):
        print(f"[AI Engine] Dropped hallucinated repeating string: {combined[:40]}")
        return False

    # 2. Check for bizarre non-Thai / non-English characters (Cyrillic, extended Latin gibberish like Ж, ŧ, ț, ç)
    if re.search(r'[ЖțçŧÉ¢]', combined):
        print(f"[AI Engine] Dropped corrupted encoding/Cyrillic gibberish: {combined[:40]}")
        return False

    # 3. Must contain at least some valid Thai characters (Thai government documents are in Thai)
    thai_chars = re.findall(r'[\u0E00-\u0E7F]', combined)
    if len(thai_chars) < 5:
        print(f"[AI Engine] Dropped non-Thai/gibberish item: {combined[:40]}")
        return False

    # 4. Filter out short random nonsense (e.g. 'JZ', '3h0', 'x478', 'KeNF')
    if len(combined.strip()) < 8 and not any(kw in combined for kw in ['TOR', 'งาน', 'ซื้อ', 'จ้าง']):
        print(f"[AI Engine] Dropped short nonsense item: {combined[:40]}")
        return False

    return True


def _parse_json_array(text: str) -> list:
    """Robustly parses a JSON array from AI response text with gibberish filtering."""
    if not text:
        return []

    raw_items = []
    # Try full array parse
    try:
        arr_match = re.search(r'\[.*\]', text, re.DOTALL)
        if arr_match:
            raw_items = json.loads(arr_match.group(0))
    except:
        pass

    if not raw_items:
        # Salvage individual objects (for truncated responses)
        object_matches = re.findall(r'\{[^{}]+\}', text, re.DOTALL)
        for obj_str in object_matches:
            try:
                obj = json.loads(obj_str)
                if any(k in obj for k in ['ลำดับ', 'หมวดหมู่หลัก', 'ข้อกำหนด / รายละเอียด (Requirement / Details)']):
                    raw_items.append(obj)
            except:
                pass

    # Strictly filter out any gibberish / hallucinated items
    valid_objs = [item for item in raw_items if isinstance(item, dict) and _is_valid_tor_item(item)]
    
    if valid_objs:
        print(f"[AI Engine] Parsed {len(valid_objs)} valid clean objects (dropped {len(raw_items) - len(valid_objs)} invalid/gibberish)")
    return valid_objs


def _parse_json_object(text: str) -> dict:
    """Parses a JSON object from AI response text."""
    if not text:
        return {}
    try:
        obj_match = re.search(r'\{.*\}', text, re.DOTALL)
        if obj_match:
            return json.loads(obj_match.group(0))
    except:
        pass
    return {}


# ========================================================================
# STEP 1: Metadata Extraction
# ========================================================================

METADATA_SYSTEM_PROMPT = """คุณคือผู้เชี่ยวชาญด้านการวิเคราะห์เอกสาร TOR (Terms of Reference) ภาครัฐไทย
หน้าที่ของคุณคือสกัดข้อมูลภาพรวมโครงการจากข้อความของเอกสาร TOR ที่ส่งมา

กรุณาสกัดข้อมูลต่อไปนี้:
1. "project_name": ชื่อโครงการหรือชื่อเรื่องของงานที่จัดซื้อจัดจ้าง
2. "client_name": ชื่อหน่วยงานเจ้าของโครงการ (เช่น กรม, กอง, สำนักงาน, การ, มหาวิทยาลัย, บริษัท)
3. "dateline": วันที่สิ้นสุดการยื่นข้อเสนอ หรือวันที่ยื่นซอง (ถ้าไม่มีระบุในเอกสาร ให้ใส่ "")

กฎเหล็กสำคัญ:
- ห้ามตอบกลับเป็น "..." หรือข้อความสมมติเด็ดขาด
- ให้ดึงข้อความชื่อโครงการจริง และชื่อหน่วยงานจริง จากเนื้อหาเอกสารที่ส่งมาเท่านั้น!

ตอบกลับเป็น JSON Object เท่านั้น โดยมีโครงสร้างดังนี้:
{
  "project_name": "ชื่อโครงการจริงจากเอกสาร",
  "client_name": "ชื่อหน่วยงานจริงจากเอกสาร",
  "dateline": "วันที่ยื่นซองจริงจากเอกสาร (ถ้ามี)"
}"""


def _extract_metadata(text_content: str) -> dict:
    """Extracts project metadata using AI with robust text parsing fallback."""
    print("[AI Engine] Extracting metadata...")
    short_text = text_content[:6000] # Inspect first 6000 chars

    response_text = _call_ai(METADATA_SYSTEM_PROMPT, f"เอกสาร TOR:\n\n{short_text}", max_tokens=512)
    meta = _parse_json_object(response_text)

    # Robust verification against AI literal copying of placeholders
    p_name = meta.get('project_name', '').strip()
    c_name = meta.get('client_name', '').strip()

    if not p_name or p_name in ["...", "ชื่อโครงการจริงจากเอกสาร", ""]:
        print("[AI Engine] AI returned placeholder/empty project_name. Using robust text fallback...")
        text_meta = _extract_metadata_from_text(text_content)
        p_name = text_meta.get('project_name', p_name)
        if not c_name or c_name in ["...", "ชื่อหน่วยงานจริงจากเอกสาร", ""]:
            c_name = text_meta.get('client_name', c_name)

    print(f"[AI Engine] Final Metadata: project='{p_name[:50]}', client='{c_name[:30]}'")
    return {
        'project_name': p_name,
        'client_name': c_name,
        'dateline': meta.get('dateline', '') if meta.get('dateline') not in ["...", "วันที่ยื่นซองจริงจากเอกสาร (ถ้ามี)"] else ""
    }


def _extract_metadata_from_text(text: str) -> dict:
    """Bulletproof fallback: extract metadata directly from text patterns."""
    lines = [l.strip() for l in text[:6000].split('\n') if l.strip()]
    project_name = ""
    client_name = ""

    for line in lines[:40]:
        # Project name patterns
        if not project_name:
            if any(kw in line for kw in ['โครงการ', 'เรื่อง', 'งานจ้าง', 'งานซื้อ', 'ประกวดราคา', 'TOR']):
                if len(line) > 10 and not line.startswith('1.'):
                    project_name = line[:200]
        # Client name patterns
        if not client_name:
            if any(kw in line for kw in ['สำนักงาน', 'กรม', 'กอง', 'การ', 'มหาวิทยาลัย', 'กระทรวง', 'สถาบัน', 'บริษัท', 'จัดทำโดย']):
                if len(line) > 5:
                    client_name = line[:100]

    return {'project_name': project_name, 'client_name': client_name, 'dateline': ''}


# ========================================================================
# STEP 2: Chunked Checklist Extraction & Post-Processing Sorting
# ========================================================================

def _build_checklist_prompt(knowledge_section: str) -> str:
    """
    Builds the checklist extraction system prompt.
    CRITICAL FIX: Explicitly mandates population of doc names and details. No literal JSON examples.
    """
    prompt = """คุณคือผู้เชี่ยวชาญด้านการจัดซื้อจัดจ้างภาครัฐไทย หน้าที่ของคุณคือวิเคราะห์ข้อความส่วนหนึ่งจากเอกสาร TOR (Terms of Reference) และสกัดข้อกำหนดทุกข้อออกมาเป็นตาราง Checklist

สิ่งสำคัญที่สุด: คุณต้องสกัดข้อกำหนดทุกข้อที่ปรากฏในเอกสารส่วนที่ส่งมา ห้ามข้ามหรือละเว้นข้อใดข้อหนึ่ง ทุกย่อหน้าที่มีเนื้อหาเกี่ยวกับข้อกำหนด ขอบเขตงาน คุณสมบัติ เงื่อนไข หรือรายละเอียดทางเทคนิค ต้องถูกสกัดออกมาเป็นรายการแยกกันทั้งหมด (ควรสกัดให้ได้หลายสิบข้อกำหนดตามเนื้อหาจริง)

กรุณาแปลงข้อมูลเป็น JSON Array โดยแต่ละรายการ (Object) จะต้องประกอบด้วยฟิลด์ดังต่อไปนี้เท่านั้น:
1. "Status": ให้ใส่ค่าว่าง "" เสมอ
2. "ลำดับ": หมายเลขลำดับข้อกำหนดตามเอกสารต้นฉบับ (เช่น "1.", "1.1", "2.", "ก.", "1)")
3. "หมวดหมู่หลัก": ชื่อหมวดหมู่หลัก (เช่น "ความเป็นมา", "วัตถุประสงค์", "คุณสมบัติของผู้ยื่นข้อเสนอ", "ขอบเขตการดำเนินงาน", "คุณลักษณะเฉพาะ", "การส่งมอบงาน")
4. "หัวข้อย่อย": ชื่อหัวข้อย่อย
5. "ข้อกำหนด / รายละเอียด (Requirement / Details)": เนื้อหาข้อกำหนดโดยละเอียดจากเอกสารจริง (ห้ามย่อ ห้ามสรุป ให้ใส่เนื้อหาเต็มของข้อกำหนดนั้นๆ)
6. "ชื่อเอกสารที่ใช้ยื่น": ชื่อเอกสารที่ต้องเตรียมยื่น (เช่น "ข้อเสนอทางเทคนิค (Technical Proposal)", "หนังสือรับรองผลงาน", "เอกสารการจดทะเบียนนิติบุคคล", "ใบเสนอราคา") ห้ามปล่อยว่างเด็ดขาด หากไม่แน่ใจให้ใส่ "ข้อเสนอทางเทคนิค (Technical Proposal)"
7. "รายละเอียดที่ต้องระบุ": อธิบายรายละเอียดสิ่งที่ผู้ยื่นข้อเสนอต้องเขียนหรือแนบในเอกสาร (เช่น "ระบุคำอธิบายยืนยันความพร้อมในการดำเนินงานตามข้อกำหนด", "แนบสำเนาหนังสือรับรองผลงานพร้อมรับรองสำเนาถูกต้อง", "อธิบายแผนงานและวิธีการดำเนินการอย่างละเอียด") ห้ามปล่อยว่างเด็ดขาด!
8. "Comply?": ให้ใส่ข้อความ "False" เสมอ
9. "หมายเหตุ (Remarks)": ให้ใส่ค่าว่าง "" เสมอ

คำเตือนสำคัญ:
- ห้ามสร้างข้อมูลสมมติขึ้นมาเองเด็ดขาด ให้สกัดจากข้อความจริงของเอกสารส่วนที่ส่งมาเท่านั้น
- ห้ามสร้างข้อความมั่วซั่ว (Gibberish) หรือข้อความซ้ำๆ เช่น 'PPPPPPPPP' หรือตัวอักษรประหลาดเด็ดขาด
- ตอบกลับมาเป็น JSON Array เท่านั้น ห้ามมีข้อความอื่นปน
- สกัดข้อกำหนดออกมาให้ครบถ้วนที่สุดเท่าที่มีในเนื้อหา"""

    if knowledge_section:
        prompt += f"""

=== ความรู้อ้างอิงจากต้นแบบ (ใช้เป็นคลังคำศัพท์และแนวทางเท่านั้น ห้ามลอกเนื้อหา) ===
{knowledge_section}
=== จบส่วนความรู้อ้างอิง ==="""

    return prompt


def _split_into_chunks(text: str) -> list:
    """Splits text into overlapping chunks for processing."""
    if len(text) <= CHUNK_SIZE:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE

        # Try to split at a paragraph break
        if end < len(text):
            break_point = text.rfind('\n', start + CHUNK_SIZE - 2000, end)
            if break_point > start:
                end = break_point

        chunks.append(text[start:end])
        start = end - CHUNK_OVERLAP  # overlap to avoid losing content at boundaries

    print(f"[AI Engine] Split document into {len(chunks)} chunks ({len(text)} chars total)")
    return chunks


def _extract_checklist_from_chunk(chunk_text: str, chunk_num: int, total_chunks: int,
                                   system_prompt: str) -> list:
    """Extracts checklist items from a single text chunk."""
    print(f"[AI Engine] Processing chunk {chunk_num}/{total_chunks} ({len(chunk_text)} chars)...")

    user_msg = f"ส่วนที่ {chunk_num}/{total_chunks} ของเอกสาร TOR:\n\n{chunk_text}"
    response_text = _call_ai(system_prompt, user_msg, max_tokens=4096)
    items = _parse_json_array(response_text)
    print(f"[AI Engine] Chunk {chunk_num}: extracted {len(items)} items")
    return items


def _deduplicate_checklist(items: list) -> list:
    """Removes duplicate items from combined chunks (based on ข้อกำหนด content) and cleans gibberish."""
    seen = set()
    unique_items = []
    for item in items:
        if not _is_valid_tor_item(item):
            continue
        content = item.get('ข้อกำหนด / รายละเอียด (Requirement / Details)', '')
        # Use first 100 chars as fingerprint to catch duplicates from chunk overlaps
        fingerprint = content[:100].strip()
        if fingerprint and fingerprint not in seen:
            seen.add(fingerprint)
            unique_items.append(item)
        elif not fingerprint:
            unique_items.append(item)
    
    removed = len(items) - len(unique_items)
    if removed > 0:
        print(f"[AI Engine] Deduplication: removed {removed} duplicate/invalid items")
    return unique_items


def _parse_ladap_key(item: dict) -> tuple:
    """
    Converts a 'ลำดับ' string into a robust tuple of integers/strings for natural hierarchical sorting.
    Example: '1.2' -> (1, 2)
             '10.1' -> (10, 1)
             '2' -> (2,)
             'ข้อ 6' -> (6,)
    Ensures that items sort naturally (e.g., 5, 6, 7, 10 instead of 10, 5, 6, 7).
    """
    ladap = str(item.get('ลำดับ', '')).strip()
    
    # Convert Thai numerals to Arabic numerals
    thai_to_arabic = str.maketrans('๐๑๒๓๔๕๖๗๘๙', '0123456789')
    ladap = ladap.translate(thai_to_arabic)
    
    # Extract all numerical parts using regex
    parts = re.findall(r'\d+', ladap)
    
    if parts:
        # Convert extracted digits to integers for proper numeric comparison (e.g. 2 < 10)
        return tuple(int(p) for p in parts)
    else:
        # Fallback if no numbers found (e.g. 'ก.', '-', empty)
        return (999999, ladap)


# ========================================================================
# MAIN ENTRY POINT
# ========================================================================

def generate_tor_checklist(text_content: str) -> dict:
    """
    Main entry point: Extracts structured TOR checklist from document text.

    Pipeline:
      1. Load Knowledge Base (RAG)
      2. Extract Metadata (dedicated small AI call + robust text fallback)
      3. Chunked Checklist Extraction (split document, call AI per chunk without dummy examples)
      4. Deduplicate & filter out gibberish/hallucinations (_is_valid_tor_item)
      5. AI Critic Self-Correction Loop (safe non-truncating)
      6. Natural Hierarchical Sorting (solves out-of-order numbering e.g. 5, 7, 10, 6)
      7. Final Polish (populates empty 'ชื่อเอกสารที่ใช้ยื่น' and 'รายละเอียดที่ต้องระบุ')
      8. Return final result

    Returns:
        dict with keys: "metadata" (dict) and "checklist" (list)
    """
    clean_text = text_content[:96000]  # Allow up to 96k chars (full document)

    # Step 1: Load Knowledge Base
    print("[AI Engine] Step 1: Loading TOR Knowledge Base...")
    knowledge_section = ""
    try:
        kb = build_tor_knowledge_base()
        knowledge_section = get_knowledge_prompt_section(kb)
        print(f"[AI Engine] KB loaded: {len(kb.get('category_names', []))} categories, {len(kb.get('document_types', []))} doc types")
    except Exception as kb_err:
        print(f"[AI Engine] KB failed (non-critical): {kb_err}")

    # Step 2: Extract Metadata
    print("[AI Engine] Step 2: Extracting Metadata...")
    metadata = _extract_metadata(clean_text)

    # Step 3: Chunked Checklist Extraction
    print("[AI Engine] Step 3: Chunked Checklist Extraction...")
    system_prompt = _build_checklist_prompt(knowledge_section)
    chunks = _split_into_chunks(clean_text)

    all_items = []
    for i, chunk in enumerate(chunks, 1):
        chunk_items = _extract_checklist_from_chunk(chunk, i, len(chunks), system_prompt)
        all_items.extend(chunk_items)

    if not all_items:
        print("[AI Engine] All AI extraction failed. Using direct text parsing fallback...")
        all_items = _direct_text_fallback(clean_text)

    # Step 4: Deduplicate & Clean Gibberish
    print(f"[AI Engine] Step 4: Deduplicating and cleaning {len(all_items)} items...")
    all_items = _deduplicate_checklist(all_items)

    # Step 5: Re-number items sequentially if missing
    for idx, item in enumerate(all_items, 1):
        if not item.get('ลำดับ'):
            item['ลำดับ'] = f"{idx}."

    print(f"[AI Engine] Total checklist items after dedup and cleaning: {len(all_items)}")

    # Step 6: AI Critic Self-Correction
    print("[AI Engine] Step 5: AI Critic Self-Correction Loop...")
    try:
        corrected = evaluate_and_correct_checklist(clean_text, all_items)
        # Clean critic output just in case it hallucinated
        clean_corrected = [item for item in corrected if isinstance(item, dict) and _is_valid_tor_item(item)] if corrected else []
        
        # Accept critic output if it retained at least half of the valid items (allowing valid pruning)
        if clean_corrected and len(clean_corrected) >= (len(all_items) // 2):
            all_items = clean_corrected
            print(f"[AI Engine] Critic completed. Final: {len(all_items)} items")
        else:
            print(f"[AI Engine] Critic returned invalid/fewer items ({len(clean_corrected)} vs {len(all_items)}). Keeping original clean items.")
    except Exception as critic_err:
        print(f"[AI Engine] Critic failed (non-critical): {critic_err}")

    # Step 7: Natural Hierarchical Sorting by ลำดับ
    print("[AI Engine] Step 6: Natural Hierarchical Sorting by ลำดับ...")
    try:
        all_items.sort(key=_parse_ladap_key)
        print("[AI Engine] Sorting completed successfully.")
    except Exception as sort_err:
        print(f"[AI Engine] Sorting failed (non-critical): {sort_err}")

    # Step 8: Final Polish - Ensure no empty values in critical columns
    print("[AI Engine] Step 7: Final Polish (Ensuring required fields are populated)...")
    for item in all_items:
        doc = str(item.get('ชื่อเอกสารที่ใช้ยื่น', '')).strip()
        if not doc or doc == 'None':
            item['ชื่อเอกสารที่ใช้ยื่น'] = "ข้อเสนอทางเทคนิค (Technical Proposal)"
            
        detail = str(item.get('รายละเอียดที่ต้องระบุ', '')).strip()
        if not detail or detail == 'None':
            req_text = str(item.get('ข้อกำหนด / รายละเอียด (Requirement / Details)', '')).strip()
            if any(kw in req_text for kw in ['ผลงาน', 'ประสบการณ์', 'เคย']):
                item['รายละเอียดที่ต้องระบุ'] = "แนบหนังสือรับรองผลงานและสำเนาสัญญาที่เกี่ยวข้อง พร้อมรับรองสำเนาถูกต้อง"
            elif any(kw in req_text for kw in ['นิติบุคคล', 'จดทะเบียน', 'ทุน', 'ล้มละลาย', 'คุณสมบัติ']):
                item['รายละเอียดที่ต้องระบุ'] = "แนบหนังสือรับรองการจดทะเบียนนิติบุคคล / เอกสารหลักฐานคุณสมบัติ พร้อมลงนามรับรอง"
            elif any(kw in req_text for kw in ['ระบบ', 'ซอฟต์แวร์', 'ฟังก์ชัน', 'เซิร์ฟเวอร์', 'ความปลอดภัย', 'สถาปัตยกรรม']):
                item['รายละเอียดที่ต้องระบุ'] = "ระบุข้อเสนอทางเทคนิค อธิบายสถาปัตยกรรมระบบ ฟังก์ชันการทำงาน และวิธีการดำเนินงานอย่างละเอียด"
            else:
                item['รายละเอียดที่ต้องระบุ'] = "ระบุคำอธิบายยืนยันความพร้อมและรายละเอียดวิธีการดำเนินงานตามข้อกำหนด"

    return {
        "metadata": metadata,
        "checklist": all_items
    }


def _direct_text_fallback(clean_text: str) -> list:
    """Fallback when all AI models fail: extracts all valid matching lines."""
    lines = [l.strip() for l in clean_text.split('\n') if l.strip() and len(l.strip()) > 15]
    extracted = []
    keywords = ["ผู้รับจ้าง", "ต้อง", "ข้อกำหนด", "วัตถุประสงค์", "ขอบเขต",
                 "โครงการ", "ระบบ", "คุณสมบัติ", "เงื่อนไข", "การดำเนินงาน",
                 "มาตรฐาน", "ความปลอดภัย", "การส่งมอบ", "ระยะเวลา", "จัดทำ"]
    for line in lines:
        if any(kw in line for kw in keywords):
            extracted.append(line)

    if not extracted:
        extracted = lines[:50]

    result = []
    for idx, req in enumerate(extracted, 1):
        result.append({
            "Status": "",
            "ลำดับ": f"{idx}.",
            "หมวดหมู่หลัก": "ข้อกำหนดโครงการ (Direct Extract)",
            "หัวข้อย่อย": "รายละเอียดข้อกำหนด",
            "ข้อกำหนด / รายละเอียด (Requirement / Details)": req,
            "ชื่อเอกสารที่ใช้ยื่น": "ข้อเสนอทางเทคนิค (Technical Proposal)",
            "รายละเอียดที่ต้องระบุ": f"ยืนยันความพร้อมตามข้อกำหนด",
            "Comply?": "False",
            "หมายเหตุ (Remarks)": "AI Fallback"
        })
    print(f"[AI Engine] Direct text fallback extracted {len(result)} items")
    return result
