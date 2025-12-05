import React, { useState, useEffect } from 'react';
import './Settings.css';

const Settings = ({ onSave }) => {
    const [settings, setSettings] = useState({
        // API Settings
        geminiApiKey: '',
        sapUsername: '',
        sapPassword: '',

        // Project Settings
        defaultProjectsDir: 'Data/projects',
        extractionMode: 'basic',

        // Step 1 Settings
        step1DefaultColumns: ['Posting Date', 'Doc Number', 'Amount', 'Quantity', 'Incoterms'],
        dateFormat: 'YYYY-MM-DD',

        // UI Settings (Optional)
        theme: 'light',
        language: 'ko'
    });

    const [showPassword, setShowPassword] = useState(false);
    const [saveStatus, setSaveStatus] = useState('');

    // Load settings on mount
    useEffect(() => {
        loadSettings();
    }, []);

    const loadSettings = async () => {
        try {
            // Try loading from backend
            const response = await fetch('/api/settings');
            if (response.ok) {
                const data = await response.json();
                setSettings(prev => ({ ...prev, ...data }));
            }
        } catch (error) {
            // Fallback to localStorage
            const savedSettings = localStorage.getItem('app_settings');
            if (savedSettings) {
                setSettings(prev => ({ ...prev, ...JSON.parse(savedSettings) }));
            }
        }
    };

    const handleChange = (field, value) => {
        setSettings(prev => ({ ...prev, [field]: value }));
    };

    const handleColumnToggle = (column) => {
        setSettings(prev => {
            const columns = prev.step1DefaultColumns.includes(column)
                ? prev.step1DefaultColumns.filter(c => c !== column)
                : [...prev.step1DefaultColumns, column];
            return { ...prev, step1DefaultColumns: columns };
        });
    };

    const handleSave = async () => {
        try {
            // Save to localStorage
            localStorage.setItem('app_settings', JSON.stringify(settings));

            // Try saving to backend
            try {
                await fetch('/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(settings)
                });
            } catch (e) {
                console.warn('Backend save failed, using localStorage only');
            }

            setSaveStatus('저장 완료!');
            setTimeout(() => setSaveStatus(''), 3000);

            if (onSave) onSave(settings);
        } catch (error) {
            setSaveStatus('저장 실패: ' + error.message);
        }
    };

    const handleFolderSelect = async () => {
        try {
            const response = await fetch('/api/select-folder', { method: 'POST' });
            const data = await response.json();
            if (data.folderPath) {
                handleChange('defaultProjectsDir', data.folderPath);
            }
        } catch (error) {
            alert('폴더 선택 실패: ' + error.message);
        }
    };

    const availableColumns = [
        'Posting Date',
        'Doc Number',
        'Amount',
        'Quantity',
        'Incoterms',
        'Currency',
        'Document Type',
        'Vendor',
        'Material'
    ];

    return (
        <div className="settings-container">
            <div className="settings-header">
                <h1>⚙️ 설정</h1>
                <button onClick={handleSave} className="save-btn">
                    💾 저장
                </button>
            </div>

            {saveStatus && (
                <div className={`save-status ${saveStatus.includes('실패') ? 'error' : 'success'}`}>
                    {saveStatus}
                </div>
            )}

            <div className="settings-content">

                {/* API Settings */}
                <section className="settings-section">
                    <h2>🔐 API 설정</h2>

                    <div className="setting-group">
                        <label>Gemini API Key</label>
                        <div className="password-input-group">
                            <input
                                type={showPassword ? 'text' : 'password'}
                                value={settings.geminiApiKey}
                                onChange={(e) => handleChange('geminiApiKey', e.target.value)}
                                placeholder="sk-..."
                            />
                            <button
                                onClick={() => setShowPassword(!showPassword)}
                                className="toggle-password-btn"
                            >
                                {showPassword ? '👁️' : '👁️‍🗨️'}
                            </button>
                        </div>
                        <p className="setting-hint">Gemini API 키는 Config/api_config.py에도 저장됩니다</p>
                    </div>

                    <div className="setting-group">
                        <label>SAP Username (선택)</label>
                        <input
                            type="text"
                            value={settings.sapUsername}
                            onChange={(e) => handleChange('sapUsername', e.target.value)}
                            placeholder="SAP 사용자명"
                        />
                    </div>

                    <div className="setting-group">
                        <label>SAP Password (선택)</label>
                        <input
                            type="password"
                            value={settings.sapPassword}
                            onChange={(e) => handleChange('sapPassword', e.target.value)}
                            placeholder="SAP 비밀번호"
                        />
                    </div>
                </section>

                {/* Project Settings */}
                <section className="settings-section">
                    <h2>📁 프로젝트 설정</h2>

                    <div className="setting-group">
                        <label>기본 프로젝트 저장 폴더</label>
                        <div className="folder-input-group">
                            <input
                                type="text"
                                value={settings.defaultProjectsDir}
                                onChange={(e) => handleChange('defaultProjectsDir', e.target.value)}
                                placeholder="Data/projects"
                            />
                            <button onClick={handleFolderSelect} className="folder-select-btn">
                                📂 선택
                            </button>
                        </div>
                    </div>

                    <div className="setting-group">
                        <label>기본 Extraction Mode</label>
                        <div className="radio-group">
                            <label className="radio-label">
                                <input
                                    type="radio"
                                    value="basic"
                                    checked={settings.extractionMode === 'basic'}
                                    onChange={(e) => handleChange('extractionMode', e.target.value)}
                                />
                                Basic (빠른 추출)
                            </label>
                            <label className="radio-label">
                                <input
                                    type="radio"
                                    value="detailed"
                                    checked={settings.extractionMode === 'detailed'}
                                    onChange={(e) => handleChange('extractionMode', e.target.value)}
                                />
                                Detailed (상세 추출)
                            </label>
                        </div>
                    </div>
                </section>

                {/* Step 1 Settings */}
                <section className="settings-section">
                    <h2>📊 Step 1 설정</h2>

                    <div className="setting-group">
                        <label>디폴트 표시 컬럼</label>
                        <div className="checkbox-grid">
                            {availableColumns.map(column => (
                                <label key={column} className="checkbox-label">
                                    <input
                                        type="checkbox"
                                        checked={settings.step1DefaultColumns.includes(column)}
                                        onChange={() => handleColumnToggle(column)}
                                    />
                                    {column}
                                </label>
                            ))}
                        </div>
                    </div>

                    <div className="setting-group">
                        <label>날짜 포맷</label>
                        <select
                            value={settings.dateFormat}
                            onChange={(e) => handleChange('dateFormat', e.target.value)}
                        >
                            <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                            <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                            <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                        </select>
                    </div>
                </section>

                {/* UI Settings (Optional) */}
                <section className="settings-section">
                    <h2>🎨 UI 설정</h2>

                    <div className="setting-group">
                        <label>테마</label>
                        <select
                            value={settings.theme}
                            onChange={(e) => handleChange('theme', e.target.value)}
                        >
                            <option value="light">Light</option>
                            <option value="dark">Dark (준비중)</option>
                        </select>
                    </div>

                    <div className="setting-group">
                        <label>언어</label>
                        <select
                            value={settings.language}
                            onChange={(e) => handleChange('language', e.target.value)}
                        >
                            <option value="ko">한국어</option>
                            <option value="en">English (준비중)</option>
                        </select>
                    </div>
                </section>

            </div>
        </div>
    );
};

export default Settings;
