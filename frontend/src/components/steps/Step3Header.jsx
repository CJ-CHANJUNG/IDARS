import React from 'react';
import { useProject } from '../../context/ProjectContext';

const Step3Header = ({
    onExtractAndCompare,
    onSendToDashboard,
    onSaveDraft,
    hasComparisonResults
}) => {
    const {
        extractionMode, setExtractionMode,
        confirmedData,
        isLoading
    } = useProject();

    return (
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
                        <span style={{ fontSize: '0.8rem', fontWeight: '500', color: '#64748b' }}>
                            모드:
                        </span>
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
                        className="action-button secondary"
                        onClick={onSaveDraft}
                        style={{
                            backgroundColor: '#64748b',
                            color: '#ffffff',
                            padding: '0.4rem 0.8rem',
                            fontSize: '0.85rem'
                        }}
                    >
                        💾 임시 저장
                    </button>
                    <button
                        className="action-button primary"
                        onClick={onExtractAndCompare}
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
                        onClick={onSendToDashboard}
                        disabled={!hasComparisonResults}
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
    );
};

export default Step3Header;
