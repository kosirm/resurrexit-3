"""
Croatian Language Customizations

This module implements Croatian-specific parsing logic and text processing rules
for the universal songbook parser.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple

from core.models import Verse, VerseLine, ParsedDocument, TextType, ClassifiedText
from languages.base_language import LanguageCustomizations


class CroatianCustomizations(LanguageCustomizations):
    """
    Croatian-specific customizations for the universal parser.
    
    Handles Croatian language patterns, text processing rules,
    and special formatting requirements.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Croatian-specific patterns
        self.croatian_words = [
            'bog', 'gospod', 'krist', 'isus', 'marija', 'sveti', 'sveta',
            'amen', 'aleluja', 'halleluja', 'slava', 'hvala', 'djeca', 'grešnici'
        ]
        
        # Common Croatian abbreviations and expansions
        self.text_expansions = {
            'sv.': 'sveti',
            'bl.': 'blaženi',
            'kr.': 'kralj',
            'g.': 'gospod',
        }
        
        # Croatian-specific role processing
        self.role_synonyms = {
            'D.': ['Djeca', 'DJECA'],
            'K.': ['Kantor', 'KANTOR'],
            'Z.': ['Zbor', 'ZBOR'],
            'P.': ['Prezbiter', 'PREZBITER'],
        }
        
        # Special Croatian responses and expansions
        self.special_responses = {
            'SMILUJ SE...': 'SMILUJ SE NAMA, KOJI SMO GREŠNICI, GOSPODINE, SMILUJ SE!',
            'smiluj se...': 'smiluj se nama, koji smo grešnici, Gospodine, smiluj se!',
        }
        
        self.logger.debug("Initialized Croatian customizations")
    
    def apply_customizations(self, verses: List[Verse], document: ParsedDocument) -> List[Verse]:
        """
        Apply Croatian-specific customizations to parsed verses.
        
        Args:
            verses: List of verses from universal parser
            document: Complete parsed document for context
            
        Returns:
            List of customized verses
        """
        self.logger.info(f"Applying Croatian customizations to {len(verses)} verses")
        
        customized_verses = []
        
        for verse in verses:
            # Apply verse-level customizations
            customized_verse = self._customize_verse(verse, document)
            
            if customized_verse:
                customized_verses.append(customized_verse)
        
        # Apply document-level customizations
        customized_verses = self._apply_document_level_customizations(customized_verses, document)
        
        self.logger.info(f"Croatian customizations complete: {len(customized_verses)} verses")
        return customized_verses
    
    def _customize_verse(self, verse: Verse, document: ParsedDocument) -> Optional[Verse]:
        """Apply customizations to a single verse"""
        if not verse.lines:
            return verse
        
        customized_lines = []
        
        for line in verse.lines:
            customized_line = self._customize_line(line, verse.role)
            if customized_line:
                customized_lines.append(customized_line)
        
        # Create new verse with customized lines
        return Verse(
            role=self._normalize_croatian_role(verse.role),
            lines=customized_lines,
            verse_type=verse.verse_type
        )
    
    def _customize_line(self, line: VerseLine, role: str) -> Optional[VerseLine]:
        """Apply customizations to a single verse line"""
        text = line.text
        
        # Apply Croatian text processing
        text = self._apply_croatian_text_fixes(text)
        text = self._apply_text_expansions(text)
        text = self._apply_special_responses(text)
        text = self._normalize_croatian_punctuation(text)
        
        # Handle special Croatian formatting
        text = self._handle_croatian_special_cases(text, role)
        
        # Create new line with customized text
        return VerseLine(
            text=text,
            chords=line.chords,  # Keep original chords
            original_line=line.original_line,
            line_type=line.line_type
        )
    
    def _apply_croatian_text_fixes(self, text: str) -> str:
        """Apply Croatian-specific text fixes"""
        if not text:
            return text
        
        # Fix common OCR issues in Croatian
        fixes = {
            'è': 'č',  # Most common encoding issue
            'È': 'Č',
            'æ': 'č',  # Alternative encoding
            'Æ': 'Č',
            'ž': 'ž',  # Ensure proper ž
            'š': 'š',  # Ensure proper š
            'Ž': 'Ž',
            'Š': 'Š',
            'ć': 'ć',  # Croatian-specific
            'Ć': 'Ć',
            'đ': 'đ',  # Croatian-specific
            'Đ': 'Đ',
        }
        
        fixed_text = text
        for old, new in fixes.items():
            fixed_text = fixed_text.replace(old, new)
        
        return fixed_text
    
    def _apply_text_expansions(self, text: str) -> str:
        """Apply Croatian text expansions"""
        expanded_text = text
        
        for abbrev, expansion in self.text_expansions.items():
            # Case-insensitive replacement
            pattern = re.compile(re.escape(abbrev), re.IGNORECASE)
            expanded_text = pattern.sub(expansion, expanded_text)
        
        return expanded_text
    
    def _apply_special_responses(self, text: str) -> str:
        """Apply Croatian special response expansions"""
        expanded_text = text
        
        for trigger, expansion in self.special_responses.items():
            if trigger in text:
                expanded_text = text.replace(trigger, expansion)
        
        return expanded_text
    
    def _normalize_croatian_punctuation(self, text: str) -> str:
        """Normalize Croatian punctuation"""
        # Fix spacing around punctuation
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)  # Remove space before punctuation
        text = re.sub(r'([,.!?;:])\s*', r'\1 ', text)  # Ensure space after punctuation
        
        # Fix multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _handle_croatian_special_cases(self, text: str, role: str) -> str:
        """Handle special Croatian text cases"""
        # Handle religious terms capitalization
        religious_terms = [
            ('bog', 'Bog'),
            ('gospod', 'Gospod'),
            ('krist', 'Krist'),
            ('isus', 'Isus'),
            ('marija', 'Marija'),
            ('gospodin', 'Gospodin'),
        ]
        
        for term, capitalized in religious_terms:
            # Capitalize at beginning of sentences or standalone
            pattern = r'\b' + re.escape(term) + r'\b'
            text = re.sub(pattern, capitalized, text, flags=re.IGNORECASE)
        
        # Handle special responses for children (Djeca)
        if role == 'D.' and 'amen' in text.lower():
            # Ensure proper formatting for children's responses
            text = re.sub(r'\bamen\b', 'Amen', text, flags=re.IGNORECASE)
        
        # Handle Croatian-specific liturgical terms
        if 'grešnici' in text.lower():
            text = re.sub(r'\bgrešnici\b', 'grešnici', text, flags=re.IGNORECASE)
        
        return text
    
    def _normalize_croatian_role(self, role: str) -> str:
        """Normalize Croatian role markers"""
        if not role:
            return role
        
        # Clean up role marker
        normalized = role.strip().rstrip('.:').upper()
        
        # Map to standard Croatian roles
        role_mapping = {
            'DJECA': 'D.',
            'DIJECA': 'D.',  # Alternative spelling
            'KANTOR': 'K.',
            'ZBOR': 'Z.',
            'PREZBITER': 'P.',
            'PREZBITER+ZBOR': 'P.+Z.',
            'KANTOR+ZBOR': 'K.+Z.',
            'KANTOR+PREZBITER': 'K.+P.',
        }
        
        return role_mapping.get(normalized, role)
    
    def _apply_document_level_customizations(self, verses: List[Verse], 
                                           document: ParsedDocument) -> List[Verse]:
        """Apply document-level Croatian customizations"""
        if not verses:
            return verses
        
        # Check for common Croatian song patterns
        customized_verses = self._handle_croatian_song_patterns(verses)
        
        # Apply verse ordering rules
        customized_verses = self._apply_croatian_verse_ordering(customized_verses)
        
        # Handle special Croatian liturgical responses
        customized_verses = self._handle_liturgical_responses(customized_verses)
        
        return customized_verses
    
    def _handle_croatian_song_patterns(self, verses: List[Verse]) -> List[Verse]:
        """Handle common Croatian song patterns"""
        processed_verses = []
        
        for i, verse in enumerate(verses):
            # Check for refrain patterns
            if verse.role == 'Z.' and i > 0:
                # Check if this is a repeated refrain
                prev_verse = verses[i-1]
                if self._is_similar_verse(verse, prev_verse):
                    # Mark as refrain continuation
                    verse.verse_type = "refrain_continuation"
            
            # Handle Croatian-specific patterns
            if verse.role == 'D.' and any('smiluj' in line.text.lower() for line in verse.lines):
                # Mark as special liturgical response
                verse.verse_type = "liturgical_response"
            
            processed_verses.append(verse)
        
        return processed_verses
    
    def _apply_croatian_verse_ordering(self, verses: List[Verse]) -> List[Verse]:
        """Apply Croatian-specific verse ordering rules"""
        # Croatian songs often follow K. -> Z. -> P. -> D. pattern
        # But we preserve the original order from the PDF
        return verses
    
    def _handle_liturgical_responses(self, verses: List[Verse]) -> List[Verse]:
        """Handle special Croatian liturgical responses"""
        processed_verses = []
        
        for verse in verses:
            # Handle common liturgical patterns
            for line in verse.lines:
                text = line.text.lower()
                
                # Expand common liturgical abbreviations
                if 'gospod pomiluj' in text or 'g. pomiluj' in text:
                    line.text = line.text.replace('g. pomiluj', 'Gospod, pomiluj se')
                    line.text = line.text.replace('G. pomiluj', 'Gospod, pomiluj se')
                
                # Handle Alleluia variations
                if 'aleluja' in text or 'halleluja' in text:
                    line.text = re.sub(r'\b(aleluja|halleluja)\b', 'Aleluja', line.text, flags=re.IGNORECASE)
                
                # Handle Croatian-specific responses
                if 'smiluj se nama' in text:
                    # Ensure proper capitalization
                    line.text = re.sub(
                        r'smiluj se nama, koji smo grešnici, gospodine, smiluj se',
                        'Smiluj se nama, koji smo grešnici, Gospodine, smiluj se',
                        line.text,
                        flags=re.IGNORECASE
                    )
            
            processed_verses.append(verse)
        
        return processed_verses
    
    def _is_similar_verse(self, verse1: Verse, verse2: Verse) -> bool:
        """Check if two verses are similar (for refrain detection)"""
        if len(verse1.lines) != len(verse2.lines):
            return False
        
        similarity_threshold = 0.8
        similar_lines = 0
        
        for line1, line2 in zip(verse1.lines, verse2.lines):
            # Simple similarity check based on text length and content
            text1 = line1.text.lower().strip()
            text2 = line2.text.lower().strip()
            
            if text1 == text2:
                similar_lines += 1
            elif len(text1) > 0 and len(text2) > 0:
                # Check for partial similarity
                common_words = set(text1.split()) & set(text2.split())
                if len(common_words) / max(len(text1.split()), len(text2.split())) > 0.6:
                    similar_lines += 1
        
        return similar_lines / len(verse1.lines) >= similarity_threshold
    
    def get_language_specific_validation(self, verses: List[Verse]) -> List[str]:
        """Perform Croatian-specific validation"""
        issues = []
        
        # Check for common Croatian issues
        for i, verse in enumerate(verses):
            # Check for missing Djeca responses
            if verse.role == 'K.' and i < len(verses) - 1:
                next_verse = verses[i + 1]
                if 'amen' in verse.lines[-1].text.lower() and next_verse.role != 'D.':
                    issues.append(f"Verse {i}: Expected Djeca (D.) response after Amen")
            
            # Check for proper capitalization of religious terms
            for j, line in enumerate(verse.lines):
                text = line.text.lower()
                for word in self.croatian_words:
                    if word in text and word.capitalize() not in line.text:
                        issues.append(f"Verse {i}, Line {j}: '{word}' should be capitalized")
            
            # Check for unexpanded special responses
            for j, line in enumerate(verse.lines):
                if 'smiluj se...' in line.text.lower() and len(line.text) < 20:
                    issues.append(f"Verse {i}, Line {j}: Special response not fully expanded")
        
        return issues
    
    def get_customization_stats(self, original_verses: List[Verse], 
                               customized_verses: List[Verse]) -> Dict[str, any]:
        """Get statistics about applied customizations"""
        stats = {
            'original_verse_count': len(original_verses),
            'customized_verse_count': len(customized_verses),
            'text_fixes_applied': 0,
            'expansions_applied': 0,
            'special_responses_expanded': 0,
            'role_normalizations': 0,
            'liturgical_fixes': 0
        }
        
        # Count changes (simplified)
        for orig, custom in zip(original_verses, customized_verses):
            if orig.role != custom.role:
                stats['role_normalizations'] += 1
            
            for orig_line, custom_line in zip(orig.lines, custom.lines):
                if orig_line.text != custom_line.text:
                    stats['text_fixes_applied'] += 1
                    
                    # Check for specific types of changes
                    if any(abbrev in orig_line.text for abbrev in self.text_expansions):
                        stats['expansions_applied'] += 1
                    
                    if any(trigger in orig_line.text for trigger in self.special_responses):
                        stats['special_responses_expanded'] += 1
                    
                    if 'amen' in orig_line.text.lower() or 'aleluja' in orig_line.text.lower():
                        stats['liturgical_fixes'] += 1
        
        return stats
