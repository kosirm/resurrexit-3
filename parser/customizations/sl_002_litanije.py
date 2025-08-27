"""
Customization for SL - 002.pdf (SPOKORNE LITANIJE)

This file has quotes in separate spans that should be removed from continuation lines.
The original Slovenian parser handles this by simply removing quotes from continuation lines.
"""

from typing import Dict, List
from .base_customization import BaseCustomization
import re


class SL002LitanijeCustomization(BaseCustomization):
    """Customization for Slovenian Litanies file SL - 002.pdf"""
    
    def __init__(self):
        super().__init__("sl")
    
    def applies_to_file(self, filename: str) -> bool:
        """Check if this applies to SL - 002.pdf"""
        return "SL - 002" in filename or "sl - 002" in filename.lower()
    
    def customize_verse_text(self, text: str, line_data: Dict) -> str:
        """Remove quotes from continuation lines in Slovenian litanies"""
        clean_text = text.strip()
        
        # Remove leading quotes and spaces for continuation lines
        # This matches the original Slovenian parser logic
        if clean_text.startswith('""'):
            clean_text = clean_text.replace('""', '').strip()
            clean_text = clean_text.replace('"', '').strip()
        elif clean_text.startswith('"'):
            # Also handle single quotes
            clean_text = clean_text.replace('"', '').strip()
        
        return clean_text
    
    def customize_span_data(self, span_data: Dict) -> Dict:
        """Customize the extracted span data before parsing"""
        # The asterisk comments are probably in text_lines, not comment_lines
        # We need to find them and move them to comment_lines
        text_lines = span_data['text_lines']
        comment_lines = span_data['comment_lines']

        # Find asterisk comments in text lines and move them to comment lines
        new_text_lines = []
        new_comment_lines = list(comment_lines)  # Copy existing comment lines

        # Group text lines by Y position to find asterisk comments
        asterisk_comments = self._extract_asterisk_comments_from_text_lines(text_lines)

        # Add the combined asterisk comments to comment lines
        new_comment_lines.extend(asterisk_comments['comment_lines'])

        # Keep only non-asterisk text lines
        new_text_lines = asterisk_comments['remaining_text_lines']

        span_data['text_lines'] = new_text_lines
        span_data['comment_lines'] = new_comment_lines

        return span_data

    def _extract_asterisk_comments_from_text_lines(self, text_lines: List[Dict]) -> Dict:
        """Extract asterisk comments from text lines and combine them"""
        if not text_lines:
            return {'comment_lines': [], 'remaining_text_lines': text_lines}

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

        # Process each Y group to find and combine asterisk comments
        comment_lines = []
        remaining_text_lines = []

        for y_pos, group_lines in y_groups.items():
            # Check if this Y group contains asterisk comments
            asterisk_comment = self._check_for_asterisk_comment_in_group(group_lines, y_pos)

            if asterisk_comment:
                # This group forms an asterisk comment
                comment_lines.append(asterisk_comment)
            else:
                # This group contains regular text lines
                remaining_text_lines.extend(group_lines)

        return {
            'comment_lines': comment_lines,
            'remaining_text_lines': remaining_text_lines
        }

    def _check_for_asterisk_comment_in_group(self, group_lines: List[Dict], y_pos: float) -> Dict:
        """Check if a group of lines at the same Y position forms an asterisk comment"""
        # Sort by X position
        sorted_lines = sorted(group_lines, key=lambda x: x['x_start'])

        # Check if we have asterisk markers and text content
        asterisk_markers = []
        text_content = []

        for line in sorted_lines:
            text = line['text'].strip()
            if text in ['*', '**']:
                asterisk_markers.append(line)
            elif text and not text.startswith('"'):  # Exclude quote lines
                text_content.append(line)

        # If we have asterisk markers and text content, this is an asterisk comment
        if asterisk_markers and text_content:
            # Get the asterisk marker and actual text content
            asterisk_text = asterisk_markers[0]['text'].strip()  # * or **
            actual_text = ' '.join(line['text'].strip() for line in text_content)

            # Create combined comment text with proper spacing
            combined_text = f"{asterisk_text}  {actual_text}"

            # Use the position of the first asterisk marker
            first_asterisk = asterisk_markers[0]
            return {
                'text': combined_text,
                'x_start': first_asterisk['x_start'],
                'x_end': max(line['x_end'] for line in sorted_lines),
                'width': max(line['x_end'] for line in sorted_lines) - first_asterisk['x_start'],
                'y': y_pos,
                'font_size': first_asterisk['font_size'],
                'color': first_asterisk.get('color', 0),
                'is_pink': first_asterisk.get('is_pink', False),
                'font_name': first_asterisk.get('font_name', ''),
                'page_num': first_asterisk.get('page_num', 0),
                'original_y': first_asterisk.get('original_y', y_pos)
            }

        # Not an asterisk comment
        return None

    def customize_text_lines(self, text_lines: List[Dict]) -> List[Dict]:
        """Combine quote marks that are in separate spans (Slovenian PDF format)"""
        # First, combine quote marks that are on the same Y position
        combined_lines = self._combine_quote_marks_by_y(text_lines)
        return combined_lines

    # Note: The old _combine_asterisk_comments_by_y method is no longer needed
    # since we now extract asterisk comments directly from text lines

    def _combine_quote_marks_by_y(self, text_lines: List[Dict]) -> List[Dict]:
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
            # Create combined text: spread quotes across expected width + actual text
            actual_text = ' '.join(line['text'].strip() for line in text_content)

            # Calculate spacing to spread quotes across reasonable width
            # "Za grehe, ki smo jih storili" = 28 characters (Slovenian)
            num_quotes = len(quote_marks)
            if num_quotes > 1:
                # Create spaced quotes like: "       "         "      "         "      text"
                quote_spacing = "       "  # 7 spaces between quotes
                quotes_str = quote_spacing.join(['"'] * num_quotes)
                combined_text = f"{quotes_str}      {actual_text}"  # 6 spaces before text
            else:
                combined_text = f'"       {actual_text}'  # Single quote case

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
    
    def get_description(self) -> str:
        """Get description of this customization"""
        return "SL-002 Slovenian Litanies: Remove quotes from continuation lines"


# Register this customization
from .base_customization import customization_manager
customization_manager.register_customization(SL002LitanijeCustomization())
