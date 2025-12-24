import React, { useState } from 'react';
import { useProject } from '../../context/ProjectContext';
import { useStep3Data } from '../../hooks/useStep3Data.jsx';
import { useStep3Handlers } from '../../hooks/useStep3Handlers.jsx';
import Step3Header from './Step3Header';
import ComparisonTableEnhanced from '../ComparisonTableEnhanced';
import PDFViewerModal from '../PDFViewerModal';

const Step3DataExtraction = () => {
    const {
        confirmedData,
        evidenceData,
        comparisonResults,
        finalJudgments // ★ Get finalJudgments from context
    } = useProject();

    const [step3SelectedRows, setStep3SelectedRows] = useState(new Set());
    const [viewMode, setViewMode] = useState('basic'); // 'basic' or 'detailed'
    const [pdfViewerState, setPdfViewerState] = useState({
        isOpen: false,
        files: [],
        title: '',
        billingDocument: null
    });

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
    } = useStep3Handlers(step3SelectedRows, setStep3SelectedRows);

    return (
        <>
            <Step3Header
                onExtractAndCompare={handleExtractAndCompare}
                onSendToDashboard={handleSendToDashboard}
                onSaveDraft={() => handleSaveDraft(finalJudgments)}
                hasComparisonResults={comparisonResults && comparisonResults.length > 0}
            />

            <div className="workspace-content" style={{ padding: '1rem', height: 'calc(100vh - 100px)', overflow: 'auto' }}>
                {comparisonResults && comparisonResults.length > 0 ? (
                    <>
                        {/* View Mode Tabs */}
                        <div style={{
                            marginBottom: '1rem',
                            borderBottom: '2px solid #e2e8f0',
                            display: 'flex',
                            gap: '0.5rem'
                        }}>
                            <button
                                onClick={() => setViewMode('basic')}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    border: 'none',
                                    background: viewMode === 'basic' ? '#3b82f6' : 'transparent',
                                    color: viewMode === 'basic' ? 'white' : '#64748b',
                                    fontWeight: viewMode === 'basic' ? 'bold' : 'normal',
                                    cursor: 'pointer',
                                    borderRadius: '4px 4px 0 0',
                                    transition: 'all 0.2s'
                                }}
                            >
                                📊 기본 뷰
                            </button>
                            <button
                                onClick={() => setViewMode('detailed')}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    border: 'none',
                                    background: viewMode === 'detailed' ? '#3b82f6' : 'transparent',
                                    color: viewMode === 'detailed' ? 'white' : '#64748b',
                                    fontWeight: viewMode === 'detailed' ? 'bold' : 'normal',
                                    cursor: 'pointer',
                                    borderRadius: '4px 4px 0 0',
                                    transition: 'all 0.2s'
                                }}
                            >
                                🔍 상세 뷰
                            </button>
                        </div>

                        <ComparisonTableEnhanced
                            data={comparisonResults}
                            viewMode={viewMode}
                            onViewPDF={(billingDocument, docType, field, coordinates) => {
                                handleViewEvidence(billingDocument, docType || 'Commercial_Invoice', field, coordinates);
                            }}
                            onUpdateField={handleUpdateField}
                            onFinalConfirm={handleFinalConfirm}
                            selectedRows={step3SelectedRows}
                            onRowSelect={handleStep3SelectRow}
                            onSelectAll={handleStep3SelectAll}
                        />
                    </>
                ) : evidenceData && evidenceData.length > 0 ? (
                    <div>
                        <div style={{
                            padding: '1rem',
                            background: '#f8fafc',
                            borderRadius: '8px',
                            marginBottom: '1rem',
                            border: '1px solid #e2e8f0'
                        }}>
                            <h4 style={{ margin: '0 0 0.5rem 0', color: '#475569' }}>
                                📋 Step 2 확정 데이터 ({evidenceData.length}건)
                            </h4>
                            <p style={{ margin: 0, fontSize: '0.9rem', color: '#64748b' }}>
                                증빙 수집이 완료된 항목입니다. "⚡ 데이터 추출 및 비교" 버튼을 클릭하여 OCR 추출을 시작하세요.
                            </p>
                        </div>
                    </div>
                ) : (
                    <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
                        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>❌</div>
                        <h4 style={{ margin: '0 0 0.5rem 0', color: '#475569' }}>확정된 데이터가 없습니다</h4>
                        <p style={{ margin: 0 }}>Step 1과 Step 2를 먼저 완료해주세요.</p>
                    </div>
                )}
            </div>

            <PDFViewerModal
                isOpen={pdfViewerState.isOpen}
                onClose={() => setPdfViewerState(prev => ({ ...prev, isOpen: false }))}
                files={pdfViewerState.files}
                title={pdfViewerState.title}
                onDelete={() => { }} // Read-only in Step 3
            />
        </>
    );
};

export default Step3DataExtraction;
