import React from 'react';
import { useProject } from '../context/ProjectContext';
import './Home.css';

const Home = ({ onStartProject, onLoadProject }) => {
    const { project } = useProject();

    return (
        <div className="landing-container">
            <div className="landing-content-wrapper">
                <div className="landing-header">
                    <h1 className="landing-title">IDARS</h1>
                    <p className="landing-subtitle">Intelligent Document-Ledger Auto-Reconciliation System</p>
                    {project && <p className="current-project">현재 프로젝트: <strong>{project.name}</strong></p>}
                </div>

                <div className="selection-step">
                    <h2 className="step-title">프로젝트 시작하기</h2>
                    <div className="source-cards">
                        <div className="source-card" onClick={onStartProject}>
                            <div className="card-icon">📂</div>
                            <h3>새 프로젝트 시작</h3>
                            <p>새로운 프로젝트를 생성하여 작업을 시작합니다.</p>
                        </div>
                        <div className="source-card" onClick={onLoadProject}>
                            <div className="card-icon">📁</div>
                            <h3>기존 프로젝트 불러오기</h3>
                            <p>이전에 저장된 프로젝트를 불러와서 작업을 계속합니다.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Home;
