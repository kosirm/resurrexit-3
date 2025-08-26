"""
Chord Detector for Universal Songbook Parser

This module identifies chord symbols and calculates their precise positioning
relative to lyrics using language-specific chord patterns.
"""

import re
import logging
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass

from core.models import PDFTextElement, ClassifiedText, TextType, Chord, ParsedDocument
from languages.base_language import LanguageConfig


@dataclass
class ChordMatch:
    """Represents a detected chord with its position and confidence"""
    chord: str
    element: PDFTextElement
    confidence: float
    normalized_chord: str


class ChordDetector:
    """
    Detects chord symbols in PDF text elements and positions them relative to lyrics.
    
    Uses language-specific chord patterns and positioning algorithms to identify
    chords and calculate their precise placement within verse lines.
    """
    
    def __init__(self, language_config: LanguageConfig):
        self.config = language_config
        self.logger = logging.getLogger(__name__)
        
        # Build chord detection patterns
        self.chord_patterns = self._build_chord_patterns()
        self.valid_chords = set(self.config.valid_chords)
        
        # Positioning parameters
        self.chord_line_tolerance = 15.0  # pixels - how close chords must be to lyrics
        self.chord_spacing_tolerance = 5.0  # pixels - chord positioning precision
        
        self.logger.debug(f"Initialized chord detector with {len(self.valid_chords)} valid chords")
    
    def _build_chord_patterns(self) -> List[re.Pattern]:
        """Build regex patterns for chord detection based on language config"""
        patterns = []
        
        # Basic chord pattern: letter + optional modifiers + optional numbers
        chord_letters = '|'.join(re.escape(letter) for letter in self.config.chord_letters)
        chord_modifiers = '|'.join(re.escape(mod) for mod in self.config.chord_modifiers)
        chord_numbers = '|'.join(self.config.chord_numbers)
        
        # Main chord pattern
        chord_pattern = (
            f'({chord_letters})'  # Base chord letter
            f'({chord_modifiers})?'  # Optional modifier
            f'({chord_numbers})?'  # Optional number
        )
        
        patterns.append(re.compile(chord_pattern, re.IGNORECASE))
        
        # Special patterns for common chord variations
        patterns.extend([
            re.compile(r'\b([A-H][#b]?(?:sus[24]?|dim|aug|maj|min|add)?[0-9]*)\b'),
            re.compile(r'\b([a-h][#b]?(?:sus[24]?|dim|aug|maj|min|add)?[0-9]*)\b'),
            re.compile(r'\*'),  # Special symbol for certain songs
            re.compile(r'd\*'),  # Special d* chord
        ])
        
        return patterns
    
    def detect_and_position(self, document: ParsedDocument) -> ParsedDocument:
        """
        Detect chords in the document and position them relative to lyrics.
        
        Args:
            document: ParsedDocument with classified text elements
            
        Returns:
            Updated ParsedDocument with positioned chords
        """
        self.logger.info("Detecting and positioning chords")
        
        # Separate chord elements from text elements
        chord_elements = [elem for elem in document.text_elements 
                         if elem.text_type == TextType.CHORD_LINE]
        text_elements = [elem for elem in document.text_elements 
                        if elem.text_type == TextType.VERSE_TEXT]
        
        self.logger.debug(f"Found {len(chord_elements)} chord elements and {len(text_elements)} text elements")
        
        # Detect chords in chord elements
        detected_chords = []
        for chord_elem in chord_elements:
            chords = self._detect_chords_in_element(chord_elem.element)
            detected_chords.extend(chords)
        
        # Also check text elements for inline chords
        for text_elem in text_elements:
            inline_chords = self._detect_inline_chords(text_elem.element)
            detected_chords.extend(inline_chords)
        
        self.logger.info(f"Detected {len(detected_chords)} chord instances")
        
        # Position chords relative to text lines
        positioned_chords = self._position_chords_to_lyrics(detected_chords, text_elements)
        
        # Update document with positioned chords
        if detected_chords:
            document.chord_elements = [
                ClassifiedText(
                    element=detected_chords[0].element,
                    text_type=TextType.CHORD_LINE,
                    confidence=detected_chords[0].confidence,
                    metadata={'positioned_chords': positioned_chords}
                )
            ]
        else:
            document.chord_elements = []
        
        return document
    
    def _detect_chords_in_element(self, element: PDFTextElement) -> List[ChordMatch]:
        """Detect all chords in a single PDF text element"""
        chords = []
        text = element.text.strip()
        
        if not text:
            return chords
        
        # Try each chord pattern
        for pattern in self.chord_patterns:
            matches = pattern.finditer(text)
            
            for match in matches:
                chord_text = match.group().strip()
                
                # Validate chord
                if self._is_valid_chord(chord_text):
                    normalized = self._normalize_chord(chord_text)
                    
                    chord_match = ChordMatch(
                        chord=chord_text,
                        element=element,
                        confidence=self._calculate_chord_confidence(chord_text, element),
                        normalized_chord=normalized
                    )
                    chords.append(chord_match)
        
        return chords
    
    def _detect_inline_chords(self, element: PDFTextElement) -> List[ChordMatch]:
        """Detect chords that appear inline with lyrics"""
        chords = []
        text = element.text
        
        # Look for chord patterns within brackets or parentheses
        bracket_patterns = [
            re.compile(r'\[([^\]]+)\]'),  # [chord]
            re.compile(r'\(([^)]+)\)'),   # (chord)
        ]
        
        for pattern in bracket_patterns:
            matches = pattern.finditer(text)
            
            for match in matches:
                potential_chord = match.group(1).strip()
                
                if self._is_valid_chord(potential_chord):
                    chord_match = ChordMatch(
                        chord=potential_chord,
                        element=element,
                        confidence=0.9,  # High confidence for bracketed chords
                        normalized_chord=self._normalize_chord(potential_chord)
                    )
                    chords.append(chord_match)
        
        return chords
    
    def _is_valid_chord(self, chord_text: str) -> bool:
        """Check if a text string represents a valid chord"""
        if not chord_text:
            return False
        
        # Clean up the chord text
        cleaned = chord_text.strip().replace(' ', '')
        
        # Check against valid chords list
        if cleaned in self.valid_chords:
            return True
        
        # Check normalized version
        normalized = self._normalize_chord(cleaned)
        return normalized in self.valid_chords
    
    def _normalize_chord(self, chord: str) -> str:
        """Normalize chord notation (e.g., remove spaces, standardize format)"""
        if not chord:
            return ""
        
        # Remove spaces
        normalized = chord.replace(' ', '')
        
        # Apply language-specific normalization rules
        normalization_rules = self.config.get_custom_processing_rules().get('chord_normalization', {})
        
        for old, new in normalization_rules.items():
            normalized = normalized.replace(old, new)
        
        return normalized
    
    def _calculate_chord_confidence(self, chord_text: str, element: PDFTextElement) -> float:
        """Calculate confidence score for a detected chord"""
        confidence = 0.5  # Base confidence
        
        # Higher confidence for exact matches
        if chord_text in self.valid_chords:
            confidence += 0.3
        
        # Higher confidence for pink/colored text (often used for chords)
        if element.is_pink:
            confidence += 0.2
        
        # Higher confidence for smaller font sizes (chords are often smaller)
        if element.font_size < self.config.text_font_size_min:
            confidence += 0.1
        
        # Higher confidence for bold text
        if element.is_bold:
            confidence += 0.1
        
        # Ensure confidence is between 0 and 1
        return min(1.0, max(0.0, confidence))
    
    def _position_chords_to_lyrics(self, chord_matches: List[ChordMatch], 
                                  text_elements: List[ClassifiedText]) -> List[Chord]:
        """Position detected chords relative to lyric lines"""
        positioned_chords = []
        
        # Group chords by vertical position (y-coordinate)
        chord_lines = self._group_chords_by_line(chord_matches)
        
        # Group text elements by line
        text_lines = self._group_text_by_line(text_elements)
        
        # Match chord lines to text lines
        for chord_line_y, chords_in_line in chord_lines.items():
            # Find the closest text line below this chord line
            closest_text_line = self._find_closest_text_line(chord_line_y, text_lines)
            
            if closest_text_line:
                # Position each chord in the line
                for chord_match in chords_in_line:
                    position = self._calculate_chord_position(chord_match, closest_text_line)
                    
                    positioned_chord = Chord(
                        chord=chord_match.normalized_chord,
                        position=position,
                        pixel_x=chord_match.element.x
                    )
                    positioned_chords.append(positioned_chord)
        
        return positioned_chords
    
    def _group_chords_by_line(self, chord_matches: List[ChordMatch]) -> Dict[float, List[ChordMatch]]:
        """Group chord matches by their vertical position (line)"""
        lines = {}
        
        for chord_match in chord_matches:
            y = chord_match.element.y
            
            # Find existing line within tolerance
            found_line = None
            for line_y in lines.keys():
                if abs(y - line_y) <= self.chord_line_tolerance:
                    found_line = line_y
                    break
            
            if found_line is not None:
                lines[found_line].append(chord_match)
            else:
                lines[y] = [chord_match]
        
        return lines
    
    def _group_text_by_line(self, text_elements: List[ClassifiedText]) -> Dict[float, List[ClassifiedText]]:
        """Group text elements by their vertical position (line)"""
        lines = {}
        
        for text_elem in text_elements:
            y = text_elem.element.y
            
            # Find existing line within tolerance
            found_line = None
            for line_y in lines.keys():
                if abs(y - line_y) <= self.chord_line_tolerance:
                    found_line = line_y
                    break
            
            if found_line is not None:
                lines[found_line].append(text_elem)
            else:
                lines[y] = [text_elem]
        
        return lines
    
    def _find_closest_text_line(self, chord_y: float, text_lines: Dict[float, List[ClassifiedText]]) -> Optional[List[ClassifiedText]]:
        """Find the text line closest to a chord line"""
        if not text_lines:
            return None
        
        closest_y = None
        min_distance = float('inf')
        
        for text_y in text_lines.keys():
            # Chords should be above text, so look for text lines below chord line
            if text_y > chord_y:
                distance = text_y - chord_y
                if distance < min_distance:
                    min_distance = distance
                    closest_y = text_y
        
        return text_lines.get(closest_y) if closest_y is not None else None
    
    def _calculate_chord_position(self, chord_match: ChordMatch, text_line: List[ClassifiedText]) -> int:
        """Calculate the character position of a chord within a text line"""
        if not text_line:
            return 0
        
        chord_x = chord_match.element.x
        
        # Find the text element that contains this x position
        for text_elem in text_line:
            elem = text_elem.element
            
            # Check if chord is within this text element's horizontal bounds
            if elem.x <= chord_x <= elem.x + elem.width:
                # Calculate relative position within the text
                relative_x = chord_x - elem.x
                char_width = elem.width / len(elem.text) if elem.text else 1
                position = int(relative_x / char_width)
                
                # Ensure position is within text bounds
                return min(position, len(elem.text))
        
        # If no exact match, find the closest text element
        closest_elem = min(text_line, key=lambda te: abs(te.element.x - chord_x))
        
        # Position at start or end based on relative position
        if chord_x < closest_elem.element.x:
            return 0
        else:
            return len(closest_elem.element.text)
    
    def get_detection_stats(self, chord_matches: List[ChordMatch]) -> Dict[str, any]:
        """Get statistics about chord detection"""
        if not chord_matches:
            return {'total_chords': 0}
        
        chord_types = {}
        confidence_scores = []
        
        for match in chord_matches:
            # Count chord types
            chord_types[match.normalized_chord] = chord_types.get(match.normalized_chord, 0) + 1
            confidence_scores.append(match.confidence)
        
        return {
            'total_chords': len(chord_matches),
            'unique_chords': len(chord_types),
            'chord_distribution': chord_types,
            'confidence': {
                'min': min(confidence_scores) if confidence_scores else 0,
                'max': max(confidence_scores) if confidence_scores else 0,
                'avg': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            }
        }
