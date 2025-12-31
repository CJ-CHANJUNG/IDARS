import React, { useState, useEffect } from 'react';
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

    const renderHighlights = () => {
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
    };

    const handlePrint = () => {
        window.print();
    };

    if (!viewerState) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <h3>Loading PDF Viewer...</h3>
            </div>
        );
    }

    const currentFile = viewerState.files?.[currentFileIndex];

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
                    {/* Page Navigation */}
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
                    {/* Zoom Controls */}
                    <button onClick={() => setScale(s => Math.max(0.5, s - 0.1))} style={{ padding: '0.3rem 0.6rem', fontSize: '0.85rem' }}>-</button>
                    <span style={{ fontSize: '0.85rem', minWidth: '50px', textAlign: 'center' }}>{Math.round(scale * 100)}%</span>
                    <button onClick={() => setScale(s => Math.min(3.0, s + 0.1))} style={{ padding: '0.3rem 0.6rem', fontSize: '0.85rem' }}>+</button>
                    <span style={{ margin: '0 0.3rem', color: '#ccc' }}>|</span>
                    {/* Additional Controls */}
                    <button
                        onClick={() => setShowThumbnails(!showThumbnails)}
                        title="썸네일 토글"
                        style={{ padding: '0.3rem 0.6rem', fontSize: '0.85rem', background: showThumbnails ? '#e3f2fd' : 'white' }}
                    >
                        📑
                    </button>
                    <button onClick={handlePrint} title="인쇄" style={{ padding: '0.3rem 0.6rem', fontSize: '0.85rem' }}>🖨️</button>
                </div>
            </div>

            {/* File List (if multiple files) */}
            {viewerState.files && viewerState.files.length > 1 && (
                <div style={{ padding: '0.4rem 1rem', background: '#e9ecef', borderBottom: '1px solid #dee2e6', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    {viewerState.files.map((file, idx) => (
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
                                <span>{file.filename}</span>
                                {file.type && (
                                    <span style={{
                                        fontSize: '0.7rem',
                                        padding: '0.1rem 0.4rem',
                                        borderRadius: '4px',
                                        background: file.type === 'original' ? '#e0f2fe' : '#f0fdf4',
                                        color: file.type === 'original' ? '#0369a1' : '#15803d',
                                        border: `1px solid ${file.type === 'original' ? '#bae6fd' : '#bbf7d0'}`
                                    }}>
                                        {file.type === 'original' ? 'Original' : 'Split'}
                                    </span>
                                )}
                            </div>
                        </button>
                    ))}
                </div>
            )}

            {/* Main Content Area */}
            <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                {/* Thumbnail Sidebar */}
                {showThumbnails && numPages && currentFile && (
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

                {/* PDF Viewer */}
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
                        <div style={{ position: 'relative' }}>
                            <Document
                                file={currentFile.url}
                                onLoadSuccess={onDocumentLoadSuccess}
                                loading={<div style={{ color: 'white' }}>Loading PDF...</div>}
                                error={<div style={{ color: 'white' }}>Failed to load PDF</div>}
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
                            {renderHighlights()}
                        </div>
                    ) : (
                        <div style={{ color: 'white' }}>No file selected</div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default PDFViewerStandalone;
