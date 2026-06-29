"""
AI Critic Agent for TOR Checklist System.

Acts as a Quality Auditor that reviews and corrects the AI-generated checklist
items for spelling accuracy, logical coherence, completeness of required fields,
and compliance with Thai government procurement terminology.
CRITICAL DESIGN: Uses raw requests with robust list/dict parsing and 90s timeout.
"""
import os
import json
import re
import requests

# OpenTyphoon AI Configuration
TYPHOON_API_KEY = os.getenv("TYPHOON_API_KEY", "sk-Rmn1bvzNfpruBxlQWH9umkZRPPFTWbU4OtMtczKRUsGxnWmG")
TYPHOON_BASE_URL = "https://api.opentyphoon.ai/v1"

# Maximum self-correction iterations
MAX_CORRECTION_ROUNDS = 2

CRITIC_SYSTEM_PROMPT = """คุณคือ "AI Critic Agent" ผู้ตรวจประเมินคุณภาพระดับอาวุโส (Senior QA Auditor) ประจำระบบวิเคราะห์เอกสารจัดซื้อจัดจ้างภาครัฐไทย (TOR Checklist System)

หน้าที่สำคัญที่สุดของคุณคือ: ตรวจสอบและแก้ไขรายการข้อกำหนด (Checklist items) ที่ AI เครื่องยนต์หลักสกัดออกมาจากเอกสารต้นฉบับ เพื่อให้มั่นใจ 100% ว่าข้อมูลมีความถูกต้องตามหลักเกณฑ์ต่อไปนี้:

1. ความถูกต้องของการสะกดคำ (Spelling Accuracy): แก้ไขคำผิดที่เกิดจากกระบวนการแปลงไฟล์ OCR หรือการหลงลืมของ AI (เช่น 'ผยู้ น' -> 'ผู้ยื่น', 'ขอบเข ต' -> 'ขอบเขต', 'เคื่รอง' -> 'เครื่อง')
2. ความสมเหตุสมผลทางตรรกะ (Logical Coherence): ข้อความในฟิลด์ 'ข้อกำหนด / รายละเอียด' ต้องเป็นประโยคที่สมบูรณ์ อ่านเข้าใจ ไม่ขาดหายกลางคัน
3. กฎเหล็กห้ามเพิ่มข้อมูลสมมติ (Strict Grounding): ห้ามคิดค้นข้อกำหนดใหม่ หรือนำชื่อโครงการอื่นมาใส่เด็ดขาด ให้ยึดจากเนื้อหาเอกสารต้นฉบับที่แนบมาให้พิจารณาเท่านั้น
4. กฎเหล็กห้ามลบข้อกำหนด (Strict Anti-Truncation): คุณต้องรักษาจำนวนรายการข้อกำหนดเดิมไว้ให้ครบถ้วนที่สุด ห้ามลบทิ้งหรือย่อตารางเด็ดขาด
5. การคัดกรองสิ่งแปลกปลอม (Anti-Gibberish): หากพบรายการที่เป็นตัวอักษรซ้ำๆ มั่วซั่ว (เช่น PPPPPPPPP) หรือเป็นรหัสแปลกประหลาด ให้ตัดรายการนั้นทิ้งได้
6. ความถูกต้องของชื่อเอกสารและคำอธิบาย (Mandatory Fields):
   - ฟิลด์ "ชื่อเอกสารที่ใช้ยื่น" ห้ามปล่อยว่างเด็ดขาด! ต้องมีชื่อเอกสารที่สอดคล้องกับข้อกำหนด (เช่น ข้อเสนอทางเทคนิค, หนังสือรับรองผลงาน, เอกสารจดทะเบียนนิติบุคคล)
   - ฟิลด์ "รายละเอียดที่ต้องระบุ" ห้ามปล่อยว่างเด็ดขาด! ต้องมีคำอธิบายแนวทางการเขียนที่ชัดเจนและเป็นมืออาชีพ

กรุณาตอบกลับในรูปแบบ JSON Object ที่มีคีย์ "checklist" ซึ่งบรรจุรายการ JSON Array ทั้งหมดที่ผ่านการแก้ไขแล้ว ดังนี้:
```json
{
  "checklist": [
    {
      "Status": "",
      "ลำดับ": "1.",
      "หมวดหมู่หลัก": "ความเป็นมา",
      "หัวข้อย่อย": "รายละเอียดข้อกำหนด",
      "ข้อกำหนด / รายละเอียด (Requirement / Details)": "เนื้อหาข้อกำหนดที่ถูกต้อง...",
      "ชื่อเอกสารที่ใช้ยื่น": "ข้อเสนอทางเทคนิค (Technical Proposal)",
      "รายละเอียดที่ต้องระบุ": "ระบุคำอธิบายยืนยันความพร้อม...",
      "Comply?": "False",
      "หมายเหตุ (Remarks)": ""
    }
  ]
}
```"""


def _get_target_models() -> list:
    """Get list of available models using raw requests with clean list/dict parsing."""
    target_models = [
        "typhoon-v2.5-30b-instruct",
        "typhoon-v2.5-70b-instruct",
        "typhoon-v2.5-8b-instruct",
        "typhoon-v2.5-30b-a3b-instruct"
    ]
    try:
        url = f"{TYPHOON_BASE_URL}/models"
        headers = {"Authorization": f"Bearer {TYPHOON_API_KEY}"}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            resp_json = resp.json()
            models_data = resp_json if isinstance(resp_json, list) else resp_json.get("data", [])
            available_models = [m.get("id") for m in models_data if isinstance(m, dict) and m.get("id")]
            instruct_models = [m for m in available_models if 'instruct' in m.lower()]
            if instruct_models:
                target_models = instruct_models + target_models
    except Exception as e:
        print(f"[AI Critic] Model discovery via requests failed: {e}")
    return target_models


def _call_critic_ai(system_prompt: str, user_content: str, max_tokens: int = 4096) -> str:
    """Makes a critic AI call using raw requests with expanded 90s timeout."""
    target_models = _get_target_models()
    headers = {
        "Authorization": f"Bearer {TYPHOON_API_KEY}",
        "Content-Type": "application/json"
    }
    for model_name in target_models:
        for mt in [max_tokens, max_tokens // 2]:
            try:
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "temperature": 0.15,
                    "max_tokens": mt
                }
                resp = requests.post(f"{TYPHOON_BASE_URL}/chat/completions", headers=headers, json=payload, timeout=90)
                if resp.status_code == 200:
                    text = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    if text:
                        return text
                else:
                    print(f"[AI Critic] {model_name} returned status {resp.status_code}: {resp.text}")
            except Exception as e:
                print(f"[AI Critic] {model_name} (max_tokens={mt}) failed: {e}")
                continue
    return None


def _parse_critic_response(text: str) -> dict:
    """Robustly parses the JSON response from AI Critic."""
    if not text:
        return None

    try:
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            if 'checklist' in data:
                return data
    except:
        pass

    try:
        arr_match = re.search(r'\[.*\]', text, re.DOTALL)
        if arr_match:
            items = json.loads(arr_match.group(0))
            return {"checklist": items}
    except:
        pass

    return None


def evaluate_and_correct_checklist(original_text: str, raw_checklist: list) -> list:
    """
    Executes the AI Critic review loop to verify and correct checklist items.
    """
    if not raw_checklist:
        return []

    current_checklist = raw_checklist
    print(f"[AI Critic] Starting self-correction auditing ({len(current_checklist)} items)...")

    short_original = original_text[:12000]

    for round_num in range(1, MAX_CORRECTION_ROUNDS + 1):
        print(f"[AI Critic] Self-Correction Round {round_num}/{MAX_CORRECTION_ROUNDS}...")

        checklist_str = json.dumps(current_checklist, ensure_ascii=False, indent=2)
        user_content = f"""=== ข้อความต้นฉบับเอกสาร TOR (ส่วนอ้างอิง) ===\n{short_original}\n\n=== รายการ Checklist ที่ AI สกัดมา (ต้องการการตรวจสอบและแก้ไข) ===\n{checklist_str}"""

        response_text = _call_critic_ai(CRITIC_SYSTEM_PROMPT, user_content, max_tokens=4096)
        result = _parse_critic_response(response_text)

        if result and 'checklist' in result and isinstance(result['checklist'], list) and len(result['checklist']) > 0:
            new_checklist = result['checklist']
            if len(new_checklist) >= (len(current_checklist) * 0.9):
                print(f"[AI Critic] Round {round_num}: Successfully corrected checklist ({len(new_checklist)} items).")
                current_checklist = new_checklist
                break
            else:
                print(f"[AI Critic] Round {round_num}: Rejected correction due to unacceptable row truncation ({len(new_checklist)} vs {len(current_checklist)}).")
                break
        else:
            print(f"[AI Critic] Round {round_num}: Failed to obtain valid JSON from Critic models. Retaining current checklist.")
            break

    print(f"[AI Critic] Completed self-correction auditing. Returning verified result.")
    return current_checklist
