import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const ProjectContext = createContext();

export const useProject = () => {
    const context = useContext(ProjectContext);
    if (!context) {
        throw new Error('useProject must be used within a ProjectProvider');
    }
    return context;
};

export const ProjectProvider = ({ children }) => {
    // Navigation State
    const [currentView, setCurrentView] = useState('landing'); // 'landing' | 'workspace'
    const [sidebarView, setSidebarView] = useState('mother'); // 'mother' | 'step1' | 'step2' | 'step3' | 'step4' | 'settings'
    const [project, setProject] = useState(null);

    // Workspace State
    const [ledgerData, setLedgerData] = useState([]);
    const [confirmedData, setConfirmedData] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [visibleColumns, setVisibleColumns] = useState([]);

    // Step 2: Evidence Tracking Data
    const [evidenceData, setEvidenceData] = useState([]);

    // Step 3: Data Extraction
    const [extractionData, setExtractionData] = useState([]);
    const [comparisonResults, setComparisonResults] = useState([]);
    const [extractionMode, setExtractionMode] = useState('basic');
    const [finalJudgments, setFinalJudgments] = useState({}); // ★ Global state for judgments

    // History State
    const [history, setHistory] = useState([]);
    const [historyIndex, setHistoryIndex] = useState(-1);

    // Constants
    const DEFAULT_COLUMNS = [
        'Billing Document', 'T/C No.', 'Billing Date', '수출보험 보험일(선적일)',
        'Description', 'Incoterms', 'Pur Incoterms1', 'Material Description',
        'Billed Quantity', 'Sales unit', 'Amount', 'Document Currency',
        'Local Amount', 'Sold-To Party', 'Name 1', 'Ship-to party', 'Name 1.1'
    ];

    // --- Actions ---

    const loadProjectData = useCallback(async (projectId) => {
        setIsLoading(true);
        try {
            const response = await fetch(`http://127.0.0.1:5000/api/projects/${projectId}/load`);
            const data = await response.json();

            if (response.ok) {
                setProject(data.metadata);
                setLedgerData(data.ledgerData || []);
                setCurrentView('workspace');

                // Set sidebar view based on project status
                const currentStep = data.metadata.current_step || 0;
                if (currentStep === 0) setSidebarView('step1');
                else if (currentStep === 1) setSidebarView('step2');
                else if (currentStep === 2) setSidebarView('step3');
                else if (currentStep === 3) setSidebarView('step4');
                else setSidebarView('mother');

                // Set columns
                if (data.metadata.visibleColumns) {
                    setVisibleColumns(data.metadata.visibleColumns);
                } else if (data.ledgerData && data.ledgerData.length > 0) {
                    const columns = Object.keys(data.ledgerData[0]);
                    const initialColumns = DEFAULT_COLUMNS.filter(col => columns.includes(col));
                    setVisibleColumns(initialColumns.length > 0 ? initialColumns : columns);
                } else {
                    setVisibleColumns([]);
                }

                // Set Confirmed Data
                if (data.confirmedData && data.confirmedData.length > 0) {
                    setConfirmedData(data.confirmedData);
                } else {
                    setConfirmedData([]);
                }

                // Evidence Data initialization is handled in Step 2 component or effect below
            } else {
                alert('프로젝트 로드 실패: ' + data.error);
            }
        } catch (err) {
            console.error(err);
            alert('프로젝트 로드 중 오류가 발생했습니다.');
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Initialize evidence data when confirmed data is loaded
    useEffect(() => {
        if (confirmedData && confirmedData.length > 0 && evidenceData.length === 0) {
            // Find Billing Document Column
            const firstRow = confirmedData[0];
            const possibleCols = ['Billing Document', 'BillingDocument', '전표번호', 'Document Number', 'Invoice Number'];
            let billingCol = possibleCols.find(col => col in firstRow);

            if (!billingCol) {
                billingCol = Object.keys(firstRow).find(col =>
                    col.toLowerCase().includes('billing') &&
                    !col.toLowerCase().includes('date') &&
                    !col.includes('일자')
                );
            }

            if (billingCol) {
                const initialEvidence = confirmedData.map((row, index) => ({
                    id: index + 1,
                    billingDocument: row[billingCol],
                    evidenceStatus: row.evidence_status?.status === 'collected' ? '완료' : '미수집',
                    Bill_of_Lading: '',
                    Commercial_Invoice: '',
                    Packing_List: '',
                    Weight_List: '',
                    Mill_Certificate: '',
                    Cargo_Insurance: '',
                    Certificate_Origin: '',
                    Customs_clearance_Letter: '',
                    Delivery_Note: '',
                    Other: '',
                    splitStatus: '미완료',
                    remarks: ''
                }));
                setEvidenceData(initialEvidence);
            }
        }
    }, [confirmedData]);

    const value = {
        currentView, setCurrentView,
        sidebarView, setSidebarView,
        project, setProject,
        ledgerData, setLedgerData,
        confirmedData, setConfirmedData,
        isLoading, setIsLoading,
        error, setError,
        visibleColumns, setVisibleColumns,
        evidenceData, setEvidenceData,
        extractionData, setExtractionData,
        comparisonResults, setComparisonResults,
        extractionMode, setExtractionMode,
        finalJudgments, setFinalJudgments,
        history, setHistory,
        historyIndex, setHistoryIndex,
        DEFAULT_COLUMNS,
        loadProjectData
    };

    return (
        <ProjectContext.Provider value={value}>
            {children}
        </ProjectContext.Provider>
    );
};
