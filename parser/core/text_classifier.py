"""
Text Classifier for Universal Songbook Parser

This module categorizes PDF text elements into titles, role markers, verse text,
chords, comments, and kapodaster information using language-specific patterns.
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from core.models import PDFTextElement, ClassifiedText, TextType, ParsedDocument
from languages.base_language import LanguageConfig


@dataclass
class ClassificationRule:
    """Represents a rule for classifying text elements"""
    text_type: TextType
    patterns: List[re.Pattern]
    font_size_range: Tuple[float, float] = (0.0, 100.0)
    position_hints: Dict[str, any] = None
    confidence_boost: float = 0.0


class TextClassifier:
    """
    Classifies PDF text elements into semantic categories.
    
    Uses language-specific patterns, font sizes, positioning, and formatting
    to determine the type and purpose of each text element.
    """
    
    def __init__(self, language_config: LanguageConfig):
        self.config = language_config
        self.logger = logging.getLogger(__name__)
        
        # Build classification rules
        self.classification_rules = self._build_classification_rules()
        
        # Positioning parameters
        self.title_position_threshold = 100.0  # pixels from top
        self.role_indent_threshold = 50.0     # pixels from left margin
        
        self.logger.debug(f"Initialized text classifier with {len(self.classification_rules)} rules")
    
    def _build_classification_rules(self) -> List[ClassificationRule]:
        """Build classification rules based on language configuration"""
        rules = []
        
        # Title classification rules
        title_patterns = [
            re.compile(r'^[A-ZČŠŽĆĐ\s\(\)\-\.\d]+$'),  # All uppercase with special chars
            re.compile(r'^[A-ZČŠŽĆĐ][A-ZČŠŽĆĐ\s\(\)\-\.\d]*$'),  # Starts with uppercase
        ]
        title_patterns.extend(self.config.title_patterns)
        
        rules.append(ClassificationRule(
            text_type=TextType.TITLE,
            patterns=title_patterns,
            font_size_range=(self.config.title_font_size_min, 100.0),
            confidence_boost=0.3
        ))
        
        # Role marker classification rules
        role_patterns = []
        for role in self.config.role_markers:
            # Exact match
            role_patterns.append(re.compile(f'^{re.escape(role)}$'))
            # With trailing space or punctuation
            role_patterns.append(re.compile(f'^{re.escape(role)}[\\s\\.]'))
        
        rules.append(ClassificationRule(
            text_type=TextType.ROLE_MARKER,
            patterns=role_patterns,
            font_size_range=(self.config.text_font_size_min, 100.0),
            confidence_boost=0.4
        ))
        
        # Kapodaster classification rules
        kapodaster_patterns = [
            re.compile(r'kapodaster', re.IGNORECASE),
            re.compile(r'kapo', re.IGNORECASE),
            re.compile(r'na\s+[IVX]+\.\s*polju', re.IGNORECASE),
        ]
        kapodaster_patterns.extend(self.config.kapodaster_patterns)
        
        rules.append(ClassificationRule(
            text_type=TextType.KAPODASTER,
            patterns=kapodaster_patterns,
            confidence_boost=0.5
        ))
        
        # Comment classification rules
        comment_patterns = [
            re.compile(f'^{re.escape(self.config.inline_comment_prefix)}'),  # C: comments
            re.compile(r'^\{comment:', re.IGNORECASE),  # ChordPro comments
            re.compile(r'^\{.*\}$'),  # Any ChordPro directive
        ]
        
        rules.append(ClassificationRule(
            text_type=TextType.INLINE_COMMENT,
            patterns=comment_patterns,
            confidence_boost=0.4
        ))
        
        # Chord line classification rules (basic patterns)
        chord_patterns = [
            re.compile(r'^[A-Ha-h\s\d\*\#b\+\-\(\)]+$'),  # Chord-like characters only
            re.compile(r'^\s*[A-Ha-h][#b]?(?:sus|dim|aug|maj|min)?\d*\s*$'),  # Single chord
        ]
        
        rules.append(ClassificationRule(
            text_type=TextType.CHORD_LINE,
            patterns=chord_patterns,
            font_size_range=(0.0, self.config.chord_font_size_min + 2.0),
            confidence_boost=0.2
        ))
        
        return rules
    
    def classify(self, elements: List[PDFTextElement]) -> ParsedDocument:
        """
        Classify all text elements and create a structured document.
        
        Args:
            elements: List of raw PDF text elements
            
        Returns:
            ParsedDocument with classified elements
        """
        self.logger.info(f"Classifying {len(elements)} text elements")
        
        classified_elements = []
        title = ""
        comments = []
        kapodaster = None
        
        # Sort elements by position (top to bottom, left to right)
        sorted_elements = sorted(elements, key=lambda e: (e.y, e.x))
        
        for element in sorted_elements:
            classification = self._classify_element(element)
            classified_elements.append(classification)
            
            # Extract special elements
            if classification.text_type == TextType.TITLE and not title:
                title = self.config.normalize_title(element.text)
            elif classification.text_type == TextType.KAPODASTER and not kapodaster:
                kapodaster = element.text.strip()
            elif classification.text_type in [TextType.COMMENT, TextType.INLINE_COMMENT]:
                comments.append(element.text.strip())
        
        # Post-process classifications
        classified_elements = self._post_process_classifications(classified_elements)
        
        document = ParsedDocument(
            title=title or "Untitled Song",
            text_elements=classified_elements,
            chord_elements=[],  # Will be populated by chord detector
            comments=comments,
            kapodaster=kapodaster,
            language=self.config.language_code
        )
        
        self.logger.info(f"Classification complete: title='{title}', {len(classified_elements)} elements")
        return document
    
    def _classify_element(self, element: PDFTextElement) -> ClassifiedText:
        """Classify a single text element"""
        text = element.text.strip()
        if not text:
            return ClassifiedText(
                element=element,
                text_type=TextType.UNKNOWN,
                confidence=0.0
            )
        
        best_classification = None
        best_confidence = 0.0
        
        # Try each classification rule
        for rule in self.classification_rules:
            confidence = self._calculate_rule_confidence(element, rule)
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_classification = rule.text_type
        
        # Default to verse text if no strong classification
        if best_confidence < 0.3:
            best_classification = TextType.VERSE_TEXT
            best_confidence = 0.5
        
        # Apply position-based adjustments
        adjusted_confidence = self._apply_position_adjustments(
            element, best_classification, best_confidence
        )
        
        return ClassifiedText(
            element=element,
            text_type=best_classification,
            confidence=adjusted_confidence,
            metadata={'original_confidence': best_confidence}
        )
    
    def _calculate_rule_confidence(self, element: PDFTextElement, rule: ClassificationRule) -> float:
        """Calculate confidence score for a classification rule"""
        confidence = 0.0
        text = element.text.strip()
        
        # Check pattern matches
        pattern_match = False
        for pattern in rule.patterns:
            if pattern.search(text):
                pattern_match = True
                break
        
        if not pattern_match:
            return 0.0
        
        # Base confidence for pattern match
        confidence = 0.5 + rule.confidence_boost
        
        # Font size check
        if rule.font_size_range[0] <= element.font_size <= rule.font_size_range[1]:
            confidence += 0.2
        
        # Formatting checks
        if rule.text_type == TextType.TITLE and element.is_bold:
            confidence += 0.2
        
        if rule.text_type == TextType.CHORD_LINE and element.is_pink:
            confidence += 0.3
        
        # Length-based adjustments
        if rule.text_type == TextType.ROLE_MARKER and len(text) <= 10:
            confidence += 0.2
        
        if rule.text_type == TextType.TITLE and 5 <= len(text) <= 50:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _apply_position_adjustments(self, element: PDFTextElement, 
                                   text_type: TextType, confidence: float) -> float:
        """Apply position-based confidence adjustments"""
        adjusted_confidence = confidence
        
        # Title position adjustments
        if text_type == TextType.TITLE:
            if element.y < self.title_position_threshold:
                adjusted_confidence += 0.2
            else:
                adjusted_confidence -= 0.1
        
        # Role marker position adjustments
        if text_type == TextType.ROLE_MARKER:
            if element.x < self.role_indent_threshold:
                adjusted_confidence += 0.1
        
        # Chord line position adjustments
        if text_type == TextType.CHORD_LINE:
            # Chords are often positioned above text
            if element.font_size < self.config.text_font_size_min:
                adjusted_confidence += 0.1
        
        return min(1.0, max(0.0, adjusted_confidence))
    
    def _post_process_classifications(self, classified_elements: List[ClassifiedText]) -> List[ClassifiedText]:
        """Post-process classifications to fix common issues"""
        if not classified_elements:
            return classified_elements
        
        # Sort by position for context analysis
        sorted_elements = sorted(classified_elements, key=lambda ce: (ce.element.y, ce.element.x))
        
        # Apply contextual corrections
        for i, element in enumerate(sorted_elements):
            # Check for misclassified role markers
            if element.text_type == TextType.VERSE_TEXT:
                text = element.element.text.strip()
                
                # Check if it looks like a role marker
                for role in self.config.role_markers:
                    if text.startswith(role):
                        # Reclassify as role marker
                        element.text_type = TextType.ROLE_MARKER
                        element.confidence = 0.8
                        break
            
            # Check for chord lines misclassified as verse text
            if element.text_type == TextType.VERSE_TEXT and element.element.is_pink:
                text = element.element.text.strip()
                
                # If it's short and contains chord-like patterns
                if len(text) < 30 and re.match(r'^[A-Ha-h\s\d\*\#b\+\-\(\)]+$', text):
                    element.text_type = TextType.CHORD_LINE
                    element.confidence = 0.7
        
        return sorted_elements
    
    def get_classification_stats(self, classified_elements: List[ClassifiedText]) -> Dict[str, any]:
        """Get statistics about text classification"""
        if not classified_elements:
            return {'total_elements': 0}
        
        type_counts = {}
        confidence_by_type = {}
        
        for element in classified_elements:
            text_type = element.text_type.value
            
            # Count by type
            type_counts[text_type] = type_counts.get(text_type, 0) + 1
            
            # Track confidence by type
            if text_type not in confidence_by_type:
                confidence_by_type[text_type] = []
            confidence_by_type[text_type].append(element.confidence)
        
        # Calculate average confidence by type
        avg_confidence_by_type = {}
        for text_type, confidences in confidence_by_type.items():
            avg_confidence_by_type[text_type] = sum(confidences) / len(confidences)
        
        return {
            'total_elements': len(classified_elements),
            'type_distribution': type_counts,
            'average_confidence_by_type': avg_confidence_by_type,
            'overall_confidence': sum(e.confidence for e in classified_elements) / len(classified_elements)
        }
