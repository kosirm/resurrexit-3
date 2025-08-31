"""
Italian Language Customizations for PDF Parser
Handles Italian-specific text processing, chord normalization, and formatting
Based on Spanish customizations structure
"""

import re
import logging
from typing import List, Optional, Dict, Any
from core.models import Verse, VerseLine, ParsedDocument, TextType, ClassifiedText, Chord
from languages.base_language import LanguageCustomizations


class ItalianCustomizations(LanguageCustomizations):
    """Italian-specific customizations for song parsing"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.language_name = "Italian"

        # Italian-specific patterns
        self.italian_words = [
            'dio', 'signore', 'cristo', 'gesù', 'maria', 'santo', 'santa',
            'amen', 'alleluia', 'gloria', 'osanna', 'padre', 'figlio', 'spirito'
        ]

        # Common Italian abbreviations and expansions
        self.text_expansions = {
            'cfr.': 'confronta',  # Biblical reference abbreviation
            'sal': 'salmo',       # Psalm
            'gen': 'genesi',      # Genesis
        }

        # Italian-specific role processing
        self.role_synonyms = {
            'C.': ['Coro', 'CORO'],
            'A.': ['Assemblea', 'ASSEMBLEA'],
            'P.': ['Presbitero', 'PRESBITERO'],
            'B.': ['Bambini', 'BAMBINI'],
            'Donne:': ['Donne', 'DONNE'],
            'Uomini:': ['Uomini', 'UOMINI'],
        }

        self.logger.debug("Initialized Italian customizations")

    def apply_customizations(self, verses: List[Verse], document: ParsedDocument) -> List[Verse]:
        """Apply Italian-specific customizations to parsed verses"""
        self.logger.info(f"Applying Italian customizations to {len(verses)} verses")

        customized_verses = []

        for verse in verses:
            customized_lines = []
            for line in verse.lines:
                customized_line = self._customize_line(line, verse.role)
                if customized_line:
                    customized_lines.append(customized_line)

            if customized_lines:
                customized_verses.append(Verse(
                    role=verse.role,
                    lines=customized_lines,
                    verse_type=verse.verse_type
                ))

        self.logger.info(f"Italian customizations complete: {len(customized_verses)} verses")
        return customized_verses

    def _customize_line(self, line: VerseLine, role: str) -> Optional[VerseLine]:
        """Apply Italian-specific line customizations"""
        if not line or not line.text:
            return line

        # Apply Italian text formatting
        customized_text = self._apply_italian_text_formatting(line.text, role)

        # Apply Italian chord formatting
        customized_chords = []
        for chord in line.chords:
            customized_chord = self._customize_chord(chord)
            if customized_chord:
                customized_chords.append(customized_chord)

        return VerseLine(
            text=customized_text,
            chords=customized_chords,
            original_line=line.original_line,
            line_type=getattr(line, 'line_type', None)
        )

    def _apply_italian_text_formatting(self, text: str, role: str) -> str:
        """Apply Italian-specific text formatting rules"""
        if not text:
            return text

        # Italian rule: All refrains (role A.) should be in uppercase
        if role == "A.":
            # Convert to uppercase, but preserve chord markers
            result = ""
            i = 0
            while i < len(text):
                if text[i] == '[':
                    # Find the end of the chord marker
                    end = text.find(']', i)
                    if end != -1:
                        # Keep chord marker as-is
                        result += text[i:end+1]
                        i = end + 1
                    else:
                        result += text[i].upper()
                        i += 1
                else:
                    result += text[i].upper()
                    i += 1
            return result

        # For other roles, keep text as-is
        return text

    def _customize_chord(self, chord: Chord) -> Optional[Chord]:
        """Apply Italian-specific chord customizations"""
        if not chord or not chord.chord:
            return chord

        # Apply Italian chord normalization
        normalized_chord = self._normalize_italian_chord(chord.chord)

        return Chord(
            chord=normalized_chord,
            position=chord.position,
            pixel_x=chord.pixel_x
        )

    def _normalize_italian_chord(self, chord_text: str) -> str:
        """Normalize Italian chord notation"""
        if not chord_text:
            return chord_text

        # Remove existing brackets to avoid double bracketing
        clean_chord = chord_text.strip()
        if clean_chord.startswith('[') and clean_chord.endswith(']'):
            clean_chord = clean_chord[1:-1]

        # Handle chords in parentheses: "(Sol 7)" -> "[(Sol7)]"
        if clean_chord.startswith('(') and clean_chord.endswith(')'):
            # Remove parentheses, normalize spaces, then add ChordPro brackets with parentheses
            inner_chord = clean_chord[1:-1].strip()
            normalized_inner = self._normalize_chord_spaces(inner_chord)
            return f"[({normalized_inner})]"

        # Handle regular chords with spaces: "Re m 9" -> "[Re m 9]" (preserve spaces)
        return f"[{self._normalize_chord_spaces(clean_chord)}]"

    def _normalize_chord_spaces(self, chord: str) -> str:
        """Normalize spaces in Italian chords while preserving the Italian format"""
        chord = chord.strip()

        # Italian chords have specific spacing: "Re m 9"
        # Pattern: [Root] [modifier] [number]

        # Match Italian chord pattern with spaces
        match = re.match(r'^(Do|Re|Mi|Fa|Sol|La|Si)(\s+[mb])?(\s+\d+.*)?$', chord)
        if match:
            root = match.group(1)
            modifier = match.group(2).strip() if match.group(2) else ""
            number = match.group(3).strip() if match.group(3) else ""

            # Reconstruct with proper spacing
            result = root
            if modifier:
                result += f" {modifier}"
            if number:
                result += f" {number}"
            return result

        # If no match, return as-is but clean up multiple spaces
        return re.sub(r'\s+', ' ', chord)

    def customize_title(self, title: str) -> str:
        """Apply Italian-specific title customizations"""
        if not title:
            return title

        # Italian titles are typically already in the correct format
        # Just apply basic normalization
        title = title.strip()

        # Remove common Italian prefixes/suffixes
        title = re.sub(r'^\d+\.\s*', '', title)  # Remove numbering
        title = re.sub(r'\s*\*+\s*$', '', title)  # Remove trailing asterisks

        return title

    def customize_subtitle(self, subtitle: str) -> str:
        """Apply Italian-specific subtitle customizations"""
        if not subtitle:
            return subtitle

        # Italian subtitles are biblical references in normal case
        # Clean up but preserve the format
        subtitle = subtitle.strip()

        # Remove extra whitespace
        subtitle = re.sub(r'\s+', ' ', subtitle)

        return subtitle
