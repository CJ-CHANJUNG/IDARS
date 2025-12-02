import React, { useState, useEffect } from 'react';
import { useProject } from '../../context/ProjectContext';
import ComparisonTableEnhanced from '../ComparisonTableEnhanced';
import PDFViewerModal from '../PDFViewerModal';

const Step3DataExtraction = () => {
    const {
        project,
        confirmedData,
        evidenceData,
        comparisonResults, setComparisonResults,
        extractionMode, setExtractionMode,
        isLoading, setIsLoading,
        setExtractionData
    } = useProject();

    const [step3SelectedRows, setStep3SelectedRows] = useState(new Set());
    const [pdfViewerState, setPdfViewerState] = useState({
        isOpen: false,
        files: [],
        title: '',
        billingDocument: null
    });

    // --- Effects ---
    useEffect(() => {
        if (project) {
            // 1. Pre-load comparison table with confirmed data
            if (confirmedData && confirmedData.length > 0) {
                if (comparisonResults.length === 0 || comparisonResults.length !== confirmedData.length) {
                    const initialData = confirmedData.map(row => ({
                        billing_document: String(row['Billing Document'] || row['전표번호']),
                        step1_data: {
                            date: row['Billing Date'],
                            amount: row['Amount'],
                            currency: row['Document Currency'],
                            quantity: row['Billed Quantity'],
                            unit: row['Sales unit'],
                            incoterms: row['Incoterms']
                        },
                        ocr_data: {
                            date: '', amount: '', quantity: '', incoterms: '',
                            date_confidence: 0, amount_confidence: 0, quantity_confidence: 0, incoterms_confidence: 0
                        },
                        bl_data: null,
                        auto_comparison: { status: 'ready', match_score: 0, details: [] },
                        api_usage: { input: 0, output: 0 }
                    }));
                    setComparisonResults(initialData);
                }
                // 2. Load extraction data
                loadStep3ExtractionData();
            }
        }
    }, [project, confirmedData]);

    // --- Data Loading ---
    const loadStep3ExtractionData = async () => {
        if (!project) return;
        try {
            const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/step3/extraction-data`);
            if (response.ok) {
                const result = await response.json();
                setExtractionData(result.data);

                if (result.data && result.data.length > 0) {
                    setComparisonResults(prevResults => {
                        let baseData = prevResults;
                        if (baseData.length === 0 && confirmedData.length > 0) {
                            baseData = confirmedData.map(row => ({
                                billing_document: String(row['Billing Document'] || row['전표번호']),
                                step1_data: {
                                    date: row['Billing Date'],
                                    amount: row['Amount'],
                                    currency: row['Document Currency'],
                                    quantity: row['Billed Quantity'],
                                    unit: row['Sales unit'],
                                    incoterms: row['Incoterms']
                                },
                                ocr_data: { date: '', amount: '', quantity: '', incoterms: '', date_confidence: 0, amount_confidence: 0, quantity_confidence: 0, incoterms_confidence: 0 },
                                bl_data: null,
                                auto_comparison: { status: 'ready', match_score: 0, details: [] },
                                api_usage: { input: 0, output: 0 }
                            }));
                        }

                        const newResults = [...baseData];
                        result.data.forEach(loadedItem => {
                            const index = newResults.findIndex(item => String(item.billing_document) === String(loadedItem.billing_document));
                            if (index !== -1) {
                                newResults[index] = {
                                    ...newResults[index],
                                    ocr_data: loadedItem.ocr_data,
                                    bl_data: loadedItem.bl_data,
                                    auto_comparison: loadedItem.auto_comparison,
                                    api_usage: loadedItem.api_usage
                                };
                            }
                        });
                        return newResults;
                    });
                }
            }
        } catch (err) {
            console.error('[STEP3 LOAD] Exception:', err);
        }
    };

    // --- Handlers ---
    const handleStep3SelectAll = (e) => {
        if (e.target.checked) {
            const allIds = new Set(comparisonResults.map(row => row.billing_document));
            setStep3SelectedRows(allIds);
        } else {
            setStep3SelectedRows(new Set());
        }
    };

    const handleStep3SelectRow = (billingDocument) => {
        const newSelected = new Set(step3SelectedRows);
        if (newSelected.has(billingDocument)) {
            newSelected.delete(billingDocument);
        } else {
            newSelected.add(billingDocument);
        }
        setStep3SelectedRows(newSelected);
    };

    const handleExtractAndCompare = async () => {
        if (!project) return;

        let selectedIds = [];
        if (step3SelectedRows.size > 0) {
            selectedIds = Array.from(step3SelectedRows);
        } else {
            alert('추출할 전표를 선택해주세요. (체크박스 선택 필수)');
            return;
        }

        setIsLoading(true);
        try {
            const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/step3/extract-and-compare`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    extraction_mode: extractionMode,
                    projectsDir: 'Data/projects',
                    target_ids: selectedIds
                }),
            });

            const result = await response.json();

            if (response.ok) {
                setComparisonResults(prevResults => {
                    const newResults = [...prevResults];
                    result.comparison_results.forEach(extractedItem => {
                        const index = newResults.findIndex(item => item.billing_document === extractedItem.billing_document);
                        if (index !== -1) {
                            newResults[index] = {
                                ...newResults[index],
                                ocr_data: extractedItem.ocr_data,
                                bl_data: extractedItem.bl_data,
                                auto_comparison: extractedItem.auto_comparison,
                                api_usage: extractedItem.api_usage
                            };
                        }
                    });
                    return newResults;
                });
                alert(`✅ 추출 및 비교 완료!\n\n추출: ${result.extraction_results.invoices_extracted}/${result.extraction_results.total_documents}\n완전일치: ${result.summary.complete_match}\n일부오류: ${result.summary.partial_error}\n재검토필요: ${result.summary.review_required}`);
            } else {
                alert('추출 실패: ' + result.error);
            }
        } catch (err) {
            console.error(err);
            alert('오류 발생: ' + err.message);
        } finally {
            setIsLoading(false);
        }
    };

    const handleViewEvidence = async (billingDocument, filterType = null) => {
        try {
            const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/evidence/search?billingDocument=${billingDocument}`);
            let files = await response.json();

            if (files && files.length > 0) {
                if (filterType) {
                    const filtered = files.filter(f => {
                        const lowerName = f.filename.toLowerCase();
                        if (filterType === 'Commercial_Invoice') return lowerName.includes('commercial_invoice') || lowerName.includes('invoice');
                        return true;
                    });
                    if (filtered.length > 0) files = filtered;
                }

                files.sort((a, b) => {
                    if (a.type === 'original' && b.type !== 'original') return -1;
                    if (a.type !== 'original' && b.type === 'original') return 1;
                    return 0;
                });

                // Open first PDF file in new window/tab
                if (files.length > 0) {
                    const firstFile = files[0];
                    const pdfUrl = `http://127.0.0.1:5000/api/projects/${project.id}/files/${firstFile.path}`;
                    window.open(pdfUrl, '_blank', 'width=1200,height=800,resizable=yes,scrollbars=yes');
                }
            } else {
                alert('해당 전표의 증빙 파일을 찾을 수 없습니다.');
            }
        } catch (err) {
            console.error(err);
            alert('증빙 파일을 검색하는데 실패했습니다.');
        }
    };

    const handleUpdateField = (billingDocument, field, value) => {
        setComparisonResults(prev => prev.map(row => {
            if (row.billing_document === billingDocument) {
                return {
                    ...row,
                    ocr_data: {
                        ...row.ocr_data,
                        [field]: value
                    }
                };
            }
            return row;
        }));
    };

    const handleFinalConfirm = (billingDocument) => {
        // TODO: Implement single row confirmation logic if needed
        console.log('Final confirm for:', billingDocument);
    };

    return (
        <>
            <div style={{
                padding: '0.4rem 1rem',
                borderBottom: '1px solid #e0e0e0',
                background: 'linear-gradient(135deg, rgba(236, 72, 153, 0.05) 0%, rgba(219, 39, 119, 0.03) 100%)'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                        <h3 style={{ margin: 0, color: '#db2777', fontSize: '0.95rem' }}>
                            Step 3: 데이터 추출
                        </h3>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ fontSize: '0.8rem', fontWeight: '500', color: '#64748b' }}>모드:</span>
                            <button
                                onClick={() => setExtractionMode('basic')}
                                style={{
                                    padding: '0.25rem 0.6rem',
                                    borderRadius: '4px',
                                    border: extractionMode === 'basic' ? '2px solid #db2777' : '1px solid #cbd5e1',
                                    backgroundColor: extractionMode === 'basic' ? '#fce7f3' : 'white',
                                    color: extractionMode === 'basic' ? '#db2777' : '#64748b',
                                    fontWeight: extractionMode === 'basic' ? '600' : '400',
                                    fontSize: '0.75rem',
                                    cursor: 'pointer'
                                }}
                            >
                                기본
                            </button>
                            <button
                                onClick={() => setExtractionMode('detailed')}
                                style={{
                                    padding: '0.25rem 0.6rem',
                                    borderRadius: '4px',
                                    border: extractionMode === 'detailed' ? '2px solid #db2777' : '1px solid #cbd5e1',
                                    backgroundColor: extractionMode === 'detailed' ? '#fce7f3' : 'white',
                                    color: extractionMode === 'detailed' ? '#db2777' : '#64748b',
                                    fontWeight: extractionMode === 'detailed' ? '600' : '400',
                                    fontSize: '0.75rem',
                                    cursor: 'pointer'
                                }}
                            >
                                상세
                            </button>
                        </div>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                            className="action-button primary"
                            onClick={handleExtractAndCompare}
                            disabled={isLoading || !confirmedData || confirmedData.length === 0}
                            style={{
                                backgroundColor: '#db2777',
                                color: '#ffffff',
                                padding: '0.4rem 0.8rem',
                                fontSize: '0.85rem'
                            }}
                        >
                            {isLoading ? '추출 중...' : '⚡ 추출 및 비교'}
                        </button>
                        <button
                            className="action-button"
                            onClick={async () => {
                                if (!project?.id) return;
                                if (!window.confirm('추출된 결과를 대시보드로 전송하시겠습니까?')) return;

                                try {
                                    const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/step3/send-to-dashboard`, {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ projectsDir: 'Data/projects' })
                                    });

                                    if (response.ok) {
                                        alert('✅ 결과가 대시보드로 전송되었습니다.');
                                    } else {
                                        const error = await response.json();
                                        alert('전송 실패: ' + (error.error || '알 수 없는 오류'));
                                    }
                                } catch (err) {
                                    alert('오류 발생: ' + err.message);
                                }
                            }}
                            disabled={!comparisonResults || comparisonResults.length === 0}
                            style={{
                                backgroundColor: '#10b981',
                                color: 'white',
                                padding: '0.4rem 0.8rem',
                                fontSize: '0.85rem'
                            }}
                        >
                            📊 대시보드 전송
                        </button>
                    </div>
                </div>
            </div>

            <div className="workspace-content" style={{ padding: '1rem', height: 'calc(100vh - 100px)', overflow: 'auto' }}>
                {comparisonResults && comparisonResults.length > 0 ? (
                    <ComparisonTableEnhanced
                        data={comparisonResults}
                        onViewPDF={(billingDocument) => {
                            handleViewEvidence(billingDocument, 'Commercial_Invoice');
                        }}
                        onUpdateField={handleUpdateField}
                        onFinalConfirm={handleFinalConfirm}
                        selectedRows={step3SelectedRows}
                        onRowSelect={handleStep3SelectRow}
                        onSelectAll={handleStep3SelectAll}
                    />
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
