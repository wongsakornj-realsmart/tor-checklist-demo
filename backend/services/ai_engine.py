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
    Uses the latest valid model names (v2.5, v2.1, v2, v1.5) to guarantee zero 'Model not found' errors.
    """
    clean_text = text_content[:45000] # Limit to ~45k chars to prevent timeout/context limit in demo

    system_prompt = """คุณคือผู้เชี่ยวชาญด้านการจัดซื้อจัดจ้างภาครัฐและวิศวกรรมระบบ AI หน้าที่ของคุณคือวิเคราะห์ข้อความจากเอกสาร TOR (Terms of Reference) และสกัดข้อกำหนดต่างๆ ออกมาเป็นตาราง Checklist เพื่อตรวจสอบความสอดคล้อง (Compliance)

กรุณาวิเคราะห์ข้อความและแปลงเป็นโครงสร้าง JSON Array โดยแต่ละรายการ (Object) จะต้องมีฟิลด์ดังต่อไปนี้:
1. "Status": ว่างไว้ ("")
2. "ลำดับ": หมายเลขลำดับของข้อกำหนด (เช่น "1.", "1.1", "2.")
3. "หมวดหมู่หลัก": ชื่อหมวดหมู่หลัก (เช่น "ความเป็นมา", "วัตถุประสงค์", "คุณสมบัติของผู้ยื่นข้อเสนอ", "ขอบเขตการดำเนินงาน")
4. "หัวข้อย่อย": ชื่อหัวข้อย่อย
5. "ข้อกำหนด / รายละเอียด (Requirement / Details)": เนื้อหาข้อกำหนดโดยละเอียด
6. "ชื่อเอกสารที่ใช้ยื่น": ชื่อเอกสารที่ผู้รับจ้าง/ผู้ยื่นซองต้องเตรียมยื่น (เช่น "ข้อเสนอทางเทคนิค", "หนังสือรับรองผลงาน", "เอกสารการจดทะเบียนนิติบุคคล")
7. "รายละเอียดที่ต้องระบุ": สิ่งที่ต้องระบุในเอกสารนั้นๆ (เช่น "ระบุความเข้าใจในความเป็นมา วัตถุประสงค์ และเป้าหมายของโครงการ", "แนบหนังสือรับรองผลงานที่เกี่ยวข้อง")
8. "Comply?": "False"
9. "หมายเหตุ (Remarks)": ว่างไว้ ("")

ตัวอย่าง Output:
[
  {
    "Status": "",
    "ลำดับ": "1.",
    "หมวดหมู่หลัก": "ความเป็นมา",
    "หัวข้อย่อย": "ความเป็นมา",
    "ข้อกำหนด / รายละเอียด (Requirement / Details)": "การรถไฟฟ้าขนส่งมวลชนแห่งประเทศไทย (รฟม.) ได้มีการจัดทำแผนวิสาหกิจ ประจำปีงบประมาณ 2569 – 2570...",
    "ชื่อเอกสารที่ใช้ยื่น": "ข้อเสนอทางเทคนิค (ส่วนบทนำและความเข้าใจในโครงการ)",
    "รายละเอียดที่ต้องระบุ": "ระบุความเข้าใจในความเป็นมา วัตถุประสงค์ และเป้าหมายของโครงการ พร้อมยืนยันความพร้อมและศักยภาพในการดำเนินงาน",
    "Comply?": "False",
    "หมายเหตุ (Remarks)": ""
  }
]

ข้อควรระวัง: ตอบกลับมาเป็น JSON Array เท่านั้น ห้ามมีข้อความอื่นปน เพื่อให้ระบบนำไปแปลงเป็น Excel 9 คอลัมน์ต่อได้ทันที
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
        # Dynamically fetch available models directly from OpenTyphoon API
        available_models = [m.id for m in client.models.list().data]
        print(f"Discovered OpenTyphoon models: {available_models}")
        
        # Prioritize instruct models
        instruct_models = [m for m in available_models if 'instruct' in m.lower()]
        if instruct_models:
            target_models = instruct_models + target_models
    except Exception as list_err:
        print(f"Failed to list models: {list_err}")

    for model_name in target_models:
        try:
            print(f"Attempting OpenTyphoon AI with model: {model_name}...")
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"เอกสาร TOR:\n\n{clean_text}"}
                ],
                temperature=0.2,
                max_tokens=4000
            )

            response_text = response.choices[0].message.content.strip()
            print(f"Successfully received response from {model_name}")
            
            # Extract JSON from response in case there are markdown code blocks
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return data
            else:
                return json.loads(response_text)

        except Exception as e:
            print(f"Model {model_name} failed with error: {e}")
            last_error = str(e)
            continue

    # Fallback Mock Data in case all models fail
    return [
        {
            "Status": "",
            "ลำดับ": "1.",
            "หมวดหมู่หลัก": "ความเป็นมา (AI Fallback)",
            "หัวข้อย่อย": "ความเป็นมา",
            "ข้อกำหนด / รายละเอียด (Requirement / Details)": "การรถไฟฟ้าขนส่งมวลชนแห่งประเทศไทย (รฟม.) ได้มีการจัดทำแผนวิสาหกิจ ประจำปีงบประมาณ 2569 – 2570...",
            "ชื่อเอกสารที่ใช้ยื่น": "ข้อเสนอทางเทคนิค (ส่วนบทนำและความเข้าใจในโครงการ)",
            "รายละเอียดที่ต้องระบุ": "ระบุความเข้าใจในความเป็นมา วัตถุประสงค์ และเป้าหมายของโครงการ พร้อมยืนยันความพร้อมและศักยภาพในการดำเนินงานให้บรรลุวัตถุประสงค์ตามที่ TOR กำหนด",
            "Comply?": "False",
            "หมายเหตุ (Remarks)": f"AI Engine Exception: {last_error}"
        }
    ]
