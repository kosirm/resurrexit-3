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

    def _build_italian_font_metrics(self) -> Dict[str, Dict[str, float]]:
        """Build Italian-specific font metrics for character width calculations"""
        return {
            # Font metrics based on analysis of Italian PDFs
            'default': {
                'char_width': 6.2,  # Default character width in pixels
                'space_width': 3.1,  # Space character width
                'font_size_multiplier': 0.53,  # Multiplier for font size to char width
            },

            # Role-specific metrics (11.6pt)
            'roles': {
                'C.': {  # Coro - similar to verse
                    'char_width': 6.2,
                    'space_width': 3.1,
                    'font_size_multiplier': 0.53,
                    'is_bold': False,
                },
                'A.': {  # Assembly/All - similar to refrain
                    'char_width': 6.2,
                    'space_width': 3.1,
                    'font_size_multiplier': 0.53,
                    'is_bold': False,
                },
                'Donne': {  # Women
                    'char_width': 6.2,
                    'space_width': 3.1,
                    'font_size_multiplier': 0.53,
                    'is_bold': False,
                },
                'Uomini': {  # Men
                    'char_width': 6.2,
                    'space_width': 3.1,
                    'font_size_multiplier': 0.53,
                    'is_bold': False,
                },
                'P.': {  # Priest
                    'char_width': 6.2,
                    'space_width': 3.1,
                    'font_size_multiplier': 0.53,
                    'is_bold': False,
                },
                'B.': {  # Bambini (Children)
                    'char_width': 6.2,
                    'space_width': 3.1,
                    'font_size_multiplier': 0.53,
                    'is_bold': False,
                },
            },

            # Chord-specific metrics (9.7pt)
            'chords': {
                'char_width': 5.1,  # Smaller font for chords
                'space_width': 2.6,
                'font_size_multiplier': 0.53,
            },

            # Title metrics (14.9pt)
            'title': {
                'char_width': 7.9,
                'space_width': 3.9,
                'font_size_multiplier': 0.53,
            },

            # Subtitle metrics (9.8pt - biblical references)
            'subtitle': {
                'char_width': 5.2,
                'space_width': 2.6,
                'font_size_multiplier': 0.53,
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

        # Normalize Italian chord to consistent internal format
        # Examples: "Fa maj 7" -> "Fa maj7", "Re m 9" -> "Re m9"
        return self._normalize_italian_chord_format(chord)

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

    def get_character_width(self, role: str = None, text_type: str = 'default', font_size: float = 12.0) -> float:
        """Get character width for Italian text based on role and context"""
        metrics = self.font_metrics

        # Get role-specific metrics
        if role and role in metrics['roles']:
            role_metrics = metrics['roles'][role]
            base_width = role_metrics['char_width']
            multiplier = role_metrics['font_size_multiplier']
        elif text_type in metrics:
            type_metrics = metrics[text_type]
            base_width = type_metrics['char_width']
            multiplier = type_metrics['font_size_multiplier']
        else:
            default_metrics = metrics['default']
            base_width = default_metrics['char_width']
            multiplier = default_metrics['font_size_multiplier']

        # Calculate final width
        final_width = base_width * (font_size / 12.0) * multiplier
        return final_width

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

    def _normalize_italian_chord_format(self, chord: str) -> str:
        """
        Normalize Italian chord to consistent internal format:
        - Major extensions: "Fa maj 7" -> "Fa maj7" (no spaces in extensions)
        - Minor extensions: "Re m 9" -> "Re m9" (space before m, no space after m)
        - Handle both spaced and merged input formats
        """
        chord = chord.strip()
        if not chord:
            return chord

        # Italian chord roots
        italian_roots = ['Do', 'Re', 'Mi', 'Fa', 'Sol', 'La', 'Si']

        # Find the root chord
        root_chord = None
        accidental = ""
        remaining = ""

        for root in italian_roots:
            if chord.startswith(root):
                root_chord = root
                remaining = chord[len(root):]

                # Check for accidental (#, b)
                if remaining.startswith('#') or remaining.startswith('b'):
                    accidental = remaining[0]
                    remaining = remaining[1:]
                break

        if not root_chord:
            return chord  # Not an Italian chord

        # Clean up remaining part (remove extra spaces)
        remaining = remaining.strip()

        if not remaining:
            # Simple chord like "Fa", "Re#"
            return root_chord + accidental

        # Handle minor chords specially
        if remaining.startswith('m') or remaining.startswith(' m'):
            return self._normalize_minor_chord(root_chord + accidental, remaining)

        # Handle major extensions (maj, dim, aug, sus, add, etc.)
        return self._normalize_major_chord(root_chord + accidental, remaining)

    def _normalize_minor_chord(self, root_with_accidental: str, remaining: str) -> str:
        """
        Normalize minor chord format: "Re m 9" -> "Re m9"
        Keep space before 'm', remove spaces after 'm'
        """
        remaining = remaining.strip()

        # Remove leading space if present
        if remaining.startswith(' m'):
            remaining = remaining[2:]  # Remove ' m'
        elif remaining.startswith('m'):
            remaining = remaining[1:]  # Remove 'm'
        else:
            return root_with_accidental + remaining  # Fallback

        # Clean up extensions after 'm'
        remaining = remaining.strip()

        if not remaining:
            # Simple minor chord "Re m"
            return f"{root_with_accidental} m"

        # Remove all spaces in extensions: "maj 7" -> "maj7", " 9" -> "9"
        extensions_clean = re.sub(r'\s+', '', remaining)

        return f"{root_with_accidental} m{extensions_clean}"

    def _normalize_major_chord(self, root_with_accidental: str, remaining: str) -> str:
        """
        Normalize major chord format: "Fa maj 7" -> "Fa maj7"
        Remove all spaces in extensions
        """
        remaining = remaining.strip()

        if not remaining:
            return root_with_accidental

        # Remove all spaces in extensions: "maj 7" -> "maj7", "dim 7" -> "dim7"
        extensions_clean = re.sub(r'\s+', '', remaining)

        return f"{root_with_accidental}{extensions_clean}"
