import React, { useState } from 'react';
import './Sidebar.css';

const MENU_ITEMS = [
    { id: 'mother', icon: '🏠', label: '메인 워크스페이스', subLabel: 'Main Workspace' },
    { id: 'step1', icon: '✅', label: 'Step 1: 전표 확정', subLabel: 'Invoice Confirmation' },
    { id: 'step2', icon: '📂', label: 'Step 2: 증빙 수집', subLabel: 'Evidence Collection' },
    { id: 'step3', icon: '🔍', label: 'Step 3: 데이터 추출', subLabel: 'Data Extraction' },
    { id: 'dashboard', icon: '📊', label: '결과 대시보드', subLabel: 'Results Dashboard' },
];

const Sidebar = ({ onGoHome, activeId, onMenuClick }) => {
    const [isCollapsed, setIsCollapsed] = useState(false);

    return (
        <div className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
            <div className="sidebar-header">
                <div className="logo-area">
                    <span className="logo-icon">🌌</span>
                    {!isCollapsed && <span className="logo-text">IDARS</span>}
                </div>
                <button
                    className="collapse-btn"
                    onClick={() => setIsCollapsed(!isCollapsed)}
                    title={isCollapsed ? "메뉴 펼치기" : "메뉴 접기"}
                >
                    {isCollapsed ? '»' : '«'}
                </button>
            </div>

            <nav className="sidebar-nav">
                <button
                    className="nav-item home-nav-item"
                    onClick={onGoHome}
                    title={isCollapsed ? "홈으로" : ""}
                >
                    <span className="nav-icon">🏠</span>
                    {!isCollapsed && (
                        <div className="nav-label-container">
                            <span className="nav-label">홈으로</span>
                            <span className="nav-sublabel">Go Home</span>
                        </div>
                    )}
                </button>
                <div className="nav-divider"></div>
                {MENU_ITEMS.map((item) => (
                    <button
                        key={item.id}
                        className={`nav-item ${activeId === item.id ? 'active' : ''}`}
                        onClick={() => onMenuClick(item.id)}
                        title={isCollapsed ? item.label : ''}
                    >
                        <span className="nav-icon">{item.icon}</span>
                        {!isCollapsed && (
                            <div className="nav-label-container">
                                <span className="nav-label">{item.label}</span>
                                <span className="nav-sublabel">{item.subLabel}</span>
                            </div>
                        )}
                    </button>
                ))}
            </nav>

            <div className="sidebar-footer">
                <button
                    className={`nav-item settings-btn ${activeId === 'settings' ? 'active' : ''}`}
                    onClick={() => onMenuClick('settings')}
                    title={isCollapsed ? "설정" : ""}
                >
                    <span className="nav-icon">⚙️</span>
                    {!isCollapsed && (
                        <div className="nav-label-container">
                            <span className="nav-label">설정</span>
                            <span className="nav-sublabel">Settings</span>
                        </div>
                    )}
                </button>
                {!isCollapsed && <span className="version-text">v2.5 MVP</span>}
            </div>
        </div>
    );
};

export default Sidebar;
