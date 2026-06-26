import React, { useState } from 'react';
import { DropZone } from './components/DropZone';
import { ResultActions } from './components/ResultActions';

export const App: React.FC = () => {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [userEmail, setUserEmail] = useState('');
  const [inputEmail, setInputEmail] = useState('');
  const [loginError, setLoginError] = useState('');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [resultData, setResultData] = useState<any>(null);

  const toggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    document.documentElement.setAttribute('data-theme', nextTheme);
  };

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputEmail.endsWith('@realsmart.co.th')) {
      setLoginError('กรุณาเข้าสู่ระบบด้วยบัญชี Google Account ของ realsmart.co.th เท่านั้น');
      return;
    }
    setLoginError('');
    setUserEmail(inputEmail);
    setIsLoggedIn(true);
  };

  return (
    <div style={{ minHeight: '100vh' }}>
      <header className="app-header">
        <div className="brand">
          <span style={{ fontSize: '2rem' }}>⚡</span> 
          <span>TOR Checklist AI Platform</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {isLoggedIn && <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>👤 {userEmail}</span>}
          {isLoggedIn && (
            <button className="btn-secondary" style={{ padding: '0.4rem 1rem', fontSize: '0.8rem' }} onClick={() => setIsLoggedIn(false)}>
              ออกจากระบบ
            </button>
          )}
          <button className="theme-toggle" onClick={toggleTheme}>
            {theme === 'dark' ? '☀️ Light Mode' : '🌙 Dark Mode'}
          </button>
        </div>
      </header>

      <main className="main-container">
        {!isLoggedIn ? (
          <div className="glass-panel login-box">
            <h1 style={{ fontSize: '2rem' }}>เข้าสู่ระบบ (Login)</h1>
            <p style={{ marginTop: '0.5rem' }}>เฉพาะบุคลากรที่มีบัญชี @realsmart.co.th</p>
            <form onSubmit={handleLogin}>
              <input 
                type="email" 
                placeholder="Google Account (user@realsmart.co.th)" 
                required 
                value={inputEmail}
                onChange={(e) => setInputEmail(e.target.value)}
                className="input-field" 
              />
              {loginError && <p style={{ color: 'var(--warning-color)', marginBottom: '1rem', fontSize: '0.9rem' }}>{loginError}</p>}
              <button type="submit" className="btn-primary" style={{ width: '100%', marginTop: '0.5rem' }}>
                Login with Google Account
              </button>
            </form>
          </div>
        ) : !resultData ? (
          <DropZone 
            onUploadSuccess={(data) => setResultData(data)} 
            onError={(msg) => alert(msg)} 
          />
        ) : (
          <ResultActions 
            resultData={resultData} 
            onReset={() => setResultData(null)} 
          />
        )}
      </main>
    </div>
  );
};

export default App;
