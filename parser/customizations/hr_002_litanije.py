"""
Customization for HR - 002.pdf (POKORNIČKE LITANIJE)

This file has a special liturgical format where quotes represent repeated text:
"Za grijehe, koje smo počinili" is repeated in each line, represented by quotes.

The quotes should be spaced to occupy the same width as the repeated text.
"""

from typing import Dict, List, Any
from .base_customization import BaseCustomization
import re


class HR002LitanijeCustomization(BaseCustomization):
    """Customization for Croatian Litanies file HR - 002.pdf"""

    def __init__(self):
        super().__init__("hr")
        self.repeated_text = "Za grijehe, koje smo počinili"
        self.repeated_text_length = len(self.repeated_text)

    def customize_verse_text(self, text: str, line_data: Dict) -> str:
        """For Croatian litanies, preserve original spacing from PDF"""
        # The key insight: we need to return the ORIGINAL text from line_data, not the processed text
        original_text = line_data.get('text', text)
        print(f"DEBUG HR002: input text: '{text}'")
        print(f"DEBUG HR002: original text: '{original_text}'")
        print(f"DEBUG HR002: returning: '{original_text}'")
        return original_text
    
    def applies_to_file(self, filename: str) -> bool:
        """Check if this applies to HR - 002.pdf"""
        return "HR - 002" in filename or "hr - 002" in filename.lower()
    
    def customize_text_lines(self, text_lines: List[Dict]) -> List[Dict]:
        """For Croatian litanies, preserve original spacing from PDF"""
        # The original Croatian parser preserves the exact spacing from the PDF
        # Our job is to NOT interfere with the original text extraction
        return text_lines

    def _combine_quote_marks_by_y(self, text_lines: List[Dict]) -> List[Dict]:
        """Combine quote marks that are on the same Y position"""
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
                else:
                    # If no combining needed, add all lines individually
                    combined_lines.extend(group_lines)

        return combined_lines

    def _merge_quote_marks_at_same_y(self, text_lines: List[Dict], y_pos: float) -> Dict:
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

            # Create combined text with quotes and actual text
            num_quotes = len(quote_marks)
            quotes_str = ' '.join(['"'] * num_quotes)
            combined_text = f"{quotes_str} {actual_text}"

            print(f"DEBUG _merge_quote_marks_at_same_y:")
            print(f"  num_quotes: {num_quotes}")
            print(f"  quotes_str: '{quotes_str}'")
            print(f"  actual_text: '{actual_text}'")
            print(f"  combined_text: '{combined_text}'")

            # Use the position of the first quote mark
            first_quote = quote_marks[0]
            return {
                'text': combined_text,
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
    
    def _has_liturgical_quotes(self, text: str) -> bool:
        """Check if text has the liturgical quote pattern"""
        # Look for pattern like: " " " " " actual text
        quote_pattern = r'^(\s*"\s*){2,}\s*\w+'
        return bool(re.match(quote_pattern, text))
    
    def _format_liturgical_quotes(self, text: str) -> str:
        """Format quotes to occupy the space of repeated text"""
        # Count the quotes
        quote_count = text.count('"')

        # Extract the actual text after quotes
        # Remove all quotes and extra spaces, then get the remaining text
        actual_text = re.sub(r'^(\s*"\s*)+', '', text).strip()

        if quote_count == 0 or not actual_text:
            return text

        # Create properly spaced quotes based on the repeated text length
        # "Za grijehe, koje smo počinili" = 30 characters
        if quote_count >= 5:
            # Five quotes distributed across the repeated text width
            formatted_quotes = '"      "      "      "      "      '
        elif quote_count == 4:
            # Four quotes evenly distributed
            formatted_quotes = '"        "        "        "        '
        elif quote_count == 3:
            # Three quotes at start, middle, end
            formatted_quotes = '"          "          "          '
        elif quote_count == 2:
            # Two quotes at start and middle
            formatted_quotes = '"              "               '
        else:
            # Single quote representing entire repeated text
            formatted_quotes = '"                               '

        return f"{formatted_quotes}{actual_text}"
    
    def customize_song(self, song) -> Any:
        """Customize the final song object"""
        # For this specific file, we need to preserve spacing in the export
        # This ensures our carefully formatted quotes don't get collapsed
        if hasattr(song, '_preserve_spacing'):
            song._preserve_spacing = True
        return song

    def get_description(self) -> str:
        """Get description of this customization"""
        return "HR-002 Croatian Litanies: Format quotes to represent repeated liturgical text"


# Register this customization
from .base_customization import customization_manager
customization_manager.register_customization(HR002LitanijeCustomization())
