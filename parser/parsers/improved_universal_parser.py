"""
Improved Universal Parser based on working Croatian/Slovenian parsers

This parser combines the best features from both working parsers while
maintaining the universal architecture for multiple languages.
"""

import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from core.models import Song, Verse, VerseLine, Comment, Chord
from core.improved_pdf_extractor import ImprovedPDFExtractor
from languages.base_language import LanguageConfig
from customizations.base_customization import customization_manager

# Import customizations to register them
try:
    import customizations.hr_002_litanije
    import customizations.sl_002_litanije
except ImportError:
    # Customizations are optional
    pass


class ImprovedUniversalParser:
    """
    Improved universal parser based on the working Croatian/Slovenian parsers.
    
    Uses span-based extraction with proper chord positioning and text classification.
    """
    
    def __init__(self, language_config: LanguageConfig):
        self.config = language_config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.pdf_extractor = ImprovedPDFExtractor(language_config)
        
        # Load customizations if available
        self.customizations = self._load_customizations()
        
        self.logger.info(f"Initialized improved {language_config.language_name} parser")
    
    def _load_customizations(self):
        """Load language-specific customizations"""
        try:
            if self.config.language_code == "sl":
                from languages.slovenian.customizations import SlovenianCustomizations
                return SlovenianCustomizations()
            elif self.config.language_code == "hr":
                from languages.croatian.customizations import CroatianCustomizations
                return CroatianCustomizations()
            elif self.config.language_code == "es":
                from languages.spanish.customizations import SpanishCustomizations
                return SpanishCustomizations()
            elif self.config.language_code == "it":
                from languages.italian.customizations import ItalianCustomizations
                return ItalianCustomizations()
            else:
                return None
        except ImportError:
            self.logger.warning(f"No customizations found for {self.config.language_code}")
            return None
    
    def parse(self, pdf_path: str, song_name: str = "") -> Song:
        """Parse PDF using improved span-based approach"""
        self.logger.info(f"Parsing PDF: {pdf_path}")

        # Get filename for customization lookup
        filename = Path(pdf_path).name

        # Check for file-specific customizations
        customization = customization_manager.get_customization_for_file(filename)
        if customization:
            self.logger.info(f"Applying customization: {customization.get_description()}")

        # Extract span data from PDF
        span_data = self.pdf_extractor.extract(pdf_path)

        # Apply customizations to span data
        if customization:
            span_data = customization.customize_span_data(span_data)
            span_data['text_lines'] = customization.customize_text_lines(span_data['text_lines'])

        # Parse into song structure using span-based positioning
        song = self._parse_with_span_positioning(span_data, song_name, customization)

        # Apply language-specific customizations
        if self.customizations:
            # Set the current file for file-specific customizations
            if hasattr(self.customizations, 'set_current_file'):
                self.customizations.set_current_file(filename)
            song.verses = self.customizations.apply_customizations(song.verses, None)

        # Apply final customizations to the song
        if customization:
            song = customization.customize_song(song)

        self.logger.info(f"Successfully parsed song: {song.title}")
        return song
    
    def _parse_with_span_positioning(self, span_data: Dict, song_name: str, customization=None) -> Song:
        """Parse using span-based positioning with enhanced classification"""
        
        chord_lines = span_data['chord_lines']
        text_lines = span_data['text_lines']
        title_lines = span_data['title_lines']
        kapodaster_lines = span_data['kapodaster_lines']
        comment_lines = span_data['comment_lines']
        
        # Extract title from title lines (should be at the top)
        title = self._extract_title_from_classified_lines(title_lines, song_name)

        # Extract subtitle lines and convert to comments (Italian-specific)
        text_lines, subtitle_comments = self._extract_subtitle_lines(text_lines)

        # Extract capo lines and convert to kapodaster (Italian-specific)
        text_lines, capo_instruction = self._extract_capo_lines(text_lines)

        # Extract kapodaster from kapodaster lines
        kapodaster = self._extract_kapodaster_from_classified_lines(kapodaster_lines)

        # Use capo instruction if no kapodaster was found
        if not kapodaster and capo_instruction:
            kapodaster = capo_instruction

        # Move inline comments from comment_lines to text_lines for proper processing
        text_lines, comment_lines = self._separate_inline_comments(text_lines, comment_lines)

        # Extract comments from comment lines (should be at the bottom)
        comments = self._extract_comments_from_classified_lines(comment_lines)

        # Add subtitle comments to the beginning of comments list
        comments = subtitle_comments + comments

        # Parse verses with span-based chord positioning (only from text_lines)
        verses = self._parse_verses_with_span_positioning(text_lines, chord_lines, customization)
        
        return Song(
            title=title,
            kapodaster=kapodaster,
            verses=verses,
            comments=comments,
            language=self.config.language_code,
            source_file=None
        )
    
    def _extract_title_from_classified_lines(self, title_lines: List[Dict], song_name: str) -> str:
        """Extract title from classified title lines"""
        if not title_lines:
            print(f"🚨 DEBUG: No title lines found for {song_name}")
            return song_name or "Untitled Song"

        print(f"🚨 DEBUG: Found {len(title_lines)} title lines for {song_name}")
        for i, title_line in enumerate(title_lines):
            print(f"  Title line {i}: '{title_line['text'][:50]}...' at Y={title_line['y']:.1f}")

        # Sort by Y coordinate (top to bottom) and take the first (topmost) title
        title_lines_sorted = sorted(title_lines, key=lambda x: x['y'])
        raw_title = title_lines_sorted[0]['text'].strip()

        # Apply language-specific normalization and encoding fixes
        title = self.config.normalize_title(raw_title)

        self.logger.debug(f"📋 TITLE (raw): '{raw_title}' -> (normalized): '{title}'")
        return title
    
    def _extract_kapodaster_from_classified_lines(self, kapodaster_lines: List[Dict]) -> str:
        """Extract kapodaster from classified kapodaster lines"""
        if not kapodaster_lines:
            return ""
        
        # Sort by Y coordinate and take the first kapodaster
        kapodaster_lines_sorted = sorted(kapodaster_lines, key=lambda x: x['y'])
        kapodaster = kapodaster_lines_sorted[0]['text'].strip()
        
        self.logger.debug(f"🎸 KAPODASTER (from classification): '{kapodaster}'")
        return kapodaster
    
    def _extract_comments_from_classified_lines(self, comment_lines: List[Dict]) -> List[Comment]:
        """Extract comments from classified comment lines, filtering out inline comments"""
        if not comment_lines:
            return []

        # Sort by Y coordinate (top to bottom) to maintain order
        comment_lines_sorted = sorted(comment_lines, key=lambda x: x['y'])

        comments = []
        for line in comment_lines_sorted:
            text = line['text'].strip()

            # Skip inline comments (C: comments) - they should be handled as verses, not end comments
            if self._is_inline_comment(text):
                self.logger.debug(f"💬 Skipping inline comment in comment processing: '{text}'")
                continue

            comments.append(Comment(text=text, comment_type="general"))

        self.logger.debug(f"💬 COMMENTS (from classification): {len(comments)} found")
        return comments

    def _extract_subtitle_lines(self, text_lines: List[Dict]) -> Tuple[List[Dict], List[Comment]]:
        """Extract subtitle lines and convert them to comments"""
        remaining_text_lines = []
        subtitle_comments = []

        for line_data in text_lines:
            if line_data.get('is_subtitle', False):
                # Convert subtitle line to comment
                subtitle_text = line_data['text'].strip()
                subtitle_comment = Comment(text=subtitle_text, comment_type="subtitle")
                subtitle_comments.append(subtitle_comment)
                self.logger.debug(f"📄 Converted subtitle to comment: '{subtitle_text}'")
            else:
                remaining_text_lines.append(line_data)

        return remaining_text_lines, subtitle_comments

    def _extract_capo_lines(self, text_lines: List[Dict]) -> Tuple[List[Dict], Optional[str]]:
        """Extract capo lines and convert them to kapodaster instruction"""
        remaining_text_lines = []
        capo_instruction = None

        for line_data in text_lines:
            if line_data.get('is_capo', False):
                # Convert capo line to kapodaster instruction
                capo_text = line_data['text'].strip()
                capo_number = self._extract_capo_number(capo_text)
                if capo_number:
                    capo_instruction = f"{{capo: {capo_number}}}"
                    self.logger.debug(f"🎸 Converted capo to kapodaster: '{capo_text}' -> {capo_instruction}")
            else:
                remaining_text_lines.append(line_data)

        return remaining_text_lines, capo_instruction

    def _extract_capo_number(self, text: str) -> Optional[int]:
        """Extract capo fret number from Italian capo instruction"""
        if not text:
            return None

        text_clean = text.strip().lower()

        # Roman numeral to number mapping
        roman_to_number = {
            'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5,
            'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9, 'x': 10
        }

        import re

        # Look for Roman numerals first
        roman_match = re.search(r'\b(i{1,3}|iv|v|vi{0,3}|ix|x)\b', text_clean)
        if roman_match:
            roman = roman_match.group(1)
            return roman_to_number.get(roman)

        # Look for Arabic numerals
        number_match = re.search(r'\b(\d+)\s*(tasto|fret)\b', text_clean)
        if number_match:
            return int(number_match.group(1))

        return None
    
    def _parse_verses_with_span_positioning(self, text_lines: List[Dict], chord_lines: List[Dict], customization=None) -> List[Verse]:
        """Parse verses using span-based chord positioning - enhanced version"""
        verses = []
        current_verse_lines = []
        current_role = ""
        
        # Sort text lines by Y coordinate to process in order
        text_lines_sorted = sorted(text_lines, key=lambda x: x['y'])
        
        # Track processed lines to avoid duplicates
        processed_indices = set()
        
        i = 0
        while i < len(text_lines_sorted):
            if i in processed_indices:
                i += 1
                continue
            
            text_line_data = text_lines_sorted[i]
            text = text_line_data['text']

            # Debug output for quote lines (removed)

            if not text.strip():
                i += 1
                continue
            
            # Check for role marker
            role_marker = self._extract_role_marker(text)
            
            if role_marker:
                # Save previous verse if exists
                if current_verse_lines and current_role:
                    verses.append(Verse(role=current_role, lines=current_verse_lines, verse_type="verse"))
                    self.logger.debug(f"🎭 Completed verse: {current_role} with {len(current_verse_lines)} lines")
                
                # Start new verse
                current_role = role_marker
                processed_indices.add(i)  # Mark role marker line as processed
                
                # Check if role marker is on same line as text or separate line
                if len(text.strip()) > len(role_marker.strip()) + 2:
                    # Role marker and text on same line
                    text_after_role = text_line_data['text_content']
                    
                    # Find chords using span-based positioning
                    chords = self._find_chords_with_span_positioning(text_line_data, chord_lines)
                    
                    verse_line = VerseLine(
                        text=text_after_role,
                        chords=chords,
                        original_line=text,
                        line_type=None
                    )
                    current_verse_lines = [verse_line]
                    self.logger.debug(f"🎵 Started verse: {current_role} (same line)")
                
                else:
                    # Role marker on separate line
                    current_verse_lines = []
                    self.logger.debug(f"🎵 Started verse: {current_role} (separate line)")
                    
                    # Continue to next line to find the actual text
                    j = i + 1
                    while j < len(text_lines_sorted):
                        next_line_data = text_lines_sorted[j]
                        next_text = next_line_data['text']
                        
                        if not next_text.strip():
                            j += 1
                            continue
                        
                        # Stop if we hit another role marker
                        if self._extract_role_marker(next_text):
                            break

                        # Stop if we hit an inline comment - it should be processed separately
                        if self._is_inline_comment(next_text):
                            break

                        # Stop if we hit an asterisk marker - it should be processed separately
                        if self._is_asterisk_marker(next_text):
                            break

                        # This is text content for the current role
                        chords = self._find_chords_with_span_positioning(next_line_data, chord_lines)
                        
                        line_text = next_line_data.get('text_content', next_text.strip())
                        verse_line = VerseLine(
                            text=line_text,
                            chords=chords,
                            original_line=next_text,
                            line_type=None
                        )
                        current_verse_lines.append(verse_line)
                        processed_indices.add(j)  # Mark this line as processed
                        self.logger.debug(f"    📝 Added text line: '{next_text.strip()[:50]}...'")
                        
                        j += 1

            elif self._is_inline_comment(text):
                # Handle inline comment (C: COMMENT TEXT) - even within existing verses
                # Save previous verse if exists
                if current_verse_lines and current_role:
                    verses.append(Verse(role=current_role, lines=current_verse_lines, verse_type="verse"))
                    current_verse_lines = []
                    current_role = ""

                # Create inline comment as a standalone verse with empty lines before and after
                formatted_comment = self._format_inline_comment(text)
                comment_verse_line = VerseLine(
                    text=f"\n{formatted_comment}\n",  # Add empty lines before and after
                    chords=[],  # Comments don't have chords
                    original_line=text,
                    line_type=None
                )
                verses.append(Verse(role="", lines=[comment_verse_line], verse_type="comment"))
                processed_indices.add(i)
                self.logger.debug(f"💬 Added inline comment: '{formatted_comment}'")

            elif self._is_asterisk_marker(text):
                # Handle multi-line asterisk comment (* or ** followed by multiple lines)
                # Save previous verse if exists
                if current_verse_lines and current_role:
                    verses.append(Verse(role=current_role, lines=current_verse_lines, verse_type="verse"))
                    current_verse_lines = []
                    current_role = ""

                # Collect the asterisk marker and following text lines
                asterisk_marker = text.strip()
                comment_text_lines = []
                j = i + 1

                # Look ahead for continuation lines (non-role, non-empty text)
                while j < len(text_lines_sorted):
                    next_line = text_lines_sorted[j]
                    next_text = next_line['text'].strip()

                    # Stop if we hit an empty line, role marker, or another asterisk
                    if (not next_text or
                        self._extract_role_marker(next_text) or
                        self._is_asterisk_marker(next_text)):
                        break

                    comment_text_lines.append(next_text)
                    processed_indices.add(j)
                    j += 1

                # Combine asterisk marker with collected text
                if comment_text_lines:
                    combined_text = f"{asterisk_marker} {' '.join(comment_text_lines)}"
                else:
                    combined_text = asterisk_marker

                formatted_comment = f"{{comment: {combined_text}}}"
                comment_verse_line = VerseLine(
                    text=f"\n{formatted_comment}\n",  # Add empty lines before and after
                    chords=[],  # Comments don't have chords
                    original_line=text,
                    line_type=None
                )
                verses.append(Verse(role="", lines=[comment_verse_line], verse_type="comment"))
                processed_indices.add(i)
                self.logger.debug(f"💬 Added multi-line asterisk comment: '{formatted_comment}'")

            elif current_role:
                # Continuation line in current verse
                if customization:
                    # Let customization handle text processing (including stripping)
                    clean_text = customization.customize_verse_text(text, text_line_data)
                else:
                    # Default behavior: Strip and remove leading quotes for continuation lines
                    clean_text = text.strip()
                    if clean_text.startswith('""'):
                        clean_text = clean_text.replace('""', '').strip()
                        clean_text = clean_text.replace('"', '').strip()

                if clean_text:  # Only add if there's actual content
                    # Find chords using span-based positioning
                    chords = self._find_chords_with_span_positioning(text_line_data, chord_lines)

                    # For customizations, use the customized text; otherwise use clean_text
                    final_text = clean_text
                    # Note: Quote spacing is now preserved by language-specific customizations

                    verse_line = VerseLine(
                        text=final_text,
                        chords=chords,
                        original_line=text,
                        line_type=None
                    )
                    current_verse_lines.append(verse_line)
                    processed_indices.add(i)  # Mark this line as processed
                    self.logger.debug(f"    📝 Added continuation line: '{clean_text[:50]}...'")
            
            i += 1
        
        # Add final verse
        if current_verse_lines and current_role:
            verses.append(Verse(role=current_role, lines=current_verse_lines, verse_type="verse"))
            self.logger.debug(f"🎭 Completed final verse: {current_role} with {len(current_verse_lines)} lines")
        
        return verses
    
    def _extract_role_marker(self, line: str) -> str:
        """Extract role marker from line"""
        for role in sorted(self.config.role_markers, key=len, reverse=True):
            if line.strip().startswith(role):
                return role
        return ""
    
    def _find_chords_with_span_positioning(self, text_line_data: Dict, chord_lines: List[Dict]) -> List[Chord]:
        """Find chords using span-based positioning - only if chord line is directly above"""
        chords = []
        
        text_y = text_line_data['y']
        
        # Find the chord line that's closest above this text line
        best_chord_line = None
        min_distance = float('inf')
        
        for chord_line_data in chord_lines:
            chord_y = chord_line_data['y']
            
            # Only consider chord lines above the text line
            if chord_y < text_y:
                distance = text_y - chord_y
                if distance < min_distance:
                    min_distance = distance
                    best_chord_line = chord_line_data
        
        if not best_chord_line:
            self.logger.debug(f"      ❌ No chord line found above text at Y={text_y}")
            return chords
        
        # Check if the chord line is reasonably close (within ~18 pixels)
        distance = text_y - best_chord_line['y']
        if distance > 18.0:
            self.logger.debug(f"      ⚠️ Chord line too far away (distance: {distance:.1f}px) - skipping chords")
            return chords
        
        self.logger.debug(f"      🔍 Found chord line above: '{best_chord_line['text'].strip()}' (distance: {distance:.1f}px)")
        
        # Extract chord positions from the chord span
        chord_positions = self.pdf_extractor.find_chord_positions_in_span(
            best_chord_line['text'],
            best_chord_line['x_start'],
            best_chord_line['width']
        )
        
        # Map each chord position to verse character position
        for chord_name, chord_pixel_x in chord_positions:
            char_position = self.pdf_extractor.map_chord_to_verse_position(
                chord_pixel_x,
                best_chord_line['x_start'],
                best_chord_line['width'],
                text_line_data['text_content'],
                text_line_data['x_start'],
                text_line_data['width'],
                text_line_data['font_size']
            )
            
            chords.append(Chord(
                chord=chord_name,
                position=char_position,
                pixel_x=chord_pixel_x
            ))
        
        return sorted(chords, key=lambda x: x.position)
    
    def export_chordpro(self, song: Song) -> str:
        """Export song to ChordPro format using the working parser's logic"""
        chordpro_lines = []
        
        # Add title
        if song.title:
            chordpro_lines.append(f"{{title: {song.title}}}")
            chordpro_lines.append("")

        # Add subtitle comments right after title
        subtitle_comments = [c for c in song.comments if c.comment_type == "subtitle"]
        for subtitle_comment in subtitle_comments:
            chordpro_lines.append(f"{{subtitle: {subtitle_comment.text}}}")
            chordpro_lines.append("")

        # Add kapodaster if present
        if song.kapodaster:
            # Check if it's already in ChordPro format (like {capo: 4})
            kapodaster_clean = song.kapodaster.strip()
            if kapodaster_clean.startswith("{") and kapodaster_clean.endswith("}"):
                # Already in ChordPro format, use as-is
                chordpro_lines.append(kapodaster_clean)
            else:
                # Wrap in comment format for Croatian-style kapodaster
                chordpro_lines.append(f"{{comment: {kapodaster_clean}}}")
            chordpro_lines.append("")
        
        # Process verses
        for verse in song.verses:
            for i, line in enumerate(verse.lines):
                if line.chords:
                    chordpro_line = self._position_chords_in_lyrics(line.chords, line.text)
                else:
                    chordpro_line = line.text
                
                # Add role prefix ONLY on first line of verse (if role exists)
                if i == 0 and verse.role:
                    chordpro_lines.append(f"{verse.role}\t{chordpro_line}")
                elif i == 0:
                    # No role - just add the line without role prefix
                    chordpro_lines.append(chordpro_line)
                else:
                    # Continuation lines - add tab only if there was a role
                    if verse.role:
                        chordpro_lines.append(f"\t{chordpro_line}")
                    else:
                        chordpro_lines.append(chordpro_line)
            
            chordpro_lines.append("")
        
        # Add general comments at the bottom (exclude subtitle comments)
        general_comments = [c for c in song.comments if c.comment_type != "subtitle"]
        for comment in general_comments:
            chordpro_lines.append(f"{{comment: {comment.text}}}")
        
        return '\n'.join(chordpro_lines)
    
    def _position_chords_in_lyrics(self, chords: List[Chord], lyric_text: str) -> str:
        """Position chords within lyric text using span-based positions"""
        if not chords or not lyric_text.strip():
            if chords:
                chord_names = [c.chord for c in chords]
                return '[' + ']['.join(chord_names) + ']'
            else:
                return lyric_text
        
        result = ""
        lyric_pos = 0
        
        sorted_chords = sorted(chords, key=lambda x: x.position)
        
        for chord in sorted_chords:
            chord_pos = chord.position
            
            # Handle chords at or beyond the end of text
            if chord_pos >= len(lyric_text):
                # Add remaining text first, then chord at the end
                if lyric_pos < len(lyric_text):
                    result += lyric_text[lyric_pos:]
                    lyric_pos = len(lyric_text)
                result += f"[{chord.chord}]"
            else:
                # Normal chord positioning within text
                target_lyric_pos = chord_pos
                
                if target_lyric_pos > lyric_pos:
                    result += lyric_text[lyric_pos:target_lyric_pos]
                    lyric_pos = target_lyric_pos
                
                result += f"[{chord.chord}]"
        
        # Add any remaining text
        if lyric_pos < len(lyric_text):
            result += lyric_text[lyric_pos:]
        
        return result

    def _is_inline_comment(self, text: str) -> bool:
        """Check if text line is an inline comment (contains C: anywhere in the text)"""
        return 'C:' in text.strip()

    def _is_asterisk_marker(self, text: str) -> bool:
        """Check if text line is an asterisk marker (* or ** only)"""
        text_clean = text.strip()
        return text_clean == '*' or text_clean == '**'

    def _format_inline_comment(self, text: str) -> str:
        """Format inline comment by removing C: prefix and adding ChordPro comment format"""
        comment_text = text.strip()

        # Handle parentheses: (C: text) -> (text)
        if comment_text.startswith('(') and comment_text.endswith(')'):
            inner_text = comment_text[1:-1].strip()  # Remove outer parentheses
            if inner_text.startswith('C:'):
                inner_text = inner_text[2:].strip()  # Remove 'C:' prefix
            comment_text = f"({inner_text})"  # Add parentheses back
        # Handle plain C: text -> text
        elif comment_text.startswith('C:'):
            comment_text = comment_text[2:].strip()  # Remove 'C:' prefix

        return f"{{comment: {comment_text}}}"

    def _separate_inline_comments(self, text_lines: List[Dict], comment_lines: List[Dict]) -> tuple:
        """Move inline comments (C: comments) from comment_lines to text_lines for proper processing"""
        new_text_lines = list(text_lines)  # Copy existing text lines
        new_comment_lines = []  # Only non-inline comments

        for comment_line in comment_lines:
            text = comment_line['text'].strip()
            if self._is_inline_comment(text):
                # This is an inline comment, move it to text_lines
                new_text_lines.append(comment_line)
                self.logger.debug(f"💬 Moved inline comment to text processing: '{text}'")
            else:
                # This is a regular comment, keep it in comment_lines
                new_comment_lines.append(comment_line)

        # Sort text_lines by Y position to maintain proper order
        new_text_lines.sort(key=lambda x: x['y'])

        return new_text_lines, new_comment_lines
