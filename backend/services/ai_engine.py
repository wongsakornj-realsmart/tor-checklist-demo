import os
import json
import re
from openai import OpenAI

# OpenTyphoon AI Configuration
TYPHOON_API_KEY = os.getenv("TYPHOON_API_KEY", "sk-Rmn1bvzNfpruBxlQWH9umkZRPPFTWbU4OtMtczKRUsGxnWmG")
TYPHOON_BASE_URL = "https://api.opentyphoon.ai/v1"

client = OpenAI(
    api_key=TYPHOON_API_KEY,
    base_url=TYPHOON_BASE_URL
)

def generate_tor_checklist(text_content: str) -> list:
    """
    Calls OpenTyphoon AI to parse TOR text content and extract structured items matching the 9 columns.
    Uses dummy generic prompt placeholders to strictly prevent Few-Shot Overfitting / Example Hallucination.
    """
    clean_text = text_content[:45000] # Limit to ~45k chars to prevent timeout/context limit in demo

    system_prompt = """คุณคือผู้เชี่ยวชาญด้านการจัดซื้อจัดจ้างภาครัฐและวิศวกรรมระบบ AI หน้าที่ของคุณคือวิเคราะห์ข้อความจากเอกสาร TOR (Terms of Reference) ที่ผู้ใช้ส่งมา และสกัดข้อกำหนดต่างๆ ออกมาเป็นตาราง Checklist เพื่อตรวจสอบความสอดคล้อง (Compliance)

กรุณาวิเคราะห์ข้อความและแปลงเป็นโครงสร้าง JSON Array โดยแต่ละรายการ (Object) จะต้องมีฟิลด์ดังต่อไปนี้:
1. "Status": ว่างไว้ ("")
2. "ลำดับ": หมายเลขลำดับของข้อกำหนด (เช่น "1.", "1.1", "2.")
3. "หมวดหมู่หลัก": ชื่อหมวดหมู่หลัก (เช่น "ความเป็นมา", "วัตถุประสงค์", "คุณสมบัติของผู้ยื่นข้อเสนอ", "ขอบเขตการดำเนินงาน")
4. "หัวข้อย่อย": ชื่อหัวข้อย่อย
5. "ข้อกำหนด / รายละเอียด (Requirement / Details)": เนื้อหาข้อกำหนดโดยละเอียดจากเอกสารจริง
6. "ชื่อเอกสารที่ใช้ยื่น": ชื่อเอกสารที่ผู้รับจ้าง/ผู้ยื่นซองต้องเตรียมยื่น (เช่น "ข้อเสนอทางเทคนิค", "หนังสือรับรองผลงาน")
7. "รายละเอียดที่ต้องระบุ": สิ่งที่ต้องระบุในเอกสารนั้นๆ
8. "Comply?": "False"
9. "หมายเหตุ (Remarks)": ว่างไว้ ("")

ตัวอย่างโครงสร้าง Output (ห้ามลอกข้อความในตัวอย่างนี้ไปตอบเด็ดขาด ให้ใช้เนื้อหาจากเอกสารจริงเท่านั้น):
[
  {
    "Status": "",
    "ลำดับ": "1.",
    "หมวดหมู่หลัก": "ความเป็นมา หรือ วัตถุประสงค์",
    "หัวข้อย่อย": "ระบุหัวข้อย่อยจากเนื้อหาจริง",
    "ข้อกำหนด / รายละเอียด (Requirement / Details)": "ระบุเนื้อหาข้อกำหนดจากเอกสารจริงที่ผู้ใช้ส่งมาเท่านั้น (ห้ามใช้ข้อความสมมติ)",
    "ชื่อเอกสารที่ใช้ยื่น": "ระบุชื่อเอกสารที่ต้องใช้ยื่นตามจริง (เช่น ข้อเสนอทางเทคนิค, หนังสือรับรอง)",
    "รายละเอียดที่ต้องระบุ": "ระบุรายละเอียดที่ต้องระบุในเอกสารนั้นๆ",
    "Comply?": "False",
    "หมายเหตุ (Remarks)": ""
  }
]

คำเตือนสำคัญ: ห้ามนำข้อความในตัวอย่างไปใส่ในผลลัพธ์เด็ดขาด! ให้สกัดเฉพาะเนื้อหาจริงจากเอกสารที่ผู้ใช้ส่งมาเท่านั้น ตอบกลับมาเป็น JSON Array เท่านั้น ห้ามมีข้อความอื่นปน
"""

    last_error = None
    
    # Official OpenTyphoon API latest model iterations (v2.5, v2.1, v2, v1.5)
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
        print(f"Discovered OpenTyphoon models: {available_models}")
        instruct_models = [m for m in available_models if 'instruct' in m.lower()]
        if instruct_models:
            target_models = instruct_models + target_models
    except Exception as list_err:
        print(f"Failed to list models (normal for some client versions): {list_err}")

    for model_name in target_models:
        for max_tokens in [2048, 1024]: # Robust fallback for max_tokens restrictions
            try:
                print(f"Attempting OpenTyphoon AI with model: {model_name} (max_tokens: {max_tokens})...")
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
                print(f"Successfully received response from {model_name}")
                
                try:
                    json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(0))
                        return data
                    else:
                        return json.loads(response_text)
                except Exception as json_err:
                    print(f"JSON decode error (likely max_tokens cutoff): {json_err}. Repairing JSON objects...")
                    object_matches = re.findall(r'\{[^{}]+\}', response_text, re.DOTALL)
                    if object_matches:
                        valid_objs = []
                        for obj_str in object_matches:
                            try:
                                valid_objs.append(json.loads(obj_str))
                            except:
                                pass
                        if valid_objs:
                            print(f"Successfully salvaged {len(valid_objs)} JSON objects from OpenTyphoon output!")
                            return valid_objs
                    raise json_err

            except Exception as e:
                print(f"Model {model_name} (max_tokens: {max_tokens}) failed with error: {e}")
                last_error = str(e)
                continue

    print(f"All AI models failed (Last error: {last_error}). Using direct text parsing fallback on actual document content...")
    lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
    extracted_reqs = []
    for line in lines:
        if any(keyword in line for keyword in ["ผู้รับจ้าง", "ต้อง", "ข้อกำหนด", "วัตถุประสงค์", "ขอบเขต", "โครงการ", "ระบบ"]):
            extracted_reqs.append(line)
            if len(extracted_reqs) >= 5: # Grab top 5 key requirements
                break
    
    if not extracted_reqs and lines:
        extracted_reqs = lines[:5]

    if not extracted_reqs:
        extracted_reqs = ["ไม่พบข้อความข้อกำหนดในเอกสาร (เอกสารอาจว่างเปล่าหรือสแกนไม่ชัดเจน)"]

    result_rows = []
    for idx, req in enumerate(extracted_reqs, 1):
        result_rows.append({
            "Status": "",
            "ลำดับ": f"{idx}.",
            "หมวดหมู่หลัก": "ข้อกำหนดโครงการ (Direct Extract)",
            "หัวข้อย่อย": "รายละเอียดข้อกำหนด",
            "ข้อกำหนด / รายละเอียด (Requirement / Details)": req,
            "ชื่อเอกสารที่ใช้ยื่น": "ข้อเสนอทางเทคนิค (Technical Proposal)",
            "รายละเอียดที่ต้องระบุ": f"ยืนยันความพร้อมและปฏิบัติตามข้อกำหนด: {req[:50]}...",
            "Comply?": "False",
            "หมายเหตุ (Remarks)": f"AI API Exception Fallback: {last_error}"
        })
    return result_rows
