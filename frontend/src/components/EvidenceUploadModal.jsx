import React, { useState, useCallback } from 'react';
import './EvidenceUploadModal.css';

const EvidenceUploadModal = ({ isOpen, onClose, onUpload, billingDocument }) => {
    const [isDragging, setIsDragging] = useState(false);
    const [selectedFile, setSelectedFile] = useState(null);
    const [isUploading, setIsUploading] = useState(false);

    const handleDragEnter = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    }, []);

    const handleDragOver = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
    }, []);

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);

        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
            validateAndSetFile(files[0]);
        }
    }, []);

    const handleFileSelect = (e) => {
        if (e.target.files && e.target.files.length > 0) {
            validateAndSetFile(e.target.files[0]);
        }
    };

    const validateAndSetFile = (file) => {
        if (file.type !== 'application/pdf') {
            alert('PDF 파일만 업로드 가능합니다.');
            return;
        }
        setSelectedFile(file);
    };

    const handleUpload = async () => {
        if (!selectedFile) return;

        setIsUploading(true);
        try {
            await onUpload(selectedFile, billingDocument);
            onClose();
            setSelectedFile(null);
        } catch (error) {
            console.error('Upload failed:', error);
            alert('업로드 실패: ' + error.message);
        } finally {
            setIsUploading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="upload-modal-overlay" onClick={onClose}>
            <div className="upload-modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="upload-modal-header">
                    <h3>증빙 수기 업로드</h3>
                    <button className="close-btn" onClick={onClose}>&times;</button>
                </div>

                <div className="upload-modal-body">
                    <div className="billing-info">
                        <span className="label">전표번호:</span>
                        <span className="value">{billingDocument}</span>
                    </div>

                    <div
                        className={`drop-zone ${isDragging ? 'dragging' : ''} ${selectedFile ? 'has-file' : ''}`}
                        onDragEnter={handleDragEnter}
                        onDragLeave={handleDragLeave}
                        onDragOver={handleDragOver}
                        onDrop={handleDrop}
                        onClick={() => document.getElementById('file-input').click()}
                    >
                        <input
                            type="file"
                            id="file-input"
                            accept=".pdf"
                            onChange={handleFileSelect}
                            style={{ display: 'none' }}
                        />

                        {selectedFile ? (
                            <div className="file-info">
                                <span className="file-icon">📄</span>
                                <span className="file-name">{selectedFile.name}</span>
                                <span className="file-size">({(selectedFile.size / 1024).toFixed(1)} KB)</span>
                            </div>
                        ) : (
                            <div className="upload-prompt">
                                <span className="upload-icon">☁️</span>
                                <p>PDF 파일을 이곳에 드래그하거나 클릭하여 선택하세요</p>
                            </div>
                        )}
                    </div>
                </div>

                <div className="upload-modal-footer">
                    <button className="cancel-btn" onClick={onClose} disabled={isUploading}>취소</button>
                    <button
                        className="upload-btn"
                        onClick={handleUpload}
                        disabled={!selectedFile || isUploading}
                    >
                        {isUploading ? '업로드 중...' : '업로드'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default EvidenceUploadModal;
