import React, { useState, useRef, useEffect } from 'react';

interface DropZoneProps {
  onUploadSuccess: (data: any) => void;
  onError: (msg: string) => void;
}

export const DropZone: React.FC<DropZoneProps> = ({ onUploadSuccess, onError }) => {
  const [dragActive, setDragActive] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [progress, setProgress] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let interval: any;
    if (isProcessing) {
      interval = setInterval(() => {
        setProgress((prev) => (prev < 90 ? prev + 10 : prev));
      }, 800);
    }
    return () => clearInterval(interval);
  }, [isProcessing]);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const processFile = async (file: File) => {
    setIsProcessing(true);
    setProgress(15);
    setStatusText('กำลังอัปโหลดและประมวลผล OCR (รองรับ PDF, DOCX, XLSX, สแกน)...');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const endpoint = 'https://tor-checklist-demo.onrender.com/api/upload';
      
      setTimeout(() => {
        setStatusText('OpenTyphoon AI กำลังวิเคราะห์และจัดหมวดหมู่ 9 คอลัมน์...');
        setProgress(60);
      }, 3000);

      setTimeout(() => {
        setStatusText('กำลังสร้างตาราง Excel และอัปโหลดขึ้น Google Drive กลาง...');
        setProgress(85);
      }, 6000);

      const res = await fetch(endpoint, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        throw new Error('Server upload failed');
      }

      const data = await res.json();
      setProgress(100);
      setTimeout(() => {
        setIsProcessing(false);
        onUploadSuccess(data);
      }, 1000);

    } catch (e: any) {
      console.warn("Backend fetch failed, triggering interactive full demo simulation mode...", e);
      onError("ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ Backend ได้ ระบบกำลังเปิดโหมดจำลองเดโม่ (Demo Simulation Mode)...");
      
      setTimeout(() => {
        setProgress(100);
        setIsProcessing(false);
        const cleanName = file.name.replace(/\.[^/.]+$/, "");
        onUploadSuccess({
          success: true,
          filename: cleanName + "_Checklist.xlsx",
          webViewLink: "https://drive.google.com/file/d/demo_mock_view_link/view?usp=sharing",
          webContentLink: "https://drive.google.com/uc?export=download&id=demo_mock_view_link",
          data: [
            {
              "Status": "",
              "ลำดับ": "1.",
              "หมวดหมู่หลัก": "ข้อมูลทั่วไปโครงการ",
              "หัวข้อย่อย": "ชื่อโครงการ / เอกสาร",
              "ข้อกำหนด / รายละเอียด (Requirement / Details)": `เอกสารข้อกำหนดและขอบเขตของงาน (TOR) สำหรับโครงการ: ${cleanName}`,
              "ชื่อเอกสารที่ใช้ยื่น": "ข้อเสนอทางเทคนิค (Technical Proposal)",
              "รายละเอียดที่ต้องระบุ": `ระบุความเข้าใจในความเป็นมา วัตถุประสงค์ และเป้าหมายของโครงการ ${cleanName} พร้อมยืนยันความพร้อมและศักยภาพในการดำเนินงาน`,
              "Comply?": "False",
              "หมายเหตุ (Remarks)": `ประมวลผลจากไฟล์: ${file.name} (Demo Simulation)`
            },
            {
              "Status": "",
              "ลำดับ": "2.",
              "หมวดหมู่หลัก": "ขอบเขตการดำเนินงาน (Scope of Work)",
              "หัวข้อย่อย": "ข้อกำหนดทางเทคนิคและการดำเนินงาน",
              "ข้อกำหนด / รายละเอียด (Requirement / Details)": `ผู้รับจ้างจะต้องดำเนินการตามข้อกำหนดทางเทคนิคและขอบเขตงานที่ระบุในเอกสาร ${file.name} อย่างครบถ้วนสมบูรณ์`,
              "ชื่อเอกสารที่ใช้ยื่น": "ข้อเสนอทางเทคนิค (แผนการดำเนินงาน)",
              "รายละเอียดที่ต้องระบุ": `นำเสนอแผนการดำเนินงาน (Work Plan) และรายละเอียดทางเทคนิคที่สอดคล้องกับข้อกำหนดของ ${cleanName}`,
              "Comply?": "False",
              "หมายเหตุ (Remarks)": ""
            }
          ]
        });
      }, 7000);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  if (isProcessing) {
    return (
      <div className="glass-panel progress-card">
        <div className="spinner"></div>
        <h2>{statusText}</h2>
        <div className="progress-bar-container">
          <div className="progress-bar-fill" style={{ width: `${progress}%` }}></div>
        </div>
        <p>ขับเคลื่อนด้วย OpenTyphoon AI และ Google Drive Central Storage</p>
      </div>
    );
  }

  return (
    <div className="glass-panel">
      <h2 style={{ textAlign: 'center', marginBottom: '0.5rem' }}>สร้าง TOR Checklist อัตโนมัติ</h2>
      <p style={{ textAlign: 'center', marginBottom: '2.5rem' }}>รองรับไฟล์ PDF, DOCX, XLSX และไฟล์สแกน (ทำงานร่วมกับระบบ OCR อัตโนมัติ)</p>
      
      <div 
        className={`dropzone-container ${dragActive ? 'drag-active' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input 
          ref={inputRef} 
          type="file" 
          style={{ display: 'none' }} 
          onChange={handleChange} 
        />
        <div className="upload-icon">📄</div>
        <h3>ลากไฟล์ TOR ของคุณมาวางที่นี่</h3>
        <p style={{ margin: '1rem 0 2rem' }}>หรือคลิกเพื่อเลือกไฟล์ (Import File)</p>
        <button className="btn-primary" onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}>
          นำเข้าไฟล์ TOR (Import File)
        </button>
      </div>
    </div>
  );
};
