"""
AI Critic Agent for TOR Checklist System.

Acts as a Quality Auditor that reviews and corrects the AI-generated checklist
items for spelling accuracy, logical coherence, completeness of required fields,
and compliance with Thai government procurement terminology.
"""
import os
import json
import re
from openai import OpenAI

# OpenTyphoon AI Configuration (shared with ai_engine)
TYPHOON_API_KEY = os.getenv("TYPHOON_API_KEY", "sk-Rmn1bvzNfpruBxlQWH9umkZRPPFTWbU4OtMtczKRUsGxnWmG")
TYPHOON_BASE_URL = "https://api.opentyphoon.ai/v1"

client = OpenAI(
    api_key=TYPHOON_API_KEY,
    base_url=TYPHOON_BASE_URL
)

MAX_CORRECTION_ROUNDS = 3

CRITIC_SYSTEM_PROMPT = """คุณคือผู้ตรวจสอบคุณภาพ (Quality Auditor) ระดับอาวุโสด้านเอกสารจัดซื้อจัดจ้างภาครัฐไทย 
หน้าที่ของคุณคือตรวจทานรายการ Checklist ที่ได้จากการสกัดข้อกำหนดเอกสาร TOR (Terms of Reference) แล้วแก้ไขให้ถูกต้องสมบูรณ์ที่สุด

กฎการตรวจสอบ:
1. ตรวจคำสะกด: ตรวจหาคำสะกดผิด สระลอย พยัญชนะผิดตำแหน่ง วรรณยุกต์ผิด แล้วแก้ไขให้ถูกต้อง
   ตัวอย่าง: "วัตถุประสงค ์" → "วัตถุประสงค์", "หลักการและเหุตผล" → "หลักการและเหตุผล", "ประสิทธิิภาพ" → "ประสิทธิภาพ"
2. ตรวจความหมาย: อ่านข้อความทุกบรรทัดแล้วประเมินว่าอ่านได้ใจความ สมเหตุสมผล (Make sense) หรือไม่ หากมีข้อความไม่สมบูรณ์หรือขาดหาย ให้แก้ไขให้อ่านรู้เรื่อง
3. ตรวจการใช้คำ: ตรวจให้แน่ใจว่าใช้คำศัพท์ที่ถูกต้องตามมาตรฐานของหน่วยงานราชการไทย
   ตัวอย่าง: ใช้ "ผู้ยื่นข้อเสนอ" ไม่ใช่ "ผู้เสนอราคา" (ถ้าเอกสารต้นฉบับใช้คำนี้), ใช้ "นิติบุคคล" ไม่ใช่ "บริษัท" (เมื่อเป็นทางการ)
4. ตรวจความสอดคล้อง: ตรวจให้แน่ใจว่าเนื้อหาในแต่ละบรรทัดสอดคล้องกับหมวดหมู่หลักและหัวข้อย่อยที่ระบุไว้
5. ตรวจความซ้ำซ้อน: หากมีข้อความซ้ำกัน 100% ให้รวมเป็นรายการเดียว
6. ห้ามเปลี่ยนเนื้อหาหลัก: ห้ามเพิ่มข้อกำหนดใหม่ที่ไม่มีในต้นฉบับ ห้ามลบข้อกำหนดที่ถูกต้องออก ให้แก้ไขเฉพาะจุดบกพร่องเท่านั้น
7. ตรวจสอบความครบถ้วนของข้อมูล (สำคัญมาก!): 
   - ฟิลด์ "ชื่อเอกสารที่ใช้ยื่น": หากพบว่าเป็นค่าว่าง "" ให้เติมชื่อเอกสารที่เหมาะสม เช่น "ข้อเสนอทางเทคนิค (Technical Proposal)" หรือ "หนังสือรับรองผลงาน" เสมอ
   - ฟิลด์ "รายละเอียดที่ต้องระบุ": หากพบว่าเป็นค่าว่าง "" ให้วิเคราะห์จากข้อกำหนดแล้วเขียนอธิบายสิ่งที่ต้องระบุ เช่น "ระบุยืนยันความพร้อมและอธิบายรายละเอียดการดำเนินงานตามข้อกำหนด" หรือ "แนบเอกสารหลักฐานพร้อมลงนามรับรอง" เสมอ ห้ามปล่อยว่างเด็ดขาด!
8. ห้ามสร้างข้อความมั่วซั่ว (Gibberish) หรือข้อความซ้ำๆ เช่น 'PPPPPPPPP' หรือตัวอักษรประหลาดเด็ดขาด หากพบรายการที่มั่วซั่วไม่มีความหมาย ให้ตัดทิ้งทันที!

ข้อมูลที่ได้รับ:
- "original_text": ข้อความต้นฉบับจากเอกสาร TOR (ใช้เป็นข้อมูลอ้างอิงในการตรวจสอบ)
- "checklist": รายการ Checklist ที่ต้องตรวจทาน (JSON Array)

ผลลัพธ์ที่ต้องตอบกลับ:
ตอบกลับเป็น JSON Object ที่มี 2 ฟิลด์:
{
  "corrections_made": จำนวนจุดที่แก้ไข (integer),
  "checklist": [ ... รายการ Checklist ที่ผ่านการตรวจทานและแก้ไขแล้ว (JSON Array) ... ]
}

ข้อย้ำ: ตอบกลับมาเป็น JSON เท่านั้น ห้ามมีข้อความอื่นปน"""


def _parse_critic_response(response_text: str) -> dict:
    """Parses the AI Critic response, handling potential JSON issues."""
    try:
        return json.loads(response_text)
    except:
        pass

    try:
        obj_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if obj_match:
            return json.loads(obj_match.group(0))
    except:
        pass

    try:
        arr_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if arr_match:
            data = json.loads(arr_match.group(0))
            return {"corrections_made": -1, "checklist": data}
    except:
        pass

    object_matches = re.findall(r'\{[^{}]+\}', response_text, re.DOTALL)
    valid_objs = []
    for obj_str in object_matches:
        try:
            obj = json.loads(obj_str)
            if 'ลำดับ' in obj or 'หมวดหมู่หลัก' in obj:
                valid_objs.append(obj)
        except:
            pass
    if valid_objs:
        return {"corrections_made": -1, "checklist": valid_objs}

    return None


def evaluate_and_correct_checklist(original_text: str, raw_checklist: list) -> list:
    """
    Runs the AI Critic Agent to review and correct the checklist.
    Uses a self-correction loop with up to MAX_CORRECTION_ROUNDS iterations.

    Args:
        original_text: The original TOR document text (for reference)
        raw_checklist: The AI-generated checklist items to review

    Returns:
        The corrected checklist items (list of dicts)
    """
    current_checklist = raw_checklist

    # Truncate original text to fit within context limits
    ref_text = original_text[:15000]

    target_models = [
        "typhoon-v2.5-30b-a3b-instruct",
        "typhoon-v2.1-12b-instruct",
        "typhoon-v2-70b-instruct",
        "typhoon-v2-8b-instruct",
    ]

    for round_num in range(1, MAX_CORRECTION_ROUNDS + 1):
        print(f"[AI Critic] Self-Correction Round {round_num}/{MAX_CORRECTION_ROUNDS}...")

        user_content = json.dumps({
            "original_text": ref_text,
            "checklist": current_checklist
        }, ensure_ascii=False)

        success = False
        for model_name in target_models:
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=0.1,
                    max_tokens=4096 # Upgraded to 4096 to prevent truncation
                )

                response_text = response.choices[0].message.content.strip()
                result = _parse_critic_response(response_text)

                if result and 'checklist' in result and len(result['checklist']) > 0:
                    corrections = result.get('corrections_made', -1)
                    new_checklist = result['checklist']

                    print(f"[AI Critic] Round {round_num}: {corrections} corrections made, {len(new_checklist)} items returned")

                    if corrections == 0:
                        print(f"[AI Critic] No corrections needed. Quality verified! ✓")
                        return new_checklist

                    current_checklist = new_checklist
                    success = True
                    break
                else:
                    print(f"[AI Critic] Round {round_num}: Could not parse response from {model_name}")
                    continue

            except Exception as e:
                print(f"[AI Critic] Round {round_num}: Model {model_name} failed: {e}")
                continue

        if not success:
            print(f"[AI Critic] Round {round_num}: All models failed. Using current checklist.")
            break

    print(f"[AI Critic] Completed {round_num} correction rounds. Returning best result.")
    return current_checklist


if __name__ == '__main__':
    test_checklist = [
        {
            "Status": "",
            "ลำดับ": "1.",
            "หมวดหมู่หลัก": "หลักการและเหุตผล",
            "หัวข้อย่อย": "หลักการและเหุตผล",
            "ข้อกำหนด / รายละเอียด (Requirement / Details)": "ตามรฐัธรรมนูญแห่งราชอาณาจักรไทย",
            "ชื่อเอกสารที่ใช้ยื่น": "",
            "รายละเอียดที่ต้องระบุ": "",
            "Comply?": "False",
            "หมายเหตุ (Remarks)": ""
        }
    ]
    result = evaluate_and_correct_checklist("ตามรัฐธรรมนูญแห่งราชอาณาจักรไทย", test_checklist)
    print(json.dumps(result, ensure_ascii=False, indent=2))
