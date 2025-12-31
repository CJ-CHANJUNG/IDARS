import React from 'react';

const ComparisonTableHeader = ({
    statusFilter,
    setStatusFilter,
    docFilter,
    setDocFilter,
    selectedRows,
    filteredData,
    onSelectAll,
    viewMode = 'basic'
}) => {
    const invoiceColspan = viewMode === 'basic' ? 4 : 10;
    const blColspan = viewMode === 'basic' ? 3 : 12;

    const filterSelectStyle = {
        marginTop: '0.25rem',
        padding: '0.2rem 0.3rem',
        fontSize: '0.7rem',
        border: '1px solid #3a3a4a',
        borderRadius: '4px',
        width: '100%',
        maxWidth: '100px',
        background: '#2d2d3d',
        color: '#e0e0e0'
    };

    const filterInputStyle = {
        marginTop: '0.25rem',
        padding: '0.2rem 0.3rem',
        fontSize: '0.7rem',
        border: '1px solid #3a3a4a',
        borderRadius: '4px',
        width: '100%',
        maxWidth: '100px',
        background: '#2d2d3d',
        color: '#e0e0e0'
    };

    const headerStyle = {
        padding: '0.6rem 0.4rem',
        textAlign: 'center',
        border: '1px solid #3a3a4a',
        fontWeight: '700',
        fontSize: '0.8rem',
        color: '#ffffff',
        background: '#2d2d3d'
    };

    const subHeaderStyle = {
        padding: '0.5rem 0.3rem',
        textAlign: 'center',
        border: '1px solid #3a3a4a',
        fontWeight: '600',
        fontSize: '0.75rem',
        color: '#a0a0b0',
        background: '#1f1f2f'
    };

    return (
        <>
            <colgroup>
                <col style={{ width: '40px' }} />
                <col style={{ width: '60px' }} />
                <col style={{ width: '80px' }} />
                <col style={{ width: '100px' }} />
                <col style={{ width: '100px' }} />
                <col style={{ width: '100px' }} />
                <col style={{ width: '50px' }} />
                <col style={{ width: '80px' }} />
                <col style={{ width: '50px' }} />
                <col style={{ width: '100px' }} />
                <col style={{ width: '100px' }} />
                <col style={{ width: '80px' }} />
                <col style={{ width: '60px' }} />
                <col className="detailed-only" style={{ width: '120px' }} />
                <col className="detailed-only" style={{ width: '100px' }} />
                <col className="detailed-only" style={{ width: '100px' }} />
                <col className="detailed-only" style={{ width: '100px' }} />
                <col className="detailed-only" style={{ width: '100px' }} />
                <col className="detailed-only" style={{ width: '100px' }} />
                <col style={{ width: '80px' }} />
                <col style={{ width: '100px' }} />
                <col style={{ width: '60px' }} />
                <col className="detailed-only" style={{ width: '120px' }} />
                <col className="detailed-only" style={{ width: '100px' }} />
                <col className="detailed-only" style={{ width: '100px' }} />
                <col className="detailed-only" style={{ width: '100px' }} />
                <col className="detailed-only" style={{ width: '100px' }} />
                <col className="detailed-only" style={{ width: '100px' }} />
                <col className="detailed-only" style={{ width: '100px' }} />
                <col className="detailed-only" style={{ width: '80px' }} />
                <col className="detailed-only" style={{ width: '80px' }} />
                <col style={{ width: '100px' }} />
            </colgroup>
            <thead style={{
                position: 'sticky',
                top: 0,
                background: '#2d2d3d',
                zIndex: 10
            }}>
                <tr>
                    <th rowSpan="2" style={headerStyle}>
                        <input
                            type="checkbox"
                            checked={filteredData.length > 0 && selectedRows.size === filteredData.length}
                            onChange={onSelectAll}
                            style={{ cursor: 'pointer', transform: 'scale(1.1)' }}
                        />
                    </th>
                    <th rowSpan="2" style={headerStyle}>
                        <div>1차 판단</div>
                        <select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            style={filterSelectStyle}
                            onClick={(e) => e.stopPropagation()}
                        >
                            <option value="all">전체</option>
                            <option value="complete_match">✅ 일치</option>
                            <option value="partial_error">⚠️ 부분오류</option>
                            <option value="review_required">❌ 검토필요</option>
                            <option value="no_evidence">🚫 증빙없음</option>
                        </select>
                    </th>
                    <th rowSpan="2" style={headerStyle}>최종 판단</th>
                    <th rowSpan="2" style={headerStyle}>
                        <div>전표번호</div>
                        <input
                            type="text"
                            value={docFilter}
                            onChange={(e) => setDocFilter(e.target.value)}
                            placeholder="검색..."
                            style={filterInputStyle}
                            onClick={(e) => e.stopPropagation()}
                        />
                    </th>
                    <th colSpan="5" style={{ ...headerStyle, background: '#2d2d3d', color: '#ffffff' }}>전표 데이터</th>
                    <th colSpan={invoiceColspan} style={{ ...headerStyle, background: 'rgba(236, 72, 153, 0.15)', color: '#f472b6' }}>Invoice 추출</th>
                    <th colSpan={blColspan} style={{ ...headerStyle, background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa' }}>BL 추출</th>
                    <th rowSpan="2" style={headerStyle}>토큰</th>
                </tr>
                <tr>
                    {/* 전표 데이터 헤더 */}
                    <th style={subHeaderStyle}>선적일</th>
                    <th style={subHeaderStyle}>금액</th>
                    <th style={subHeaderStyle}>통화</th>
                    <th style={subHeaderStyle}>수량</th>
                    <th style={subHeaderStyle}>Inco</th>

                    {/* Invoice 헤더 */}
                    <th style={subHeaderStyle}>날짜</th>
                    <th style={subHeaderStyle}>금액</th>
                    <th style={subHeaderStyle}>수량</th>
                    <th style={subHeaderStyle}>Inco</th>
                    {viewMode === 'detailed' && (
                        <>
                            <th style={subHeaderStyle}>품목</th>
                            <th style={subHeaderStyle}>판매자</th>
                            <th style={subHeaderStyle}>구매자</th>
                            <th style={subHeaderStyle}>선박명</th>
                            <th style={subHeaderStyle}>선적항</th>
                            <th style={subHeaderStyle}>도착항</th>
                        </>
                    )}

                    {/* BL 헤더 */}
                    <th style={subHeaderStyle}>수량(Net)</th>
                    <th style={subHeaderStyle}>선적일</th>
                    <th style={subHeaderStyle}>운임비</th>
                    {viewMode === 'detailed' && (
                        <>
                            <th style={subHeaderStyle}>품목</th>
                            <th style={subHeaderStyle}>BL번호</th>
                            <th style={subHeaderStyle}>선박명</th>
                            <th style={subHeaderStyle}>선적항</th>
                            <th style={subHeaderStyle}>도착항</th>
                            <th style={subHeaderStyle}>선적인</th>
                            <th style={subHeaderStyle}>수하인</th>
                            <th style={subHeaderStyle}>Net Wgt</th>
                            <th style={subHeaderStyle}>Gross Wgt</th>
                        </>
                    )}
                </tr>
            </thead>
        </>
    );
};

export default ComparisonTableHeader;
