"""
Spanish Language Configuration for PDF Parser
Handles Spanish chord notation, role markers, and text processing
"""

import re
from typing import Dict, List, Set
from ..base_language import LanguageConfig


class SpanishConfig(LanguageConfig):
    """Configuration for Spanish language parsing"""
    
    def __init__(self):
        # Initialize parent first
        super().__init__()

        # Set basic properties
        self.language_code = "es"
        self.language_name = "Spanish"

        # Spanish role markers
        # S. = Solista, A. = Asamblea, P. = Presbitero (in red)
        # Mujeres = Women, Hombres = Men, Niños = Children
        # S1., S2., S3. = Soloist 1, 2, 3
        # A1., A2., A3. = Assembly 1, 2, 3
        # N. = Narrator, S. A. = Soloist and Assembly
        self.role_markers = [
            'Mujeres:', 'Hombres:', 'Niños:', 'S. A.', 'S.', 'A.', 'P.', 'N.',
            'S1.', 'S2.', 'S3.', 'A1.', 'A2.', 'A3.'
        ]

        # Spanish chord notation - based on the chord notation document
        # Major chords: DO, RE, MI, FA, SOL, LA, SI (and with #)
        # Minor chords: Do-, Re-, Mi-, Fa-, Sol-, La-, Si- (and with #)
        # Extensions: 7, 6, 7aum, dim, etc.
        self.chord_letters = self._build_spanish_chords()

        # Chord numbers and modifiers (Spanish specific)
        self.chord_numbers = ['7', '6', '9', '5']
        self.chord_modifiers = ['7aum', 'dim', 'dism', '+5dim', '+9', '-6', '-7', '-9', '-5', '5/9dim', 'maj7']

        # Spanish-specific character encoding fixes (if any)
        self.encoding_fixes = {
            # Add Spanish-specific encoding issues if discovered
        }

        # Spanish capodaster terms
        self.capodaster_terms = ['cejilla', 'capo']

        # Inline comment prefix (same as Croatian/Slovenian)
        self.inline_comment_prefix = 'C:'

        # Spanish-specific font metrics (based on analysis of ES-021)
        self.font_metrics = self._build_spanish_font_metrics()

    def _build_spanish_chords(self) -> List[str]:
        """Build comprehensive list of Spanish chords from the notation document"""
        # Use the EXACT chords from the chord notation document
        spanish_chords_from_document = [
            # All chords from line 6 of the document (split by comma and cleaned)
            'DO', 'Do7aum', 'Do7', 'Do6', 'Do-', 'Do#', 'Do#7aum', 'Do#7', 'Do#6', 'Do#-',
            'Re', 'Re7aum', 'Re7', 'Re6', 'Re-', 'Re#', 'Re#7aum', 'Re#7', 'Re#6', 'Re#-',
            'Mi', 'Mi7aum', 'Mi7', 'Mi6', 'Mi-',
            'Fa', 'Fa7aum', 'Fa7', 'Fa6', 'Fa-', 'Fa#', 'Fa#7aum', 'Fa#7', 'Fa#6', 'Fa#-',
            'Sol', 'Sol7aum', 'Sol7', 'Sol6', 'Sol-', 'Sol#', 'Sol#7aum', 'Sol#7', 'Sol#6', 'Sol#-',
            'La', 'La7aum', 'La7', 'La6', 'La-', 'La#', 'La#7aum', 'La#7', 'La#6', 'La#-',
            'Si', 'Si7aum', 'Si7', 'Si6', 'Si-',
            # Complex chords from the document
            'Re-6', 'Re-9', 'Mi-6', 'La-6', 'La-7', 'Sib6+5dim', 'Do#dim', 'Sol7', 'Re-5',
            'Mi9', 'Sol7+9', 'Mi7', 'Fa7+5dim', 'Re-dim', 'La-5', 'Fa#5/9dim', 'Sol-6',
            'Fa#dism', 'Mi-7'
        ]

        # Add variations with different dash characters (en dash vs hyphen)
        # Spanish uses en dash (–) but PDFs might have hyphen (-)
        additional_variations = []
        for chord in spanish_chords_from_document:
            if '-' in chord:
                # Add version with en dash
                additional_variations.append(chord.replace('-', '–'))
            if '–' in chord:
                # Add version with hyphen
                additional_variations.append(chord.replace('–', '-'))

        all_chords = spanish_chords_from_document + additional_variations

        # Add uppercase variations for major chords (from the table)
        uppercase_variations = []
        major_chord_map = {
            'Do': 'DO', 'Re': 'RE', 'Mi': 'MI', 'Fa': 'FA',
            'Sol': 'SOL', 'La': 'LA', 'Si': 'SI'
        }

        for chord in all_chords:
            for mixed_case, upper_case in major_chord_map.items():
                if chord.startswith(mixed_case) and not chord.startswith(mixed_case + '#'):
                    uppercase_variations.append(chord.replace(mixed_case, upper_case, 1))

        all_chords.extend(uppercase_variations)

        # Add spaced chord extensions (e.g., "Mi– 6", "Re– 9", "La– 7")
        spaced_extensions = []
        base_chords_for_spacing = ['Do', 'Re', 'Mi', 'Fa', 'Sol', 'La', 'Si',
                                  'Do#', 'Re#', 'Fa#', 'Sol#', 'La#']
        extensions_for_spacing = ['6', '7', '9']

        for base in base_chords_for_spacing:
            for ext in extensions_for_spacing:
                # Add both minor and major versions with spaces
                spaced_extensions.append(f"{base}– {ext}")  # Minor with en dash
                spaced_extensions.append(f"{base}- {ext}")   # Minor with hyphen
                spaced_extensions.append(f"{base} {ext}")    # Major

        all_chords.extend(spaced_extensions)

        # Add common Spanish chord chains (pipe-separated)
        chord_chains = [
            'Do |Mi |Fa', 'Do |Mi |Fa Mi', 'Re |Sol |La', 'Mi |La |Si',
            'Fa |Sol |Do', 'Sol |Do |Re', 'La |Re |Mi', 'Si |Mi |Fa#',
            # Add minor chord chains
            'Do– |Mi– |Fa–', 'Re– |Sol– |La–', 'Mi– |La– |Si–',
            # Mixed major/minor chains
            'Do |Mi– |Fa', 'Re |Sol– |La', 'Mi– |La |Si',
        ]
        all_chords.extend(chord_chains)

        return sorted(list(set(all_chords)))  # Remove duplicates and sort

    def requires_chord_chain_processing(self, filename: str) -> bool:
        """Check if a specific file requires chord chain processing"""
        # List of files that contain chord chains (Do |Mi |Fa patterns)
        chord_chain_files = {
            'ES - 020',  # AVE MARÍA II (1984) - has Do |Mi |Fa chord chains
            # Add more files here as needed when chord chains are discovered
            # 'ES - XXX',  # Another file with chord chains
        }

        # Extract base filename without extension
        base_filename = filename.replace('.pdf', '').replace('.chordpro', '')

        return base_filename in chord_chain_files

    def _build_spanish_font_metrics(self) -> Dict[str, Dict[str, float]]:
        """Build Spanish-specific font metrics for character width calculations"""
        return {
            # Font metrics based on analysis of Spanish PDFs
            'default': {
                'char_width': 6.5,  # Default character width in pixels
                'space_width': 3.2,  # Space character width
                'font_size_multiplier': 0.55,  # Multiplier for font size to char width
            },

            # Role-specific font metrics
            'roles': {
                'S.': {  # Solista - regular text (11.5pt)
                    'char_width': 6.3,
                    'space_width': 3.1,
                    'font_size_multiplier': 0.55,
                    'is_bold': False,
                },
                'A.': {  # Asamblea - bold text (12.1pt)
                    'char_width': 7.2,  # Wider due to bold formatting
                    'space_width': 3.6,
                    'font_size_multiplier': 0.60,  # Bold text is wider
                    'is_bold': True,
                },
                'P.': {  # Presbitero - red text (similar to S.)
                    'char_width': 6.3,
                    'space_width': 3.1,
                    'font_size_multiplier': 0.55,
                    'is_bold': False,
                },
                'Mujeres:': {  # Women - similar to A.
                    'char_width': 7.0,
                    'space_width': 3.5,
                    'font_size_multiplier': 0.58,
                    'is_bold': True,
                },
                'Hombres:': {  # Men - similar to A.
                    'char_width': 7.0,
                    'space_width': 3.5,
                    'font_size_multiplier': 0.58,
                    'is_bold': True,
                },
                'Niños:': {  # Children - similar to A.
                    'char_width': 7.0,
                    'space_width': 3.5,
                    'font_size_multiplier': 0.58,
                    'is_bold': True,
                },
            },

            # Chord-specific metrics (9.5pt)
            'chords': {
                'char_width': 5.2,  # Smaller font for chords
                'space_width': 2.6,
                'font_size_multiplier': 0.55,
            },

            # Title metrics (15.2pt)
            'title': {
                'char_width': 8.4,
                'space_width': 4.2,
                'font_size_multiplier': 0.55,
            },

            # Subtitle metrics (9.9pt - biblical references)
            'subtitle': {
                'char_width': 5.4,
                'space_width': 2.7,
                'font_size_multiplier': 0.55,
            }
        }

    def get_character_width(self, role: str = None, text_type: str = 'default', font_size: float = 12.0) -> float:
        """Get character width for Spanish text based on role and context"""
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

    def is_verse_text(self, text: str, font_size: float = 12.0, role_context: str = None) -> bool:
        """Spanish-specific method to determine if text should be treated as verse content"""
        text_clean = text.strip()

        # Empty text is not verse content
        if not text_clean:
            return False

        # Check if it's a role marker
        if any(text_clean.startswith(role) for role in self.role_markers):
            return False

        # Spanish-specific rules for ALL CAPS text
        if text_clean.isupper():
            # If we have role context and it's A. (Asamblea), ALL CAPS is likely verse text
            if role_context == 'A.':
                # Short ALL CAPS lines in A. context are verse text
                if len(text_clean) <= 50:
                    return True

            # Check for common Spanish verse patterns in ALL CAPS
            verse_patterns = [
                r'^(NUESTROS|NUESTRAS|LOS|LAS|A\s+)',  # Common beginnings
                r'^[A-ZÁÉÍÓÚÑ\s\-\(\)\.!¡¿?]{1,50}$',  # Short ALL CAPS phrases
                r'(ENEMIGOS|OPRESORES|SEÑOR|DIOS)',  # Common liturgical words
            ]

            for pattern in verse_patterns:
                if re.match(pattern, text_clean):
                    return True

        # Regular text classification
        # If font size is much larger than normal text, it might be a title
        if font_size > 14.0:
            return False

        # If it contains common verse indicators, it's verse text
        verse_indicators = [
            r'[¿¡]',  # Spanish question/exclamation marks
            r'[\.!?]$',  # Ends with punctuation
            r'\b(que|si|de|en|con|por|para)\b',  # Common Spanish words
        ]

        for indicator in verse_indicators:
            if re.search(indicator, text_clean, re.IGNORECASE):
                return True

        # Default: if it's not obviously a title, treat as verse text
        return True

    def classify_text_type(self, text: str, font_size: float = 12.0,
                          position_y: float = 0, role_context: str = None,
                          is_red: bool = False, is_bold: bool = False) -> str:
        """Classify text using visual characteristics for Spanish songs"""
        text_clean = text.strip()

        # Empty text
        if not text_clean:
            return 'unknown'

        # Role markers
        if any(text_clean.startswith(role) for role in self.role_markers):
            return 'role'

        # VISUAL-BASED TITLE DETECTION (most reliable)
        # Spanish titles: Red + Bold + Large font (15.2pt)
        if font_size >= 15.0 and is_red and is_bold:
            return 'title'

        # VISUAL-BASED VERSE DETECTION (most reliable)
        # Spanish verse text: Regular color + smaller font (11.5-12.1pt)
        if font_size <= 13.0 and not is_red:
            # This includes ALL CAPS A. verses - they're just regular verse text
            return 'verse'

        # Chord detection (Spanish chord notation)
        if any(chord in text_clean for chord in self.chord_letters[:20]):  # Check common chords
            # If it's mostly chords, classify as chord
            words = text_clean.split()
            chord_words = sum(1 for word in words if any(chord in word for chord in self.chord_letters[:20]))
            if len(words) > 0 and chord_words / len(words) > 0.5:
                return 'chord'

        # Subtitle detection (biblical references) - smaller than title, larger than verse
        if re.match(r'^(Salmo|Sal|Mt|Mc|Lc|Jn|Hch|Rm)', text_clean):
            return 'subtitle'

        # Inline comments
        if 'C:' in text_clean:
            return 'comment'

        # Fallback: if font size suggests verse text, treat as verse
        if font_size <= 13.0:
            return 'verse'

        # Default for unclear cases
        return 'unknown'

    def get_title_detection_rules(self) -> Dict[str, any]:
        """Spanish-specific title detection rules - use visual characteristics"""
        return {
            # Visual-based title detection (much more reliable)
            'font_size_threshold': 15.0,  # Spanish titles are 15.2pt (much larger than verse text)
            'color_detection': {
                'red_titles': True,  # Spanish titles ARE red + bold
                'red_color_threshold': 0.6,  # Lower threshold for red detection
                'bold_weight_threshold': 600,  # Bold font weight
                'require_both_red_and_bold': True,  # Must be BOTH red AND bold for title
            },
            'position_rules': {
                'top_margin_threshold': 100.0,  # Titles appear near top
                'center_alignment_tolerance': 0.4,  # Titles are usually centered
            },
            'visual_priority': {
                # If text meets these visual criteria, it's definitely a title
                'definite_title_criteria': {
                    'min_font_size': 15.0,  # 15.2pt titles
                    'must_be_red': True,
                    'must_be_bold': True,
                },
                # If text meets these criteria, it's definitely NOT a title (even if ALL CAPS)
                'definite_verse_criteria': {
                    'max_font_size': 13.0,  # Verse text is 11.5-12.1pt
                    'not_red': True,  # Verse text is black/regular color
                    'short_length': 60,  # Short lines are likely verses, not titles
                }
            },
            'text_patterns': {
                'exclude_patterns': [r'^\d+$', r'^página \d+$'],  # Exclude page numbers
                # Remove text-based title patterns - rely on visual cues instead
            }
        }

    def get_capodaster_detection_rules(self) -> Dict[str, any]:
        """Spanish capodaster (cejilla) detection rules"""
        return {
            'terms': self.capodaster_terms,
            'patterns': [
                r'cejilla\s+(\d+)\s+traste',  # "cejilla 3 traste"
                r'capo\s+(\d+)',  # "capo 3"
                r'cejilla\s+en\s+(\d+)',  # "cejilla en 3"
            ],
            'color_detection': {
                'small_text': True,  # Cejilla might be small text
                'min_font_size': 6.0,
                'max_font_size': 10.0,
            }
        }

    def get_role_detection_rules(self) -> Dict[str, any]:
        """Spanish role marker detection rules"""
        return {
            'red_roles': ['P.'],  # Presbitero in red
            'standard_roles': [
                'S.', 'A.', 'Mujeres:', 'Hombres:', 'Niños:', 'S. A.', 'N.',
                'S1.', 'S2.', 'S3.', 'A1.', 'A2.', 'A3.'
            ],
            'color_detection': {
                'red_color_threshold': 0.8,  # For P. (Presbitero)
            },
            'position_rules': {
                'left_margin_threshold': 20.0,  # Role markers at left margin
                'indentation_tolerance': 10.0,
            }
        }

    def normalize_title(self, title: str) -> str:
        """Normalize title text for Spanish"""
        # Apply encoding fixes
        title = self.fix_text_encoding(title)
        
        # Remove extra whitespace
        title = ' '.join(title.split())
        
        # Spanish titles are typically in uppercase
        return title.strip()

    def normalize_chord(self, chord: str) -> str:
        """Normalize Spanish chord notation"""
        if not chord:
            return chord
        
        # Remove extra spaces (Fa #7 -> Fa#7)
        chord = chord.replace(' ', '')
        
        # Handle common variations
        chord_fixes = {
            'Sib': 'Si b',  # Normalize Si bemol
            'DO': 'DO',     # Keep uppercase for major
            'do': 'Do',     # Normalize case
        }
        
        for old, new in chord_fixes.items():
            chord = chord.replace(old, new)
        
        return chord

    def get_custom_processing_rules(self) -> Dict[str, any]:
        """Spanish-specific processing rules"""
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
            'spanish_specific': {
                'detect_biblical_references': True,  # Subtitle biblical references
                'cejilla_optional': True,  # Cejilla detection is optional
                'visual_classification': True,  # Use visual cues for classification
                'title_criteria': {
                    'min_font_size': 15.0,  # Titles are 15.2pt
                    'must_be_red': True,    # Titles are red
                    'must_be_bold': True,   # Titles are bold
                },
                'verse_criteria': {
                    'max_font_size': 13.0,  # Verse text is 11.5-12.1pt
                    'allow_all_caps': True, # A. verses are ALL CAPS
                    'regular_color': True,  # Verse text is regular color
                },
                'presbitero_red_required': True,  # P. should be red
                'preserve_caps_formatting': True,  # Keep original capitalization
            }
        }

    def get_export_settings(self) -> Dict[str, any]:
        """Settings for exporting Spanish songs"""
        return {
            'use_tabs_for_alignment': True,
            'preserve_original_spacing': False,
            'add_language_metadata': True,
            'chord_bracket_style': 'square',  # [chord] vs (chord)
            'comment_style': 'chordpro',      # {comment: text}
            'title_case': 'preserve',         # Preserve original title case
        }
