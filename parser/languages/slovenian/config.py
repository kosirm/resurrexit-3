"""
Slovenian language configuration for the universal parser.
"""

import re
from typing import Dict, List, Pattern
from languages.base_language import LanguageConfig
from .customizations import SlovenianCustomizations


class SlovenianConfig(LanguageConfig):
    """Configuration for Slovenian songbook parsing"""
    
    def __init__(self):
        # Initialize parent first
        super().__init__()

        # Set basic properties
        self.language_code = "sl"
        self.language_name = "Slovenian"

        # Slovenian role markers (O. for Otroci, not D. for Djeca)
        self.role_markers = ['K.+Z.', 'P.+Z.', 'K.', 'Z.', 'P.', 'O.']

        # Standard European chord notation
        self.chord_letters = [
            'E', 'F', 'FIS', 'G', 'GIS', 'A', 'B', 'H', 'C', 'CIS', 'D', 'DIS',
            'e', 'f', 'fis', 'g', 'gis', 'a', 'b', 'h', 'c', 'cis', 'd', 'dis'
        ]

        # Chord numbers and modifiers
        self.chord_numbers = ['7', '9', '11', '13']
        self.chord_modifiers = ['sus', 'dim', 'aug', 'maj', 'min']

        # Slovenian-specific character encoding fixes
        # Main issue: PDF encodes č as è
        self.encoding_fixes = {
            'è': 'č',  # Most common issue
            'È': 'Č',  # Uppercase version
        }

        # Comment markers
        self.inline_comment_prefix = "C:"

        # Font size thresholds
        self.title_font_size_min = 12.0
        self.text_font_size_min = 10.0
        self.chord_font_size_min = 10.0

        # Slovenian-specific font metrics (based on working parser)
        self.font_metrics = self._build_slovenian_font_metrics()

        # Initialize customizations
        self.customizations = SlovenianCustomizations()
        
        # Slovenian-specific title patterns
        self.title_patterns = [
            re.compile(r'^[A-ZČŠŽĆĐ\s\(\)\-\.\d]+$'),  # Slovenian uppercase with special chars
            re.compile(r'^[A-ZČŠŽĆĐ][A-ZČŠŽĆĐ\s\(\)\-\.\d]*$'),  # Must start with uppercase
        ]
        
        # Additional Slovenian patterns
        self.kapodaster_patterns.extend([
            re.compile(r'Kapodaster na [IVX]+\. polju', re.IGNORECASE),
        ])
    
    def get_custom_processing_rules(self) -> Dict[str, any]:
        """Slovenian-specific processing rules"""
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
            }
        }
    
    def is_slovenian_specific_text(self, text: str) -> bool:
        """Check for Slovenian-specific text patterns"""
        slovenian_words = [
            'gospod', 'bog', 'kristus', 'jezus', 'marija', 'sveti', 'sveta',
            'amen', 'aleluja', 'halleluja', 'slava', 'hvala'
        ]
        
        text_lower = text.lower()
        return any(word in text_lower for word in slovenian_words)
    
    def get_role_display_name(self, role: str) -> str:
        """Get human-readable role name"""
        role_names = {
            'K.': 'Kantor',
            'Z.': 'Zbor',
            'P.': 'Prezbiter', 
            'O.': 'Otroci',
            'K.+Z.': 'Kantor + Zbor',
            'P.+Z.': 'Prezbiter + Zbor',
        }
        return role_names.get(role, role)
    
    def should_merge_chord_lines(self, line1_y: float, line2_y: float) -> bool:
        """Determine if two chord lines should be merged based on Y position"""
        # Slovenian PDFs sometimes have chords split across very close lines
        return abs(line1_y - line2_y) < 3.0
    
    def get_chord_positioning_rules(self) -> Dict[str, float]:
        """Slovenian-specific chord positioning rules"""
        return {
            'max_chord_distance_from_text': 15.0,  # pixels
            'chord_alignment_tolerance': 2.0,      # pixels
            'prefer_vowel_positioning': True,
            'vowels': 'aeiouAEIOU',
        }
    
    def normalize_title(self, title: str) -> str:
        """Normalize title text for Slovenian"""
        # Apply encoding fixes
        title = self.fix_text_encoding(title)
        
        # Remove extra whitespace
        title = ' '.join(title.split())
        
        # Ensure proper capitalization for Slovenian titles
        # (Most Slovenian titles are all uppercase)
        return title.strip()
    
    def get_export_settings(self) -> Dict[str, any]:
        """Settings for exporting Slovenian songs"""
        return {
            'use_tabs_for_alignment': True,
            'preserve_original_spacing': False,
            'add_language_metadata': True,
            'chord_bracket_style': 'square',  # [chord] vs (chord)
            'comment_style': 'chordpro',      # {comment: text}
        }

    def _build_slovenian_font_metrics(self) -> Dict[str, Dict[str, float]]:
        """Build Slovenian-specific font metrics for character width calculations"""
        return {
            # Font metrics based on working Slovenian parser
            'default': {
                'char_width': 6.0,  # Default character width in pixels
                'space_width': 3.0,  # Space character width
                'font_size_multiplier': 0.50,  # Multiplier for font size to char width
            },

            # Role-specific font metrics (Slovenian roles are typically not bold)
            'roles': {
                'S.': {  # Solist - regular text
                    'char_width': 6.0,
                    'space_width': 3.0,
                    'font_size_multiplier': 0.50,
                    'is_bold': False,
                },
                'Z.': {  # Zbor - regular text
                    'char_width': 6.0,
                    'space_width': 3.0,
                    'font_size_multiplier': 0.50,
                    'is_bold': False,
                },
                'L.': {  # Ljudstvo - regular text
                    'char_width': 6.0,
                    'space_width': 3.0,
                    'font_size_multiplier': 0.50,
                    'is_bold': False,
                },
                'D.': {  # Duhovnik - regular text
                    'char_width': 6.0,
                    'space_width': 3.0,
                    'font_size_multiplier': 0.50,
                    'is_bold': False,
                },
            },

            # Chord-specific metrics
            'chords': {
                'char_width': 5.5,  # Slightly smaller for chords
                'space_width': 2.8,
                'font_size_multiplier': 0.50,
            },

            # Title metrics
            'title': {
                'char_width': 7.0,
                'space_width': 3.5,
                'font_size_multiplier': 0.50,
            },
        }

    def get_character_width(self, role: str = None, text_type: str = 'default', font_size: float = 12.0) -> float:
        """Get character width for Slovenian text based on role and context"""
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

        # Adjust for font size
        size_factor = font_size / 12.0  # Normalize to 12pt
        return base_width * size_factor * multiplier
