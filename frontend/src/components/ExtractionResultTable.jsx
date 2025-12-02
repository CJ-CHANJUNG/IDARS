import React, { useState } from 'react';
import {
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
    Paper, Typography, Box, Chip, IconButton, Collapse, Button
} from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';

const Row = ({ row, onPdfClick }) => {
    const [open, setOpen] = useState(false);

    // 동적 필드 추출
    const fields = row.fields || {};

    return (
        <React.Fragment>
            <TableRow sx={{ '& > *': { borderBottom: 'unset' } }}>
                <TableCell>
                    <IconButton
                        aria-label="expand row"
                        size="small"
                        onClick={() => setOpen(!open)}
                    >
                        {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
                    </IconButton>
                </TableCell>
                <TableCell component="th" scope="row">
                    <Chip
                        label={row.type}
                        color={row.type === 'BL' ? 'primary' : 'secondary'}
                        size="small"
                    />
                </TableCell>
                <TableCell>{row.file_name}</TableCell>
                <TableCell>
                    <Chip
                        label={`${(row.confidence * 100).toFixed(0)}%`}
                        color={row.confidence > 0.8 ? 'success' : 'warning'}
                        variant="outlined"
                        size="small"
                    />
                </TableCell>
                <TableCell>
                    <Button
                        startIcon={<PictureAsPdfIcon />}
                        size="small"
                        onClick={() => onPdfClick(row)}
                    >
                        View
                    </Button>
                </TableCell>
            </TableRow>
            <TableRow>
                <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={6}>
                    <Collapse in={open} timeout="auto" unmountOnExit>
                        <Box sx={{ margin: 1 }}>
                            <Typography variant="h6" gutterBottom component="div" size="small">
                                Extracted Fields
                            </Typography>
                            <Table size="small" aria-label="purchases">
                                <TableHead>
                                    <TableRow>
                                        <TableCell>Field Name</TableCell>
                                        <TableCell>Value</TableCell>
                                        <TableCell>Confidence</TableCell>
                                    </TableRow>
                                </TableHead>
                                <TableBody>
                                    {Object.entries(fields).map(([key, value]) => (
                                        <TableRow key={key}>
                                            <TableCell component="th" scope="row">
                                                {key}
                                            </TableCell>
                                            <TableCell>{value}</TableCell>
                                            <TableCell>
                                                {row.field_confidence && row.field_confidence[key]
                                                    ? `${(row.field_confidence[key] * 100).toFixed(0)}%`
                                                    : '-'}
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>

                            {row.token_usage && (
                                <Box sx={{ mt: 2, p: 1, bgcolor: '#f5f5f5', borderRadius: 1 }}>
                                    <Typography variant="caption" display="block">
                                        Token Usage: Input {row.token_usage.input_tokens} / Output {row.token_usage.output_tokens}
                                    </Typography>
                                    <Typography variant="caption" display="block" color="text.secondary">
                                        Est. Cost: ₩{row.token_usage.estimated_cost_krw}
                                    </Typography>
                                </Box>
                            )}
                        </Box>
                    </Collapse>
                </TableCell>
            </TableRow>
        </React.Fragment>
    );
};

export default function ExtractionResultTable({ data, onPdfClick }) {
    if (!data || data.length === 0) {
        return <Typography sx={{ p: 2 }}>No extraction data available.</Typography>;
    }

    // Flatten documents from slips with safety checks
    const allDocuments = data.flatMap(slip => {
        // Safety check: ensure slip has documents array
        if (!slip || !slip.documents || !Array.isArray(slip.documents)) {
            console.warn('Invalid slip data:', slip);
            return [];
        }
        return slip.documents.map(doc => ({ ...doc, slip_id: slip.slip_id }));
    });

    return (
        <TableContainer component={Paper} sx={{ mt: 2, maxHeight: 600 }}>
            <Table aria-label="collapsible table" stickyHeader>
                <TableHead>
                    <TableRow>
                        <TableCell />
                        <TableCell>Type</TableCell>
                        <TableCell>File Name</TableCell>
                        <TableCell>Confidence</TableCell>
                        <TableCell>Action</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {allDocuments.map((doc, index) => (
                        <Row key={index} row={doc} onPdfClick={onPdfClick} />
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
    );
}
