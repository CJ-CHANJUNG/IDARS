import React, { useState } from 'react'
import { ProjectProvider, useProject } from './context/ProjectContext'
import Sidebar from './components/Sidebar'
import LandingPage from './components/LandingPage'
import ProjectListModal from './components/ProjectListModal'
import Step1InvoiceConfirmation from './components/steps/Step1InvoiceConfirmation'
import Step1DtermInvoiceConfirmation from './components/steps/Step1DtermInvoiceConfirmation'
import Step2EvidenceCollection from './components/steps/Step2EvidenceCollection'
import Step2DtermEvidenceCollection from './components/steps/Step2DtermEvidenceCollection'
import Step3DataExtraction from './components/steps/Step3DataExtraction'
import ResultsDashboard from './components/ResultsDashboard'
import Settings from './components/Settings'
import DesignPreview from './components/DesignPreview'

import './components/DesignPreview.css'
import './App.css'

function AppContent() {
  const {
    currentView, setCurrentView,
    sidebarView, setSidebarView,
    project, setProject,
    setLedgerData, setConfirmedData, setEvidenceData, setExtractionData, setVisibleColumns, setError, setHistory, setHistoryIndex,
    loadProjectData,
    isLoading
  } = useProject();

  const [isProjectListOpen, setIsProjectListOpen] = useState(false);

  // --- Project Management Handlers ---
  const handleStartProject = async (name, workflowType) => {
    console.log("Starting project:", name, workflowType);
    try {
      const response = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name,
          workflow_type: workflowType  // ★ workflow_type 전달
        })
      });
      const newProject = await response.json();
      console.log("Project created:", newProject);

      if (response.ok) {
        setProject(newProject);
        setCurrentView('workspace');

        // Reset ALL workspace state
        setLedgerData([]);
        setConfirmedData([]);
        setEvidenceData([]);
        setExtractionData([]);
        setVisibleColumns([]);
        setError(null);
        setHistory([]);
        setHistoryIndex(-1);

        // Set sidebar view to step1
        setSidebarView('step1');
      } else {
        alert('프로젝트 생성 실패: ' + newProject.error);
      }
    } catch (err) {
      console.error(err);
      alert('프로젝트 생성 중 오류가 발생했습니다.');
    }
  };

  const handleLoadProject = () => {
    setIsProjectListOpen(true);
  };

  const handleProjectSelect = (projectId) => {
    loadProjectData(projectId);
    setIsProjectListOpen(false);
    setSidebarView('step1'); // Default to Step 1 on load
  };

  const handleGoHome = () => {
    setCurrentView('landing');
    setSidebarView('step1');
  };

  const handleMenuClick = (id) => {
    setSidebarView(id);
  };

  return (
    <div className="app-container">
      <Sidebar
        onGoHome={handleGoHome}
        activeId={sidebarView}
        onMenuClick={handleMenuClick}
      />
      <div className="main-content">
        {currentView === 'landing' ? (
          <>
            <LandingPage
              onProjectStart={handleStartProject}
              projects={[]}
              onLoadProject={handleLoadProject}
            />
            <ProjectListModal
              isOpen={isProjectListOpen}
              onClose={() => setIsProjectListOpen(false)}
              onLoadProject={handleProjectSelect}
            />
          </>
        ) : (
          <>
            <div className="workspace-header" style={{
              padding: '0.25rem 1rem',
              borderBottom: '1px solid #e0e0e0',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              backgroundColor: '#fafafa',
              minHeight: '32px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <span style={{ fontSize: '0.95rem', fontWeight: '600', color: '#333' }}>{project?.name}</span>
                <span style={{ fontSize: '0.75rem', color: '#666', padding: '0.15rem 0.5rem', backgroundColor: '#e9ecef', borderRadius: '4px' }}>ID: {project?.id}</span>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  className="action-button"
                  onClick={() => loadProjectData(project.id)}
                  disabled={isLoading}
                  title="데이터 새로고침"
                  style={{ padding: '0.3rem 0.8rem', fontSize: '0.85rem' }}
                >
                  🔄
                </button>
              </div>
            </div>

            <div className="content-area">
              {/* ★ Step 1: 워크플로우별 분기 */}
              {sidebarView === 'step1' && (
                project?.workflow_type === 'dterm_arrival'
                  ? <Step1DtermInvoiceConfirmation />
                  : <Step1InvoiceConfirmation />
              )}

              {/* ★ Step 2: 워크플로우별 분기 */}
              {sidebarView === 'step2' && (
                project?.workflow_type === 'dterm_arrival'
                  ? <Step2DtermEvidenceCollection />
                  : <Step2EvidenceCollection />
              )}

              {/* ★ Step 3: 추후 분기 예정 */}
              {sidebarView === 'step3' && <Step3DataExtraction />}

              {/* Results Dashboard (replaced Step 4) */}
              {sidebarView === 'dashboard' && <ResultsDashboard project={project} />}

              {/* Settings */}
              {sidebarView === 'settings' && (
                <Settings onSave={(settings) => console.log('Settings saved:', settings)} />
              )}

              {/* Design Preview */}
              {sidebarView === 'preview' && <DesignPreview />}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function App() {
  return (
    <ProjectProvider>
      <AppContent />
    </ProjectProvider>
  );
}

export default App;
