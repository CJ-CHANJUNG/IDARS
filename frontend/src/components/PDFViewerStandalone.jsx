import React, { useState, useEffect, useMemo } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import './PDFViewerModal.css';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const PDFViewerStandalone = () => {
    const [viewerState, setViewerState] = useState(null);
    const [currentFileIndex, setCurrentFileIndex] = useState(0);
    const [numPages, setNumPages] = useState(null);
    const [pageNumber, setPageNumber] = useState(1);
    const [scale, setScale] = useState(1.0);
    const [pageDimensions, setPageDimensions] = useState(null);
    const [showThumbnails, setShowThumbnails] = useState(true);
    const [showEvidencePanel, setShowEvidencePanel] = useState(true);

    // 파일 타입 감지
    const getFileType = (filename) => {
        if (!filename) return 'unknown';
        const ext = filename.split('.').pop().toLowerCase();
        if (ext === 'pdf') return 'pdf';
        if (['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'].includes(ext)) return 'image';
        return 'other';
    };

    useEffect(() => {
        // Retrieve viewer state from localStorage
        const stateJson = localStorage.getItem('pdfViewerPopoutState');
        if (stateJson) {
            try {
                const state = JSON.parse(stateJson);
                setViewerState(state);
            } catch (err) {
                console.error('Failed to parse viewer state:', err);
            }
        }
    }, []);

    const onDocumentLoadSuccess = ({ numPages }) => {
        setNumPages(numPages);
        setPageNumber(1);
    };

    const onPageLoadSuccess = (page) => {
        const { width, height } = page;
        setPageDimensions({ width, height });
    };

    const highlights = useMemo(() => {
        if (!viewerState?.highlightCoordinates || !pageDimensions) return null;

        // Normalize input to array of coordinate arrays
        let coordsArray = [];
        if (Array.isArray(viewerState.highlightCoordinates)) {
            if (viewerState.highlightCoordinates.length === 4 && typeof viewerState.highlightCoordinates[0] === 'number') {
                coordsArray = [viewerState.highlightCoordinates];
            } else if (viewerState.highlightCoordinates.length > 0 && Array.isArray(viewerState.highlightCoordinates[0])) {
                coordsArray = viewerState.highlightCoordinates;
            }
        }

        return coordsArray.map((coords, index) => {
            const [ymin, xmin, ymax, xmax] = coords;
            if (ymin === 0 && xmin === 0 && ymax === 0 && xmax === 0) return null;

            const width = pageDimensions.width * scale;
            const height = pageDimensions.height * scale;

            const top = (ymin / 1000) * height;
            const left = (xmin / 1000) * width;
            const boxHeight = ((ymax - ymin) / 1000) * height;
            const boxWidth = ((xmax - xmin) / 1000) * width;

            return (
                <div
                    key={index}
                    style={{
                        position: 'absolute',
                        top: `${top}px`,
                        left: `${left}px`,
                        width: `${boxWidth}px`,
                        height: `${boxHeight}px`,
                        backgroundColor: 'rgba(255, 255, 0, 0.3)',
                        border: '2px solid red',
                        zIndex: 10,
                        pointerEvents: 'none'
                    }}
                />
            );
        });
    }, [viewerState?.highlightCoordinates, pageDimensions, scale]);

    const renderEvidencePanel = () => {
        if (!showEvidencePanel || !viewerState?.extractionData) return null;

        const { extractionData } = viewerState;
        const evidence = extractionData.evidence || [];
        const notes = extractionData.notes || '';

        return (
            <div style={{
                width: '320px',
                background: '#ffffff',
                borderLeft: '1px solid #e0e0e0',
                padding: '1rem',
                overflowY: 'auto',
                fontSize: '0.85rem'
            }}>
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '1rem',
                    paddingBottom: '0.5rem',
                    borderBottom: '2px solid #3b82f6'
                }}>
                    <h3 style={{ margin: 0, fontSize: '1rem', color: '#1e293b' }}>📋 Evidence</h3>
                    <button
                        onClick={() => setShowEvidencePanel(false)}
                        style={{
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            fontSize: '1.2rem',
                            color: '#64748b'
                        }}
                    >×</button>
                </div>

                {evidence.length > 0 ? (
                    evidence.map((item, index) => {
                        const fieldLabel = item.field === 'total_amount' ? '금액' :
                            item.field === 'total_quantity' ? '수량' : item.field;
                        const values = item.values || [];
                        const hasValidCoords = item.coordinates && item.coordinates.some(c =>
                            Array.isArray(c) && c.some(v => v !== 0)
                        );

                        return (
                            <div key={index} style={{
                                marginBottom: '1rem',
                                padding: '0.75rem',
                                background: '#f8fafc',
                                borderRadius: '6px',
                                border: '1px solid #e2e8f0'
                            }}>
                                <div style={{
                                    fontWeight: '700',
                                    color: '#3b82f6',
                                    marginBottom: '0.5rem',
                                    fontSize: '0.9rem'
                                }}>
                                    {fieldLabel}
                                </div>

                                {values.length > 0 && (
                                    <div style={{ marginBottom: '0.5rem' }}>
                                        <div style={{
                                            fontSize: '0.75rem',
                                            color: '#64748b',
                                            marginBottom: '0.3rem'
                                        }}>
                                            {values.length > 1 ? `${values.length}개 라인 항목:` : '값:'}
                                        </div>
                                        {values.map((val, vIdx) => (
                                            <div key={vIdx} style={{
                                                padding: '0.3rem 0.5rem',
                                                background: hasValidCoords ? '#dbeafe' : '#fef3c7',
                                                borderLeft: `3px solid ${hasValidCoords ? '#3b82f6' : '#f59e0b'}`,
                                                marginBottom: '0.2rem',
                                                fontSize: '0.8rem',
                                                color: '#1e293b',
                                                fontFamily: 'monospace'
                                            }}>
                                                {vIdx + 1}. {typeof val === 'number' ? val.toLocaleString() : val}
                                                {!hasValidCoords && vIdx === 0 && (
                                                    <span style={{
                                                        marginLeft: '0.5rem',
                                                        fontSize: '0.7rem',
                                                        color: '#f59e0b'
                                                    }}>⚠️ 좌표 없음</span>
                                                )}
                                            </div>
                                        ))}

                                        {values.length > 1 && (
                                            <div style={{
                                                marginTop: '0.5rem',
                                                padding: '0.4rem 0.6rem',
                                                background: '#10b981',
                                                color: 'white',
                                                borderRadius: '4px',
                                                fontWeight: '700',
                                                fontSize: '0.85rem',
                                                textAlign: 'center'
                                            }}>
                                                = {values.reduce((sum, v) => sum + (parseFloat(v) || 0), 0).toLocaleString()}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {item.reason && (
                                    <div style={{
                                        fontSize: '0.75rem',
                                        color: '#475569',
                                        fontStyle: 'italic',
                                        marginTop: '0.5rem',
                                        paddingTop: '0.5rem',
                                        borderTop: '1px dashed #cbd5e1'
                                    }}>
                                        💡 {item.reason}
                                    </div>
                                )}
                            </div>
                        );
                    })
                ) : (
                    <div style={{
                        color: '#94a3b8',
                        textAlign: 'center',
                        padding: '1rem',
                        fontStyle: 'italic'
                    }}>
                        No evidence data available
                    </div>
                )}

                {notes && (
                    <div style={{
                        marginTop: '1rem',
                        padding: '0.75rem',
                        background: '#fef9c3',
                        borderRadius: '6px',
                        border: '1px solid #fde047'
                    }}>
                        <div style={{
                            fontWeight: '700',
                            color: '#854d0e',
                            marginBottom: '0.3rem',
                            fontSize: '0.8rem'
                        }}>
                            📝 Notes
                        </div>
                        <div style={{
                            fontSize: '0.75rem',
                            color: '#713f12',
                            lineHeight: '1.4'
                        }}>
                            {notes}
                        </div>
                    </div>
                )}
            </div>
        );
    };

    const handlePrint = () => {
        window.print();
    };

    if (!viewerState) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <h3>Loading Viewer...</h3>
            </div>
        );
    }

    const currentFile = viewerState.files?.[currentFileIndex];
    const fileType = currentFile ? getFileType(currentFile.filename) : 'unknown';

    return (
        <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column', background: '#525659' }}>
            {/* Header */}
            <div style={{
                padding: '0.5rem 1rem',
                background: '#f8f9fa',
                borderBottom: '1px solid #dee2e6',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
                    <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: '600' }}>{viewerState.title}</h3>
                    {currentFile && (
                        <span style={{ fontSize: '0.8rem', color: '#666' }}>{currentFile.filename}</span>
                    )}
                </div>
                <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'center' }}>
                    {/* Page Navigation - PDF만 */}
                    {fileType === 'pdf' && (
                        <>
                            <button
                                onClick={() => setPageNumber(p => Math.max(1, p - 1))}
                                disabled={pageNumber <= 1}
                                style={{ padding: '0.3rem 0.6rem', fontSize: '0.85rem', cursor: pageNumber <= 1 ? 'not-allowed' : 'pointer' }}
                            >
                                ◀
                            </button>
                            <span style={{ fontSize: '0.85rem', minWidth: '60px', textAlign: 'center' }}>
                                {pageNumber} / {numPages || '?'}
                            </span>
                            <button
                                onClick={() => setPageNumber(p => Math.min(numPages, p + 1))}
                                disabled={pageNumber >= numPages}
                                style={{ padding: '0.3rem 0.6rem', fontSize: '0.85rem', cursor: pageNumber >= numPages ? 'not-allowed' : 'pointer' }}
                            >
                                ▶
                            </button>
                            <span style={{ margin: '0 0.3rem', color: '#ccc' }}>|</span>
                        </>
                    )}
                    {/* Zoom Controls */}
                    <button onClick={() => setScale(s => Math.max(0.5, s - 0.1))} style={{ padding: '0.3rem 0.6rem', fontSize: '0.85rem' }}>-</button>
                    <span style={{ fontSize: '0.85rem', minWidth: '50px', textAlign: 'center' }}>{Math.round(scale * 100)}%</span>
                    <button onClick={() => setScale(s => Math.min(3.0, s + 0.1))} style={{ padding: '0.3rem 0.6rem', fontSize: '0.85rem' }}>+</button>
                    <span style={{ margin: '0 0.3rem', color: '#ccc' }}>|</span>
                    {/* Additional Controls */}
                    {fileType === 'pdf' && (
                        <button
                            onClick={() => setShowThumbnails(!showThumbnails)}
                            title="썸네일 토글"
                            style={{ padding: '0.3rem 0.6rem', fontSize: '0.85rem', background: showThumbnails ? '#e3f2fd' : 'white' }}
                        >
                            📑
                        </button>
                    )}
                    <button onClick={handlePrint} title="인쇄" style={{ padding: '0.3rem 0.6rem', fontSize: '0.85rem' }}>🖨️</button>
                </div>
            </div>

            {/* File List (if multiple files) */}
            {viewerState.files && viewerState.files.length > 1 && (
                <div style={{ padding: '0.4rem 1rem', background: '#e9ecef', borderBottom: '1px solid #dee2e6', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    {viewerState.files.map((file, idx) => {
                        const fType = getFileType(file.filename);
                        const icon = fType === 'pdf' ? '📄' : fType === 'image' ? '🖼️' : '📎';
                        return (
                            <button
                                key={idx}
                                onClick={() => {
                                    setCurrentFileIndex(idx);
                                    setPageNumber(1);
                                }}
                                style={{
                                    padding: '0.25rem 0.6rem',
                                    background: idx === currentFileIndex ? '#3b82f6' : 'white',
                                    color: idx === currentFileIndex ? 'white' : 'black',
                                    border: '1px solid #ccc',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    fontSize: '0.8rem',
                                    fontWeight: idx === currentFileIndex ? '600' : 'normal'
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <span>{icon} {file.filename}</span>
                                    {file.type && (
                                        <span style={{
                                            fontSize: '0.7rem',
                                            padding: '0.1rem 0.4rem',
                                            borderRadius: '4px',
                                            background: file.type === 'original' ? '#e0f2fe' : file.type === 'dterm' ? '#fef3c7' : '#f0fdf4',
                                            color: file.type === 'original' ? '#0369a1' : file.type === 'dterm' ? '#854d0e' : '#15803d',
                                            border: `1px solid ${file.type === 'original' ? '#bae6fd' : file.type === 'dterm' ? '#fde047' : '#bbf7d0'}`
                                        }}>
                                            {file.type}
                                        </span>
                                    )}
                                </div>
                            </button>
                        );
                    })}
                </div>
            )}

            {/* Main Content Area */}
            <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                {/* Thumbnail Sidebar - PDF만 */}
                {showThumbnails && fileType === 'pdf' && numPages && currentFile && (
                    <div style={{
                        width: '180px',
                        background: '#f8f9fa',
                        borderRight: '1px solid #dee2e6',
                        overflowY: 'auto',
                        padding: '0.5rem'
                    }}>
                        <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#666', marginBottom: '0.5rem', padding: '0 0.25rem' }}>
                            Pages ({numPages})
                        </div>
                        <Document file={currentFile.url}>
                            {Array.from({ length: numPages }, (_, i) => i + 1).map(page => (
                                <div
                                    key={page}
                                    onClick={() => setPageNumber(page)}
                                    style={{
                                        marginBottom: '0.75rem',
                                        padding: '0.25rem',
                                        background: page === pageNumber ? '#e3f2fd' : 'white',
                                        border: page === pageNumber ? '2px solid #2196f3' : '1px solid #e0e0e0',
                                        borderRadius: '4px',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s',
                                        boxShadow: page === pageNumber ? '0 2px 8px rgba(33, 150, 243, 0.3)' : 'none'
                                    }}
                                    onMouseEnter={(e) => {
                                        if (page !== pageNumber) {
                                            e.currentTarget.style.background = '#f5f5f5';
                                            e.currentTarget.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.1)';
                                        }
                                    }}
                                    onMouseLeave={(e) => {
                                        if (page !== pageNumber) {
                                            e.currentTarget.style.background = 'white';
                                            e.currentTarget.style.boxShadow = 'none';
                                        }
                                    }}
                                >
                                    <Page
                                        pageNumber={page}
                                        width={140}
                                        renderTextLayer={false}
                                        renderAnnotationLayer={false}
                                    />
                                    <div style={{
                                        textAlign: 'center',
                                        fontSize: '0.7rem',
                                        marginTop: '0.25rem',
                                        color: page === pageNumber ? '#1976d2' : '#666',
                                        fontWeight: page === pageNumber ? '600' : 'normal'
                                    }}>
                                        {page}
                                    </div>
                                </div>
                            ))}
                        </Document>
                    </div>
                )}

                {/* Viewer */}
                <div style={{
                    flex: 1,
                    overflow: 'auto',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'flex-start',
                    padding: '1rem',
                    position: 'relative'
                }}>
                    {currentFile ? (
                        <>
                            {/* PDF 뷰어 */}
                            {fileType === 'pdf' && (
                                <div style={{ position: 'relative' }}>
                                    <Document
                                        file={currentFile.url}
                                        onLoadSuccess={onDocumentLoadSuccess}
                                        loading={<div style={{ color: 'white' }}>Loading PDF...</div>}
                                        error={<div style={{ color: 'white', padding: '20px' }}>
                                            Failed to load PDF<br /><small>{currentFile.url}</small>
                                        </div>}
                                    >
                                        <Page
                                            pageNumber={pageNumber}
                                            scale={scale}
                                            onLoadSuccess={onPageLoadSuccess}
                                            loading={<div style={{ color: 'white' }}>Loading page...</div>}
                                            renderTextLayer={true}
                                            renderAnnotationLayer={true}
                                        />
                                    </Document>
                                    {highlights}
                                </div>
                            )}

                            {/* 이미지 뷰어 */}
                            {fileType === 'image' && (
                                <div style={{
                                    position: 'relative',
                                    maxWidth: '100%',
                                    maxHeight: '100%',
                                    overflow: 'auto',
                                    display: 'flex',
                                    justifyContent: 'center',
                                    alignItems: 'center'
                                }}>
                                    <img
                                        src={currentFile.url}
                                        alt={currentFile.filename}
                                        style={{
                                            transform: `scale(${scale})`,
                                            transformOrigin: 'center center',
                                            transition: 'transform 0.1s ease-out',
                                            maxWidth: 'none',
                                            maxHeight: 'none',
                                            display: 'block'
                                        }}
                                        onError={(e) => {
                                            const errorDiv = document.createElement('div');
                                            errorDiv.style.cssText = 'color: white; padding: 20px; text-align: center;';
                                            errorDiv.innerHTML = `<p>이미지 로드 실패</p><small>${currentFile.url}</small>`;
                                            e.target.parentElement.replaceChild(errorDiv, e.target);
                                        }}
                                    />
                                </div>
                            )}

                            {/* 기타 파일 */}
                            {fileType === 'other' && (
                                <div style={{ color: 'white', padding: '40px', textAlign: 'center' }}>
                                    <p style={{ marginBottom: '20px' }}>미리보기를 지원하지 않는 파일 형식입니다.</p>
                                    <p style={{ fontSize: '14px', color: '#ccc', marginBottom: '20px' }}>{currentFile.filename}</p>
                                    <a
                                        href={currentFile.url}
                                        download={currentFile.filename}
                                        style={{
                                            display: 'inline-block',
                                            padding: '10px 20px',
                                            backgroundColor: '#007bff',
                                            color: 'white',
                                            textDecoration: 'none',
                                            borderRadius: '4px'
                                        }}
                                    >
                                        📥 다운로드
                                    </a>
                                </div>
                            )}
                        </>
                    ) : (
                        <div style={{ color: 'white' }}>No file selected</div>
                    )}
                </div>

                {/* Evidence Panel (if exists) */}
                {renderEvidencePanel()}
            </div>
        </div>
    );
};

export default PDFViewerStandalone;
