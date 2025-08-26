"""
ChordPro Exporter for Universal Songbook Parser

This module converts Song objects to ChordPro format with proper chord
positioning and language-specific formatting.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

from core.models import Song, Verse, VerseLine, Comment, Chord
from languages.base_language import LanguageConfig


class ChordProExporter:
    """
    Exports Song objects to ChordPro format.
    
    Handles chord positioning, language-specific formatting rules,
    and ChordPro directive generation.
    """
    
    def __init__(self, language_config: LanguageConfig):
        self.config = language_config
        self.logger = logging.getLogger(__name__)
        
        # Get export settings
        self.export_settings = self.config.get_export_settings()
        
        # Formatting options
        self.use_tabs = self.export_settings.get('use_tabs_for_alignment', True)
        self.preserve_spacing = self.export_settings.get('preserve_original_spacing', False)
        self.add_metadata = self.export_settings.get('add_language_metadata', True)
        self.chord_bracket_style = self.export_settings.get('chord_bracket_style', 'square')
        self.comment_style = self.export_settings.get('comment_style', 'chordpro')
        
        self.logger.debug("Initialized ChordPro exporter")
    
    def export(self, song: Song) -> str:
        """
        Export a Song object to ChordPro format.
        
        Args:
            song: Song object to export
            
        Returns:
            ChordPro formatted string
        """
        self.logger.info(f"Exporting song '{song.title}' to ChordPro format")
        
        lines = []
        
        # Add ChordPro header
        lines.extend(self._generate_header(song))
        
        # Add song content
        lines.extend(self._export_verses(song.verses))
        
        # Add footer comments
        lines.extend(self._export_comments(song.comments))
        
        # Join all lines
        chordpro_content = "\n".join(lines)
        
        # Apply final formatting
        chordpro_content = self._apply_final_formatting(chordpro_content)
        
        self.logger.info(f"ChordPro export complete: {len(lines)} lines")
        return chordpro_content
    
    def _generate_header(self, song: Song) -> List[str]:
        """Generate ChordPro header with metadata"""
        header_lines = []
        
        # Title (required)
        header_lines.append(f"{{title: {song.title}}}")
        
        # Language metadata (if enabled)
        if self.add_metadata and song.language:
            header_lines.append(f"{{meta: language {song.language}}}")
            header_lines.append("{meta: parser universal_parser_v1}")
        
        # Source file (if available)
        if self.add_metadata and song.source_file:
            import os
            filename = os.path.basename(song.source_file)
            header_lines.append(f"{{meta: source {filename}}}")
        
        # Export timestamp (if enabled)
        if self.add_metadata:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            header_lines.append(f"{{meta: exported {timestamp}}}")
        
        # Kapodaster (if present)
        if song.kapodaster:
            kapodaster_line = self._format_kapodaster(song.kapodaster)
            if kapodaster_line:
                header_lines.append(kapodaster_line)
        
        # Add empty line after header
        header_lines.append("")
        
        return header_lines
    
    def _format_kapodaster(self, kapodaster: str) -> str:
        """Format kapodaster information"""
        # Clean up kapodaster text
        cleaned = kapodaster.strip()
        
        # Check if it's already in ChordPro format
        if cleaned.startswith("{") and cleaned.endswith("}"):
            return cleaned
        
        # Convert to ChordPro comment format
        return f"{{comment: {cleaned}}}"
    
    def _export_verses(self, verses: List[Verse]) -> List[str]:
        """Export all verses to ChordPro format"""
        verse_lines = []
        
        for i, verse in enumerate(verses):
            # Add verse content
            verse_content = self._export_verse(verse)
            if verse_content:
                verse_lines.extend(verse_content)
                
                # Add empty line between verses (except after last verse)
                if i < len(verses) - 1:
                    verse_lines.append("")
        
        return verse_lines
    
    def _export_verse(self, verse: Verse) -> List[str]:
        """Export a single verse to ChordPro format"""
        if not verse.lines:
            return []
        
        verse_lines = []
        
        # Handle different verse types
        if verse.verse_type == "comment":
            return self._export_comment_verse(verse)
        
        # Regular verse
        for i, line in enumerate(verse.lines):
            chordpro_line = self._export_verse_line(line, verse.role, i == 0)
            if chordpro_line:
                verse_lines.append(chordpro_line)
        
        return verse_lines
    
    def _export_comment_verse(self, verse: Verse) -> List[str]:
        """Export a comment verse"""
        comment_lines = []
        
        for line in verse.lines:
            text = line.text.strip()
            
            # Check if already in ChordPro comment format
            if text.startswith("{comment:") or text.startswith("{c:"):
                comment_lines.append(text)
            else:
                # Format as ChordPro comment
                if self.comment_style == 'chordpro':
                    comment_lines.append(f"{{comment: {text}}}")
                else:
                    comment_lines.append(text)
        
        return comment_lines
    
    def _export_verse_line(self, line: VerseLine, role: str, is_first_line: bool) -> str:
        """Export a single verse line with chords"""
        if not line.text.strip():
            return ""
        
        # Build the line with positioned chords
        chordpro_line = self._build_line_with_chords(line)
        
        # Add role marker for first line
        if is_first_line and role:
            if self.use_tabs:
                return f"{role}\t{chordpro_line}"
            else:
                return f"{role} {chordpro_line}"
        else:
            # Continuation line
            if role and self.use_tabs:
                return f"\t{chordpro_line}"
            else:
                return chordpro_line
    
    def _build_line_with_chords(self, line: VerseLine) -> str:
        """Build a line with properly positioned chords"""
        if not line.chords:
            return line.text
        
        # Sort chords by position
        sorted_chords = sorted(line.chords, key=lambda c: c.position)
        
        result = ""
        text_pos = 0
        
        for chord in sorted_chords:
            chord_pos = chord.position
            
            # Add text up to chord position
            if chord_pos > text_pos:
                result += line.text[text_pos:chord_pos]
                text_pos = chord_pos
            
            # Add chord in appropriate format
            chord_text = self._format_chord(chord.chord)
            result += chord_text
        
        # Add remaining text
        if text_pos < len(line.text):
            result += line.text[text_pos:]
        
        return result
    
    def _format_chord(self, chord: str) -> str:
        """Format a chord according to the configured style"""
        if not chord:
            return ""
        
        # Apply chord bracket style
        if self.chord_bracket_style == 'square':
            return f"[{chord}]"
        elif self.chord_bracket_style == 'round':
            return f"({chord})"
        elif self.chord_bracket_style == 'curly':
            return f"{{{chord}}}"
        else:
            return f"[{chord}]"  # Default to square brackets
    
    def _export_comments(self, comments: List[Comment]) -> List[str]:
        """Export general comments"""
        if not comments:
            return []
        
        comment_lines = []
        
        # Add separator before comments
        comment_lines.append("")
        
        for comment in comments:
            if comment.comment_type == "general":
                comment_text = comment.text.strip()
                
                if self.comment_style == 'chordpro':
                    comment_lines.append(f"{{comment: {comment_text}}}")
                else:
                    comment_lines.append(comment_text)
        
        return comment_lines
    
    def _apply_final_formatting(self, content: str) -> str:
        """Apply final formatting rules to the ChordPro content"""
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            # Apply language-specific text fixes
            fixed_line = self.config.fix_text_encoding(line)
            
            # Apply spacing rules
            if not self.preserve_spacing:
                # Normalize whitespace
                fixed_line = ' '.join(fixed_line.split())
            
            formatted_lines.append(fixed_line)
        
        # Remove excessive empty lines
        result_lines = []
        prev_empty = False
        
        for line in formatted_lines:
            is_empty = not line.strip()
            
            if is_empty and prev_empty:
                continue  # Skip consecutive empty lines
            
            result_lines.append(line)
            prev_empty = is_empty
        
        return '\n'.join(result_lines)
    
    def validate_chordpro(self, content: str) -> List[str]:
        """
        Validate ChordPro content and return list of issues.
        
        Args:
            content: ChordPro content to validate
            
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        lines = content.split('\n')
        
        # Check for required title
        has_title = any(line.strip().startswith('{title:') for line in lines)
        if not has_title:
            issues.append("Missing {title:} directive")
        
        # Check for malformed directives
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Check for unclosed directives
            if stripped.startswith('{') and not stripped.endswith('}'):
                issues.append(f"Line {i}: Unclosed directive: {stripped}")
            
            # Check for malformed chord brackets
            open_brackets = stripped.count('[')
            close_brackets = stripped.count(']')
            if open_brackets != close_brackets:
                issues.append(f"Line {i}: Mismatched chord brackets: {stripped}")
        
        return issues
    
    def get_export_stats(self, song: Song) -> Dict[str, any]:
        """Get statistics about the exported song"""
        stats = {
            'title': song.title,
            'language': song.language,
            'total_verses': len(song.verses),
            'total_comments': len(song.comments),
            'has_kapodaster': bool(song.kapodaster),
            'verse_types': {},
            'role_distribution': {},
            'total_chords': 0,
            'unique_chords': set()
        }
        
        # Analyze verses
        for verse in song.verses:
            # Count verse types
            verse_type = verse.verse_type
            stats['verse_types'][verse_type] = stats['verse_types'].get(verse_type, 0) + 1
            
            # Count roles
            role = verse.role or 'no_role'
            stats['role_distribution'][role] = stats['role_distribution'].get(role, 0) + 1
            
            # Count chords
            for line in verse.lines:
                stats['total_chords'] += len(line.chords)
                for chord in line.chords:
                    stats['unique_chords'].add(chord.chord)
        
        # Convert set to count
        stats['unique_chords'] = len(stats['unique_chords'])
        
        return stats
