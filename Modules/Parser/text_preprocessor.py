# -*- coding: utf-8 -*-
"""
Text Preprocessor for Smart Extraction Engine
Reduces token usage by filtering irrelevant text (T&C) while preserving key data.
"""

import re

class TextPreprocessor:
    def __init__(self):
        # Keywords that MUST be preserved
        self.KEYWORDS = [
            "DATE", "AMOUNT", "TOTAL", "QUANTITY", "WEIGHT", "NET", "GROSS",
            "SHIPPER", "CONSIGNEE", "NOTIFY", "VESSEL", "VOYAGE", "PORT",
            "INCOTERMS", "PRICE", "UNIT", "CURRENCY", "BL NO", "B/L NO",
            "INVOICE NO", "DESCRIPTION", "MARKS", "NOS", "CONTAINER", "SEAL"
        ]
        
        # Regex for detecting lines with numbers (potential values)
        self.NUMBER_PATTERN = re.compile(r'\d')
        
    def preprocess(self, text: str, doc_type: str) -> str:
        """
        Preprocess text based on document type.
        Returns optimized text or original text if optimization is unsafe.
        """
        if not text:
            return ""
            
        original_length = len(text)
        lines = text.split('\n')
        optimized_lines = []
        
        # 1. Basic Cleaning
        # Remove lines that are too long and have no numbers (likely legal text)
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Strategy: Keep line if:
            # 1. It contains a keyword (Case insensitive)
            # 2. It contains a number (Value)
            # 3. It is short (Header/Footer info often short)
            # 4. It is part of a table (often has multiple spaces or tabs - hard to detect in raw text, so rely on numbers)
            
            is_relevant = False
            line_upper = line.upper()
            
            # Check keywords
            if any(kw in line_upper for kw in self.KEYWORDS):
                is_relevant = True
            
            # Check numbers
            elif self.NUMBER_PATTERN.search(line):
                is_relevant = True
                
            # Check length (Short lines might be labels)
            elif len(line) < 50:
                is_relevant = True
                
            if is_relevant:
                optimized_lines.append(line)
        
        optimized_text = '\n'.join(optimized_lines)
        
        # 2. Safety Check
        # If we removed too much (>80%) or text is too short, revert to original
        # This prevents accidental loss of data in unexpected formats
        if len(optimized_text) < 100 or len(optimized_text) < (original_length * 0.2):
            # print(f"[TextPreprocessor] Optimization unsafe (too aggressive). Reverting to original. ({len(optimized_text)}/{original_length})")
            return text
            
        # print(f"[TextPreprocessor] Optimized: {original_length} -> {len(optimized_text)} chars")
        return optimized_text
