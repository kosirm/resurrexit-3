"""
Verse Builder for Universal Songbook Parser

This module constructs verse objects from classified text elements,
handling role assignment and line grouping logic.
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from core.models import ClassifiedText, TextType, Verse, VerseLine, Chord, ParsedDocument
from languages.base_language import LanguageConfig


@dataclass
class VerseGroup:
    """Represents a group of text elements that form a verse"""
    role: str
    elements: List[ClassifiedText]
    start_y: float
    end_y: float


class VerseBuilder:
    """
    Builds verse objects from classified text elements.
    
    Groups text elements into verses based on role markers, positioning,
    and language-specific rules for verse continuation and line grouping.
    """
    
    def __init__(self, language_config: LanguageConfig):
        self.config = language_config
        self.logger = logging.getLogger(__name__)
        
        # Get language-specific processing rules
        self.processing_rules = self.config.get_custom_processing_rules()
        
        # Verse grouping parameters
        self.max_line_distance = self.processing_rules.get('verse_continuation_rules', {}).get(
            'max_distance_between_lines', 30.0
        )
        self.role_assignment_threshold = self.processing_rules.get(
            'role_assignment_distance_threshold', 15.0
        )
        
        self.logger.debug("Initialized verse builder")
    
    def build_verses(self, document: ParsedDocument) -> List[Verse]:
        """
        Build verses from classified text elements.
        
        Args:
            document: ParsedDocument with classified text elements
            
        Returns:
            List of Verse objects
        """
        self.logger.info("Building verses from classified elements")
        
        # Filter relevant elements for verse building
        verse_elements = [
            elem for elem in document.text_elements
            if elem.text_type in [TextType.ROLE_MARKER, TextType.VERSE_TEXT, TextType.INLINE_COMMENT]
        ]
        
        if not verse_elements:
            self.logger.warning("No verse elements found")
            return []
        
        # Sort elements by position
        sorted_elements = sorted(verse_elements, key=lambda e: (e.element.y, e.element.x))
        
        # Group elements into verses
        verse_groups = self._group_elements_into_verses(sorted_elements)
        
        # Build verse objects
        verses = []
        for group in verse_groups:
            verse = self._build_verse_from_group(group, document)
            if verse and verse.lines:  # Only add non-empty verses
                verses.append(verse)
        
        self.logger.info(f"Built {len(verses)} verses")
        return verses
    
    def _group_elements_into_verses(self, elements: List[ClassifiedText]) -> List[VerseGroup]:
        """Group text elements into verse groups based on role markers and positioning"""
        groups = []
        current_group = None
        current_role = ""
        
        for element in elements:
            if element.text_type == TextType.ROLE_MARKER:
                # Start new verse group
                if current_group and current_group.elements:
                    groups.append(current_group)
                
                role_text = element.element.text.strip()
                current_role = self._normalize_role_marker(role_text)
                
                current_group = VerseGroup(
                    role=current_role,
                    elements=[],
                    start_y=element.element.y,
                    end_y=element.element.y
                )
                
            elif element.text_type in [TextType.VERSE_TEXT, TextType.INLINE_COMMENT]:
                # Add to current group or create new one
                if current_group is None:
                    # No role marker found, create group with empty role
                    current_group = VerseGroup(
                        role="",
                        elements=[],
                        start_y=element.element.y,
                        end_y=element.element.y
                    )
                
                # Check if element belongs to current group
                if self._should_add_to_current_group(element, current_group):
                    current_group.elements.append(element)
                    current_group.end_y = max(current_group.end_y, element.element.y)
                else:
                    # Start new group (verse continuation without role marker)
                    if current_group.elements:
                        groups.append(current_group)
                    
                    current_group = VerseGroup(
                        role=current_role,  # Inherit previous role
                        elements=[element],
                        start_y=element.element.y,
                        end_y=element.element.y
                    )
        
        # Add final group
        if current_group and current_group.elements:
            groups.append(current_group)
        
        return groups
    
    def _normalize_role_marker(self, role_text: str) -> str:
        """Normalize role marker text"""
        # Remove trailing punctuation and whitespace
        normalized = role_text.rstrip('.:').strip()
        
        # Check if it's a valid role marker
        for role in self.config.role_markers:
            if normalized == role or normalized == role.rstrip('.'):
                return role
        
        return normalized
    
    def _should_add_to_current_group(self, element: ClassifiedText, current_group: VerseGroup) -> bool:
        """Determine if an element should be added to the current verse group"""
        if not current_group.elements:
            return True
        
        # Check vertical distance from last element in group
        last_element = current_group.elements[-1]
        vertical_distance = abs(element.element.y - last_element.element.y)
        
        if vertical_distance > self.max_line_distance:
            return False
        
        # Check if it's an inline comment
        if element.text_type == TextType.INLINE_COMMENT:
            return True
        
        # Check language-specific continuation rules
        continuation_rules = self.processing_rules.get('verse_continuation_rules', {})
        
        if continuation_rules.get('require_role_for_new_verse', False):
            # If we require roles for new verses, continue current group
            return True
        
        return True
    
    def _build_verse_from_group(self, group: VerseGroup, document: ParsedDocument) -> Optional[Verse]:
        """Build a Verse object from a VerseGroup"""
        if not group.elements:
            return None
        
        lines = []
        
        # Group elements into lines based on vertical position
        line_groups = self._group_elements_into_lines(group.elements)
        
        for line_elements in line_groups:
            verse_line = self._build_verse_line(line_elements, document)
            if verse_line:
                lines.append(verse_line)
        
        if not lines:
            return None
        
        # Determine verse type
        verse_type = "verse"
        if any(elem.text_type == TextType.INLINE_COMMENT for elem in group.elements):
            verse_type = "comment"
        
        return Verse(
            role=group.role,
            lines=lines,
            verse_type=verse_type
        )
    
    def _group_elements_into_lines(self, elements: List[ClassifiedText]) -> List[List[ClassifiedText]]:
        """Group elements into lines based on vertical position"""
        if not elements:
            return []
        
        # Sort by position
        sorted_elements = sorted(elements, key=lambda e: (e.element.y, e.element.x))
        
        lines = []
        current_line = []
        current_y = None
        
        for element in sorted_elements:
            element_y = element.element.y
            
            if current_y is None or abs(element_y - current_y) <= 5.0:  # Same line tolerance
                current_line.append(element)
                current_y = element_y
            else:
                # New line
                if current_line:
                    lines.append(current_line)
                current_line = [element]
                current_y = element_y
        
        # Add final line
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def _build_verse_line(self, line_elements: List[ClassifiedText], 
                         document: ParsedDocument) -> Optional[VerseLine]:
        """Build a VerseLine from elements on the same line"""
        if not line_elements:
            return None
        
        # Sort elements by horizontal position
        sorted_elements = sorted(line_elements, key=lambda e: e.element.x)
        
        # Combine text from all elements
        text_parts = []
        original_parts = []
        
        for element in sorted_elements:
            if element.text_type == TextType.VERSE_TEXT:
                text_parts.append(element.element.text)
                original_parts.append(element.element.text)
            elif element.text_type == TextType.INLINE_COMMENT:
                # Handle inline comments
                comment_text = element.element.text
                if comment_text.startswith(self.config.inline_comment_prefix):
                    # Format as ChordPro comment
                    comment_content = comment_text[len(self.config.inline_comment_prefix):].strip()
                    text_parts.append(f"{{comment: {comment_content}}}")
                else:
                    text_parts.append(comment_text)
                original_parts.append(comment_text)
        
        if not text_parts:
            return None
        
        # Join text parts
        combined_text = " ".join(text_parts).strip()
        original_text = " ".join(original_parts).strip()
        
        # Apply text encoding fixes
        fixed_text = self.config.fix_text_encoding(combined_text)
        
        # Find associated chords for this line
        chords = self._find_chords_for_line(line_elements, document)
        
        return VerseLine(
            text=fixed_text,
            chords=chords,
            original_line=original_text,
            line_type=TextType.VERSE_TEXT
        )
    
    def _find_chords_for_line(self, line_elements: List[ClassifiedText], 
                             document: ParsedDocument) -> List[Chord]:
        """Find chords associated with this line"""
        chords = []
        
        if not line_elements or not document.chord_elements:
            return chords
        
        # Get the vertical position of this line
        line_y = line_elements[0].element.y
        
        # Look for chord elements positioned above this line
        for chord_elem in document.chord_elements:
            if hasattr(chord_elem, 'metadata') and 'positioned_chords' in chord_elem.metadata:
                positioned_chords = chord_elem.metadata['positioned_chords']
                
                # Check if chords are positioned for this line
                for chord in positioned_chords:
                    # Simple heuristic: if chord is within reasonable distance above the line
                    chord_y = chord_elem.element.y
                    if 0 < line_y - chord_y < 30:  # Chord should be above text
                        chords.append(chord)
        
        # Sort chords by position
        chords.sort(key=lambda c: c.position)
        
        return chords
    
    def _apply_language_customizations(self, verses: List[Verse]) -> List[Verse]:
        """Apply language-specific customizations to verses"""
        customized_verses = []
        
        for verse in verses:
            # Apply special text expansions
            special_responses = self.processing_rules.get('special_responses', {})
            
            for line in verse.lines:
                for trigger, expansion in special_responses.items():
                    if isinstance(expansion, dict) and 'trigger' in expansion:
                        trigger_text = expansion['trigger']
                        expansion_text = expansion['expansion']
                        
                        if trigger_text in line.text:
                            line.text = line.text.replace(trigger_text, expansion_text)
            
            customized_verses.append(verse)
        
        return customized_verses
    
    def get_building_stats(self, verses: List[Verse]) -> Dict[str, any]:
        """Get statistics about verse building"""
        if not verses:
            return {'total_verses': 0}
        
        role_counts = {}
        line_counts = []
        verse_types = {}
        
        for verse in verses:
            # Count by role
            role = verse.role or "no_role"
            role_counts[role] = role_counts.get(role, 0) + 1
            
            # Count lines per verse
            line_counts.append(len(verse.lines))
            
            # Count by type
            verse_types[verse.verse_type] = verse_types.get(verse.verse_type, 0) + 1
        
        return {
            'total_verses': len(verses),
            'role_distribution': role_counts,
            'verse_type_distribution': verse_types,
            'lines_per_verse': {
                'min': min(line_counts) if line_counts else 0,
                'max': max(line_counts) if line_counts else 0,
                'avg': sum(line_counts) / len(line_counts) if line_counts else 0
            },
            'total_lines': sum(line_counts)
        }
