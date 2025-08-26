"""
HTML Generator for Universal Songbook Parser

This module converts Song objects to HTML format with chord positioning
and styling for web display and printing.
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import html

from core.models import Song, Verse, VerseLine, Comment, Chord
from languages.base_language import LanguageConfig


class HTMLGenerator:
    """
    Generates HTML output from Song objects.
    
    Creates styled HTML with proper chord positioning, responsive design,
    and print-friendly formatting.
    """
    
    def __init__(self, language_config: LanguageConfig):
        self.config = language_config
        self.logger = logging.getLogger(__name__)
        
        # HTML generation settings
        self.font_family = "Arial, sans-serif"
        self.chord_color = "#d63384"  # Bootstrap pink
        self.role_color = "#0d6efd"   # Bootstrap blue
        
        # Spacing and sizing
        self.base_font_size = "14px"
        self.chord_font_size = "12px"
        self.title_font_size = "24px"
        self.line_height = "1.6"
        
        self.logger.debug("Initialized HTML generator")
    
    def generate(self, song: Song) -> str:
        """
        Generate HTML from a Song object.
        
        Args:
            song: Song object to convert
            
        Returns:
            Complete HTML document as string
        """
        self.logger.info(f"Generating HTML for song '{song.title}'")
        
        # Build HTML components
        html_parts = []
        
        # HTML document structure
        html_parts.append(self._generate_html_header(song))
        html_parts.append(self._generate_css_styles())
        html_parts.append("</head>")
        html_parts.append("<body>")
        html_parts.append('<div class="song-container">')
        
        # Song content
        html_parts.append(self._generate_title(song.title))
        
        if song.kapodaster:
            html_parts.append(self._generate_kapodaster(song.kapodaster))
        
        html_parts.append(self._generate_verses(song.verses))
        
        if song.comments:
            html_parts.append(self._generate_comments(song.comments))
        
        # Close document
        html_parts.append("</div>")
        html_parts.append("</body>")
        html_parts.append("</html>")
        
        html_content = "\n".join(html_parts)
        
        self.logger.info("HTML generation complete")
        return html_content
    
    def _generate_html_header(self, song: Song) -> str:
        """Generate HTML document header"""
        title = html.escape(song.title)
        
        return f"""<!DOCTYPE html>
<html lang="{self.config.language_code}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="generator" content="Universal Songbook Parser">
    <meta name="language" content="{self.config.language_code}">"""
    
    def _generate_css_styles(self) -> str:
        """Generate CSS styles for the HTML document"""
        return f"""    <style>
        body {{
            font-family: {self.font_family};
            font-size: {self.base_font_size};
            line-height: {self.line_height};
            margin: 0;
            padding: 20px;
            background-color: #ffffff;
            color: #333333;
        }}
        
        .song-container {{
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #ffffff;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            border-radius: 8px;
        }}
        
        .song-title {{
            font-size: {self.title_font_size};
            font-weight: bold;
            text-align: center;
            margin-bottom: 20px;
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        
        .kapodaster {{
            text-align: center;
            font-style: italic;
            margin-bottom: 20px;
            padding: 10px;
            background-color: #f8f9fa;
            border-left: 4px solid #17a2b8;
            border-radius: 4px;
        }}
        
        .verse {{
            margin-bottom: 20px;
            padding: 10px 0;
        }}
        
        .verse-line {{
            margin-bottom: 8px;
            position: relative;
            font-family: 'Courier New', monospace;
            white-space: pre-wrap;
        }}
        
        .role-marker {{
            color: {self.role_color};
            font-weight: bold;
            display: inline-block;
            min-width: 60px;
            margin-right: 10px;
        }}
        
        .chord {{
            color: {self.chord_color};
            font-size: {self.chord_font_size};
            font-weight: bold;
            position: relative;
            top: -0.3em;
        }}
        
        .lyrics {{
            color: #333333;
        }}
        
        .comment {{
            font-style: italic;
            color: #6c757d;
            margin: 10px 0;
            padding: 8px 12px;
            background-color: #f8f9fa;
            border-left: 3px solid #6c757d;
            border-radius: 4px;
        }}
        
        .inline-comment {{
            color: #6c757d;
            font-style: italic;
        }}
        
        /* Print styles */
        @media print {{
            body {{
                font-size: 12px;
                padding: 0;
                background-color: white;
            }}
            
            .song-container {{
                box-shadow: none;
                max-width: none;
                padding: 0;
            }}
            
            .song-title {{
                font-size: 18px;
                margin-bottom: 15px;
            }}
            
            .verse {{
                margin-bottom: 15px;
                page-break-inside: avoid;
            }}
            
            .chord {{
                font-size: 10px;
            }}
        }}
        
        /* Mobile responsive */
        @media (max-width: 600px) {{
            body {{
                padding: 10px;
                font-size: 13px;
            }}
            
            .song-container {{
                padding: 15px;
            }}
            
            .song-title {{
                font-size: 20px;
            }}
            
            .role-marker {{
                min-width: 50px;
                margin-right: 8px;
            }}
        }}
    </style>"""
    
    def _generate_title(self, title: str) -> str:
        """Generate HTML for song title"""
        escaped_title = html.escape(title)
        return f'    <h1 class="song-title">{escaped_title}</h1>'
    
    def _generate_kapodaster(self, kapodaster: str) -> str:
        """Generate HTML for kapodaster information"""
        escaped_kapodaster = html.escape(kapodaster.strip())
        return f'    <div class="kapodaster">{escaped_kapodaster}</div>'
    
    def _generate_verses(self, verses: List[Verse]) -> str:
        """Generate HTML for all verses"""
        if not verses:
            return ""
        
        verse_html_parts = []
        
        for verse in verses:
            verse_html = self._generate_verse(verse)
            if verse_html:
                verse_html_parts.append(verse_html)
        
        return "\n".join(verse_html_parts)
    
    def _generate_verse(self, verse: Verse) -> str:
        """Generate HTML for a single verse"""
        if not verse.lines:
            return ""
        
        # Handle comment verses differently
        if verse.verse_type == "comment":
            return self._generate_comment_verse(verse)
        
        verse_parts = []
        verse_parts.append('    <div class="verse">')
        
        for i, line in enumerate(verse.lines):
            line_html = self._generate_verse_line(line, verse.role, i == 0)
            if line_html:
                verse_parts.append(f"        {line_html}")
        
        verse_parts.append('    </div>')
        
        return "\n".join(verse_parts)
    
    def _generate_comment_verse(self, verse: Verse) -> str:
        """Generate HTML for a comment verse"""
        comment_parts = []
        
        for line in verse.lines:
            text = line.text.strip()
            if text:
                escaped_text = html.escape(text)
                comment_parts.append(f'    <div class="comment">{escaped_text}</div>')
        
        return "\n".join(comment_parts)
    
    def _generate_verse_line(self, line: VerseLine, role: str, is_first_line: bool) -> str:
        """Generate HTML for a single verse line with chords"""
        if not line.text.strip():
            return ""
        
        # Build line with chords
        line_content = self._build_line_with_chords_html(line.text, line.chords)
        
        # Add role marker for first line
        role_html = ""
        if is_first_line and role:
            escaped_role = html.escape(role)
            role_html = f'<span class="role-marker">{escaped_role}</span>'
        
        return f'<div class="verse-line">{role_html}{line_content}</div>'
    
    def _build_line_with_chords_html(self, text: str, chords: List[Chord]) -> str:
        """Build HTML for a line with positioned chords"""
        if not chords:
            escaped_text = html.escape(text)
            return f'<span class="lyrics">{escaped_text}</span>'
        
        # Sort chords by position
        sorted_chords = sorted(chords, key=lambda c: c.position)
        
        result_parts = []
        text_pos = 0
        
        for chord in sorted_chords:
            chord_pos = min(chord.position, len(text))
            
            # Add text up to chord position
            if chord_pos > text_pos:
                text_segment = text[text_pos:chord_pos]
                escaped_segment = html.escape(text_segment)
                result_parts.append(f'<span class="lyrics">{escaped_segment}</span>')
                text_pos = chord_pos
            
            # Add chord
            escaped_chord = html.escape(chord.chord)
            result_parts.append(f'<span class="chord">[{escaped_chord}]</span>')
        
        # Add remaining text
        if text_pos < len(text):
            remaining_text = text[text_pos:]
            escaped_remaining = html.escape(remaining_text)
            result_parts.append(f'<span class="lyrics">{escaped_remaining}</span>')
        
        return "".join(result_parts)
    
    def _generate_comments(self, comments: List[Comment]) -> str:
        """Generate HTML for general comments"""
        if not comments:
            return ""
        
        comment_parts = []
        
        for comment in comments:
            if comment.comment_type == "general":
                text = comment.text.strip()
                if text:
                    escaped_text = html.escape(text)
                    comment_parts.append(f'    <div class="comment">{escaped_text}</div>')
        
        return "\n".join(comment_parts)
    
    def generate_minimal_html(self, song: Song) -> str:
        """
        Generate minimal HTML without full document structure.
        Useful for embedding in other documents.
        
        Args:
            song: Song object to convert
            
        Returns:
            HTML fragment (no <html>, <head>, <body> tags)
        """
        parts = []
        
        # Title
        parts.append(self._generate_title(song.title))
        
        # Kapodaster
        if song.kapodaster:
            parts.append(self._generate_kapodaster(song.kapodaster))
        
        # Verses
        parts.append(self._generate_verses(song.verses))
        
        # Comments
        if song.comments:
            parts.append(self._generate_comments(song.comments))
        
        return "\n".join(parts)
    
    def generate_with_custom_css(self, song: Song, custom_css: str) -> str:
        """
        Generate HTML with custom CSS styles.
        
        Args:
            song: Song object to convert
            custom_css: Custom CSS to include
            
        Returns:
            Complete HTML document with custom styles
        """
        # Generate standard HTML
        html_content = self.generate(song)
        
        # Insert custom CSS before closing </head>
        css_insertion_point = html_content.find("</head>")
        if css_insertion_point != -1:
            custom_style_tag = f"\n    <style>\n{custom_css}\n    </style>\n"
            html_content = (
                html_content[:css_insertion_point] +
                custom_style_tag +
                html_content[css_insertion_point:]
            )
        
        return html_content
    
    def get_generation_stats(self, song: Song) -> Dict[str, any]:
        """Get statistics about HTML generation"""
        stats = {
            'title': song.title,
            'language': song.language,
            'total_verses': len(song.verses),
            'total_comments': len(song.comments),
            'has_kapodaster': bool(song.kapodaster),
            'total_lines': sum(len(verse.lines) for verse in song.verses),
            'total_chords': sum(
                len(line.chords) 
                for verse in song.verses 
                for line in verse.lines
            ),
            'estimated_html_size': 0  # Will be calculated after generation
        }
        
        # Estimate HTML size (rough calculation)
        estimated_size = len(song.title) * 2  # Title with markup
        
        for verse in song.verses:
            for line in verse.lines:
                estimated_size += len(line.text) * 3  # Text with markup
                estimated_size += len(line.chords) * 20  # Chord markup
        
        stats['estimated_html_size'] = estimated_size
        
        return stats
