# -*- coding: utf-8 -*-
"""
Combination Finder for N:1 Matching
Finds subsets of numbers in text that sum up to a target value.
Used to provide hints for N:1 matching in invoices.
"""

import re
import itertools
from typing import List, Dict, Optional, Tuple

class CombinationFinder:
    def __init__(self):
        # Regex to find potential monetary/quantity values
        # Matches: 1,234.56 or 1234.56 or 1,234
        self.NUMBER_PATTERN = re.compile(r'[\d,]+\.?\d*')
        
    def _extract_numbers(self, text: str) -> List[float]:
        """Extract all valid numbers from text."""
        numbers = []
        seen = set()
        
        # Find all number-like strings
        matches = self.NUMBER_PATTERN.findall(text)
        
        for match in matches:
            # Clean string (remove commas)
            clean_str = match.replace(',', '')
            try:
                # Skip empty or just '.'
                if not clean_str or clean_str == '.':
                    continue
                    
                val = float(clean_str)
                
                # Filter out unlikely values (e.g. dates like 2024, small integers like 1, 2)
                # But be careful not to filter out real small quantities
                if val <= 0:
                    continue
                    
                # Avoid duplicates to reduce combination complexity?
                # No, duplicates might be valid line items (e.g. 2 items of price 100)
                # But for performance, maybe limit total count
                numbers.append(val)
                
            except ValueError:
                continue
                
        return numbers

    def find_combination(self, text: str, target_value: float, tolerance: float = 0.05, max_items: int = 5) -> Optional[List[float]]:
        """
        Find a combination of numbers in text that sum to target_value.
        Returns the list of numbers if found, else None.
        """
        if not text or target_value <= 0:
            return None
            
        numbers = self._extract_numbers(text)
        
        # Optimization: Filter numbers larger than target (assuming positive values)
        candidates = [n for n in numbers if n <= target_value + tolerance]
        
        # Sort descending to try larger numbers first (greedy-ish approach usually faster)
        candidates.sort(reverse=True)
        
        # Limit candidates count to prevent explosion (e.g. top 50 relevant numbers)
        candidates = candidates[:50]
        
        # Try combinations from 1 to max_items (Start from 1 to find exact matches)
        for r in range(1, max_items + 1):
            for combo in itertools.combinations(candidates, r):
                combo_sum = sum(combo)
                if abs(combo_sum - target_value) <= tolerance:
                    return list(combo)
                    
        return None
