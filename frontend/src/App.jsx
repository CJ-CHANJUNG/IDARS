import React, { useState, useEffect, useRef } from 'react'
import Sidebar from './components/Sidebar'
import LedgerTable from './components/LedgerTable'
import ColumnSelector from './components/ColumnSelector'
import LandingPage from './components/LandingPage'
import DataImportModal from './components/DataImportModal'
import ProjectListModal from './components/ProjectListModal'
import PDFViewerModal from './components/PDFViewerModal'
import EvidenceUploadModal from './components/EvidenceUploadModal'

import './App.css'

const DEFAULT_COLUMNS = [
  'Billing Document',
  'T/C No.',
  'Billing Date',
  '수출보험 보험일(선적일)',
  'Description',
  'Incoterms',
  'Pur Incoterms1',
  'Material Description',
  'Billed Quantity',
  'Sales unit',
  'Amount',
  'Document Currency',
  'Local Amount',
  'Sold-To Party',
  'Name 1',
  'Ship-to party',
  'Name 1.1' // Assuming duplicate Name 1 might be renamed, keeping one as potential fallback or user can adjust
]

function App() {
  // Navigation State
  const [currentView, setCurrentView] = useState('landing') // 'landing' | 'workspace'
  const [project, setProject] = useState(null) // { name, id, ... }

  // Workspace State
  const [ledgerData, setLedgerData] = useState([])
  const [confirmedData, setConfirmedData] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('imported')
  const [visibleColumns, setVisibleColumns] = useState([])

  // History State
  const [history, setHistory] = useState([])
  const [historyIndex, setHistoryIndex] = useState(-1)

  // Selection State (lifted up or managed via ref/callback)
  // For now, we'll pass a trigger to table or handle add row directly.
  // Delete selected requires knowing selection. We'll pass a callback to Table to get selection or expose it.
  // Simpler: Pass a "requestDeleteSelected" trigger or similar? 
  // Better: Let Table handle "Delete Selected" UI? 
  // User asked for button in toolbar. So App needs to know selection or tell Table to delete.
  // We will pass a ref to LedgerTable to trigger delete.
  const tableRef = useRef(null)

  // Modal State
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [showDownloadProgress, setShowDownloadProgress] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState({ current: 0, total: 0, message: '', status: '' });
  const [isProjectListOpen, setIsProjectListOpen] = useState(false)

  const [importModalTab, setImportModalTab] = useState('local') // 'local' | 'sap'

  // Edit Mode State
  const [isEditMode, setIsEditMode] = useState(false)

  // Step 2: Evidence Tracking Data
  const [evidenceData, setEvidenceData] = useState([])

  // Step 3: Data Extraction
  const [extractionData, setExtractionData] = useState([])

  // Evidence Modals State
  const [pdfViewerState, setPdfViewerState] = useState({
    isOpen: false,
    files: [],
    title: '',
    billingDocument: null
  });

  // Selection State
  const [selectedRows, setSelectedRows] = useState(new Set());

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      const allIds = new Set(evidenceData.map(row => row.billingDocument));
      setSelectedRows(allIds);
    } else {
      setSelectedRows(new Set());
    }
  };

  const handleSelectRow = (billingDocument) => {
    const newSelected = new Set(selectedRows);
    if (newSelected.has(billingDocument)) {
      newSelected.delete(billingDocument);
    } else {
      newSelected.add(billingDocument);
    }
    setSelectedRows(newSelected);
  };
  const [uploadModalState, setUploadModalState] = useState({ isOpen: false, billingDocument: '' });

  // Initialize evidence data when confirmed data is loaded or updated
  useEffect(() => {
    if (confirmedData && confirmedData.length > 0 && evidenceData.length === 0) {
      // Create evidence tracking records from confirmed invoices
      const evidenceRecords = confirmedData.map((invoice, index) => ({
        id: index,
        billingDocument: invoice['Billing Document'] || invoice['전표번호'] || '',
        evidenceStatus: '미수집', // 미수집, 수집중, 완료
        BL: '',
        Invoice: '',
        PackingList: '',
        Other: '',
        notes: '',
        downloadedAt: null,
        splitStatus: '대기중' // 대기중, Split 완료
      }))
      setEvidenceData(evidenceRecords)
    }
  }, [confirmedData])

  // Fetch initial data (only if a project is loaded directly, e.g., from a deep link or refresh)
  useEffect(() => {
    if (currentView === 'workspace' && project) {
      fetchData()
    }
  }, [currentView, project])

  // --- Project Management Handlers ---
  const handleStartProject = async (name, source) => {
    console.log("Starting project:", name, source);
    try {
      const response = await fetch('http://127.0.0.1:5000/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      const newProject = await response.json();
      console.log("Project created:", newProject);

      if (response.ok) {
        setProject(newProject);
        setCurrentView('workspace');

        // Reset ALL workspace state to prevent data leakage from previous projects
        setLedgerData([]);
        setConfirmedData([]);
        setExtractionData([]);
        setVisibleColumns([]);
        setError(null);

        // Reset History
        setHistory([]);
        setHistoryIndex(-1);

        // Set sidebar view based on source
        if (source === 'local' || source === 'sap') {
          setSidebarView('step1');  // Go to Step 1 for data import
        } else {
          setSidebarView('mother');  // Go to Mother Workspace
        }

        if (source) {
          console.log("Opening modal for source:", source);
          setImportModalTab(source);
          setTimeout(() => {
            console.log("Setting modal open true");
            setIsImportModalOpen(true);
          }, 100);
        }
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
  };

  const loadProjectData = async (projectId) => {
    setIsLoading(true);
    try {
      const response = await fetch(`http://127.0.0.1:5000/api/projects/${projectId}/load`);
      const data = await response.json();

      if (response.ok) {
        setProject(data.metadata);
        setLedgerData(data.ledgerData);
        setCurrentView('workspace');

        // Set sidebar view based on project status
        const currentStep = data.metadata.current_step || 0;
        if (currentStep === 0) {
          setSidebarView('step1');  // New project, start at Step 1
        } else if (currentStep === 1) {
          setSidebarView('step2');  // Step 1 complete, show Step 2
        } else if (currentStep === 2) {
          setSidebarView('step3');
        } else if (currentStep === 3) {
          setSidebarView('step4');
        } else {
          setSidebarView('mother');  // Default to mother workspace
        }

        // Set columns if data exists
        if (data.metadata.visibleColumns) {
          setVisibleColumns(data.metadata.visibleColumns);
        } else if (data.ledgerData.length > 0) {
          const columns = Object.keys(data.ledgerData[0]);
          const initialColumns = DEFAULT_COLUMNS.filter(col => columns.includes(col));
          setVisibleColumns(initialColumns.length > 0 ? initialColumns : columns);
        } else {
          setVisibleColumns([]);
        }

        // Set Confirmed Data and Initialize Evidence Data
        if (data.confirmedData && data.confirmedData.length > 0) {
          setConfirmedData(data.confirmedData);

          // Find Billing Document Column
          const firstRow = data.confirmedData[0];
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
            const initialEvidence = data.confirmedData.map((row, index) => ({
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
        } else {
          setConfirmedData([]);
          setEvidenceData([]);
        }
      } else {
        alert('프로젝트 로드 실패: ' + data.error);
      }
    } catch (err) {
      console.error(err);
      alert('프로젝트 로드 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleUnconfirm = async (step) => {
    if (!project) return;

    if (!window.confirm(`Step ${step} 확정을 취소하시겠습니까?\n이후 단계의 데이터가 잠금 해제되거나 영향을 받을 수 있습니다.`)) {
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/unconfirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ step })
      });
      const result = await response.json();

      if (response.ok) {
        alert(`✅ Step ${step} 확정이 취소되었습니다.`);
        // Reload project data to reflect changes
        await loadProjectData(project.id);

        // If unconfirming Step 1, go to Step 1 tab
        if (step === 1) {
          setSidebarView('step1');
          setActiveTab('imported');
          setIsEditMode(true);
        } else if (step === 2) {
          setSidebarView('step2');
        }
      } else {
        alert('Failed to unconfirm: ' + result.error);
      }
    } catch (err) {
      console.error('[UNCONFIRM] Error:', err);
      alert('Error unconfirming step: ' + err.message);
    }
    setIsLoading(false);
  }

  const handleDMSDownload = async () => {
    if (!project) return;

    const targetDocuments = selectedRows.size > 0 ? Array.from(selectedRows) : null;
    const message = targetDocuments
      ? `선택된 ${targetDocuments.length}개 전표의 증빙을 다운로드 하시겠습니까?`
      : '전체 전표의 증빙을 다운로드 하시겠습니까?';

    if (!window.confirm(message)) return;

    // Ask about redownload behavior
    const forceRedownload = window.confirm(
      '이미 다운로드된 파일이 있을 경우:\n\n' +
      '「확인」 = 다시 다운로드 (최신 파일 보장)\n' +
      '「취소」 = 건너뛰기 (빠른 실행)'
    );

    console.log('[DMS] User selected forceRedownload:', forceRedownload);

    setIsLoading(true);
    try {
      const requestBody = {
        targetDocuments,
        forceRedownload
      };
      console.log('[DMS] Sending request:', requestBody);

      const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/dms-download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });
      const result = await response.json();

      if (response.ok) {
        const mode = forceRedownload ? '(전체 재다운로드)' : '(신규만 다운로드)';
        alert(`DMS 다운로드가 시작되었습니다 ${mode}\n백그라운드에서 진행됩니다.`);
        // Start polling for progress
        pollDMSProgress();
        // Clear selection
        setSelectedRows(new Set());
      } else {
        alert('DMS Download failed: ' + result.error);
        setIsLoading(false);
      }
    } catch (err) {
      console.error(err);
      alert('Error starting DMS download: ' + err.message);
      setIsLoading(false);
    }
  };

  const pollDMSProgress = () => {
    if (!project) return;

    // Show progress UI
    setShowDownloadProgress(true);
    setDownloadProgress({ current: 0, total: 0, message: 'Starting...', status: 'running' });

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`http://127.0.0.1:5000/api/dms/progress/${project.id}`);
        if (response.ok) {
          const progress = await response.json();

          // Update progress display
          setDownloadProgress({
            current: progress.current || 0,
            total: progress.total || 0,
            message: progress.message || '',
            status: progress.status || 'running'
          });

          if (progress.status === 'completed' || progress.status === 'error') {
            clearInterval(pollInterval);
            setIsLoading(false);

            // Hide progress UI after a delay
            setTimeout(() => setShowDownloadProgress(false), 3000);

            if (progress.status === 'completed') {
              // Reload evidence status to show downloaded files
              checkEvidenceStatus();
              alert('✅ DMS 다운로드 완료!');
            } else {
              alert('❌ Download Error: ' + progress.message);
            }
          }
        }
      } catch (err) {
        console.error('Progress polling error:', err);
      }
    }, 1000);
  };

  const handleSaveProgress = async () => {
    if (!project) return;
    setIsLoading(true);
    try {
      const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ledgerData: ledgerData,
          visibleColumns: visibleColumns
        })
      });
      const result = await response.json();

      if (response.ok) {
        alert('진행 상황이 저장되었습니다.');
      } else {
        alert('저장 실패: ' + result.error);
      }
    } catch (err) {
      console.error(err);
      alert('저장 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirm = async () => {
    console.log('[CONFIRM] Button clicked, project:', project);
    console.log('[CONFIRM] LedgerData length:', ledgerData?.length);

    if (!project) {
      alert('프로젝트가 로드되지 않았습니다.');
      return;
    }

    if (!ledgerData || ledgerData.length === 0) {
      alert('확정할 데이터가 없습니다. 먼저 데이터를 가져오세요.');
      return;
    }

    // Direct confirmation without dialog - user already clicked the confirm button
    console.log('[CONFIRM] Starting confirmation...');
    setIsLoading(true);
    try {
      const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ledgerData: ledgerData,
          visibleColumns: visibleColumns
        })
      });
      const result = await response.json();
      console.log('[CONFIRM] Response:', response.ok, result);

      if (response.ok) {
        setConfirmedData(ledgerData);
        setActiveTab('confirmed');
        setIsEditMode(false);
        setSidebarView('step2'); // Move to Step 2
        alert('✅ 전표가 성공적으로 확정되었습니다!\n\nStep 2 (증빙 수집)로 이동합니다.');
      } else {
        alert('Failed to confirm data: ' + result.error);
      }
    } catch (err) {
      console.error('[CONFIRM] Error:', err);
      alert('Error confirming data: ' + err.message);
    }
    setIsLoading(false);
  }


  const handleSplitEvidence = async () => {
    if (!project) return;

    const targetDocuments = selectedRows.size > 0 ? Array.from(selectedRows) : null;
    const message = targetDocuments
      ? `선택된 ${targetDocuments.length}개 전표의 증빙을 Split 하시겠습니까?`
      : '전체 증빙 문서를 Split 하시겠습니까?';

    if (!window.confirm(message)) return;

    console.log('[SPLIT] Starting PDF split...', targetDocuments ? `Targets: ${targetDocuments.length}` : 'ALL');
    setIsLoading(true);

    try {
      const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/split-evidence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ targetDocuments })
      });
      const result = await response.json();

      if (response.ok) {
        alert('PDF Split이 시작되었습니다. 백그라운드에서 진행됩니다.');
        // Start polling for progress
        pollSplitProgress();
        // Clear selection
        setSelectedRows(new Set());
      } else {
        alert('Split failed: ' + result.error);
        setIsLoading(false);
      }
    } catch (err) {
      console.error(err);
      alert('Error starting split: ' + err.message);
      setIsLoading(false);
    }
  };

  const pollSplitProgress = () => {
    if (!project) return;

    // Show progress UI
    setShowDownloadProgress(true);
    setDownloadProgress({ current: 0, total: 0, message: 'Split 준비 중...', status: 'running' });

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`http://127.0.0.1:5000/api/split/progress/${project.id}`);
        if (response.ok) {
          const progress = await response.json();

          // Update progress display
          setDownloadProgress({
            current: progress.current || 0,
            total: progress.total || 0,
            message: progress.message || 'Processing...', status: progress.status || 'running'
          });

          if (progress.status === 'completed' || progress.status === 'error') {
            clearInterval(pollInterval);
            setIsLoading(false);

            // Hide progress UI after a delay
            setTimeout(() => setShowDownloadProgress(false), 3000);

            if (progress.status === 'completed') {
              // Reload evidence status to show split files
              checkEvidenceStatus();
              alert('✅ PDF Split 완료!');
            } else {
              alert('❌ Split Error: ' + progress.message);
            }
          }
        }
      } catch (err) {
        console.error('Progress polling error:', err);
      }
    }, 1000);
  };
  const handleConfirmStep2 = async () => {
    if (!project) return;

    console.log('[CONFIRM STEP2] Starting confirmation...');
    console.log('[CONFIRM STEP2] Evidence data count:', evidenceData?.length);

    if (!evidenceData || evidenceData.length === 0) {
      alert('증빙 데이터가 없습니다.');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/confirm-step2`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          evidenceData: evidenceData
        })
      });
      const result = await response.json();
      console.log('[CONFIRM STEP2] Response:', result);

      if (response.ok) {
        setSidebarView('step3'); // Move to Step 3
        alert('✅ 증빙이 성공적으로 확정되었습니다!\n\nStep 3 (데이터 추출)로 이동합니다.');
      } else {
        alert('Failed to confirm Step 2: ' + result.error);
      }
    } catch (err) {
      console.error('[CONFIRM STEP2] Error:', err);
      alert('Error confirming Step 2: ' + err.message);
    }
    setIsLoading(false);
  }

  const handleViewEvidence = async (row, filterType = null) => {
    try {
      const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/evidence/search?billingDocument=${row.billingDocument}`);
      let files = await response.json();

      if (files && files.length > 0) {
        // Filter by type if requested
        if (filterType) {
          const filtered = files.filter(f => {
            const lowerName = f.filename.toLowerCase();

            if (filterType === 'Bill_of_Lading') return lowerName.includes('bill_of_lading') || lowerName.includes('b_l');
            if (filterType === 'Commercial_Invoice') return lowerName.includes('commercial_invoice') || lowerName.includes('invoice');
            if (filterType === 'Packing_List') return lowerName.includes('packing_list') || lowerName.includes('packing');
            if (filterType === 'Weight_List') return lowerName.includes('weight_list');
            if (filterType === 'Mill_Certificate') return lowerName.includes('mill_certificate');
            if (filterType === 'Cargo_Insurance') return lowerName.includes('cargo_insurance') || lowerName.includes('insurance');
            if (filterType === 'Certificate_Origin') return lowerName.includes('certificate_origin') || lowerName.includes('origin');
            if (filterType === 'Customs_clearance_Letter') return lowerName.includes('customs_clearance') || lowerName.includes('declaration');
            if (filterType === 'Delivery_Note') return lowerName.includes('delivery_note') || lowerName.includes('delivery');

            if (filterType === 'Other') {
              // Exclude all known types
              const knownTypes = ['bill_of_lading', 'b_l', 'commercial_invoice', 'invoice', 'packing_list', 'packing',
                'weight_list', 'mill_certificate', 'cargo_insurance', 'insurance',
                'certificate_origin', 'origin', 'customs_clearance', 'declaration', 'delivery_note', 'delivery'];
              return !knownTypes.some(t => lowerName.includes(t));
            }
            return true;
          });
          // If filtered result exists, use it. Otherwise show all (fallback)
          if (filtered.length > 0) {
            files = filtered;
          } else {
            console.warn(`No files found for type ${filterType}, showing all.`);
          }
        }

        // Sort: Original first, then Split
        files.sort((a, b) => {
          if (a.type === 'original' && b.type !== 'original') return -1;
          if (a.type !== 'original' && b.type === 'original') return 1;
          return 0;
        });

        // Map files to include full URL
        const filesWithUrl = files.map(f => ({
          ...f,
          url: `http://127.0.0.1:5000/api/projects/${project.id}/files/${f.path}`
        }));

        setPdfViewerState({
          isOpen: true,
          files: filesWithUrl,
          title: `증빙 문서: ${row.billingDocument}${filterType ? ` (${filterType})` : ''}`,
          billingDocument: row.billingDocument
        });
      } else {
        alert('해당 전표의 증빙 파일(원본 또는 Split)을 찾을 수 없습니다.');
      }
    } catch (err) {
      console.error(err);
      alert('증빙 파일을 검색하는데 실패했습니다.');
    }
  }

  const handleUploadEvidence = (row) => {
    setUploadModalState({
      isOpen: true,
      billingDocument: row.billingDocument
    });
  }

  const onManualUpload = async (file, billingDocument) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('billingDocument', billingDocument);

    try {
      const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/evidence/upload`, {
        method: 'POST',
        body: formData
      });
      const result = await response.json();

      if (response.ok) {
        alert('업로드 성공!');
        // Update local state to 'Collected'
        setEvidenceData(prev => prev.map(row => {
          if (row.billingDocument === billingDocument) {
            return { ...row, evidenceStatus: '완료' };
          }
          return row;
        }));
      } else {
        alert('Upload failed: ' + result.error);
      }
    } catch (err) {
      console.error(err);
      alert('Error uploading file');
    }
  }

  const handleDeleteEvidence = async (file) => {
    try {
      const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/evidence/delete`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filepath: file.path })
      });
      const result = await response.json();

      if (response.ok) {
        alert('파일이 삭제되었습니다.');
        // Refresh the file list in the viewer
        // We need to re-fetch the list for the current billing document
        const billingDoc = pdfViewerState.billingDocument;
        if (billingDoc) {
          // Re-use the logic from handleViewEvidence to fetch and update state
          // Or simpler: just remove the file from local state
          setPdfViewerState(prev => ({
            ...prev,
            files: prev.files.filter(f => f.path !== file.path)
          }));

          // Also update evidence status if no files remain?
          // That's complex because we don't know if other files exist without fetching.
          // For now, just update the viewer list.
        }
      } else {
        alert('파일 삭제 실패: ' + result.error);
      }
    } catch (err) {
      console.error(err);
      alert('파일 삭제 중 오류가 발생했습니다.');
    }
  }

  const checkEvidenceStatus = async () => {
    if (!project) return;

    try {
      const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/evidence/status`);
      const statusMap = await response.json();

      if (response.ok) {
        setEvidenceData(prevData => {
          return prevData.map(row => {
            const docStatus = statusMap[row.billingDocument];
            if (docStatus) {
              const newRow = { ...row };

              // Update overall status
              if (docStatus.original || docStatus.split) {
                newRow.evidenceStatus = '완료';
              }

              // Update Split Status
              newRow.splitStatus = docStatus.split ? 'Split 완료' : '대기중';

              // Update Document Type Columns (Parking)
              // Reset first
              newRow.Bill_of_Lading = '';
              newRow.Commercial_Invoice = '';
              newRow.Packing_List = '';
              newRow.Weight_List = '';
              newRow.Mill_Certificate = '';
              newRow.Cargo_Insurance = '';
              newRow.Certificate_Origin = '';
              newRow.Customs_clearance_Letter = '';
              newRow.Delivery_Note = '';
              newRow.Other = '';

              if (docStatus.types && docStatus.types.length > 0) {
                if (docStatus.types.includes('Bill_of_Lading')) newRow.Bill_of_Lading = 'O';
                if (docStatus.types.includes('Commercial_Invoice')) newRow.Commercial_Invoice = 'O';
                if (docStatus.types.includes('Packing_List')) newRow.Packing_List = 'O';
                if (docStatus.types.includes('Weight_List')) newRow.Weight_List = 'O';
                if (docStatus.types.includes('Mill_Certificate')) newRow.Mill_Certificate = 'O';
                if (docStatus.types.includes('Cargo_Insurance')) newRow.Cargo_Insurance = 'O';
                if (docStatus.types.includes('Certificate_Origin')) newRow.Certificate_Origin = 'O';
                if (docStatus.types.includes('Customs_clearance_Letter')) newRow.Customs_clearance_Letter = 'O';
                if (docStatus.types.includes('Delivery_Note')) newRow.Delivery_Note = 'O';
                if (docStatus.types.includes('Other')) newRow.Other = 'O';
              }
              return newRow;
            }
            return row;
          });
        });
      }
    } catch (err) {
      console.error("Error checking evidence status:", err);
    }
  };

  const loadStep3ExtractionData = async () => {
    if (!project) return;

    try {
      const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/step3/extraction-data`);
      if (response.ok) {
        const result = await response.json();
        console.log('[STEP3] Extraction data loaded:', result);
        setExtractionData(result.data);

        if (result.missing_fields && result.missing_fields.length > 0) {
          console.warn('[STEP3] Missing fields:', result.missing_fields);
        }
      } else {
        const error = await response.json();
        console.error('[STEP3] Failed to load extraction data:', error);
      }
    } catch (err) {
      console.error('[STEP3] Error:', err);
    }
  };

  // Sidebar State
  const [sidebarView, setSidebarView] = useState('mother') // 'mother' | 'step1' | 'step2' | 'step3' | 'step4' | 'dashboard'

  // --- Handlers ---
  const handleGoHome = () => {
    setCurrentView('landing')
    // Don't clear project data - just change the view
    // setProject(null) // REMOVED - keep project loaded
    // setLedgerData([]) // REMOVED - keep data loaded
    // setConfirmedData([]) // REMOVED - keep confirmed data
    setSidebarView('mother')
  }

  const handleMenuClick = (id) => {
    console.log('[MENU] Clicked:', id)
    setSidebarView(id)

    // Load data when switching to certain views
    if (id === 'step2') {
      checkEvidenceStatus();
    } else if (id === 'step3') {
      loadStep3ExtractionData();
    }
  }

  // --- Workspace Handlers ---
  const fetchData = async () => {
    setIsLoading(true)
    setError(null)
    try {
      // Use project.id if available, otherwise default to 'test'
      const projectId = project?.id || 'test';
      const response = await fetch(`http://127.0.0.1:5000/api/projects/${projectId}/load`)
      if (!response.ok) {
        // It's okay if file doesn't exist yet, just show empty
        if (response.status === 404) {
          setLedgerData([])
          return
        }
        throw new Error('데이터를 불러오는데 실패했습니다.')
      }
      const result = await response.json()

      if (result.ledgerData && Array.isArray(result.ledgerData)) {
        setLedgerData(result.ledgerData)
        // Initialize visible columns if empty and data exists
        if (result.metadata && result.metadata.visibleColumns) {
          setVisibleColumns(result.metadata.visibleColumns)
        } else if (result.ledgerData.length > 0 && visibleColumns.length === 0) {
          const columns = Object.keys(result.ledgerData[0])
          const initialColumns = DEFAULT_COLUMNS.filter(col => columns.includes(col))
          setVisibleColumns(initialColumns.length > 0 ? initialColumns : columns)
        }
      } else {
        setLedgerData([])
      }

      if (result.confirmedData && Array.isArray(result.confirmedData)) {
        setConfirmedData(result.confirmedData)
      } else {
        setConfirmedData([])
      }
    } catch (err) {
      console.error('Error fetching data:', err)
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  // --- History Management ---
  const handleDataChange = (newData, saveToHistory = true) => {
    if (saveToHistory) {
      const newHistory = history.slice(0, historyIndex + 1)
      newHistory.push(ledgerData)
      // Limit history size if needed (e.g., 50)
      if (newHistory.length > 50) newHistory.shift()

      setHistory(newHistory)
      setHistoryIndex(newHistory.length - 1)
    }
    setLedgerData(newData)
  }

  const undo = () => {
    if (historyIndex >= 0) {
      const previousData = history[historyIndex]
      const newHistory = history.slice(0, historyIndex + 1) // Keep current in history for redo?
      // Actually, standard undo/redo:
      // History: [State0, State1, State2]
      // Index: 2 (Current is State2, but usually current state is separate or last in history)
      // Let's use: history = [State0, State1], current = State2.

      // Revised:
      // history stores PAST states.
      // future stores FUTURE states.
      // But single array with index is easier.

      // Let's stick to: history includes ALL states [S0, S1, S2]. index points to current.
      // When change happens: remove future, add new state, index++.

      // Wait, simpler:
      // history = [S0, S1]. current = S2.
      // Undo: future.push(current), current = history.pop().

      // Let's use the implementation plan's approach:
      // We need to save *current* state to 'future' before restoring 'past'.

      // Let's try this simple approach:
      // history: Array of { data: [] }
      // index: current pointer
    }
  }

  // Refined History Implementation
  // We need to capture initial state too.
  useEffect(() => {
    if (ledgerData.length > 0 && history.length === 0) {
      // Initialize history with first data load? No, only on user change.
    }
  }, [ledgerData])

  const pushHistory = (data) => {
    const newHistory = history.slice(0, historyIndex + 1)
    newHistory.push(data)
    setHistory(newHistory)
    setHistoryIndex(newHistory.length - 1)
  }

  const handleUndo = () => {
    if (historyIndex >= 0) {
      // Current state needs to be saved to history? No, history has past states.
      // If we are at index 2 (S2), and undo, we go to S2. 
      // Wait, if history = [S0, S1], current is S2.
      // Undo -> current becomes S1. S2 is pushed to future?

      // Let's use: history = [S0, S1, S2]. index = 2.
      // Current display is history[index].

      const newIndex = historyIndex - 1
      if (newIndex >= 0) {
        setHistoryIndex(newIndex)
        setLedgerData(history[newIndex])
      }
    }
  }

  // Actually, let's restart history logic to be robust.
  // When data changes (user action):
  // 1. Push CURRENT ledgerData to history (past).
  // 2. Clear future.
  // 3. Update ledgerData.

  // Undo:
  // 1. Push CURRENT ledgerData to future.
  // 2. Pop from history.
  // 3. Set ledgerData.

  // Redo:
  // 1. Push CURRENT to history.
  // 2. Pop from future.
  // 3. Set ledgerData.

  // We need separate past/future arrays or one array with index.
  // One array with index: [S0, S1, S2, S3]. Index = 3.
  // Undo -> Index = 2. Data = S2.
  // Change -> [S0, S1, S2, NewS]. Index = 3.

  const updateDataWithHistory = (newData) => {
    const newHistory = history.slice(0, historyIndex + 1)
    newHistory.push(ledgerData) // Save current state before change
    setHistory(newHistory)
    setHistoryIndex(newHistory.length - 1)
    setLedgerData(newData)

    // Also push the NEW state? No, if we push current state (S0), then set S1.
    // History: [S0]. Current: S1.
    // Undo: Set Current to S0. History index?

    // Let's do: History stores ALL states including current.
    // Init: History = [InitialData]. Index = 0.
    // Change: History = [InitialData, NewData]. Index = 1.
    // Undo: Index = 0. Data = InitialData.

    // Implementation:
    const nextHistory = [...newHistory, newData]
    setHistory(nextHistory)
    setHistoryIndex(nextHistory.length - 1)
    setLedgerData(newData)
  }

  // But wait, if I use updateDataWithHistory, I need to ensure I don't loop.
  // And initial load shouldn't trigger history? Or maybe it should be the base.

  const onDataChange = (newData) => {
    // If history is empty, push current as base?
    let baseHistory = history
    let baseIndex = historyIndex

    if (history.length === 0 && ledgerData.length > 0) {
      baseHistory = [ledgerData]
      baseIndex = 0
    }

    const newHistory = baseHistory.slice(0, baseIndex + 1)
    newHistory.push(newData)
    setHistory(newHistory)
    setHistoryIndex(newHistory.length - 1)
    setLedgerData(newData)
  }

  const performUndo = () => {
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1
      setHistoryIndex(newIndex)
      setLedgerData(history[newIndex])
    }
  }

  const performRedo = () => {
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1
      setHistoryIndex(newIndex)
      setLedgerData(history[newIndex])
    }
  }

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault()
        if (e.shiftKey) {
          performRedo()
        } else {
          performUndo()
        }
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
        e.preventDefault()
        performRedo()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [history, historyIndex])

  // --- Row Operations ---
  const handleAddRow = () => {
    if (tableRef.current && tableRef.current.insertRowAboveSelection) {
      tableRef.current.insertRowAboveSelection()
    } else {
      // Fallback: Append to end
      const newRow = {}
      if (ledgerData.length > 0) {
        Object.keys(ledgerData[0]).forEach(key => newRow[key] = '')
      } else {
        DEFAULT_COLUMNS.forEach(key => newRow[key] = '')
      }
      const newData = [...ledgerData, newRow]
      onDataChange(newData)
    }
  }

  const handleDeleteSelected = () => {
    if (tableRef.current) {
      tableRef.current.deleteSelectedRows()
    }
  }

  const handleFileUpload = async (file) => {
    if (!file) return

    console.log("[FILE UPLOAD] Starting upload for file:", file.name);
    const formData = new FormData()
    formData.append('file', file)
    // If a project is active, append its ID
    if (project?.id) {
      formData.append('projectId', project.id);
      console.log("[FILE UPLOAD] Project ID:", project.id);
    }

    setIsLoading(true)
    setError(null)
    try {
      console.log("[FILE UPLOAD] Sending request to backend");
      const response = await fetch('http://127.0.0.1:5000/api/upload', {
        method: 'POST',
        body: formData,
      })
      console.log("[FILE UPLOAD] Response status:", response.ok);

      let result;
      try {
        const text = await response.text();
        try {
          result = JSON.parse(text);
        } catch (e) {
          console.error("[FILE UPLOAD] JSON Parse Error. Raw response:", text);
          throw new Error("Invalid JSON response from server");
        }
      } catch (e) {
        console.error("[FILE UPLOAD] Error reading response:", e);
        throw e;
      }

      console.log("[FILE UPLOAD] Response data:", result);

      if (response.ok && Array.isArray(result)) {
        console.log("[FILE UPLOAD] Upload success, data length:", result.length);
        console.log("[FILE UPLOAD] Setting ledgerData with", result.length, "rows");
        setLedgerData(result)
        // Reset visible columns to show all new columns by default
        if (result.length > 0) {
          const columns = Object.keys(result[0])
          console.log("[FILE UPLOAD] Available columns:", columns);
          const initialColumns = DEFAULT_COLUMNS.filter(col => columns.includes(col))
          setVisibleColumns(initialColumns.length > 0 ? initialColumns : columns)
          console.log("[FILE UPLOAD] Visible columns set to:", initialColumns.length > 0 ? initialColumns : columns);
        }
        alert("파일 업로드 성공! " + result.length + "개의 행을 로드했습니다.");
      } else {
        console.error("[FILE UPLOAD] Upload error result:", result)
        alert("Failed to load file: " + (result.error || "Unknown error"))
      }
    } catch (error) {
      console.error('[FILE UPLOAD] Error uploading file:', error)
      alert("Error uploading file")
    } finally {
      console.log("[FILE UPLOAD] Finishing upload, closing modal");
      setIsLoading(false)
      setIsImportModalOpen(false); // Close modal after upload attempt
    }
  }

  const handleSapFetch = async (config) => {
    if (!project?.id) {
      alert('프로젝트가 선택되지 않았습니다.');
      return;
    }

    console.log("[SAP FETCH] Starting SAP download");
    console.log("[SAP FETCH] Project ID:", project.id);
    console.log("[SAP FETCH] Config:", config);

    setIsLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:5000/api/sap/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          projectId: project.id,
          dateFrom: config.dateFrom,
          dateTo: config.dateTo
        })
      });
      const result = await response.json();

      console.log("[SAP FETCH] Response status:", response.ok);
      console.log("[SAP FETCH] Response data:", result);

      if (response.ok && Array.isArray(result)) {
        console.log("[SAP FETCH] Success, data length:", result.length);
        setLedgerData(result);
        // Reset visible columns
        if (result.length > 0) {
          const columns = Object.keys(result[0]);
          const initialColumns = DEFAULT_COLUMNS.filter(col => columns.includes(col));
          setVisibleColumns(initialColumns.length > 0 ? initialColumns : columns);
        }
        alert('SAP 데이터 다운로드 및 로드 완료: ' + result.length + '개의 행');
      } else {
        console.error("[SAP FETCH] SAP Download error:", result);
        alert("SAP 데이터 다운로드 실패: " + (result.error || "Unknown error"));
      }
    } catch (error) {
      console.error('[SAP FETCH] Error fetching SAP data:', error);
      alert("SAP 데이터 요청 중 오류가 발생했습니다.");
    } finally {
      setIsLoading(false);
      setIsImportModalOpen(false);
    }
  }

  const handleColumnReorder = (newOrder) => {
    setVisibleColumns(newOrder)
  }

  const toggleColumn = (column) => {
    if (visibleColumns.includes(column)) {
      setVisibleColumns(visibleColumns.filter(c => c !== column))
    } else {
      setVisibleColumns([...visibleColumns, column])
    }
  }

  const resetColumns = () => {
    if (ledgerData.length > 0) {
      const columns = Object.keys(ledgerData[0])
      const initialColumns = DEFAULT_COLUMNS.filter(col => columns.includes(col))
      setVisibleColumns(initialColumns.length > 0 ? initialColumns : columns)
    }
  }

  const handleExtract = async () => {
    if (!tableRef.current) return;
    const selectedRows = tableRef.current.getSelectedRows();

    if (selectedRows.length === 0) {
      alert('추출할 항목을 선택해주세요.');
      return;
    }

    setIsLoading(true);
    try {
      const selectedIds = selectedRows.map(row => row['Billing Document'] || row['전표번호']);
      const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/step3/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selectedIds })
      });

      if (response.ok) {
        const result = await response.json();
        alert(`추출 완료!\n선택: ${result.total_processed}건\n성공: ${result.total_success}건\n전체 누적: ${result.total_accumulated}건`);
        loadStep3ExtractionData(); // Reload data
      } else {

        const error = await response.json();
        alert(`추출 실패: ${error.error} `);
      }
    } catch (err) {
      console.error(err);
      alert('데이터 추출 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCellClick = (row, column, rowIndex, colIndex, e) => {
    if (sidebarView === 'step3' && column.startsWith('Extracted')) {
      const docId = row['Billing Document'] || row['전표번호'];
      if (docId) {
        // Open Commercial Invoice for the clicked document
        handleViewEvidence({ billingDocument: docId }, 'Commercial_Invoice');
      }
    }
  };

  // Header Styles for Step 3
  const step3HeaderStyles = {
    'Extracted Incoterms': { backgroundColor: '#e3f2fd', color: '#1565c0' },
    'Extracted Quantity': { backgroundColor: '#e3f2fd', color: '#1565c0' },
    'Extracted Amount': { backgroundColor: '#e3f2fd', color: '#1565c0' },
    'Extracted Date': { backgroundColor: '#e3f2fd', color: '#1565c0' }
  };

  const step3ColumnGroups = [
    {
      title: 'Step 1 확정 데이터 (Confirmed Data)',
      columns: ['Billing Document', 'Billing Date', 'Incoterms', 'Billed Quantity', 'Sales Unit', 'Document Currency', 'Amount'],
      style: { backgroundColor: '#fdf2f8', color: '#db2777' }
    },
    {
      title: '인보이스 추출 데이터 (Extracted Data)',
      columns: ['Extracted Incoterms', 'Extracted Quantity', 'Extracted Amount', 'Extracted Date'],
      style: { backgroundColor: '#e3f2fd', color: '#1565c0' }
    }
  ];

  // --- Render ---
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
              projects={[]} // TODO: Load projects
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
            <div className="workspace-header">
              <div className="project-info">
                <h2>{project?.name}</h2>
                <span className="project-id">ID: {project?.id}</span>
              </div>
              <div className="header-actions">
                <button
                  className="action-button"
                  onClick={() => fetchData()}
                  disabled={isLoading}
                  title="데이터 새로고침"
                  style={{ marginRight: '8px' }}
                >
                  🔄 새로고침
                </button>
                <button className="action-button" onClick={handleSaveProgress}>
                  💾 프로젝트 저장
                </button>
              </div>
            </div>

            <div className="content-area">
              {sidebarView === 'mother' && (
                <div className="placeholder-view">
                  <h3>메인 워크스페이스 (Main Workspace)</h3>
                  <p>전체 프로젝트 진행 상황을 한눈에 볼 수 있습니다.</p>
                  {/* TODO: Implement Mother Workspace Dashboard */}
                </div>
              )}

              {sidebarView === 'step1' && (
                <>
                  <div className="tabs">
                    <button
                      className={`tab - button ${activeTab === 'imported' ? 'active' : ''} `}
                      onClick={() => setActiveTab('imported')}
                    >
                      Imported Data ({ledgerData.length})
                    </button>
                    <button
                      className={`tab - button ${activeTab === 'confirmed' ? 'active' : ''} `}
                      onClick={() => setActiveTab('confirmed')}
                    >
                      Confirmed Data ({confirmedData.length})
                    </button>
                  </div>

                  <div className="tab-content">
                    {activeTab === 'imported' && (
                      <>
                        {/* Toolbar */}
                        <div className="table-toolbar" style={{
                          padding: '12px',
                          borderBottom: '1px solid #e0e0e0',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          gap: '12px',
                          backgroundColor: '#f5f5f5',
                          flexWrap: 'wrap'
                        }}>
                          {/* Left side - Edit Mode and Data Operations */}
                          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                            {/* Edit Mode Toggle */}
                            <label style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px',
                              cursor: 'pointer',
                              padding: '6px 12px',
                              backgroundColor: isEditMode ? '#fff3cd' : 'white',
                              border: '1px solid #ddd',
                              borderRadius: '4px'
                            }}>
                              <input
                                type="checkbox"
                                checked={isEditMode}
                                onChange={(e) => setIsEditMode(e.target.checked)}
                              />
                              <span>Edit Mode</span>
                            </label>

                            {/* Import Button */}
                            <button
                              className="action-button"
                              onClick={() => setIsImportModalOpen(true)}
                            >
                              📥 데이터 가져오기
                            </button>

                            {/* Row Operations - only visible in edit mode */}
                            {isEditMode && (
                              <>
                                <button
                                  className="action-button"
                                  onClick={handleAddRow}
                                  title="Add new row"
                                >
                                  ➕ 행 추가
                                </button>
                                <button
                                  className="action-button"
                                  onClick={handleDeleteSelected}
                                  title="Delete selected rows"
                                >
                                  🗑️ 선택 삭제
                                </button>
                              </>
                            )}

                            {/* Column Selector */}
                            {ledgerData.length > 0 && (
                              <ColumnSelector
                                allColumns={Object.keys(ledgerData[0])}
                                visibleColumns={visibleColumns}
                                onToggleColumn={toggleColumn}
                                onReorderColumns={handleColumnReorder}
                                onReset={resetColumns}
                              />
                            )}
                          </div>

                          {/* Right side - Save and Confirm */}
                          {ledgerData.length > 0 && (
                            <div style={{ display: 'flex', gap: '8px' }}>
                              <button
                                className="action-button"
                                onClick={handleSaveProgress}
                                disabled={isLoading || (project?.steps?.step2?.status === 'completed')}
                                title={project?.steps?.step2?.status === 'completed' ? "Step 2가 확정되어 수정할 수 없습니다." : "임시 저장"}
                              >
                                💾 임시 저장
                              </button>

                              {project?.steps?.step1?.status === 'completed' ? (
                                <button
                                  className="action-button"
                                  onClick={() => handleUnconfirm(1)}
                                  disabled={isLoading || (project?.steps?.step2?.status === 'completed')}
                                  style={{
                                    backgroundColor: '#ef4444',
                                    color: 'white'
                                  }}
                                  title={project?.steps?.step2?.status === 'completed' ? "Step 2가 확정되어 취소할 수 없습니다." : "확정 취소"}
                                >
                                  ↩️ 확정 취소
                                </button>
                              ) : (
                                <button
                                  className="action-button primary"
                                  onClick={handleConfirm}
                                  disabled={isLoading || (project?.steps?.step2?.status === 'completed')}
                                  style={{
                                    backgroundColor: '#4CAF50',
                                    color: 'white',
                                    opacity: (project?.steps?.step2?.status === 'completed') ? 0.5 : 1
                                  }}
                                  title={project?.steps?.step2?.status === 'completed' ? "Step 2가 확정되어 수정할 수 없습니다." : "전표 확정"}
                                >
                                  ✅ 전표 확정
                                </button>
                              )}
                            </div>
                          )}
                        </div>

                        {/* Table */}
                        <LedgerTable
                          ref={tableRef}
                          data={ledgerData}
                          onDataChange={onDataChange}
                          isLoading={isLoading}
                          visibleColumns={visibleColumns}
                          onColumnReorder={handleColumnReorder}
                          isEditMode={isEditMode}
                        />
                      </>
                    )}
                    {activeTab === 'confirmed' && (
                      <>
                        {confirmedData.length > 0 ? (
                          <LedgerTable
                            data={confirmedData}
                            onDataChange={() => { }} // Read-only
                            isLoading={isLoading}
                            visibleColumns={visibleColumns}
                            onColumnReorder={handleColumnReorder}
                            isEditMode={false}
                          />
                        ) : (
                          <div className="empty-state">
                            <p>확정된 데이터가 없습니다.</p>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </>
              )}

              {sidebarView === 'step2' && (
                <>
                  <div className="step-header" style={{
                    padding: '1.5rem 2rem',
                    borderBottom: '1px solid #e0e0e0',
                    background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.05) 0%, rgba(6, 182, 212, 0.03) 100%)'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <h3 style={{ margin: '0 0 0.5rem 0', color: '#0ea5e9', fontSize: '1.3rem' }}>
                          Step 2: 증빙 수집 (Evidence Collection)
                        </h3>
                        <p style={{ margin: 0, color: '#64748b', fontSize: '0.9rem' }}>
                          전표별 증빙 문서 다운로드 및 분류 상태를 관리합니다
                        </p>
                      </div>
                      <div style={{ display: 'flex', gap: '0.75rem' }}>
                        <button
                          className="action-button primary"
                          onClick={() => {
                            setImportModalTab('dms')
                            setIsImportModalOpen(true)
                          }}
                          style={{
                            background: 'linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%)',
                            color: 'white',
                            padding: '0.75rem 1.5rem',
                            borderRadius: '8px',
                            border: 'none',
                            fontWeight: '600',
                            cursor: 'pointer',
                            boxShadow: '0 2px 8px rgba(14, 165, 233, 0.3)'
                          }}
                        >
                          📥 증빙 다운로드
                        </button>
                        <button
                          className="action-button"
                          onClick={handleSplitEvidence}
                          disabled={isLoading}
                          style={{
                            background: 'linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%)',
                            color: 'white',
                            padding: '0.75rem 1.5rem',
                            borderRadius: '8px',
                            border: 'none',
                            fontWeight: '600',
                            cursor: 'pointer',
                            boxShadow: '0 2px 8px rgba(139, 92, 246, 0.3)'
                          }}
                        >
                          ✂️ Split PDF
                        </button>
                        <button
                          className="action-button success"
                          onClick={project?.steps?.step2?.status === 'completed' ? () => handleUnconfirm(2) : handleConfirmStep2}
                          disabled={isLoading || (project?.steps?.step3?.status === 'completed')}
                          style={{
                            background: project?.steps?.step2?.status === 'completed'
                              ? 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)'
                              : 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                            color: 'white',
                            padding: '0.75rem 1.5rem',
                            borderRadius: '8px',
                            border: 'none',
                            fontWeight: '600',
                            cursor: 'pointer',
                            boxShadow: project?.steps?.step2?.status === 'completed'
                              ? '0 2px 8px rgba(239, 68, 68, 0.3)'
                              : '0 2px 8px rgba(16, 185, 129, 0.3)',
                            opacity: (project?.steps?.step3?.status === 'completed') ? 0.5 : 1
                          }}
                        >
                          {project?.steps?.step2?.status === 'completed' ? '↩️ 확정 취소' : '✅ 증빙 확정'}
                        </button>
                      </div>
                    </div>
                  </div>

                  {evidenceData.length > 0 ? (
                    <div className="evidence-table-container" style={{ padding: '1.5rem' }}>
                      <div style={{
                        overflowX: 'auto',
                        border: '1px solid #e0e0e0',
                        borderRadius: '8px',
                        backgroundColor: 'white'
                      }}>
                        <table style={{
                          width: '100%',
                          borderCollapse: 'collapse',
                          fontSize: '0.9rem'
                        }}>
                          <thead>
                            <tr style={{ background: '#f8fafc', borderBottom: '2px solid #e0e0e0' }}>
                              <th style={{ padding: '1rem', textAlign: 'center', width: '40px' }}>
                                <input
                                  type="checkbox"
                                  checked={evidenceData.length > 0 && selectedRows.size === evidenceData.length}
                                  onChange={handleSelectAll}
                                  style={{ cursor: 'pointer' }}
                                />
                              </th>
                              <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>전표번호</th>
                              <th style={{ padding: '1rem', textAlign: 'center', fontWeight: '600', color: '#475569' }}>증빙</th>
                              <th style={{ padding: '1rem', textAlign: 'center', fontWeight: '600', color: '#475569' }}>증빙상태</th>
                              <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>BL</th>
                              <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>인보이스</th>
                              <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>패킹리스트</th>
                              <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>중량명세서</th>
                              <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>밀시트</th>
                              <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>화물보험증권</th>
                              <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>원산지증명서</th>
                              <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>통관서류</th>
                              <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>납품서</th>
                              <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>기타</th>
                              <th style={{ padding: '1rem', textAlign: 'center', fontWeight: '600', color: '#475569' }}>Split 상태</th>
                              <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>비고</th>
                            </tr>
                          </thead>
                          <tbody>
                            {evidenceData.map((row, index) => (
                              <tr key={row.id} style={{
                                borderBottom: '1px solid #f1f5f9',
                                transition: 'background 0.2s'
                              }}
                                onMouseEnter={(e) => e.currentTarget.style.background = '#f8fafc'}
                                onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
                              >
                                <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                  <input
                                    type="checkbox"
                                    checked={selectedRows.has(row.billingDocument)}
                                    onChange={() => handleSelectRow(row.billingDocument)}
                                    style={{ cursor: 'pointer' }}
                                  />
                                </td>
                                <td style={{ padding: '0.875rem 1rem', fontWeight: '500', color: '#1e293b' }}>
                                  {row.billingDocument}
                                </td>
                                <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                  <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                                    <button
                                      onClick={() => handleViewEvidence(row)}
                                      title="증빙 보기"
                                      style={{
                                        background: 'none',
                                        border: 'none',
                                        cursor: 'pointer',
                                        fontSize: '1.2rem',
                                        opacity: row.evidenceStatus === '미수집' ? 0.3 : 1
                                      }}
                                    >
                                      📄
                                    </button>
                                    <button
                                      onClick={() => handleUploadEvidence(row)}
                                      title="증빙 업로드"
                                      style={{
                                        background: 'none',
                                        border: 'none',
                                        cursor: 'pointer',
                                        fontSize: '1.2rem'
                                      }}
                                    >
                                      📤
                                    </button>
                                  </div>
                                </td>
                                <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                  <select
                                    value={row.evidenceStatus}
                                    onChange={(e) => {
                                      const newData = [...evidenceData]
                                      newData[index].evidenceStatus = e.target.value
                                      setEvidenceData(newData)
                                    }}
                                    style={{
                                      padding: '0.375rem 0.75rem',
                                      borderRadius: '6px',
                                      border: '1px solid #e0e0e0',
                                      fontSize: '0.85rem',
                                      backgroundColor: row.evidenceStatus === '완료' ? '#dcfce7' :
                                        row.evidenceStatus === '수집중' ? '#fef3c7' : '#f1f5f9'
                                    }}
                                  >
                                    <option value="미수집">미수집</option>
                                    <option value="수집중">수집중</option>
                                    <option value="완료">완료</option>
                                  </select>
                                </td>
                                <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                  {row.Bill_of_Lading === 'O' ? (
                                    <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Bill_of_Lading')} title="BL 보기">📄</span>
                                  ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                </td>
                                <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                  {row.Commercial_Invoice === 'O' ? (
                                    <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Commercial_Invoice')} title="인보이스 보기">📄</span>
                                  ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                </td>
                                <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                  {row.Packing_List === 'O' ? (
                                    <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Packing_List')} title="패킹리스트 보기">📄</span>
                                  ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                </td>
                                <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                  {row.Weight_List === 'O' ? (
                                    <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Weight_List')} title="중량명세서 보기">📄</span>
                                  ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                </td>
                                <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                  {row.Mill_Certificate === 'O' ? (
                                    <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Mill_Certificate')} title="밀시트 보기">📄</span>
                                  ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                </td>
                                <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                  {row.Cargo_Insurance === 'O' ? (
                                    <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Cargo_Insurance')} title="화물보험증권 보기">📄</span>
                                  ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                </td>
                                <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                  {row.Certificate_Origin === 'O' ? (
                                    <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Certificate_Origin')} title="원산지증명서 보기">📄</span>
                                  ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                </td>
                                <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                  {row.Customs_clearance_Letter === 'O' ? (
                                    <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Customs_clearance_Letter')} title="통관서류 보기">📄</span>
                                  ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                </td>
                                <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                  {row.Delivery_Note === 'O' ? (
                                    <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Delivery_Note')} title="납품서 보기">📄</span>
                                  ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                </td>
                                <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                  {row.Other === 'O' ? (
                                    <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Other')} title="기타 문서 보기">📄</span>
                                  ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                </td>
                                <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                  <select
                                    value={row.splitStatus}
                                    onChange={(e) => {
                                      const newData = [...evidenceData]
                                      newData[index].splitStatus = e.target.value
                                      setEvidenceData(newData)
                                    }}
                                    style={{
                                      padding: '0.375rem 0.75rem',
                                      borderRadius: '6px',
                                      border: '1px solid #e0e0e0',
                                      fontSize: '0.85rem',
                                      backgroundColor: row.splitStatus === 'Split 완료' ? '#dcfce7' : '#f1f5f9'
                                    }}
                                  >
                                    <option value="대기중">대기중</option>
                                    <option value="Split 완료">Split 완료</option>
                                  </select>
                                </td>
                                <td style={{ padding: '0.875rem 1rem' }}>
                                  <input
                                    type="text"
                                    value={row.notes}
                                    onChange={(e) => {
                                      const newData = [...evidenceData]
                                      newData[index].notes = e.target.value
                                      setEvidenceData(newData)
                                    }}
                                    placeholder="메모"
                                    style={{
                                      width: '100%',
                                      padding: '0.5rem',
                                      border: '1px solid #e0e0e0',
                                      borderRadius: '4px',
                                      fontSize: '0.85rem'
                                    }}
                                  />
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      {/* Summary Stats */}
                      <div style={{
                        marginTop: '1.5rem',
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                        gap: '1rem'
                      }}>
                        <div style={{
                          padding: '1rem',
                          background: 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)',
                          borderRadius: '8px',
                          border: '1px solid #bae6fd'
                        }}>
                          <div style={{ fontSize: '0.85rem', color: '#0369a1', marginBottom: '0.25rem' }}>전체 전표</div>
                          <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#0c4a6e' }}>{evidenceData.length}</div>
                        </div>
                        <div style={{
                          padding: '1rem',
                          background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
                          borderRadius: '8px',
                          border: '1px solid #fcd34d'
                        }}>
                          <div style={{ fontSize: '0.85rem', color: '#b45309', marginBottom: '0.25rem' }}>수집중</div>
                          <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#78350f' }}>
                            {evidenceData.filter(r => r.evidenceStatus === '수집중').length}
                          </div>
                        </div>
                        <div style={{
                          padding: '1rem',
                          background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)',
                          borderRadius: '8px',
                          border: '1px solid #86efac'
                        }}>
                          <div style={{ fontSize: '0.85rem', color: '#15803d', marginBottom: '0.25rem' }}>수집 완료</div>
                          <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#14532d' }}>
                            {evidenceData.filter(r => r.evidenceStatus === '완료').length}
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="empty-state" style={{
                      padding: '3rem',
                      textAlign: 'center',
                      color: '#94a3b8'
                    }}>
                      <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📋</div>
                      <h4 style={{ margin: '0 0 0.5rem 0', color: '#475569' }}>증빙 수집 대상이 없습니다</h4>
                      <p style={{ margin: 0 }}>Step 1에서 전표를 확정해주세요.</p>
                    </div>
                  )}
                </>
              )}

              {/* Step 3: Data Extraction */}
              {sidebarView === 'step3' && (
                <>
                  <div className="step-header" style={{
                    padding: '1.5rem 2rem',
                    borderBottom: '1px solid #e0e0e0',
                    background: 'linear-gradient(135deg, rgba(236, 72, 153, 0.05) 0%, rgba(219, 39, 119, 0.03) 100%)'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <h3 style={{ margin: '0 0 0.5rem 0', color: '#db2777', fontSize: '1.3rem' }}>
                          Step 3: 데이터 추출 (Data Extraction)
                        </h3>
                        <p style={{ margin: 0, color: '#64748b', fontSize: '0.9rem' }}>
                          확정된 전표 데이터에서 주요 정보를 추출하고 비교합니다
                        </p>
                      </div>
                      <div className="header-actions">
                        <button
                          className="action-button primary"
                          onClick={handleExtract}
                          disabled={isLoading}
                          style={{ backgroundColor: '#db2777' }}
                        >
                          {isLoading ? '추출 중...' : '⚡ 데이터 추출 실행'}
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className="workspace-content" style={{ padding: '1.5rem' }}>
                    {extractionData.length === 0 ? (
                      <div className="empty-state">
                        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📋</div>
                        <h4 style={{ margin: '0 0 0.5rem 0', color: '#475569' }}>데이터가 없습니다</h4>
                        <p style={{ margin: 0 }}>Step 1에서 전표를 확정해주세요.</p>
                      </div>
                    ) : (
                      <LedgerTable
                        ref={tableRef}
                        data={extractionData}
                        onDataChange={() => { }} // Read-only
                        isLoading={isLoading}
                        visibleColumns={[
                          'Billing Document',
                          'Billing Date',
                          'Incoterms',
                          'Billed Quantity',
                          'Sales Unit',
                          'Document Currency',
                          'Amount',
                          'Extracted Incoterms',
                          'Extracted Quantity',
                          'Extracted Amount',
                          'Extracted Date'
                        ]}
                        onColumnReorder={() => { }}
                        isEditMode={true} // Enable selection
                        headerStyles={step3HeaderStyles}
                        columnGroups={step3ColumnGroups}
                        onCellClick={handleCellClick}
                      />
                    )}
                  </div>
                </>
              )}

              {sidebarView === 'step4' && (
                <div className="placeholder-view">
                  <h3>Step 4: 자동 대사 (Auto-Reconciliation)</h3>
                  <p>추출된 데이터와 전표 데이터를 자동으로 대사합니다.</p>
                </div>
              )}

              {sidebarView === 'dashboard' && (
                <div className="placeholder-view">
                  <h3>결과 대시보드 (Results Dashboard)</h3>
                  <p>최종 대사 결과 및 통계를 확인합니다.</p>
                </div>
              )}
            </div>

            <DataImportModal
              isOpen={isImportModalOpen}
              onClose={() => setIsImportModalOpen(false)}
              onFileUpload={handleFileUpload}
              onSapFetch={handleSapFetch}
              onDMSDownload={handleDMSDownload}
              initialTab={importModalTab}
              project={project}
              currentStep={sidebarView}
            />
            {/* Download Progress Modal */}
            {showDownloadProgress && (
              <div className="modal-overlay">
                <div className="modal-content" style={{ width: '400px', textAlign: 'center' }}>
                  <h3>📥 DMS 증빙 다운로드 중...</h3>
                  <div style={{ margin: '20px 0' }}>
                    <div style={{
                      width: '100%',
                      height: '20px',
                      backgroundColor: '#eee',
                      borderRadius: '10px',
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        width: `${(downloadProgress.current / downloadProgress.total) * 100}% `,
                        height: '100%',
                        backgroundColor: '#4CAF50',
                        transition: 'width 0.3s ease'
                      }} />
                    </div>
                    <p style={{ marginTop: '10px' }}>
                      {downloadProgress.current} / {downloadProgress.total} 완료
                    </p>
                    <p style={{ fontSize: '12px', color: '#666', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {downloadProgress.message}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Evidence Modals */}
            <PDFViewerModal
              isOpen={pdfViewerState.isOpen}
              onClose={() => setPdfViewerState(prev => ({ ...prev, isOpen: false }))}
              files={pdfViewerState.files}
              title={pdfViewerState.title}
              onDelete={handleDeleteEvidence}
            />
            <EvidenceUploadModal
              isOpen={uploadModalState.isOpen}
              onClose={() => setUploadModalState(prev => ({ ...prev, isOpen: false }))}
              onUpload={onManualUpload}
              billingDocument={uploadModalState.billingDocument}
            />

            {/* Loading Overlay */}
            {isLoading && (
              <div className="loading-overlay">
                <div className="spinner"></div>
                <p>Loading...</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default App
