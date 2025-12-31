import React, { useState } from 'react';
import { useProject } from '../../context/ProjectContext';
import { useStep3Data } from '../../hooks/useStep3Data.jsx';
import { useStep3Handlers } from '../../hooks/useStep3Handlers.jsx';
import Step3Header from './Step3Header';
import ComparisonTableEnhanced from '../ComparisonTableEnhanced';
import PDFViewerModal from '../PDFViewerModal';
import ProgressBar from '../ProgressBar';

const Step3DataExtraction = () => {
    const {
        confirmedData,
        evidenceData,
        comparisonResults,
        finalJudgments, // ★ Get finalJudgments from context
        project // ★ Get project
    } = useProject();

    const [step3SelectedRows, setStep3SelectedRows] = useState(new Set());
    // viewMode removed - using only Basic view as main interface
    const [pdfViewerState, setPdfViewerState] = useState({
        isOpen: false,
        files: [],
        title: '',

        billingDocument: null,
        highlightCoordinates: null // ★ Add highlightCoordinates
    });
    const [extractionProgress, setExtractionProgress] = useState(null); // ★ Progress state

    // Load data using custom hook
    useStep3Data();

    // Get handlers from custom hook
    const {
        handleStep3SelectAll,
        handleStep3SelectRow,
        handleExtractAndCompare,
        handleViewEvidence,
        handleUpdateField,
        handleFinalConfirm,
        handleSendToDashboard,

        handleSaveDraft // ★ Get handleSaveDraft
    } = useStep3Handlers(step3SelectedRows, setStep3SelectedRows, setExtractionProgress); // ★ Pass setter

    return (
        <div className="dp-card">
            {/* Header */}
            <div className="dp-dashboard-header" style={{ padding: '1.5rem', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#1e293b', marginBottom: '0.5rem' }}>Step 3: Data Extraction & Comparison</h1>
                    <p style={{ color: '#64748b' }}>Extract data from evidence and compare with ledger.</p>
                </div>
                <div className="dp-panel-controls" style={{ border: 'none', padding: 0, background: 'transparent' }}>
                    <div className="dp-panel-group">
                        <button
                            className="dp-btn dp-btn-primary"
                            onClick={handleExtractAndCompare}
                            disabled={extractionProgress?.status === 'running'}
                        >
                            ⚡ Extract & Compare
                        </button>
                        <button
                            className="dp-btn dp-btn-secondary"
                            onClick={() => handleSaveDraft(finalJudgments)}
                        >
                            💾 Save Draft
                        </button>
                        <button
                            className="dp-btn dp-btn-success"
                            onClick={handleSendToDashboard}
                            disabled={!comparisonResults || comparisonResults.length === 0}
                        >
                            🚀 Send to Dashboard
                        </button>
                    </div>
                </div>
            </div>

            <div className="workspace-content" style={{ padding: '1.5rem', height: 'calc(100vh - 180px)', overflow: 'auto', background: 'white' }}>
                {/* Progress Bar */}
                {extractionProgress && extractionProgress.status === 'running' && (
                    <div style={{ marginBottom: '1.5rem' }}>
                        <ProgressBar progress={extractionProgress} />
                    </div>
                )}

                {comparisonResults && comparisonResults.length > 0 ? (
                    <>
                        <div className="dp-table-wrapper">
                            <ComparisonTableEnhanced
                                data={comparisonResults}
                                viewMode="basic"
                                onViewPDF={async (billingDocument, docType, field, coordinates) => {
                                    try {
                                        const response = await fetch(
                                            `/api/projects/${project?.id}/evidence/search?billingDocument=${billingDocument}`
                                        );
                                        let files = await response.json();

                                        if (files && files.length > 0) {
                                            const filterType = docType || 'Commercial_Invoice';
                                            const filtered = files.filter(f => {
                                                const lowerName = f.filename.toLowerCase();
                                                if (filterType === 'Commercial_Invoice') {
                                                    return lowerName.includes('commercial_invoice') || lowerName.includes('invoice');
                                                } else if (filterType === 'Bill_of_Lading') {
                                                    return lowerName.includes('bill_of_lading') || lowerName.includes('bl') || lowerName.includes('b_l');
                                                }
                                                return true;
                                            });
                                            if (filtered.length > 0) files = filtered;

                                            files.sort((a, b) => {
                                                if (a.type === 'original' && b.type !== 'original') return -1;
                                                if (a.type !== 'original' && b.type === 'original') return 1;
                                                return 0;
                                            });

                                            const filesWithUrl = files.map(f => ({
                                                ...f,
                                                url: `/api/projects/${project?.id}/files/${f.path}`
                                            }));

                                            console.log(`[PDFViewer] Opening ${billingDocument} (${filterType})`);
                                            console.log(`[PDFViewer] Field: ${field}, Coordinates:`, coordinates);

                                            const viewerState = {
                                                files: filesWithUrl,
                                                title: `${billingDocument} (${filterType})`,
                                                highlightCoordinates: coordinates
                                            };
                                            localStorage.setItem('pdfViewerPopoutState', JSON.stringify(viewerState));

                                            const popoutUrl = `${window.location.origin}${window.location.pathname}?mode=viewer`;
                                            window.open(popoutUrl, `pdf_${billingDocument}`, 'width=1200,height=900,resizable=yes,scrollbars=yes');
                                        } else {
                                            alert('해당 전표의 증빙 파일을 찾을 수 없습니다.');
                                        }
                                    } catch (err) {
                                        console.error(err);
                                        alert('증빙 파일을 검색하는데 실패했습니다.');
                                    }
                                }}
                                onUpdateField={handleUpdateField}
                                onFinalConfirm={handleFinalConfirm}
                                selectedRows={step3SelectedRows}
                                onRowSelect={handleStep3SelectRow}
                                onSelectAll={handleStep3SelectAll}
                            />
                        </div>
                    </>
                ) : evidenceData && evidenceData.length > 0 ? (
                    <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8', background: '#f8fafc', borderRadius: '12px', border: '2px dashed #e2e8f0' }}>
                        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📋</div>
                        <h4 style={{ margin: '0 0 0.5rem 0', color: '#475569', fontSize: '1.2rem' }}>Ready for Extraction</h4>
                        <p style={{ margin: 0, color: '#64748b' }}>
                            {evidenceData.length} items confirmed in Step 2.<br />
                            Click "⚡ Extract & Compare" to start the OCR process.
                        </p>
                    </div>
                ) : (
                    <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>
                        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>❌</div>
                        <h4 style={{ margin: '0 0 0.5rem 0', color: '#475569', fontSize: '1.2rem' }}>No Data Available</h4>
                        <p style={{ margin: 0, color: '#64748b' }}>Please complete Step 1 and Step 2 first.</p>
                    </div>
                )}
            </div>

            <PDFViewerModal
                isOpen={pdfViewerState.isOpen}
                onClose={() => setPdfViewerState(prev => ({ ...prev, isOpen: false }))}
                files={pdfViewerState.files}
                title={pdfViewerState.title}
                highlightCoordinates={pdfViewerState.highlightCoordinates}
                onDelete={() => { }}
            />
        </div>
    );
};

export default Step3DataExtraction;
