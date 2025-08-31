"""
Italian Language Configuration for PDF Parser
Handles Italian chord notation, role markers, and text processing
Based on Spanish configuration structure
"""

import re
from typing import Dict, List, Set
from ..base_language import LanguageConfig


class ItalianConfig(LanguageConfig):
    """Configuration for Italian language parsing"""

    def __init__(self):
        # Initialize parent first
        super().__init__()

        # Set basic properties
        self.language_code = "it"
        self.language_name = "Italian"

        # Italian role markers
        # C. = Coro, A. = Assembly, P. = Priest, B. = Bambini (Children)
        # Donne = Women, Uomini = Men
        self.role_markers = [
            'Donne:', 'Uomini:', 'C.', 'A.', 'P.', 'B.'
        ]

        # Italian chord notation - based on the chord notation document
        # Major chords: Do, Re, Mi, Fa, Sol, La, Si (with spaces: "Re m 9")
        # Minor chords: Do m, Re m, Mi m, Fa m, Sol m, La m, Si m
        # Extensions: 7, 9, 6, etc.
        self.chord_letters = self._build_italian_chords()

        # Chord numbers and modifiers (Italian specific)
        self.chord_numbers = ['7', '6', '9', '5', '4', '2', '11', '13']
        self.chord_modifiers = ['dim', 'aug', '+', '°', 'maj7', 'sus4', 'sus2']

        # Italian-specific character encoding fixes (if any)
        self.encoding_fixes = {
            # Add Italian-specific encoding issues if discovered
        }

        # Italian capodaster terms
        self.capodaster_terms = ['capotasto', 'capo']

        # Inline comment prefix (same as Spanish)
        self.inline_comment_prefix = 'C:'

        # Italian-specific font metrics (based on analysis of IT-002)
        self.font_metrics = self._build_italian_font_metrics()

    def _build_italian_chords(self) -> List[str]:
        """Build comprehensive list of Italian chords"""
        # Italian chord roots
        roots = ['Do', 'Re', 'Mi', 'Fa', 'Sol', 'La', 'Si']

        # Build all combinations
        all_chords = []

        # Major chords
        for root in roots:
            all_chords.append(root)

        # Minor chords (with space: "Re m")
        for root in roots:
            all_chords.append(f"{root} m")

        # Extended chords
        extensions = ['7', '9', '6', '4', '2', '11', '13']
        for root in roots:
            for ext in extensions:
                all_chords.append(f"{root} {ext}")
                all_chords.append(f"{root} m {ext}")

        # Special chords
        special_modifiers = ['dim', 'aug', '+', '°', 'maj7', 'sus4', 'sus2']
        for root in roots:
            for mod in special_modifiers:
                all_chords.append(f"{root} {mod}")

        # Chords in parentheses (keep parentheses)
        parentheses_chords = []
        for chord in all_chords:
            parentheses_chords.append(f"({chord})")

        all_chords.extend(parentheses_chords)

        return sorted(list(set(all_chords)))  # Remove duplicates and sort

    def _build_italian_font_metrics(self) -> Dict[str, any]:
        """Italian-specific font metrics based on IT-002 analysis"""
        return {
            'title': {
                'size': 14.9,
                'color': 14355506,  # Red
                'bold': False,
                'uppercase': True,
            },
            'subtitle': {
                'size': 9.8,
                'color': 2301728,  # Black
                'bold': False,
                'uppercase': False,
            },
            'role': {
                'size': 11.6,
                'color': 9079950,  # Gray
                'bold': False,
                'uppercase': False,
            },
            'verse': {
                'size': 11.6,
                'color': 2301728,  # Black
                'bold': False,
                'uppercase': False,
            },
            'chord': {
                'size': 9.7,
                'color': 14355506,  # Red (same as title)
                'bold': False,
                'uppercase': False,
            },
            'comment': {
                'size': 11.6,
                'color': 9079950,  # Gray (same as role)
                'bold': False,
                'uppercase': False,
            }
        }

    def normalize_chord(self, chord: str) -> str:
        """Normalize Italian chord notation"""
        if not chord:
            return chord

        # Handle chords in parentheses: "(Sol 7)" -> "[(Sol7)]"
        if chord.startswith('(') and chord.endswith(')'):
            # Remove parentheses, normalize spaces, then add ChordPro brackets with parentheses
            inner_chord = chord[1:-1].strip()
            normalized_inner = self._normalize_chord_spaces(inner_chord)
            return f"[({normalized_inner})]"

        # Handle regular chords with spaces: "Re m 9" -> "[Re m 9]" (preserve spaces)
        return f"[{self._normalize_chord_spaces(chord)}]"

    def _normalize_chord_spaces(self, chord: str) -> str:
        """Normalize spaces in Italian chords while preserving the Italian format"""
        chord = chord.strip()

        # Italian chords have specific spacing: "Re m 9"
        # Pattern: [Root] [modifier] [number]

        # Match Italian chord pattern with spaces
        match = re.match(r'^(Do|Re|Mi|Fa|Sol|La|Si)(\s+[mb])?(\s+\d+.*)?$', chord)
        if match:
            root = match.group(1)
            modifier = match.group(2).strip() if match.group(2) else ""
            number = match.group(3).strip() if match.group(3) else ""

            # Reconstruct with proper spacing
            result = root
            if modifier:
                result += f" {modifier}"
            if number:
                result += f" {number}"
            return result

        # If no match, return as-is but clean up multiple spaces
        return re.sub(r'\s+', ' ', chord)

    def normalize_title(self, title: str) -> str:
        """Normalize title text for Italian"""
        # Apply encoding fixes
        title = self.fix_text_encoding(title)

        # Remove extra whitespace
        title = ' '.join(title.split())

        # Remove common Italian prefixes/suffixes
        title = re.sub(r'^\d+\.\s*', '', title)  # Remove numbering
        title = re.sub(r'\s*\*+\s*$', '', title)  # Remove trailing asterisks

        # Italian titles are typically in uppercase
        return title.strip()

    def get_role_detection_rules(self) -> Dict[str, any]:
        """Italian role marker detection rules"""
        return {
            'gray_roles': ['C.', 'A.', 'P.', 'B.'],  # Italian roles in gray
            'standard_roles': [
                'C.', 'A.', 'Donne:', 'Uomini:', 'P.', 'B.'
            ],
            'color_detection': {
                'gray_color_value': 9079950,  # Specific Italian gray color
                'color_tolerance': 100000,    # Tolerance for color matching
            },
            'position_rules': {
                'left_margin_threshold': 20.0,  # Role markers at left margin
                'indentation_tolerance': 10.0,
            }
        }

    def get_custom_processing_rules(self) -> Dict[str, any]:
        """Italian-specific processing rules"""
        return {
            'preserve_case_in_roles': True,
            'allow_mixed_case_titles': False,
            'chord_spacing_tolerance': 5.0,  # pixels
            'role_assignment_distance_threshold': 15.0,  # pixels
            'inline_comment_formatting': {
                'add_empty_lines': True,
                'format_as_chordpro_comment': True,
            },
            'verse_continuation_rules': {
                'max_distance_between_lines': 30.0,  # pixels
                'require_role_for_new_verse': False,
            },
            'italian_specific': {
                'detect_biblical_references': True,  # Subtitle biblical references
                'visual_classification': True,  # Use visual cues for classification
                'title_criteria': {
                    'min_font_size': 14.0,  # Titles are 14.9pt
                    'must_be_red': True,    # Titles are red
                    'must_be_bold': False,  # Italian titles are NOT bold
                    'color_value': 14355506, # Specific red color
                },
                'role_criteria': {
                    'must_be_gray': True,   # Italian roles are gray
                    'must_be_bold': False,  # Italian roles are NOT bold
                    'color_value': 9079950, # Specific gray color
                },
                'verse_criteria': {
                    'max_font_size': 12.0,  # Verse text is 11.6pt
                    'allow_all_caps': True, # A. verses are ALL CAPS
                    'regular_color': True,  # Verse text is regular color
                    'color_value': 2301728, # Black color
                },
                'chord_criteria': {
                    'font_size': 9.7,      # Chords are 9.7pt
                    'color_value': 14355506, # Red color (same as title)
                },
                'assembly_uppercase': True,  # A. role text should be uppercase
                'preserve_chord_parentheses': True,  # Keep (Sol 7) format
                'preserve_chord_spacing': True,  # Keep "Re m 9" spacing
            }
        }

    def get_export_settings(self) -> Dict[str, any]:
        """Settings for exporting Italian songs"""
        return {
            'use_tabs_for_alignment': True,
            'preserve_original_spacing': False,
            'add_language_metadata': True,
            'chord_bracket_style': 'square',  # [chord] vs (chord)
            'comment_style': 'chordpro',      # {comment: text}
            'title_case': 'preserve',         # Preserve original title case
        }
