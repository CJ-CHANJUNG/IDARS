import { useEffect } from 'react';
import { useProject } from '../context/ProjectContext';

/**
 * Custom hook for managing Step 3 data loading
 * Handles initialization and loading of extraction data
 */
export const useStep3Data = () => {
    const {
        project,
        confirmedData,
        comparisonResults, setComparisonResults,
        setExtractionData
    } = useProject();

    // Load extraction data from backend
    const loadStep3ExtractionData = async () => {
        if (!project) return;

        try {
            const response = await fetch(`/api/projects/${project.id}/step3/extraction-data`);
            if (response.ok) {
                const result = await response.json();
                setExtractionData(result.data);

                if (result.data && result.data.length > 0) {
                    setComparisonResults(prevResults => {
                        let baseData = prevResults;

                        // Initialize base data if empty
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
                                ocr_data: {
                                    date: '', amount: '', quantity: '', incoterms: '',
                                    date_confidence: 0, amount_confidence: 0,
                                    quantity_confidence: 0, incoterms_confidence: 0
                                },
                                bl_data: null,
                                auto_comparison: { status: 'ready', match_score: 0, details: [] },
                                api_usage: { input: 0, output: 0 }
                            }));
                        }

                        // Merge loaded data with base data
                        const newResults = [...baseData];
                        result.data.forEach(loadedItem => {
                            const index = newResults.findIndex(
                                item => String(item.billing_document) === String(loadedItem.billing_document)
                            );
                            if (index !== -1) {
                                newResults[index] = {
                                    ...newResults[index],
                                    ocr_data: loadedItem.ocr_data,
                                    bl_data: loadedItem.bl_data,
                                    auto_comparison: loadedItem.auto_comparison,
                                    api_usage: loadedItem.api_usage,
                                    final_status: loadedItem.final_status, // ★ Include final_status
                                    user_corrections: loadedItem.user_corrections // ★ Include user_corrections
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

    // Initialize comparison table with confirmed data
    useEffect(() => {
        if (project && confirmedData && confirmedData.length > 0) {
            // Pre-load comparison table with confirmed data
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
                        date_confidence: 0, amount_confidence: 0,
                        quantity_confidence: 0, incoterms_confidence: 0
                    },
                    bl_data: null,
                    auto_comparison: { status: 'ready', match_score: 0, details: [] },
                    api_usage: { input: 0, output: 0 }
                }));
                setComparisonResults(initialData);
            }

            // Load extraction data
            loadStep3ExtractionData();
        }
    }, [project, confirmedData]);

    return {
        loadStep3ExtractionData
    };
};
