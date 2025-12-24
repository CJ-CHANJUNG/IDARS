import { useState, useEffect, useRef } from 'react';
import { useProject } from '../context/ProjectContext'; // Import context

/**
 * Custom hook for managing comparison table state and logic
 */
export const useComparisonTable = (data, selectedRows, viewMode = 'basic') => {
    const { finalJudgments, setFinalJudgments } = useProject(); // Use global state

    const [statusFilter, setStatusFilter] = useState('all');
    const [docFilter, setDocFilter] = useState('');
    const [editingCell, setEditingCell] = useState(null);
    const [editValue, setEditValue] = useState('');
    const [userCorrections, setUserCorrections] = useState({});
    // const [finalJudgments, setFinalJudgments] = useState({}); // Removed local state
    const initializedRef = useRef(false);

    // ★ Auto-populate finalJudgments from 1차 판단 (only once when data first loads and global state is empty)
    useEffect(() => {
        // Check if data is "real" (has actual status or final_status), not just default 'ready' placeholders
        const hasValidData = data && data.length > 0 && data.some(item =>
            item.final_status || (item.auto_comparison?.status && item.auto_comparison.status !== 'ready')
        );

        if (hasValidData && (!initializedRef.current || Object.keys(finalJudgments).length === 0)) {
            console.log('[useComparisonTable] Initializing finalJudgments from loaded data');
            const initialJudgments = {};
            const initialCorrections = {};

            data.forEach(item => {
                const billingDoc = item.billing_document;

                // ★ FIX: Only initialize if not already in global state (preserve in-memory edits)
                if (!finalJudgments[billingDoc]) {
                    // Prioritize saved draft (final_status) over system judgment (auto_comparison)
                    let autoStatus = item.final_status || item.auto_comparison?.status;

                    // ★ Infer 'no_evidence' if BL data is missing and no final status is set
                    if (!item.final_status && (!item.bl_data || Object.keys(item.bl_data).length === 0)) {
                        autoStatus = 'no_evidence';
                    }

                    if (item.final_status) {
                        console.log(`[DEBUG] Found final_status for ${billingDoc}: ${item.final_status}`);
                    }

                    // Map auto status to final judgment value
                    let judgment = '';
                    if (autoStatus === 'complete_match') {
                        judgment = 'complete_match'; // Use exact status codes for consistency
                    } else if (autoStatus === 'partial_error') {
                        judgment = 'partial_error';
                    } else if (autoStatus === 'review_required') {
                        judgment = 'review_required';
                    } else if (autoStatus === 'no_evidence') {
                        judgment = 'no_evidence';
                    }

                    if (judgment) {
                        initialJudgments[billingDoc] = judgment;
                    }
                }

                // Load user corrections (Always load since local state resets on mount)
                if (item.user_corrections && Object.keys(item.user_corrections).length > 0) {
                    initialCorrections[billingDoc] = item.user_corrections;
                }
            });

            console.log('[useComparisonTable] Initial judgments:', Object.keys(initialJudgments).length, 'items');

            // Only update if we have something to set, or if we want to ensure we're synced
            if (Object.keys(initialJudgments).length > 0) {
                setFinalJudgments(prev => ({ ...prev, ...initialJudgments }));
            }
            if (Object.keys(initialCorrections).length > 0) {
                setUserCorrections(prev => ({ ...prev, ...initialCorrections }));
            }

            // Mark as initialized only if we actually processed valid data
            initializedRef.current = true;
        }
    }, [data, setFinalJudgments]); // Removed finalJudgments from dependency to avoid loops, we use functional update

    // Define visible columns based on viewMode
    const visibleColumns = {
        basic: {
            invoice: ['date', 'amount', 'quantity', 'incoterms'],
            bl: ['on_board_date', 'quantity', 'incoterms']
        },
        detailed: {
            invoice: ['date', 'amount', 'quantity', 'incoterms', 'item_description', 'seller', 'buyer', 'vessel_name', 'port_of_loading', 'port_of_discharge', 'bl_number_on_invoice'],
            bl: ['on_board_date', 'quantity', 'incoterms', 'item_description', 'bl_number', 'vessel_name', 'port_of_loading', 'port_of_discharge', 'shipper', 'consignee']
        }
    };

    // Filtering logic
    let filteredData = data;
    if (statusFilter !== 'all') {
        filteredData = filteredData.filter(item => {
            let status = item.auto_comparison?.status || item.final_status;
            // Infer no_evidence for filtering (Match backend logic: Missing BL AND Missing Invoice)
            if (!item.final_status) {
                const hasInvoice = item.ocr_data && Object.values(item.ocr_data).some(val => val && (typeof val === 'object' ? val.value : val));
                const hasBL = item.bl_data && Object.keys(item.bl_data).length > 0;

                if (!hasBL && !hasInvoice) {
                    status = 'no_evidence';
                }
            }
            return status === statusFilter;
        });
    }
    if (docFilter) {
        filteredData = filteredData.filter(item =>
            item.billing_document?.includes(docFilter)
        );
    }

    // Calculate statistics
    const stats = {
        total: data.length,
        complete_match: data.filter(d => (d.auto_comparison?.status || d.final_status) === 'complete_match').length,
        partial_error: data.filter(d => (d.auto_comparison?.status || d.final_status) === 'partial_error').length,
        review_required: data.filter(d => (d.auto_comparison?.status || d.final_status) === 'review_required').length,
        corrected: Object.keys(userCorrections).length,
        selected: selectedRows ? selectedRows.size : 0
    };

    // Calculate total tokens
    const totalTokens = data.reduce((sum, item) => {
        const usage = item.api_usage || {};
        return {
            input: sum.input + (usage.input || 0),
            output: sum.output + (usage.output || 0)
        };
    }, { input: 0, output: 0 });

    // Cell editing handlers
    const handleCellDoubleClick = (rowIdx, field, currentValue, billingDoc) => {
        setEditingCell({ rowIdx, field, billingDoc, originalValue: currentValue });
        setEditValue(currentValue || '');
    };

    const handleCellEditComplete = (billingDoc, field, onUpdateField) => {
        const originalValue = editingCell?.originalValue || '';
        if (editValue !== '' && editValue !== originalValue) {
            setUserCorrections(prev => ({
                ...prev,
                [billingDoc]: {
                    ...(prev[billingDoc] || {}),
                    [field]: editValue
                }
            }));
            if (onUpdateField) {
                onUpdateField(billingDoc, field, editValue);
            }
        }
        setEditingCell(null);
        setEditValue('');
    };

    const handleFinalJudgmentChange = (billingDoc, value) => {
        console.log('[useComparisonTable] Final judgment changed:', billingDoc, value);
        setFinalJudgments(prev => ({
            ...prev,
            [billingDoc]: value
        }));
    };

    // ★ Bulk Update Logic
    const handleBulkJudgmentUpdate = (status) => {
        if (!selectedRows || selectedRows.size === 0) {
            alert('일괄 적용할 항목을 선택해주세요.');
            return;
        }

        setFinalJudgments(prev => {
            const newJudgments = { ...prev };
            selectedRows.forEach(docId => {
                newJudgments[docId] = status;
            });
            return newJudgments;
        });

        // alert(`✅ 선택된 ${selectedRows.size}건을 '${status}'(으)로 일괄 변경했습니다.`);
    };

    const getCorrectedValue = (billingDoc, field, ocrValue) => {
        return userCorrections[billingDoc]?.[field] || ocrValue;
    };

    // Utility functions
    const getStatusIcon = (status) => {
        switch (status) {
            case 'complete_match': return '✅';
            case 'partial_error': return '⚠️';
            case 'review_required': return '❌';
            case 'no_evidence': return '🚫'; // Add icon for no evidence
            default: return '⏳';
        }
    };

    const getConfidenceBadge = (confidence) => {
        if (!confidence && confidence !== 0) return null;
        const pct = (confidence * 100).toFixed(0);
        let colorClass = 'conf-low';
        if (confidence >= 0.9) colorClass = 'conf-high';
        else if (confidence >= 0.7) colorClass = 'conf-mid';
        return <span className={`confidence-badge ${colorClass}`} title={`신뢰도: ${pct}%`}>{pct}%</span>;
    };

    const formatAmount = (val) => {
        if (val === null || val === undefined || val === '') return '';
        const num = parseFloat(val);
        if (isNaN(num)) return val;
        return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };

    const renderValue = (val, isAmount = false) => {
        if (val === null || val === undefined) return '';
        if (typeof val === 'object') {
            if (val.value !== undefined) {
                const displayVal = isAmount ? formatAmount(val.value) : val.value;
                return `${displayVal} ${val.unit || val.currency || ''}`;
            }
            return JSON.stringify(val);
        }
        return isAmount ? formatAmount(val) : val;
    };

    return {
        statusFilter,
        setStatusFilter,
        docFilter,
        setDocFilter,
        editingCell,
        setEditingCell,
        editValue,
        setEditValue,
        userCorrections,
        finalJudgments,
        filteredData,
        stats,
        totalTokens,
        handleCellDoubleClick,
        handleCellEditComplete,
        handleFinalJudgmentChange,
        handleBulkJudgmentUpdate, // Export bulk handler
        getCorrectedValue,
        getStatusIcon,
        getConfidenceBadge,
        renderValue,
        visibleColumns: visibleColumns[viewMode] || visibleColumns.basic
    };
};
