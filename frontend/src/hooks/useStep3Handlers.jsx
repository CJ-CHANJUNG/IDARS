import { useProject } from '../context/ProjectContext';

/**
 * Custom hook for Step 3 event handlers
 * Manages extraction, comparison, and evidence viewing logic
 */
export const useStep3Handlers = (step3SelectedRows, setStep3SelectedRows) => {
    const {
        project,
        comparisonResults, setComparisonResults,
        extractionMode,
        setIsLoading
    } = useProject();

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
                        const index = newResults.findIndex(
                            item => item.billing_document === extractedItem.billing_document
                        );
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
            const response = await fetch(
                `http://127.0.0.1:5000/api/projects/${project.id}/evidence/search?billingDocument=${billingDocument}`
            );
            let files = await response.json();

            if (files && files.length > 0) {
                // Apply filter if specified
                if (filterType) {
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
                }

                // Sort to prioritize original files
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

    const handleSendToDashboard = async () => {
        if (!project?.id) return;
        if (!window.confirm('추출된 결과를 대시보드로 전송하시겠습니까?')) return;

        try {
            const response = await fetch(
                `http://127.0.0.1:5000/api/projects/${project.id}/step3/send-to-dashboard`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ projectsDir: 'Data/projects' })
                }
            );

            if (response.ok) {
                alert('✅ 결과가 대시보드로 전송되었습니다.');
            } else {
                const error = await response.json();
                alert('전송 실패: ' + (error.error || '알 수 없는 오류'));
            }
        } catch (err) {
            alert('오류 발생: ' + err.message);
        }
    };

    return {
        handleStep3SelectAll,
        handleStep3SelectRow,
        handleExtractAndCompare,
        handleViewEvidence,
        handleUpdateField,
        handleFinalConfirm,
        handleSendToDashboard
    };
};
