"""
Improved PDF Extractor based on the working Croatian/Slovenian parsers

This module combines the best features from both working parsers:
- Span-based positioning with pixel-perfect accuracy
- Color detection for proper text classification
- Multi-page support with coordinate adjustment
- Font metrics for accurate character positioning
"""

import fitz  # PyMuPDF
import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

from core.models import PDFTextElement


class ImprovedPDFExtractor:
    """
    Improved PDF extractor based on the working Croatian/Slovenian parsers.
    
    Uses span-based extraction with color detection and proper text classification.
    """
    
    def __init__(self, language_config):
        self.config = language_config
        self.logger = logging.getLogger(__name__)
        
        # Arial font character widths (from working parser)
        self.arial_char_widths = {
            'A': 667, 'B': 667, 'C': 722, 'D': 722, 'E': 667, 'F': 611, 'G': 778, 'H': 722, 'I': 278, 'J': 500,
            'K': 667, 'L': 556, 'M': 833, 'N': 722, 'O': 778, 'P': 667, 'Q': 778, 'R': 722, 'S': 667, 'T': 611,
            'U': 722, 'V': 667, 'W': 944, 'X': 667, 'Y': 667, 'Z': 611,
            'a': 556, 'b': 556, 'c': 500, 'd': 556, 'e': 556, 'f': 278, 'g': 556, 'h': 556, 'i': 222, 'j': 222,
            'k': 500, 'l': 222, 'm': 833, 'n': 556, 'o': 556, 'p': 556, 'q': 556, 'r': 333, 's': 500, 't': 278,
            'u': 556, 'v': 500, 'w': 722, 'x': 500, 'y': 500, 'z': 500,
            ' ': 278, '.': 278, ',': 278, ':': 278, ';': 278, '!': 333, '?': 556, '"': 355, "'": 191,
            '(': 333, ')': 333, '[': 278, ']': 278, '{': 334, '}': 334, '-': 333, '_': 556, '=': 584,
            '+': 584, '*': 389, '/': 278, '\\': 278, '|': 260, '&': 667, '%': 889, '$': 556, '#': 556,
            '@': 1015, '^': 469, '~': 584, '`': 333, '0': 556, '1': 556, '2': 556, '3': 556, '4': 556,
            '5': 556, '6': 556, '7': 556, '8': 556, '9': 556
        }
        
        # Pink colors used in Croatian/Slovenian songbooks
        self.pink_colors = {
            15466636,  # Main pink color used in songbooks
            15466637,  # Slight variation
            15466635,  # Slight variation
        }
        
        self.logger.debug("Initialized improved PDF extractor")
    
    def get_char_width(self, char: str, font_size: float) -> float:
        """Get the actual width of a character in Arial font at given size"""
        font_units = self.arial_char_widths.get(char, 556)  # 556 is average Arial character width
        return (font_units / 1000.0) * font_size
    
    def extract(self, pdf_path: str) -> Dict[str, List[Dict]]:
        """
        Extract span data from PDF with proper classification.
        
        Returns:
            Dictionary with classified lines: chord_lines, text_lines, title_lines, etc.
        """
        self.logger.info(f"Extracting spans from PDF: {pdf_path}")

        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        doc = fitz.open(pdf_path)
        
        chord_lines = []
        text_lines = []
        title_lines = []
        kapodaster_lines = []
        comment_lines = []
        
        self.logger.debug(f"Processing {len(doc)} page(s)")
        
        # Process all pages
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_dict = page.get_text("dict")
            
            self.logger.debug(f"Processing page {page_num + 1}/{len(doc)}")
            
            for block in text_dict["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        line_text = ''.join([span['text'] for span in line['spans']])
                        
                        if not line_text.strip():
                            continue
                        
                        # Get the main span for analysis
                        main_span = line['spans'][0] if line['spans'] else None
                        if not main_span:
                            continue
                        
                        # Extract color and font information
                        color = main_span.get('color', 0)  # 0 = black, other values = colors
                        font_size = main_span.get('size', 11.0)
                        font_name = main_span.get('font', '')
                        
                        # Convert color to RGB for analysis (pink detection)
                        is_pink = self._is_pink_color(color)

                        # Detect bold font from font name
                        is_bold = self._is_bold_font(font_name)

                        # Get exact RGB color values for debugging
                        rgb_color = self._get_rgb_color(color)

                        # Debug exact color for Spanish songs
                        if self.config.language_code == "es" and line_text.strip():
                            self.logger.debug(f"🎨 COLOR DEBUG: '{line_text.strip()[:30]}...' | "
                                            f"color_int: {color} | RGB: {rgb_color} | "
                                            f"is_pink: {is_pink} | font_size: {font_size:.1f} | "
                                            f"font: {font_name}")

                        # Adjust Y coordinate for multi-page (add page offset)
                        page_height = page.rect.height
                        adjusted_y = line['bbox'][1] + (page_num * page_height)
                        
                        line_data = {
                            'text': line_text,
                            'text_content': line_text.strip(),
                            'x_start': main_span['bbox'][0],
                            'x_end': main_span['bbox'][2],
                            'width': main_span['bbox'][2] - main_span['bbox'][0],
                            'y': adjusted_y,  # Use adjusted Y coordinate
                            'original_y': line['bbox'][1],  # Keep original for reference
                            'page_num': page_num,
                            'font_size': font_size,
                            'color': color,
                            'is_pink': is_pink,
                            'font_name': font_name,
                            'spans': line['spans']  # Keep all spans for multi-span lines
                        }
                        
                        # Classify the line based on content, color, and font
                        if self._is_chord_line_text(line_text, color, font_size):
                            chord_lines.append(line_data)
                            # Enhanced debug for Spanish red chords
                            if self.config.language_code == "es":
                                is_red = self._is_red_color(color)
                                self.logger.debug(f"🎼 Chord line (page {page_num + 1}): '{line_text.strip()}' (red: {is_red}, pink: {is_pink}, size: {font_size:.1f})")
                            else:
                                self.logger.debug(f"🎼 Chord line (page {page_num + 1}): '{line_text.strip()}' (pink: {is_pink}, size: {font_size:.1f})")
                        
                        elif self._is_title_line(line_text, font_size, is_pink, color):
                            title_lines.append(line_data)
                            self.logger.debug(f"📋 Title line (page {page_num + 1}): '{line_text.strip()}' (pink: {is_pink}, size: {font_size:.1f})")
                            if "SL - 110.pdf" in pdf_path or "SL - 128.pdf" in pdf_path:
                                print(f"🎯 FOUND TITLE in {pdf_path}: '{line_text.strip()[:50]}...' (size: {font_size:.1f}, pink: {is_pink})")

                        
                        elif self._is_kapodaster_line(line_text, is_pink):
                            kapodaster_lines.append(line_data)
                            self.logger.debug(f"🎸 Kapodaster line (page {page_num + 1}): '{line_text.strip()}' (pink: {is_pink}, size: {font_size:.1f})")
                        
                        elif self._is_comment_line(line_text, is_pink):
                            comment_lines.append(line_data)
                            self.logger.debug(f"💬 Comment line (page {page_num + 1}): '{line_text.strip()}' (pink: {is_pink}, size: {font_size:.1f})")
                        
                        # Check for Italian role lines using language-specific detection
                        elif (self.config.language_code == "it" and
                              hasattr(self.config, 'is_role_line') and
                              self.config.is_role_line(line_text, font_size, is_bold, color)):
                            # Italian role line detected
                            line_data['is_role'] = True
                            text_lines.append(line_data)
                            self.logger.debug(f"🎭 Role line (page {page_num + 1}): '{line_text.strip()}' (size: {font_size:.1f})")

                        else:
                            # Regular text line (verses, role markers for other languages)
                            # Handle role markers and text content for non-Italian languages
                            has_role_marker = any(role in line_text for role in self.config.role_markers)

                            if has_role_marker:
                                # Extract text content after role marker
                                for role in sorted(self.config.role_markers, key=len, reverse=True):
                                    if line_text.strip().startswith(role):
                                        text_after_role = line_text[len(role):].strip()
                                        if text_after_role:
                                            line_data['text_content'] = text_after_role
                                        break

                            text_lines.append(line_data)
                            role_info = " (with role)" if has_role_marker else ""

                            # Enhanced debug for Spanish
                            if self.config.language_code == "es":
                                caps_info = f", ALL_CAPS: {line_text.strip().isupper()}"
                                color_info = f", pink: {is_pink}"
                                self.logger.debug(f"📝 Text line{role_info} (page {page_num + 1}): '{line_text.strip()[:50]}...' (size: {font_size:.1f}{caps_info}{color_info})")

                            else:
                                self.logger.debug(f"📝 Text line{role_info} (page {page_num + 1}): '{line_text.strip()[:50]}...' (size: {font_size:.1f})")
        
        doc.close()
        
        # Combine chord lines that are on the same Y position
        combined_chord_lines = self._combine_chord_lines_by_y_position(chord_lines)

        # Note: Quote combining is now handled by file-specific customizations
        # This allows for more precise control over different quote formats

        # Spanish-specific: Combine text lines separated by chord chain spacing
        if self.config.language_code == "es":
            text_lines = self._combine_spanish_chord_spaced_lines(text_lines)

        result = {
            'chord_lines': combined_chord_lines,
            'text_lines': text_lines,  # Let customizations handle quote combining
            'title_lines': title_lines,
            'kapodaster_lines': kapodaster_lines,
            'comment_lines': comment_lines
        }
        
        self.logger.info(f"Extracted spans: {len(combined_chord_lines)} chord lines, {len(text_lines)} text lines, {len(title_lines)} titles")
        return result
    
    def _is_pink_color(self, color: int) -> bool:
        """Check if color is pink/magenta (used for titles, kapodaster, comments)"""
        return color in self.pink_colors

    def _get_rgb_color(self, color: int) -> tuple:
        """Convert PyMuPDF color integer to RGB tuple"""
        if color == 0:
            return (0, 0, 0)  # Black

        # PyMuPDF stores color as integer, convert to RGB
        # Extract RGB components from the integer
        r = (color >> 16) & 0xFF
        g = (color >> 8) & 0xFF
        b = color & 0xFF

        return (r, g, b)

    def _is_red_color(self, color: int, threshold: float = 0.6) -> bool:
        """Check if color is red (for Spanish titles)"""
        if color == 0:
            return False  # Black is not red

        r, g, b = self._get_rgb_color(color)

        # Normalize to 0-1 range
        r_norm = r / 255.0
        g_norm = g / 255.0
        b_norm = b / 255.0

        # Red color: high red component, low green and blue
        return (r_norm > threshold and
                r_norm > g_norm * 1.5 and
                r_norm > b_norm * 1.5)
    
    def _is_chord_line_text(self, text: str, color: int = 0, font_size: float = 12.0) -> bool:
        """Check if text line contains primarily chords - enhanced for Spanish red chords"""
        words = text.split()
        if not words:
            return False

        # Spanish-specific chord detection: Red color + small font + Spanish chord notation
        if self.config.language_code == "es":
            is_red = self._is_red_color(color)
            is_small_font = font_size <= 10.0  # Spanish chords are 9.5pt

            # If it's red and small font, check if it looks like Spanish chords
            if is_red and is_small_font:
                # Handle chord chains with pipes (e.g., "Do |Mi |Fa", "Do |Mi |Fa Mi")
                if '|' in text:
                    # Split by pipes and check if most parts are chords
                    pipe_parts = [part.strip() for part in text.split('|')]
                    chord_parts = 0
                    for part in pipe_parts:
                        # Each part can be a single chord or multiple chords
                        part_words = part.split()
                        if part_words and all(self._looks_like_spanish_chord(word) for word in part_words):
                            chord_parts += 1

                    # If most pipe-separated parts are chords, it's a chord line
                    if len(pipe_parts) > 0 and (chord_parts / len(pipe_parts)) > 0.7:
                        return True

                # Handle spaced chord extensions (e.g., "Mi– 6", "Re– 9")
                if len(words) == 2:
                    base_chord = words[0]
                    extension = words[1]
                    # Check if first word is Spanish chord and second is extension
                    if (self._looks_like_spanish_chord(base_chord) and
                        extension.isdigit() or extension in ['6', '7', '9', 'maj7', 'dim', 'aum']):
                        return True

                # Handle single word chords or multiple chords
                spanish_chord_count = 0
                for word in words:
                    if self._looks_like_spanish_chord(word):
                        spanish_chord_count += 1

                # If most words look like Spanish chords, it's a chord line
                if len(words) > 0 and (spanish_chord_count / len(words)) > 0.7:
                    return True

        # Italian-specific chord detection
        if self.config.language_code == "it":
            # Handle Italian spaced chords like "La m", "Re m 9", "(Sol 7)"

            # Handle parentheses chords: "(Sol 7)"
            if text.startswith('(') and text.endswith(')'):
                inner_text = text[1:-1].strip()
                if self._looks_like_italian_chord(inner_text.split()[0]):
                    return True

            # Handle spaced chord extensions (e.g., "La m", "Re m 9")
            if len(words) >= 2:
                base_chord = words[0]
                # Check if first word is Italian chord and second is extension
                if (self._looks_like_italian_chord(base_chord) and
                    (words[1] in ['m'] or words[1].isdigit() or words[1] in ['6', '7', '9', 'maj7', 'dim', 'aug'])):
                    return True

            # Handle single Italian chords
            if len(words) == 1 and self._looks_like_italian_chord(words[0]):
                return True

            # Handle multiple Italian chords
            italian_chord_count = 0
            for word in words:
                if self._looks_like_italian_chord(word):
                    italian_chord_count += 1

            # If most words look like Italian chords, it's a chord line
            if len(words) > 0 and (italian_chord_count / len(words)) > 0.7:
                return True

        # Original logic for Croatian/Slovenian (content-based)
        # Special case: single spaced chord like "H 7" should be recognized as chord line
        if len(words) == 2:
            normalized_single_chord = self._normalize_chord(' '.join(words))
            if normalized_single_chord in self.config.valid_chords:
                return True

        chord_count = 0
        for word in words:
            if self._looks_like_chord(word):
                chord_count += 1

        return (chord_count / len(words)) > 0.6
    
    def _normalize_chord(self, chord_text: str) -> str:
        """Normalize chord text by removing spaces between chord and number"""
        # Handle spaced numbered chords like "H 7" -> "H7"
        import re
        # Match chord letter(s) followed by space and number
        normalized = re.sub(r'([A-H][a-z]*)\s+(\d+)', r'\1\2', chord_text)
        return normalized

    def _looks_like_spanish_chord(self, word: str) -> bool:
        """Check if word looks like a Spanish chord (DO, Re-, Mi–, Fa#, Sol7, etc.) or chord chain"""
        word_clean = word.strip()

        # Handle chord chains with pipes (e.g., "Do |Mi |Fa")
        if '|' in word_clean:
            # Split by pipes and check if all parts are chords
            pipe_parts = [part.strip() for part in word_clean.split('|')]
            return all(self._looks_like_spanish_chord(part) for part in pipe_parts if part)

        # Check against Spanish chord list from config
        if hasattr(self.config, 'chord_letters') and word_clean in self.config.chord_letters:
            return True

        # Common Spanish chord patterns
        spanish_chord_patterns = [
            r'^(DO|Do|Re|Mi|Fa|Sol|La|Si)([#b]?)([–\-]?)(\d*)$',  # Basic Spanish chords
            r'^(DO|Do|Re|Mi|Fa|Sol|La|Si)([#b]?)([–\-]?)(7|6|9|maj7|dim|aum)$',  # With extensions
        ]

        import re
        for pattern in spanish_chord_patterns:
            if re.match(pattern, word_clean):
                return True

        return False

    def _looks_like_chord(self, word: str) -> bool:
        """Check if a word looks like a chord"""
        # First normalize the word (handle "H 7" -> "H7")
        normalized_word = self._normalize_chord(word)

        if normalized_word in self.config.valid_chords:
            return True

        # Check for compound chords
        if ' ' in word:
            parts = word.split()
            return any(self._normalize_chord(part) in self.config.valid_chords for part in parts)

        if len(word) > 1:
            for i in range(1, len(word)):
                left_part = word[:i]
                right_part = word[i:]
                if (self._normalize_chord(left_part) in self.config.valid_chords and
                    self._normalize_chord(right_part) in self.config.valid_chords):
                    return True

        return False
    
    def _is_title_line(self, text: str, font_size: float, is_pink: bool, color: int = 0) -> bool:
        """Check if line is a title based on content, font size, and color"""
        text_clean = text.strip()

        # Italian-specific title detection
        if self.config.language_code == "it":
            # Italian titles: red color (14355506), size ~14.9, uppercase
            is_red = abs(color - 14355506) < 100000  # Italian red color
            is_large = abs(font_size - 14.9) < 2.0   # Italian title size
            is_uppercase = text_clean.isupper()
            is_reasonable_length = len(text_clean) > 5

            return is_red and is_large and is_uppercase and is_reasonable_length

        # Enhanced title detection for other languages
        import re

        # Remove biblical references and parentheses content for uppercase check
        # Handle various formats:
        # - "TITLE - Ps 83 (84)"
        # - "TITLE - Tobijev hvalospev (Tob 13) *"
        # - "TITLE - Mt 5,1-12"
        text_for_case_check = re.sub(r'\s*-\s*[A-Za-z][^(]*(\([^)]*\))?[^A-Z]*$', '', text_clean)
        text_for_case_check = re.sub(r'\([^)]*\)', '', text_for_case_check).strip()

        # Check if the main part is mostly uppercase
        if text_for_case_check:
            uppercase_chars = sum(1 for c in text_for_case_check if c.isupper())
            lowercase_chars = sum(1 for c in text_for_case_check if c.islower())
            total_letters = uppercase_chars + lowercase_chars

            if total_letters > 0:
                uppercase_ratio = uppercase_chars / total_letters
                is_mostly_uppercase = uppercase_ratio >= 0.7  # At least 70% uppercase
            else:
                is_mostly_uppercase = True  # No letters, consider as valid
        else:
            is_mostly_uppercase = text_clean.isupper()

        # Title criteria: mostly uppercase, reasonable length, larger font
        # Language-specific color requirements:
        # - Croatian: Pink color required (is_pink)
        # - Slovenian: Pink color preferred but not required
        # - Spanish: Red color + bold + large font (15.2pt)
        color_requirement = True  # Default: no color requirement
        font_size_requirement = 12.0  # Default font size

        if self.config.language_code == "hr":
            color_requirement = is_pink  # Croatian requires pink
            font_size_requirement = 12.0
        elif self.config.language_code == "sl":
            color_requirement = True  # Slovenian doesn't require pink
            font_size_requirement = 12.0
        elif self.config.language_code == "es":
            # Spanish: Pure Red + Bold + Large font (15.2pt)
            is_red = self._is_red_color(color)
            color_requirement = is_red  # Spanish titles are pure red, not pink
            font_size_requirement = 15.0  # Spanish titles are much larger

            # Debug Spanish title detection
            self.logger.debug(f"🔍 Spanish title check: '{text_clean[:30]}...' | "
                            f"font_size: {font_size:.1f} (req: {font_size_requirement}) | "
                            f"is_red: {is_red} | is_pink: {is_pink} | uppercase: {is_mostly_uppercase} | "
                            f"len: {len(text_clean)}")

        is_title = (is_mostly_uppercase and
                   len(text_clean) > 4 and
                   font_size >= font_size_requirement and
                   color_requirement and
                   not any(role in text_clean for role in self.config.role_markers) and
                   not self._is_chord_line_text(text_clean) and
                   'kapodaster' not in text_clean.lower() and
                   'cejilla' not in text_clean.lower())  # Spanish capodaster term

        # Debug output for Spanish
        if self.config.language_code == "es":
            self.logger.debug(f"🔍 Spanish title result: {is_title} for '{text_clean[:30]}...'")

        return is_title
    
    def _is_kapodaster_line(self, text: str, is_pink: bool) -> bool:
        """Check if line is kapodaster based on content and color"""
        text_lower = text.strip().lower()
        return (is_pink and
                ('kapodaster' in text_lower or 'kapo' in text_lower))
    
    def _is_comment_line(self, text: str, is_pink: bool) -> bool:
        """Enhanced comment detection based on content and color"""
        text_clean = text.strip()
        
        # Pink text in parentheses = comment
        if (is_pink and
            text_clean.startswith('(') and
            text_clean.endswith(')')):
            return True
        
        # Continuation of parentheses comment
        if text_clean.startswith('bez:'):
            return True
        
        # Only catch ending ')' if it's clearly a continuation comment, not a title
        if (text_clean.endswith(')') and
            'blagoslovljen' in text_clean.lower() and
            not text_clean.startswith('SVET')):
            return True
        
        # Starts with * or ** (usually under horizontal line)
        if text_clean.startswith('*') and ('zbor' in text_clean.lower() or 'odgovara' in text_clean.lower()):
            return True
        
        return False
    
    def _combine_chord_lines_by_y_position(self, chord_lines: List[Dict]) -> List[Dict]:
        """Combine chord lines that are on the same Y position into single chord lines"""
        if not chord_lines:
            return []
        
        # Group chord lines by Y position (with small tolerance for floating point differences)
        y_groups = {}
        for chord_line in chord_lines:
            y_pos = chord_line['y']
            
            # Find existing group with similar Y position (within 1 pixel tolerance)
            found_group = None
            for existing_y in y_groups.keys():
                if abs(y_pos - existing_y) < 1.0:
                    found_group = existing_y
                    break
            
            if found_group is not None:
                y_groups[found_group].append(chord_line)
            else:
                y_groups[y_pos] = [chord_line]
        
        # Combine chord lines in each Y group
        combined_lines = []
        for y_pos, group_lines in y_groups.items():
            if len(group_lines) == 1:
                # Single chord line, use as-is
                combined_lines.append(group_lines[0])
            else:
                # Multiple chord lines at same Y position - combine them
                combined_line = self._merge_chord_lines_at_same_y(group_lines, y_pos)
                combined_lines.append(combined_line)
        
        return combined_lines

    def _combine_spanish_chord_spaced_lines(self, text_lines: List[Dict]) -> List[Dict]:
        """Combine Spanish text lines that are separated by chord chain spacing"""
        if not text_lines:
            return []



        # Group text lines by Y position (with small tolerance)
        y_groups = {}
        for i, text_line in enumerate(text_lines):
            y_pos = text_line['y']

            # Find existing group with similar Y position (within 5 pixels tolerance for Spanish)
            found_group = None
            for existing_y in y_groups.keys():
                if abs(y_pos - existing_y) < 5.0:  # Larger tolerance for Spanish chord spacing
                    found_group = existing_y
                    break

            if found_group is not None:
                y_groups[found_group].append(text_line)
            else:
                y_groups[y_pos] = [text_line]

        # Process each Y group to combine chord-spaced lines
        combined_lines = []
        for y_pos, group_lines in y_groups.items():
            if len(group_lines) == 1:
                # Single line, use as-is
                combined_lines.append(group_lines[0])
            else:
                # Multiple lines at same Y - check if they should be combined
                merge_result = self._merge_spanish_chord_spaced_lines(group_lines, y_pos)
                if merge_result:
                    if isinstance(merge_result, list):
                        # Multiple lines returned (role markers + combined text)
                        combined_lines.extend(merge_result)
                    else:
                        # Single combined line returned
                        combined_lines.append(merge_result)
                else:
                    # If no combining needed, add all lines individually
                    combined_lines.extend(group_lines)

        return combined_lines

    def _merge_spanish_chord_spaced_lines(self, text_lines: List[Dict], y_pos: float) -> Optional[Dict]:
        """Merge Spanish text lines that are separated by chord chain spacing"""
        if len(text_lines) < 2:
            return None



        # Sort by X position (left to right)
        sorted_lines = sorted(text_lines, key=lambda x: x['x_start'])

        # Separate role markers from combinable text lines
        role_markers = []
        combinable_lines = []

        for line in sorted_lines:
            text = line['text'].strip()
            # Identify role markers (S., A., etc.) - they should be preserved separately
            if len(text) <= 3 and text.endswith('.') and text[:-1].isalpha():
                role_markers.append(line)
            else:
                combinable_lines.append(line)

        # Only combine if we have multiple combinable text lines
        if len(combinable_lines) < 2:
            return None  # No combination possible

        # For Spanish chord spacing: if we have multiple text lines at same Y, combine them
        # This handles cases like "Ave" and "María," being split due to chord chain spacing

        # Combine the combinable text lines with single space separation
        combined_text_parts = []
        combined_x_start = combinable_lines[0]['x_start']

        for line in combinable_lines:
            text = line['text'].strip()
            if text:
                combined_text_parts.append(text)

        # Join with single space (simpler than trying to calculate exact spacing)
        combined_text = ' '.join(combined_text_parts)

        # Calculate combined width
        last_line = combinable_lines[-1]
        combined_width = (last_line['x_start'] + last_line['width']) - combined_x_start

        # Create combined line with all required fields
        combined_line = {
            'text': combined_text,
            'text_content': combined_text.strip(),  # Required field!
            'x_start': combined_x_start,
            'x_end': last_line['x_start'] + last_line['width'],
            'y': y_pos,
            'width': combined_width,
            'font_size': combinable_lines[0]['font_size'],
            'font_name': combinable_lines[0]['font_name'],
            'color': combinable_lines[0]['color'],
            'is_pink': combinable_lines[0].get('is_pink', False),
            'page_num': combinable_lines[0].get('page_num', 0),
            'original_y': combinable_lines[0].get('original_y', y_pos),
            'spans': combinable_lines[0].get('spans', [])  # Keep spans if available
        }



        # Return both role markers and the combined text line
        # Role markers should come first (they're typically at the left)
        result_lines = role_markers + [combined_line]
        return result_lines

    def _combine_quote_mark_lines(self, text_lines: List[Dict]) -> List[Dict]:
        """Combine consecutive quote mark lines at the same Y position into single lines"""
        if not text_lines:
            return []

        # Group text lines by Y position (with small tolerance)
        y_groups = {}
        for text_line in text_lines:
            y_pos = text_line['y']

            # Find existing group with similar Y position (within 1 pixel tolerance)
            found_group = None
            for existing_y in y_groups.keys():
                if abs(y_pos - existing_y) < 1.0:
                    found_group = existing_y
                    break

            if found_group is not None:
                y_groups[found_group].append(text_line)
            else:
                y_groups[y_pos] = [text_line]

        # Process each Y group to combine quote marks
        combined_lines = []
        for y_pos, group_lines in y_groups.items():
            if len(group_lines) == 1:
                # Single line, use as-is
                combined_lines.append(group_lines[0])
            else:
                # Multiple lines at same Y - check if we need to combine quote marks
                combined_line = self._merge_quote_marks_at_same_y(group_lines, y_pos)
                if combined_line:
                    combined_lines.append(combined_line)
                    self.logger.debug(f"📝 Combined quote line at Y={y_pos:.1f}: '{combined_line['text'].strip()}'")
                else:
                    # If no combining needed, add all lines individually
                    combined_lines.extend(group_lines)

        return combined_lines

    def _merge_quote_marks_at_same_y(self, text_lines: List[Dict], y_pos: float) -> Optional[Dict]:
        """Merge quote marks and text at the same Y position into a single line"""
        # Sort by X position
        sorted_lines = sorted(text_lines, key=lambda x: x['x_start'])

        # Check if we have quote marks followed by actual text
        quote_marks = []
        text_content = []

        for line in sorted_lines:
            text = line['text'].strip()
            if text == '"':
                quote_marks.append(line)
            else:
                text_content.append(line)

        # If we have quote marks and text content, combine them
        if quote_marks and text_content:
            # Get the actual text content
            actual_text = ' '.join(line['text'].strip() for line in text_content)

            # Calculate the width that quotes should occupy
            # This should match the width of the repeated text from the first line
            # For liturgical texts, this is typically the opening phrase

            # Estimate the repeated text length based on common liturgical patterns
            # For Croatian: "Za grijehe, koje smo počinili" ≈ 30 characters
            # For Slovenian: "Za grehe, ki smo jih storili" ≈ 28 characters

            num_quotes = len(quote_marks)
            if num_quotes > 1:
                # Calculate spacing to match the repeated text width
                # "Za grijehe, koje smo počinili" is about 30 characters
                # We want quotes to span this width before the actual text starts

                if num_quotes == 2:
                    # Two quotes: start and middle of repeated text
                    combined_text = f'"              "               {actual_text}'
                elif num_quotes == 3:
                    # Three quotes: start, 1/3, 2/3 of repeated text
                    combined_text = f'"          "          "          {actual_text}'
                elif num_quotes == 4:
                    # Four quotes: evenly distributed across repeated text width
                    combined_text = f'"        "        "        "        {actual_text}'
                elif num_quotes == 5:
                    # Five quotes: distributed across repeated text width
                    combined_text = f'"      "      "      "      "      {actual_text}'
                else:
                    # More than 5 quotes: compact but still spanning the repeated text
                    quote_spacing = "    "  # 4 spaces between quotes
                    quotes_str = quote_spacing.join(['"'] * num_quotes)
                    combined_text = f"{quotes_str}    {actual_text}"
            else:
                # Single quote case - quote represents the entire repeated text
                combined_text = f'"                               {actual_text}'

            # Use the position of the first quote mark
            first_quote = quote_marks[0]
            return {
                'text': combined_text,
                'text_content': actual_text,  # Store clean text content
                'x_start': first_quote['x_start'],
                'x_end': max(line['x_end'] for line in sorted_lines),
                'width': max(line['x_end'] for line in sorted_lines) - first_quote['x_start'],
                'y': y_pos,
                'font_size': first_quote['font_size'],
                'color': first_quote.get('color', 0),
                'is_pink': first_quote.get('is_pink', False),
                'font_name': first_quote.get('font_name', ''),
                'page_num': first_quote.get('page_num', 0),
                'original_y': first_quote.get('original_y', y_pos)
            }

        # If no quote marks to combine, return None (use original lines)
        return None

    def find_chord_positions_in_span(self, chord_span_text: str, chord_span_start: float, chord_span_width: float) -> List[Tuple[str, float]]:
        """Find individual chord positions within the chord span - enhanced for Spanish spaced chords"""
        chord_positions = []

        # Spanish-specific handling for spaced chord extensions
        if self.config.language_code == "es":
            return self._find_spanish_chord_positions(chord_span_text, chord_span_start, chord_span_width)

        # Italian-specific handling for spaced chord extensions
        if self.config.language_code == "it":
            return self._find_italian_chord_positions(chord_span_text, chord_span_start, chord_span_width)

        # First normalize the entire chord span text to handle spaced chords
        normalized_chord_text = self._normalize_chord(chord_span_text)

        # Parse chords from the normalized span text
        words = normalized_chord_text.split()
        current_pos = 0

        for word in words:
            if self._looks_like_chord(word):
                # We need to map back to the original text position
                word_start_in_text = chord_span_text.find(word, current_pos)

                # If direct match fails, try to find the chord pattern in original text
                if word_start_in_text == -1:
                    # Handle case where normalized chord (e.g., "H7") doesn't exist in original ("H 7")
                    # Look for the base chord letter(s) in the original text
                    import re
                    base_chord = re.match(r'([A-H][a-z]*)', word)
                    if base_chord:
                        base_chord_text = base_chord.group(1)
                        word_start_in_text = chord_span_text.find(base_chord_text, current_pos)

                if word_start_in_text != -1:
                    # Calculate proportional position within the span
                    proportional_pos = word_start_in_text / len(chord_span_text) if len(chord_span_text) > 0 else 0
                    pixel_pos = chord_span_start + (proportional_pos * chord_span_width)

                    # Use the normalized chord name for output
                    normalized_word = self._normalize_chord(word)
                    chord_positions.append((normalized_word, pixel_pos))
                    self.logger.debug(f"      🎸 Found chord '{normalized_word}' (from '{word}') at text_pos={word_start_in_text}, pixel_x={pixel_pos:.1f}")

                    current_pos = word_start_in_text + len(word)

        return chord_positions

    def _find_spanish_chord_positions(self, chord_span_text: str, chord_span_start: float, chord_span_width: float) -> List[Tuple[str, float]]:
        """Find Spanish chord positions, handling spaced extensions and chord chains"""
        chord_positions = []
        text = chord_span_text.strip()

        if not text:
            return chord_positions

        # Handle chord chains with pipes (e.g., "Do |Mi |Fa", "Do |Mi |Fa Mi")
        if '|' in text:
            # For chord chains, treat the entire line as a single chord unit
            proportional_pos = 0  # Start at the beginning
            pixel_pos = chord_span_start

            chord_positions.append((text, pixel_pos))
            self.logger.debug(f"      🎸 Spanish chord chain '{text}' at pixel_x={pixel_pos:.1f}")
            return chord_positions

        # Handle spaced chord extensions (e.g., "Mi– 6", "Re– 9")
        import re

        # Pattern for Spanish chord with optional spaced extension
        # Matches: Mi–, Mi– 6, Re–, Re– 9, Sol7, La, etc.
        spanish_chord_pattern = r'((?:DO|Do|Re|Mi|Fa|Sol|La|Si)(?:[#b]?)(?:[–\-]?))\s*(\d+|maj7|dim|aum)?'

        current_pos = 0

        # Find all chord matches in the text
        for match in re.finditer(spanish_chord_pattern, text):
            base_chord = match.group(1)  # e.g., "Mi–"
            extension = match.group(2)   # e.g., "6"

            # Combine base chord with extension
            if extension:
                full_chord = f"{base_chord} {extension}".strip()
                # Also try without space for normalization
                normalized_chord = f"{base_chord}{extension}"
            else:
                full_chord = base_chord
                normalized_chord = base_chord

            # Check if this looks like a valid Spanish chord
            if self._looks_like_spanish_chord(base_chord):
                # Calculate position in the original text
                match_start = match.start()

                # Calculate proportional position within the span
                proportional_pos = match_start / len(text) if len(text) > 0 else 0
                pixel_pos = chord_span_start + (proportional_pos * chord_span_width)

                # Use the full chord name (with extension)
                chord_positions.append((full_chord, pixel_pos))
                self.logger.debug(f"      🎸 Spanish chord '{full_chord}' (normalized: '{normalized_chord}') at text_pos={match_start}, pixel_x={pixel_pos:.1f}")

        # If no Spanish chord patterns found, fall back to word-by-word analysis
        if not chord_positions:
            words = text.split()
            current_pos = 0

            i = 0
            while i < len(words):
                word = words[i]

                # Check if current word is a Spanish chord base
                if self._looks_like_spanish_chord(word):
                    full_chord = word

                    # Check if next word is an extension
                    if i + 1 < len(words):
                        next_word = words[i + 1]
                        if next_word.isdigit() or next_word in ['maj7', 'dim', 'aum']:
                            full_chord = f"{word} {next_word}"
                            i += 1  # Skip the extension word in next iteration

                    # Find position in original text
                    word_start = text.find(word, current_pos)
                    if word_start != -1:
                        proportional_pos = word_start / len(text) if len(text) > 0 else 0
                        pixel_pos = chord_span_start + (proportional_pos * chord_span_width)

                        chord_positions.append((full_chord, pixel_pos))
                        self.logger.debug(f"      🎸 Spanish chord '{full_chord}' at text_pos={word_start}, pixel_x={pixel_pos:.1f}")

                        current_pos = word_start + len(full_chord)

                i += 1

        return chord_positions

    def map_chord_to_verse_position(self, chord_pixel_x: float, chord_span_start: float, chord_span_width: float,
                                   verse_text: str, verse_span_start: float, verse_span_width: float, font_size: float) -> int:
        """Map chord pixel position to verse character position using direct pixel mapping"""

        # Map chord position directly to verse span, not via chord span proportions
        # Calculate proportional position of chord within the verse span
        if verse_span_width == 0:
            return 0

        # Clamp chord position to verse span boundaries
        chord_x_clamped = max(verse_span_start, min(chord_pixel_x, verse_span_start + verse_span_width))

        # Calculate proportional position within verse span
        proportional_pos = (chord_x_clamped - verse_span_start) / verse_span_width

        # The target pixel position is the clamped chord position
        verse_pixel_x = chord_x_clamped

        self.logger.debug(f"      🎯 Chord at x={chord_pixel_x:.1f} -> clamped_x={chord_x_clamped:.1f} -> proportion={proportional_pos:.3f}")

        # Convert verse pixel position to character position using Arial font metrics
        current_pixel = verse_span_start
        char_position = 0

        for i, char in enumerate(verse_text):
            char_width = self.get_char_width(char, font_size)
            char_center = current_pixel + (char_width / 2)

            if verse_pixel_x <= char_center:
                char_position = i
                break

            current_pixel += char_width
            char_position = i + 1

        # Ensure position is within bounds
        char_position = max(0, min(char_position, len(verse_text)))

        char_at_pos = verse_text[char_position] if char_position < len(verse_text) else 'END'
        self.logger.debug(f"      📍 Mapped to char_pos={char_position} ('{char_at_pos}')")

        return char_position
    
    def _merge_chord_lines_at_same_y(self, chord_lines: List[Dict], y_pos: float) -> Dict:
        """Merge multiple chord lines at the same Y position into a single chord line"""
        # Sort by X position
        sorted_lines = sorted(chord_lines, key=lambda x: x['x_start'])
        
        # Find the overall bounding box
        min_x = min(line['x_start'] for line in sorted_lines)
        max_x = max(line['x_end'] for line in sorted_lines)
        
        # Create combined text by positioning each chord at its correct X position
        combined_text = ""
        current_x = min_x
        
        for line in sorted_lines:
            # Add spaces to reach the chord position
            spaces_needed = max(0, int((line['x_start'] - current_x) / 6))  # Approximate character width
            combined_text += " " * spaces_needed
            combined_text += line['text'].strip()
            current_x = line['x_end']
        
        # Create the combined chord line data
        return {
            'text': combined_text,
            'text_content': combined_text.strip(),
            'x_start': min_x,
            'x_end': max_x,
            'width': max_x - min_x,
            'y': y_pos,
            'font_size': sorted_lines[0]['font_size'],
            'color': sorted_lines[0]['color'],
            'is_pink': sorted_lines[0]['is_pink'],
            'font_name': sorted_lines[0]['font_name'],
            'spans': [span for line in sorted_lines for span in line.get('spans', [])]
        }

    def _is_bold_font(self, font_name: str) -> bool:
        """Check if font name indicates bold formatting"""
        if not font_name:
            return False

        font_lower = font_name.lower()
        bold_indicators = ['bold', 'black', 'heavy', 'semibold', 'demibold', 'extrabold']

        return any(indicator in font_lower for indicator in bold_indicators)

    def _find_italian_chord_positions(self, chord_span_text: str, chord_span_start: float, chord_span_width: float) -> List[Tuple[str, float]]:
        """Find Italian chord positions, handling spaced extensions like 'La m', 'Re m 9', '(Sol 7)'"""
        chord_positions = []
        text = chord_span_text.strip()

        if not text:
            return chord_positions

        # Handle chords in parentheses: "(Sol 7)" -> keep as single unit
        if text.startswith('(') and text.endswith(')'):
            # Treat entire parentheses content as one chord
            proportional_pos = 0  # Start at the beginning
            pixel_pos = chord_span_start
            chord_positions.append((text, pixel_pos))
            self.logger.debug(f"      🎸 Italian parentheses chord '{text}' at pixel_x={pixel_pos:.1f}")
            return chord_positions

        # Handle spaced chord extensions (e.g., "La m", "Re m 9", "Sol 7")
        import re

        # Pattern for Italian chord with optional spaced extension
        # Matches: La, La m, Re m 9, Sol 7, Do maj7, etc.
        italian_chord_pattern = r'((?:Do|Re|Mi|Fa|Sol|La|Si)(?:[#b]?))\s*(m)?\s*(\d+|maj7|dim|aug)?'

        current_pos = 0

        # Find all chord matches in the text
        for match in re.finditer(italian_chord_pattern, text):
            base_chord = match.group(1)  # e.g., "La"
            minor = match.group(2)       # e.g., "m"
            extension = match.group(3)   # e.g., "9"

            # Combine base chord with minor and extension
            full_chord = base_chord
            if minor:
                full_chord += f" {minor}"
            if extension:
                full_chord += f" {extension}"

            # Check if this looks like a valid Italian chord
            if self._looks_like_italian_chord(base_chord):
                # Calculate position in the original text
                match_start = match.start()

                # Calculate proportional position within the span
                proportional_pos = match_start / len(text) if len(text) > 0 else 0
                pixel_pos = chord_span_start + (proportional_pos * chord_span_width)

                # Use the full chord name (with extension)
                chord_positions.append((full_chord.strip(), pixel_pos))
                self.logger.debug(f"      🎸 Italian chord '{full_chord.strip()}' at text_pos={match_start}, pixel_x={pixel_pos:.1f}")

        # If no Italian chord patterns found, fall back to word-by-word analysis
        if not chord_positions:
            words = text.split()
            current_pos = 0

            for i, word in enumerate(words):
                if self._looks_like_italian_chord(word):
                    # Calculate position for this word
                    proportional_pos = current_pos / len(text) if len(text) > 0 else 0
                    pixel_pos = chord_span_start + (proportional_pos * chord_span_width)

                    chord_positions.append((word, pixel_pos))
                    self.logger.debug(f"      🎸 Italian fallback chord '{word}' at pixel_x={pixel_pos:.1f}")

                # Update position for next word
                current_pos += len(word)
                if i < len(words) - 1:  # Add space if not last word
                    current_pos += 1

        return chord_positions

    def _looks_like_italian_chord(self, text: str) -> bool:
        """Check if text looks like an Italian chord"""
        if not text:
            return False

        # Italian chord roots
        italian_roots = ['Do', 'Re', 'Mi', 'Fa', 'Sol', 'La', 'Si']

        # Check for basic Italian chord pattern
        for root in italian_roots:
            if text.startswith(root):
                return True

        return False
