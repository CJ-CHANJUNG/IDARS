import { useProject } from '../context/ProjectContext';

/**
 * Custom hook for Step 3 event handlers
 * Manages extraction, comparison, and evidence viewing logic
 */
export const useStep3Handlers = (step3SelectedRows, setStep3SelectedRows, setExtractionProgress) => {
    const {
        project,
        comparisonResults, setComparisonResults,
        extractionMode,
        setIsLoading,
        setSidebarView
    } = useProject();

    const handleStep3SelectAll = (e, specificIds = null) => {
        if (e.target.checked) {
            if (specificIds) {
                // If specific IDs are provided (e.g. from filtered view), select only those
                setStep3SelectedRows(new Set(specificIds));
            } else {
                // Otherwise select all loaded results
                const allIds = new Set(comparisonResults.map(row => row.billing_document));
                setStep3SelectedRows(allIds);
            }
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

        // ★ Start Polling
        let intervalId;
        if (setExtractionProgress) {
            setExtractionProgress({ status: 'running', current: 0, total: selectedIds.length, message: '추출 시작...' });

            const pollProgress = async () => {
                try {
                    const res = await fetch(`/api/projects/${project.id}/extraction-progress`);
                    if (res.ok) {
                        const data = await res.json();
                        setExtractionProgress(data);
                    }
                } catch (e) {
                    console.error("Polling error", e);
                }
            };

            // Initial poll
            pollProgress();
            intervalId = setInterval(pollProgress, 1000);
        }
        try {
            const response = await fetch(`/api/projects/${project.id}/step3/extract-and-compare`, {
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
            alert('증빙 파일을 검색하는데 실패했습니다.');
        } finally {
            if (intervalId) clearInterval(intervalId);
            if (setExtractionProgress) setExtractionProgress(null);
            setIsLoading(false);
        }
    };

    const handleSaveDraft = async (finalJudgments) => {
        if (!project?.id) return;

        // ★ Use confirm-judgment endpoint (same as final confirmation)
        try {
            const response = await fetch(
                `/api/projects/${project.id}/step3/confirm-judgment`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        judgments: finalJudgments,
                        projectsDir: 'Data/projects'
                    })
                }
            );

            if (response.ok) {
                alert('✅ 임시 저장이 완료되었습니다.');
            } else {
                const error = await response.json();
                alert('저장 실패: ' + (error.error || '알 수 없는 오류'));
            }
        } catch (err) {
            alert('오류 발생: ' + err.message);
        }
    };

    const handleViewEvidence = async (billingDocument, filterType = null, field = null, coordinates = null) => {
        try {
            const response = await fetch(
                `/api/projects/${project.id}/evidence/search?billingDocument=${billingDocument}`
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

                // Sort: Original first
                files.sort((a, b) => {
                    if (a.type === 'original' && b.type !== 'original') return -1;
                    if (a.type !== 'original' && b.type === 'original') return 1;
                    return 0;
                });

                // Open first PDF file in new window/tab
                if (files.length > 0) {
                    const firstFile = files[0];
                    let pdfUrl = `/api/projects/${project.id}/files/${firstFile.path}`;

                    // Append highlight coordinates if available
                    if (coordinates && Array.isArray(coordinates) && coordinates.length === 4) {
                        const [ymin, xmin, ymax, xmax] = coordinates;
                        // Check if coordinates are valid (not all 0)
                        if (ymin !== 0 || xmin !== 0 || ymax !== 0 || xmax !== 0) {
                            pdfUrl += `?highlight=${ymin},${xmin},${ymax},${xmax}`;
                        }
                    }

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

    const handleFinalConfirm = async (selectedCorrections, selectedIds, finalJudgments) => {
        if (!project?.id) return;

        // Prepare judgments payload
        const judgments = {};
        selectedIds.forEach(docId => {
            // Use the status from finalJudgments if available, otherwise default to current status?
            // Actually, finalJudgments contains the *current UI state* of the dropdowns.
            if (finalJudgments[docId]) {
                judgments[docId] = finalJudgments[docId];
            }
        });

        if (Object.keys(judgments).length === 0) {
            console.warn('No judgments to save');
            return;
        }

        try {
            const response = await fetch(
                `/api/projects/${project.id}/step3/confirm-judgment`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        judgments: judgments,
                        projectsDir: 'Data/projects'
                    })
                }
            );

            if (response.ok) {
                // alert('✅ 최종 판단이 저장되었습니다.'); // ComparisonTableEnhanced already alerts
                console.log('Judgments saved successfully');

                // ★ DO NOT update auto_comparison.status!
                // 1차 판단은 AI 자동 판단이므로 변경하지 않음
                // final_status만 서버에 저장됨
            } else {
                const error = await response.json();
                alert('저장 실패: ' + (error.error || '알 수 없는 오류'));
            }
        } catch (err) {
            alert('오류 발생: ' + err.message);
        }
    };

    const handleSendToDashboard = async () => {
        console.log('[DEBUG] handleSendToDashboard called');
        console.log('[DEBUG] Project:', project);

        if (!project?.id) {
            console.error('[DEBUG] No project ID found');
            return;
        }

        if (!window.confirm('추출된 결과를 대시보드로 전송하시겠습니까?')) {
            console.log('[DEBUG] User cancelled confirm');
            return;
        }

        console.log('[DEBUG] Sending request...');
        try {
            const response = await fetch(
                `/api/projects/${project.id}/step3/send-to-dashboard`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ projectsDir: 'Data/projects' })
                }
            );

            if (response.ok) {
                alert('✅ 결과가 대시보드로 전송되었습니다.');
                // Navigate to Dashboard
                if (setSidebarView) {
                    setSidebarView('step4');
                }
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
        handleSendToDashboard,
        handleSaveDraft
    };
};

// End of hook
