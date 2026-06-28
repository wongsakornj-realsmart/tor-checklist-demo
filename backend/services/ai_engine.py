"""
AI Engine for TOR Checklist System.

Uses OpenTyphoon AI with Dynamic RAG (Knowledge Base) and AI Critic (Self-Correction)
to extract structured checklist items from TOR documents.
"""
import os
import json
import re
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


def _build_system_prompt(knowledge_section: str) -> str:
    """Builds the full system prompt with injected RAG knowledge."""
    base_prompt = """คุณคือผู้เชี่ยวชาญด้านการจัดซื้อจัดจ้างภาครัฐและวิศวกรรมระบบ AI หน้าที่ของคุณคือวิเคราะห์ข้อความจากเอกสาร TOR (Terms of Reference) ที่ผู้ใช้ส่งมา และสกัดข้อกำหนดต่างๆ ออกมาเป็นตาราง Checklist เพื่อตรวจสอบความสอดคล้อง (Compliance)

กรุณาวิเคราะห์ข้อความและแปลงเป็นโครงสร้าง JSON Object ที่มี 2 ส่วน:

ส่วนที่ 1 - "metadata": ข้อมูลภาพรวมโครงการ ประกอบด้วย:
- "project_name": ชื่อโครงการ (สกัดจากชื่อเรื่องหรือหัวเรื่องของเอกสาร)
- "client_name": ชื่อหน่วยงานเจ้าของโครงการ (เช่น ชื่อกรม/กอง/สำนักงาน/บริษัท)
- "dateline": วันที่สิ้นสุดการยื่นข้อเสนอ หรือวันที่ยื่นซอง (ถ้าไม่มีระบุในเอกสาร ให้ใส่ "")

ส่วนที่ 2 - "checklist": JSON Array ของรายการ Checklist โดยแต่ละรายการมีฟิลด์ดังนี้:
1. "Status": ว่างไว้ ("")
2. "ลำดับ": หมายเลขลำดับ (เช่น "1.", "1.1", "2.")
3. "หมวดหมู่หลัก": ชื่อหมวดหมู่หลัก
4. "หัวข้อย่อย": ชื่อหัวข้อย่อย
5. "ข้อกำหนด / รายละเอียด (Requirement / Details)": เนื้อหาข้อกำหนดโดยละเอียดจากเอกสารจริง
6. "ชื่อเอกสารที่ใช้ยื่น": ชื่อเอกสารที่ผู้รับจ้าง/ผู้ยื่นซองต้องเตรียมยื่น
7. "รายละเอียดที่ต้องระบุ": สิ่งที่ต้องระบุในเอกสารนั้นๆ
8. "Comply?": "False"
9. "หมายเหตุ (Remarks)": ว่างไว้ ("")
"""

    if knowledge_section:
        base_prompt += f"""
=== ความรู้อ้างอิงจากตัวอย่างเอกสาร TOR ที่ผ่านมา (ใช้เป็นแนวทางรูปแบบเท่านั้น ห้ามลอกเนื้อหา) ===
{knowledge_section}
=== จบส่วนความรู้อ้างอิง ===
"""

    base_prompt += """
ตัวอย่างโครงสร้าง Output:
{
  "metadata": {
    "project_name": "ชื่อโครงการจริงจากเอกสาร",
    "client_name": "ชื่อหน่วยงานจริงจากเอกสาร",
    "dateline": "วันที่ยื่นซอง (ถ้ามี) หรือ ว่าง"
  },
  "checklist": [
    {
      "Status": "",
      "ลำดับ": "1.",
      "หมวดหมู่หลัก": "สกัดจากเอกสารจริง",
      "หัวข้อย่อย": "สกัดจากเอกสารจริง",
      "ข้อกำหนด / รายละเอียด (Requirement / Details)": "เนื้อหาจากเอกสารจริงเท่านั้น",
      "ชื่อเอกสารที่ใช้ยื่น": "สกัดจากเอกสารจริง",
      "รายละเอียดที่ต้องระบุ": "สกัดจากเอกสารจริง",
      "Comply?": "False",
      "หมายเหตุ (Remarks)": ""
    }
  ]
}

คำเตือนสำคัญ:
- ห้ามนำข้อความในตัวอย่างไปใส่ในผลลัพธ์เด็ดขาด ให้สกัดเฉพาะเนื้อหาจริงจากเอกสารที่ผู้ใช้ส่งมาเท่านั้น
- ตอบกลับมาเป็น JSON เท่านั้น ห้ามมีข้อความอื่นปน
- ตรวจสอบคำสะกดให้ถูกต้องก่อนตอบ ใช้คำศัพท์ราชการที่ถูกต้องเสมอ"""

    return base_prompt


def _parse_ai_response(response_text: str) -> dict:
    """
    Parses the AI response into metadata + checklist structure.
    Handles both the new format (with metadata) and legacy format (array only).
    """
    # Try parsing as full JSON object with metadata
    try:
        obj_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if obj_match:
            data = json.loads(obj_match.group(0))
            if 'metadata' in data and 'checklist' in data:
                return data
            # If it's a single checklist item, wrap it
            if 'ลำดับ' in data:
                return {"metadata": {}, "checklist": [data]}
    except:
        pass

    # Try parsing as JSON Array (legacy format / fallback)
    try:
        arr_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if arr_match:
            data = json.loads(arr_match.group(0))
            if isinstance(data, list):
                return {"metadata": {}, "checklist": data}
    except:
        pass

    # Last resort: extract individual complete JSON objects
    object_matches = re.findall(r'\{[^{}]+\}', response_text, re.DOTALL)
    if object_matches:
        valid_objs = []
        for obj_str in object_matches:
            try:
                obj = json.loads(obj_str)
                if 'ลำดับ' in obj or 'หมวดหมู่หลัก' in obj:
                    valid_objs.append(obj)
            except:
                pass
        if valid_objs:
            print(f"[AI Engine] Salvaged {len(valid_objs)} JSON objects from truncated response")
            return {"metadata": {}, "checklist": valid_objs}

    return None


def generate_tor_checklist(text_content: str) -> dict:
    """
    Main entry point: Extracts structured TOR checklist from document text.

    Pipeline:
      1. Load Knowledge Base (RAG)
      2. Call OpenTyphoon AI for initial extraction (metadata + checklist)
      3. Call AI Critic for self-correction
      4. Return final result

    Returns:
        dict with keys: "metadata" (dict) and "checklist" (list)
    """
    clean_text = text_content[:45000]

    # Step 1: Load Knowledge Base
    print("[AI Engine] Step 1: Loading TOR Knowledge Base...")
    try:
        kb = build_tor_knowledge_base()
        knowledge_section = get_knowledge_prompt_section(kb)
        print(f"[AI Engine] Knowledge Base loaded: {len(kb.get('category_names', []))} categories, {len(kb.get('document_types', []))} doc types")
    except Exception as kb_err:
        print(f"[AI Engine] Knowledge Base load failed (non-critical): {kb_err}")
        knowledge_section = ""

    # Build system prompt with RAG knowledge
    system_prompt = _build_system_prompt(knowledge_section)

    # Step 2: Call OpenTyphoon AI
    print("[AI Engine] Step 2: Initial AI Extraction (Metadata + Checklist)...")
    last_error = None

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
        print(f"[AI Engine] Discovered OpenTyphoon models: {available_models}")
        instruct_models = [m for m in available_models if 'instruct' in m.lower()]
        if instruct_models:
            target_models = instruct_models + target_models
    except Exception as list_err:
        print(f"[AI Engine] Failed to list models: {list_err}")

    result = None
    for model_name in target_models:
        for max_tokens in [2048, 1024]:
            try:
                print(f"[AI Engine] Trying model: {model_name} (max_tokens: {max_tokens})...")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"เอกสาร TOR:\n\n{clean_text}"}
                    ],
                    temperature=0.2,
                    max_tokens=max_tokens
                )

                response_text = response.choices[0].message.content.strip()
                print(f"[AI Engine] Got response from {model_name} ({len(response_text)} chars)")

                parsed = _parse_ai_response(response_text)
                if parsed and parsed.get('checklist'):
                    result = parsed
                    print(f"[AI Engine] Extracted {len(result['checklist'])} checklist items")
                    break
                else:
                    print(f"[AI Engine] Could not parse response from {model_name}")
                    continue

            except Exception as e:
                print(f"[AI Engine] Model {model_name} (max_tokens: {max_tokens}) failed: {e}")
                last_error = str(e)
                continue

        if result:
            break

    # If all AI models failed, use direct text parsing fallback
    if not result:
        print(f"[AI Engine] All AI models failed. Using direct text parsing fallback...")
        result = _direct_text_fallback(clean_text, last_error)

    # Step 3: AI Critic Self-Correction
    print("[AI Engine] Step 3: AI Critic Self-Correction Loop...")
    try:
        corrected_checklist = evaluate_and_correct_checklist(clean_text, result['checklist'])
        result['checklist'] = corrected_checklist
        print(f"[AI Engine] Critic completed. Final checklist: {len(result['checklist'])} items")
    except Exception as critic_err:
        print(f"[AI Engine] Critic failed (non-critical, using uncorrected data): {critic_err}")

    # Ensure metadata has all required fields
    meta = result.get('metadata', {})
    if not isinstance(meta, dict):
        meta = {}
    result['metadata'] = {
        'project_name': meta.get('project_name', ''),
        'client_name': meta.get('client_name', ''),
        'dateline': meta.get('dateline', '')
    }

    return result


def _direct_text_fallback(clean_text: str, last_error: str) -> dict:
    """Fallback when all AI models fail: extract requirements directly from text."""
    lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
    extracted_reqs = []
    for line in lines:
        if any(kw in line for kw in ["ผู้รับจ้าง", "ต้อง", "ข้อกำหนด", "วัตถุประสงค์", "ขอบเขต", "โครงการ", "ระบบ"]):
            extracted_reqs.append(line)
            if len(extracted_reqs) >= 10:
                break

    if not extracted_reqs and lines:
        extracted_reqs = lines[:5]

    if not extracted_reqs:
        extracted_reqs = ["ไม่พบข้อความข้อกำหนดในเอกสาร (เอกสารอาจว่างเปล่าหรือสแกนไม่ชัดเจน)"]

    checklist = []
    for idx, req in enumerate(extracted_reqs, 1):
        checklist.append({
            "Status": "",
            "ลำดับ": f"{idx}.",
            "หมวดหมู่หลัก": "ข้อกำหนดโครงการ (Direct Extract)",
            "หัวข้อย่อย": "รายละเอียดข้อกำหนด",
            "ข้อกำหนด / รายละเอียด (Requirement / Details)": req,
            "ชื่อเอกสารที่ใช้ยื่น": "ข้อเสนอทางเทคนิค (Technical Proposal)",
            "รายละเอียดที่ต้องระบุ": f"ยืนยันความพร้อมตามข้อกำหนด: {req[:50]}...",
            "Comply?": "False",
            "หมายเหตุ (Remarks)": f"AI API Fallback: {last_error}" if last_error else ""
        })

    # Try to extract metadata from first few lines
    project_name = ""
    client_name = ""
    for line in lines[:15]:
        if 'โครงการ' in line or 'เรื่อง' in line:
            project_name = line[:120]
        if any(kw in line for kw in ['กรม', 'สำนักงาน', 'กอง', 'การ', 'มหาวิทยาลัย']):
            if not client_name:
                client_name = line[:80]

    return {
        "metadata": {
            "project_name": project_name,
            "client_name": client_name,
            "dateline": ""
        },
        "checklist": checklist
    }
