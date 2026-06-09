"""Error pattern recognition and clustering module."""
import re
from typing import List, Dict, Tuple
from collections import Counter
import hashlib


class PatternRecognizer:
    """Identifies and groups error patterns."""
    
    def __init__(self):
        self.pattern_cache = {}
    
    def extract_error_patterns(self, analyses: List[Dict]) -> List[Dict]:
        """
        Extract and group error patterns from analyses.
        
        Returns groups of similar errors with frequency
        """
        if not analyses:
            return []
        
        try:
            patterns = []
            error_groups = {}
            
            for analysis in analyses:
                error = analysis.get('identified_error', '').strip().lower()
                if not error:
                    continue
                
                # Create pattern key by extracting main error type
                pattern_key = self._extract_pattern_key(error)
                
                if pattern_key not in error_groups:
                    error_groups[pattern_key] = {
                        "pattern": pattern_key,
                        "error_type": analysis.get('identified_error', ''),
                        "count": 0,
                        "occurrences": [],
                        "probable_causes": [],
                        "suggested_fixes": []
                    }
                
                error_groups[pattern_key]["count"] += 1
                error_groups[pattern_key]["occurrences"].append(analysis.get('identified_error', ''))
                
                # Collect unique causes and fixes
                cause = analysis.get('probable_cause', '')
                if cause and cause not in error_groups[pattern_key]["probable_causes"]:
                    error_groups[pattern_key]["probable_causes"].append(cause)
                
                fix = analysis.get('suggested_fix', '')
                if fix and fix not in error_groups[pattern_key]["suggested_fixes"]:
                    error_groups[pattern_key]["suggested_fixes"].append(fix)
            
            # Sort by frequency
            patterns = sorted(error_groups.values(), key=lambda x: x['count'], reverse=True)
            return patterns
        except Exception as e:
            return []
    
    def _extract_pattern_key(self, error_text: str) -> str:
        """Extract main pattern from error text."""
        # Remove numbers and special characters for pattern matching
        cleaned = re.sub(r'[0-9]+', '#', error_text)
        cleaned = re.sub(r'[\'\"]+', '', cleaned)
        
        # Get first meaningful part
        parts = cleaned.split(':')
        return parts[0][:50] if parts else error_text[:50]
    
    def get_error_frequency(self, analyses: List[Dict]) -> Dict[str, int]:
        """Get frequency of different error types."""
        errors = Counter()
        for analysis in analyses:
            error_type = analysis.get('identified_error', 'Unknown').split(':')[0]
            errors[error_type] += 1
        return dict(errors.most_common(10))
    
    def identify_related_errors(self, analyses: List[Dict], error_index: int) -> List[Dict]:
        """Find errors related to a specific error."""
        if error_index >= len(analyses):
            return []
        
        target_error = analyses[error_index]
        target_cause = target_error.get('probable_cause', '').lower()
        
        related = []
        for i, analysis in enumerate(analyses):
            if i == error_index:
                continue
            
            cause = analysis.get('probable_cause', '').lower()
            
            # Check similarity
            if self._calculate_similarity(target_cause, cause) > 0.5:
                related.append({
                    "index": i,
                    "error": analysis.get('identified_error', ''),
                    "similarity": self._calculate_similarity(target_cause, cause)
                })
        
        return sorted(related, key=lambda x: x['similarity'], reverse=True)
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity calculation."""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if len(words1) == 0 or len(words2) == 0:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def categorize_errors(self, analyses: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize errors by type."""
        categories = {
            "Database": [],
            "Network": [],
            "Authentication": [],
            "Resource": [],
            "Configuration": [],
            "Runtime": [],
            "Unknown": []
        }
        
        keywords = {
            "Database": ["database", "connection", "sql", "query", "transaction", "table", "index"],
            "Network": ["network", "socket", "connection", "timeout", "dns", "http", "port"],
            "Authentication": ["auth", "permission", "unauthorized", "forbidden", "token", "password"],
            "Resource": ["memory", "cpu", "disk", "heap", "out of", "limit"],
            "Configuration": ["config", "settings", "property", "parameter", "env", "variable"],
            "Runtime": ["null", "exception", "error", "crash", "panic", "stack"]
        }
        
        for analysis in analyses:
            error = analysis.get('identified_error', '').lower()
            cause = analysis.get('probable_cause', '').lower()
            combined = f"{error} {cause}".lower()
            
            categorized = False
            for category, keywords_list in keywords.items():
                if any(kw in combined for kw in keywords_list):
                    categories[category].append(analysis)
                    categorized = True
                    break
            
            if not categorized:
                categories["Unknown"].append(analysis)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def get_error_chain(self, analyses: List[Dict]) -> List[List[Dict]]:
        """Identify chains of related errors."""
        chains = []
        used = set()
        
        for i, analysis in enumerate(analyses):
            if i in used:
                continue
            
            chain = [analysis]
            used.add(i)
            
            # Find related errors
            related = self.identify_related_errors(analyses, i)
            for rel in related:
                if rel['index'] not in used:
                    chain.append(analyses[rel['index']])
                    used.add(rel['index'])
            
            if len(chain) > 1:
                chains.append(chain)
        
        return chains
