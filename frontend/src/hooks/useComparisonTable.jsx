import { useState, useEffect, useRef } from 'react';

/**
 * Custom hook for managing comparison table state and logic
 */
export const useComparisonTable = (data, selectedRows, viewMode = 'basic') => {
    const [statusFilter, setStatusFilter] = useState('all');
    const [docFilter, setDocFilter] = useState('');
    const [editingCell, setEditingCell] = useState(null);
    const [editValue, setEditValue] = useState('');
    const [userCorrections, setUserCorrections] = useState({});
    const [finalJudgments, setFinalJudgments] = useState({});
    const initializedRef = useRef(false); // ★ Track initialization

    // ★ Auto-populate finalJudgments from 1차 판단 (only once when data first loads)
    useEffect(() => {
        if (data && data.length > 0 && !initializedRef.current) {
            console.log('[useComparisonTable] Initializing finalJudgments from auto_comparison');
            const initialJudgments = {};

            data.forEach(item => {
                const billingDoc = item.billing_document;
                const autoStatus = item.auto_comparison?.status || item.final_status;

                // Map auto status to final judgment value
                let judgment = '';
                if (autoStatus === 'complete_match') {
                    judgment = 'match';
                } else if (autoStatus === 'partial_error') {
                    judgment = 'mismatch';
                } else if (autoStatus === 'review_required') {
                    judgment = 'mismatch';
                }

                if (judgment) {
                    initialJudgments[billingDoc] = judgment;
                }
            });

            console.log('[useComparisonTable] Initial judgments:', Object.keys(initialJudgments).length, 'items');
            setFinalJudgments(initialJudgments);
            initializedRef.current = true;
        }
    }, [data]);

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
            const status = item.auto_comparison?.status || item.final_status;
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

    const getCorrectedValue = (billingDoc, field, ocrValue) => {
        return userCorrections[billingDoc]?.[field] || ocrValue;
    };

    // Utility functions
    const getStatusIcon = (status) => {
        switch (status) {
            case 'complete_match': return '✅';
            case 'partial_error': return '⚠️';
            case 'review_required': return '❌';
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
        getCorrectedValue,
        getStatusIcon,
        getConfidenceBadge,
        renderValue,
        visibleColumns: visibleColumns[viewMode] || visibleColumns.basic
    };
};
