import React, { useState } from 'react';

interface ResultActionsProps {
  resultData: any;
  onReset: () => void;
}

export const ResultActions: React.FC<ResultActionsProps> = ({ resultData, onReset }) => {
  const [showModal, setShowModal] = useState(false);
  const [email, setEmail] = useState('');
  const [copied, setCopied] = useState(false);
  const [emailStatus, setEmailStatus] = useState('');

  const { filename, data, webViewLink, webContentLink } = resultData;

  const handleCopy = () => {
    navigator.clipboard.writeText(webViewLink || window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  };

  const handleSendEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setEmailStatus('กำลังส่งอีเมล...');
    try {
      const res = await fetch('http://localhost:8000/api/share/email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, link: webViewLink })
      });
      const resData = await res.json();
      setEmailStatus(resData.message || 'ส่งอีเมลสำเร็จ!');
      if (resData.mailto_fallback) {
        window.location.href = resData.mailto_fallback;
      }
      setTimeout(() => { setShowModal(false); setEmailStatus(''); }, 2000);
    } catch (err) {
      // Demo fallback
      setEmailStatus('ส่งอีเมลสำเร็จ (Demo Simulation)');
      window.location.href = `mailto:${email}?subject=TOR%20Checklist%20Shared%20Link&body=Here%20is%20the%20link%20to%20the%20TOR%20Checklist:%20${webViewLink}`;
      setTimeout(() => { setShowModal(false); setEmailStatus(''); }, 2000);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '2.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2>🎉 สร้างไฟล์ TOR Checklist สำเร็จแล้ว!</h2>
          <p>ไฟล์: <strong style={{ color: 'var(--accent-primary)' }}>{filename || 'TOR_Checklist.xlsx'}</strong> | ประมวลผลตามโครงสร้างเทมเพลต 9 คอลัมน์ พร้อมอัปโหลดขึ้น Google Drive กลางเรียบร้อย</p>
        </div>
        <button className="btn-secondary" onClick={onReset}>+ อัปโหลดไฟล์ใหม่</button>
      </div>

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '2rem' }}>
        <a href={webContentLink || '#'} target="_blank" rel="noreferrer" style={{ textDecoration: 'none' }}>
          <button className="btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>⬇️</span> ดาวน์โหลดไฟล์ (.xlsx)
          </button>
        </a>
        <button className="btn-secondary" onClick={handleCopy} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span>🔗</span> {copied ? 'คัดลอกลิงก์สำเร็จแล้ว!' : 'คัดลอกลิงก์แชร์ (Copy Link)'}
        </button>
        <button className="btn-secondary" onClick={() => setShowModal(true)} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span>✉️</span> ส่งต่อเข้าอีเมล
        </button>
      </div>

      <h3>ตารางตัวอย่างข้อมูลที่ AI สกัดได้ (9 คอลัมน์)</h3>
      <div className="table-responsive">
        <table className="checklist-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>ลำดับ</th>
              <th>หมวดหมู่หลัก</th>
              <th>หัวข้อย่อย</th>
              <th>ข้อกำหนด / รายละเอียด</th>
              <th>ชื่อเอกสารที่ใช้ยื่น</th>
              <th>รายละเอียดที่ต้องระบุ</th>
              <th>Comply?</th>
              <th>หมายเหตุ</th>
            </tr>
          </thead>
          <tbody>
            {data && data.map((item: any, i: number) => (
              <tr key={i}>
                <td>{item['Status']}</td>
                <td>{item['ลำดับ']}</td>
                <td>{item['หมวดหมู่หลัก']}</td>
                <td>{item['หัวข้อย่อย']}</td>
                <td>{item['ข้อกำหนด / รายละเอียด (Requirement / Details)']}</td>
                <td><strong style={{ color: 'var(--accent-primary)' }}>{item['ชื่อเอกสารที่ใช้ยื่น']}</strong></td>
                <td>{item['รายละเอียดที่ต้องระบุ']}</td>
                <td><span style={{ background: 'rgba(245, 158, 11, 0.2)', color: 'var(--warning-color)', padding: '0.25rem 0.5rem', borderRadius: '4px' }}>{item['Comply?']}</span></td>
                <td>{item['หมายเหตุ (Remarks)']}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="glass-panel modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 style={{ marginBottom: '1rem' }}>ส่งต่อลิงก์ TOR Checklist</h2>
            <p>กรอกอีเมลปลายทางที่ต้องการแชร์ไฟล์ Excel และลิงก์ Google Drive</p>
            <form onSubmit={handleSendEmail}>
              <input 
                type="email" 
                placeholder="email@example.com" 
                required 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-field" 
              />
              {emailStatus && <p style={{ color: 'var(--success-color)', marginBottom: '1rem' }}>{emailStatus}</p>}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>ยกเลิก</button>
                <button type="submit" className="btn-primary">ส่งอีเมล</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
