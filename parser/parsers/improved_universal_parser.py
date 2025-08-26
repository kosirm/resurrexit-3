"""
Improved Universal Parser based on working Croatian/Slovenian parsers

This parser combines the best features from both working parsers while
maintaining the universal architecture for multiple languages.
"""

import logging
from typing import List, Dict, Optional
from pathlib import Path

from core.models import Song, Verse, VerseLine, Comment, Chord
from core.improved_pdf_extractor import ImprovedPDFExtractor
from languages.base_language import LanguageConfig


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
            else:
                return None
        except ImportError:
            self.logger.warning(f"No customizations found for {self.config.language_code}")
            return None
    
    def parse(self, pdf_path: str, song_name: str = "") -> Song:
        """Parse PDF using improved span-based approach"""
        self.logger.info(f"Parsing PDF: {pdf_path}")
        
        # Extract span data from PDF
        span_data = self.pdf_extractor.extract(pdf_path)
        
        # Parse into song structure using span-based positioning
        song = self._parse_with_span_positioning(span_data, song_name)
        
        # Apply language-specific customizations
        if self.customizations:
            song.verses = self.customizations.apply_customizations(song.verses, None)
        
        self.logger.info(f"Successfully parsed song: {song.title}")
        return song
    
    def _parse_with_span_positioning(self, span_data: Dict, song_name: str) -> Song:
        """Parse using span-based positioning with enhanced classification"""
        
        chord_lines = span_data['chord_lines']
        text_lines = span_data['text_lines']
        title_lines = span_data['title_lines']
        kapodaster_lines = span_data['kapodaster_lines']
        comment_lines = span_data['comment_lines']
        
        # Extract title from title lines (should be at the top)
        title = self._extract_title_from_classified_lines(title_lines, song_name)
        
        # Extract kapodaster from kapodaster lines
        kapodaster = self._extract_kapodaster_from_classified_lines(kapodaster_lines)
        
        # Extract comments from comment lines (should be at the bottom)
        comments = self._extract_comments_from_classified_lines(comment_lines)
        
        # Parse verses with span-based chord positioning (only from text_lines)
        verses = self._parse_verses_with_span_positioning(text_lines, chord_lines)
        
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
            return song_name or "Untitled Song"
        
        # Sort by Y coordinate (top to bottom) and take the first (topmost) title
        title_lines_sorted = sorted(title_lines, key=lambda x: x['y'])
        title = title_lines_sorted[0]['text'].strip()
        
        self.logger.debug(f"📋 TITLE (from classification): '{title}'")
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
        """Extract comments from classified comment lines"""
        if not comment_lines:
            return []
        
        # Sort by Y coordinate (top to bottom) to maintain order
        comment_lines_sorted = sorted(comment_lines, key=lambda x: x['y'])
        
        comments = []
        for line in comment_lines_sorted:
            text = line['text'].strip()
            comments.append(Comment(text=text, comment_type="general"))
        
        self.logger.debug(f"💬 COMMENTS (from classification): {len(comments)} found")
        return comments
    
    def _parse_verses_with_span_positioning(self, text_lines: List[Dict], chord_lines: List[Dict]) -> List[Verse]:
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
            
            elif current_role:
                # Continuation line in current verse
                clean_text = text.strip()
                
                # Remove leading quotes and spaces for continuation lines
                if clean_text.startswith('""'):
                    clean_text = clean_text.replace('""', '').strip()
                    clean_text = clean_text.replace('"', '').strip()
                
                if clean_text:  # Only add if there's actual content
                    # Find chords using span-based positioning
                    chords = self._find_chords_with_span_positioning(text_line_data, chord_lines)
                    
                    verse_line = VerseLine(
                        text=clean_text,
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
        
        # Add kapodaster if present
        if song.kapodaster:
            chordpro_lines.append(f"{{comment: {song.kapodaster}}}")
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
        
        # Add comments at the bottom
        for comment in song.comments:
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
