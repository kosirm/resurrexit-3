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
                        if self._is_chord_line_text(line_text):
                            chord_lines.append(line_data)
                            self.logger.debug(f"🎼 Chord line (page {page_num + 1}): '{line_text.strip()}' (pink: {is_pink}, size: {font_size:.1f})")
                        
                        elif self._is_title_line(line_text, font_size, is_pink):
                            title_lines.append(line_data)
                            self.logger.debug(f"📋 Title line (page {page_num + 1}): '{line_text.strip()}' (pink: {is_pink}, size: {font_size:.1f})")
                        
                        elif self._is_kapodaster_line(line_text, is_pink):
                            kapodaster_lines.append(line_data)
                            self.logger.debug(f"🎸 Kapodaster line (page {page_num + 1}): '{line_text.strip()}' (pink: {is_pink}, size: {font_size:.1f})")
                        
                        elif self._is_comment_line(line_text, is_pink):
                            comment_lines.append(line_data)
                            self.logger.debug(f"💬 Comment line (page {page_num + 1}): '{line_text.strip()}' (pink: {is_pink}, size: {font_size:.1f})")
                        
                        else:
                            # Regular text line (verses, role markers)
                            # Handle role markers and text content
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
                            self.logger.debug(f"📝 Text line{role_info} (page {page_num + 1}): '{line_text.strip()[:50]}...' (size: {font_size:.1f})")
        
        doc.close()
        
        # Combine chord lines that are on the same Y position
        combined_chord_lines = self._combine_chord_lines_by_y_position(chord_lines)

        # Combine consecutive quote mark lines (fix for Slovenian quote parsing)
        combined_text_lines = self._combine_quote_mark_lines(text_lines)

        result = {
            'chord_lines': combined_chord_lines,
            'text_lines': combined_text_lines,
            'title_lines': title_lines,
            'kapodaster_lines': kapodaster_lines,
            'comment_lines': comment_lines
        }
        
        self.logger.info(f"Extracted spans: {len(combined_chord_lines)} chord lines, {len(text_lines)} text lines, {len(title_lines)} titles")
        return result
    
    def _is_pink_color(self, color: int) -> bool:
        """Check if color is pink/magenta (used for titles, kapodaster, comments)"""
        return color in self.pink_colors
    
    def _is_chord_line_text(self, text: str) -> bool:
        """Check if text line contains primarily chords"""
        words = text.split()
        if not words:
            return False

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
    
    def _is_title_line(self, text: str, font_size: float, is_pink: bool) -> bool:
        """Check if line is a title based on content, font size, and color"""
        text_clean = text.strip()

        # Enhanced title detection
        import re

        # Remove biblical references and parentheses content for uppercase check
        text_for_case_check = re.sub(r'\s*-\s*[A-Z][a-z]+\s*\d+[^)]*(\([^)]*\))?', '', text_clean)
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
        color_requirement = True  # Default: no color requirement
        if self.config.language_code == "hr":
            color_requirement = is_pink  # Croatian requires pink
        elif self.config.language_code == "sl":
            color_requirement = True  # Slovenian doesn't require pink

        return (is_mostly_uppercase and
                len(text_clean) > 4 and
                font_size >= 12.0 and
                color_requirement and
                not any(role in text_clean for role in self.config.role_markers) and
                not self._is_chord_line_text(text_clean) and
                'kapodaster' not in text_clean.lower())
    
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
        """Find individual chord positions within the chord span"""
        chord_positions = []

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
