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
        self.current_file = ""  # Track current file for file-specific customizations

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

    def set_current_file(self, filename: str):
        """Set the current file being processed for file-specific customizations"""
        self.current_file = filename
        self.logger.debug(f"Set current file for Italian customizations: {filename}")

    def apply_customizations(self, verses: List[Verse], document: ParsedDocument) -> List[Verse]:
        """Apply Italian-specific customizations to parsed verses"""
        self.logger.info(f"Applying Italian customizations to {len(verses)} verses")

        customized_verses = []

        for verse in verses:
            customized_lines = []
            subtitle_lines = []
            trailing_chords_to_move = []  # Store chords that need to be moved to next line

            for i, line in enumerate(verse.lines):
                # Check if this line is an Italian subtitle
                if self._is_italian_subtitle_line(line.text):
                    subtitle_lines.append(line)
                    self.logger.debug(f"🔍 Found Italian subtitle: '{line.text.strip()}'")
                else:
                    # Check for trailing chords before customizing the line
                    extracted_chord_info = None
                    if self._should_apply_chord_on_same_line_fix():
                        extracted_chord_info = self._extract_trailing_chord_info(line)

                    customized_line = self._customize_line(line, verse.role)
                    if customized_line:
                        # If we extracted a trailing chord, store it for movement
                        if extracted_chord_info:
                            self.logger.debug(f"🎸 Found extracted trailing chord: '{extracted_chord_info['chord_text']}' to move to line {len(customized_lines) + 1}")
                            trailing_chords_to_move.append({
                                'chord_text': extracted_chord_info['chord_text'],
                                'target_line_index': len(customized_lines) + 1  # Next line
                            })

                        customized_lines.append(customized_line)

            # Apply trailing chord movements
            if trailing_chords_to_move and self._should_apply_chord_on_same_line_fix():
                self.logger.debug(f"🎸 Applying {len(trailing_chords_to_move)} trailing chord movements")
                customized_lines = self._apply_trailing_chord_movements(customized_lines, trailing_chords_to_move)
            elif trailing_chords_to_move:
                self.logger.debug(f"⚠️ Found {len(trailing_chords_to_move)} trailing chords but chord_on_same_line_fix is disabled")
            else:
                self.logger.debug("🎸 No trailing chords to move")

            # Convert subtitle lines to comment verses
            for subtitle_line in subtitle_lines:
                subtitle_text = subtitle_line.text.strip()
                comment_line = VerseLine(
                    text=f"{{subtitle: {subtitle_text}}}",
                    chords=[],
                    original_line=subtitle_line.original_line
                )
                comment_verse = Verse(
                    role="",
                    lines=[comment_line],
                    verse_type="comment"
                )
                customized_verses.append(comment_verse)

            # Add the regular verse if it has lines
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

        # Check if this file needs the "chord_on_the_same_line" customization
        if self._should_apply_chord_on_same_line_fix():
            # First, check for trailing chords in text and extract them
            line_with_extracted_chords = self._extract_trailing_chords_from_text(line)
            if line_with_extracted_chords:
                line = line_with_extracted_chords

        # Then, try to fix chord positioning using Y-coordinate mapping
        line_with_fixed_positioning = self._fix_italian_chord_positioning(line)
        if line_with_fixed_positioning:
            line = line_with_fixed_positioning

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

    def _should_apply_chord_on_same_line_fix(self) -> bool:
        """
        Check if the current file needs the 'chord_on_the_same_line' customization.
        This fixes cases where chords appear at the end of text lines but should be
        positioned over the next line.

        Currently applies to:
        - IT - 032: CANTICO DEI TRE GIOVANI NELLA FORNACE - II PARTE
        """
        # List of files that need this customization
        files_needing_fix = [
            '032',  # CANTICO DEI TRE GIOVANI NELLA FORNACE - II PARTE
        ]

        # Check if current file matches any of the files needing this fix
        for file_pattern in files_needing_fix:
            if file_pattern in self.current_file:
                self.logger.debug(f"🎯 Applying 'chord_on_the_same_line' customization for file: {self.current_file}")
                return True

        return False

    def _extract_trailing_chord_info(self, line: VerseLine) -> Optional[Dict]:
        """Extract trailing chord information from a line without modifying the line"""
        if not line or not line.text:
            return None

        text = line.text.strip()

        # Look for patterns like "Figli dell'uomo *         Mi 7" or "Folgori e nubi *              Mi 7"
        import re

        # Pattern to match text ending with asterisk followed by spaces and chord(s)
        pattern = r'^(.+\*)\s{2,}(.+)$'
        match = re.match(pattern, text)

        if match:
            text_part = match.group(1).strip()
            chord_part = match.group(2).strip()

            # Check if the chord part looks like Italian chord(s)
            if self._looks_like_italian_chord_sequence(chord_part):
                self.logger.debug(f"🎸 Found trailing chord info: '{chord_part}' in line: '{text}'")
                return {
                    'chord_text': chord_part,
                    'text_part': text_part,
                    'original_line': line
                }

        return None

    def _apply_trailing_chord_movements(self, lines: List[VerseLine], trailing_chords: List[Dict]) -> List[VerseLine]:
        """Apply trailing chord movements to position chords on the next line"""
        if not trailing_chords:
            return lines

        for chord_movement in trailing_chords:
            chord_text = chord_movement['chord_text']
            target_line_index = chord_movement['target_line_index']

            # Check if target line exists
            if target_line_index < len(lines):
                target_line = lines[target_line_index]

                # Parse the chord and position it at the end of the target line
                normalized_chord = self._normalize_italian_chord(chord_text)

                # Position the chord near the end of the target line text
                # For Italian, position it around 3/4 of the way through the text
                text_length = len(target_line.text)
                chord_position = max(0, int(text_length * 0.75))

                new_chord = Chord(
                    chord=normalized_chord,
                    position=chord_position,
                    pixel_x=0.0
                )

                # Create new line with the added chord
                new_chords = list(target_line.chords) + [new_chord]
                lines[target_line_index] = VerseLine(
                    text=target_line.text,
                    chords=new_chords,
                    original_line=target_line.original_line,
                    line_type=getattr(target_line, 'line_type', None)
                )

                self.logger.debug(f"🎸 Moved trailing chord '{normalized_chord}' to line {target_line_index}: '{target_line.text[:30]}...'")
            else:
                self.logger.warning(f"⚠️ Cannot move trailing chord '{chord_text}' - target line {target_line_index} does not exist")

        return lines

    def _extract_trailing_chords_from_text(self, line: VerseLine) -> Optional[VerseLine]:
        """Extract trailing chords from text lines that contain both text and chords"""
        if not line or not line.text:
            return line

        # Check if we should apply the chord extraction for this file
        if not self._should_apply_chord_on_same_line_fix():
            return line

        # Get the trailing chord info
        chord_info = self._extract_trailing_chord_info(line)

        if chord_info:
            # Create new line with just the text part (chord removed)
            new_line = VerseLine(
                text=chord_info['text_part'],
                chords=line.chords,  # Keep existing chords
                original_line=line.original_line,
                line_type=getattr(line, 'line_type', None)
            )

            self.logger.debug(f"🎸 Removed trailing chord from text: '{line.text}' -> '{chord_info['text_part']}'")
            return new_line

        return line

    def _looks_like_italian_chord_sequence(self, text: str) -> bool:
        """Check if text looks like a sequence of Italian chords"""
        if not text or len(text.strip()) < 2:
            return False

        words = text.split()
        if len(words) == 0:
            return False

        # Parse chord units (same logic as in PDF extractor)
        chord_units = []
        i = 0
        while i < len(words):
            if i < len(words) - 1:
                # Check for two-word chord units like "La m", "Mi 7"
                two_word_unit = f"{words[i]} {words[i + 1]}"
                if self._looks_like_italian_chord_unit(two_word_unit):
                    chord_units.append(two_word_unit)
                    i += 2
                    continue

            if i < len(words) - 2:
                # Check for three-word chord units like "Fa maj 7"
                three_word_unit = f"{words[i]} {words[i + 1]} {words[i + 2]}"
                if self._looks_like_italian_chord_unit(three_word_unit):
                    chord_units.append(three_word_unit)
                    i += 3
                    continue

            # Check for single-word chord
            if self._looks_like_italian_chord(words[i]):
                chord_units.append(words[i])

            i += 1

        # If most units are chord units, it's a chord sequence
        if len(chord_units) > 0:
            chord_ratio = len(chord_units) / len(words)
            # Use >= 0.5 to include single chords like "Mi 7" (1 chord unit / 2 words = 0.5)
            return chord_ratio >= 0.5

        return False

    def _looks_like_italian_chord_unit(self, unit: str) -> bool:
        """Check if a unit (potentially multi-word) looks like an Italian chord"""
        if not unit:
            return False

        words = unit.split()
        if len(words) == 1:
            return self._looks_like_italian_chord(words[0])
        elif len(words) == 2:
            # Two-word units like "La m", "Mi 7", "Fa maj"
            return (self._looks_like_italian_chord(words[0]) and
                   words[1] in ['m', 'maj', '7', '9', '6', '4', '2', '11', '13', 'dim', 'aug', 'sus4', 'sus2'])
        elif len(words) == 3:
            # Three-word units like "Fa maj 7", "Re m 9"
            return (self._looks_like_italian_chord(words[0]) and
                   words[1] in ['maj', 'm'] and
                   words[2] in ['7', '9', '6', '4', '2', '11', '13'])

        return False

    def _looks_like_italian_chord(self, word: str) -> bool:
        """Check if a single word looks like an Italian chord root"""
        if not word:
            return False

        # Italian chord roots
        italian_roots = ['Do', 'Re', 'Mi', 'Fa', 'Sol', 'La', 'Si']

        # Check for basic root
        for root in italian_roots:
            if word.startswith(root):
                remaining = word[len(root):]
                if not remaining:
                    return True  # Just the root
                elif remaining in ['#', 'b', 'm', '7', '9', '6', '4', '2', '11', '13', 'maj7', 'dim', 'aug', 'sus4', 'sus2']:
                    return True  # Root with extension
                elif remaining.startswith('m') and len(remaining) > 1:
                    # Minor chord with extension like "Rem7"
                    extension = remaining[1:]
                    return extension in ['7', '9', '6', '4', '2', '11', '13']
                elif remaining.startswith('#') or remaining.startswith('b'):
                    # Accidental chord like "Re#", "Sib"
                    return len(remaining) <= 2

        return False

    def _parse_italian_chord_sequence_to_chords(self, chord_sequence: str, text_part: str) -> List[Chord]:
        """Parse a chord sequence and create positioned Chord objects"""
        chords = []

        # For trailing chords, position them at the end of the text
        text_length = len(text_part)

        # Parse chord units from the sequence
        words = chord_sequence.split()
        chord_units = []
        i = 0
        while i < len(words):
            if i < len(words) - 1:
                # Check for two-word chord units
                two_word_unit = f"{words[i]} {words[i + 1]}"
                if self._looks_like_italian_chord_unit(two_word_unit):
                    chord_units.append(two_word_unit)
                    i += 2
                    continue

            if i < len(words) - 2:
                # Check for three-word chord units
                three_word_unit = f"{words[i]} {words[i + 1]} {words[i + 2]}"
                if self._looks_like_italian_chord_unit(three_word_unit):
                    chord_units.append(three_word_unit)
                    i += 3
                    continue

            # Single-word chord
            if self._looks_like_italian_chord(words[i]):
                chord_units.append(words[i])

            i += 1

        # Create Chord objects positioned at the end of the text
        for i, chord_unit in enumerate(chord_units):
            # Normalize the chord
            normalized_chord = self._normalize_italian_chord(chord_unit)

            # Position chords at the end of text, spaced slightly apart
            position = text_length + i

            chord = Chord(
                chord=normalized_chord,
                position=position,
                pixel_x=0.0  # Trailing chords don't have specific pixel positions
            )
            chords.append(chord)
            self.logger.debug(f"🎸 Created trailing chord: '{normalized_chord}' at position {position}")

        return chords

    def _customize_chord(self, chord: Chord) -> Optional[Chord]:
        """Apply Italian-specific chord customizations"""
        if not chord or not chord.chord:
            return chord

        # First normalize merged chords like "Rem" -> "Re m"
        chord_text = chord.chord.strip('[]')  # Remove brackets for processing
        normalized_merged = self._normalize_merged_italian_chord(chord_text)

        # Then apply Italian chord normalization (adds brackets)
        normalized_chord = self._normalize_italian_chord(normalized_merged)

        return Chord(
            chord=normalized_chord,
            position=chord.position,
            pixel_x=chord.pixel_x
        )

    def _normalize_italian_chord(self, chord_text: str) -> str:
        """Normalize Italian chord notation (without adding brackets - main parser handles that)"""
        if not chord_text:
            return chord_text

        # Remove existing brackets to avoid double bracketing
        clean_chord = chord_text.strip()
        if clean_chord.startswith('[') and clean_chord.endswith(']'):
            clean_chord = clean_chord[1:-1]

        # Handle chords in parentheses: "(Sol 7)" -> "[(Sol7)]" (normalize and keep parentheses)
        if clean_chord.startswith('(') and clean_chord.endswith(')'):
            inner_chord = clean_chord[1:-1].strip()
            normalized_inner = self._normalize_italian_chord_format(inner_chord)
            return f"({normalized_inner})"

        # Handle regular chords: "Fa maj 7" -> "Fa maj7", "Re m 9" -> "Re m9" (no brackets - main parser adds them)
        normalized_chord = self._normalize_italian_chord_format(clean_chord)
        return normalized_chord

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

    def _fix_italian_chord_positioning(self, line: VerseLine) -> Optional[VerseLine]:
        """Fix Italian chord positioning using Y-coordinate mapping from PDF span data"""
        if not line.chords:
            return line

        # Check if this line has multiple spaces (indicating chord spacing conflicts)
        has_multiple_spaces = self._has_multiple_spaces(line.text)

        if not has_multiple_spaces:
            # Use standard positioning for lines without spacing conflicts
            return line

        # Get original span data for Y-coordinate positioning
        if not hasattr(line, 'original_line') or not line.original_line:
            return line

        original_data = line.original_line
        if not isinstance(original_data, dict) or 'spans' not in original_data:
            return line

        # Extract chord and text Y-positions from spans
        chord_y_positions = self._extract_italian_chord_y_positions(original_data['spans'])
        text_y_positions = self._extract_italian_text_y_positions(original_data['spans'], line.text)

        if not chord_y_positions or not text_y_positions:
            return line

        # Reposition chords based on Y-coordinate matching
        new_chords = []
        for chord in line.chords:
            chord_name = chord.chord.strip('[]')  # Remove brackets for matching

            # Find Y-coordinate for this chord
            chord_y = chord_y_positions.get(chord_name)
            if chord_y is not None:
                # Find best character position based on Y-coordinate
                best_position = self._find_best_character_position_by_y(line.text, chord_y, text_y_positions)
                new_chords.append(Chord(
                    chord=chord.chord,
                    position=best_position,
                    pixel_x=chord.pixel_x
                ))
            else:
                # Keep original position if no Y-coordinate found
                new_chords.append(chord)

        # Create new line with repositioned chords
        return VerseLine(
            text=line.text,
            chords=sorted(new_chords, key=lambda x: x.position),
            original_line=line.original_line,
            line_type=getattr(line, 'line_type', None)
        )

    def _has_multiple_spaces(self, text: str) -> bool:
        """Check if text has multiple consecutive spaces (indicating chord spacing conflicts)"""
        import re
        # Look for 3 or more consecutive spaces
        return bool(re.search(r'\s{3,}', text))

    def _extract_italian_chord_y_positions(self, spans: List[Dict]) -> Dict[str, float]:
        """Extract Y-coordinates of Italian chords from PDF spans"""
        chord_y_positions = {}

        for span in spans:
            span_text = span.get('text', '').strip()
            if not span_text:
                continue

            span_y = span.get('bbox', [0, 0, 0, 0])[1]  # Y-coordinate

            # Check if this span contains Italian chords
            if self._looks_like_italian_chord(span_text):
                chord_y_positions[span_text] = span_y
            else:
                # Check for multiple chords in one span (e.g., "Re m Fa Mi")
                words = span_text.split()
                for word in words:
                    if self._looks_like_italian_chord(word):
                        chord_y_positions[word] = span_y

        return chord_y_positions

    def _extract_italian_text_y_positions(self, spans: List[Dict], text: str) -> Dict[int, float]:
        """Extract Y-coordinates for each character position in Italian text"""
        text_y_positions = {}
        current_position = 0

        for span in spans:
            span_text = span.get('text', '')
            if not span_text:
                continue

            span_y = span.get('bbox', [0, 0, 0, 0])[1]  # Y-coordinate

            # Skip chord spans - only map text spans
            if not self._looks_like_italian_chord(span_text.strip()):
                # Map each character in this span to the span's Y-coordinate
                for i, char in enumerate(span_text):
                    if current_position < len(text):
                        text_y_positions[current_position] = span_y
                        current_position += 1

        return text_y_positions

    def _find_best_character_position_by_y(self, text: str, chord_y: float, text_y_positions: Dict[int, float]) -> int:
        """Find the character position with Y-coordinate closest to the chord Y-coordinate"""
        if not text_y_positions:
            # Fallback to middle position if no Y-coordinate data
            return len(text) // 2

        best_position = 0
        best_y_diff = float('inf')

        for position, text_y in text_y_positions.items():
            y_diff = abs(chord_y - text_y)
            if y_diff < best_y_diff:
                best_y_diff = y_diff
                best_position = position

        # Ensure position is within text bounds
        best_position = max(0, min(best_position, len(text)))
        return best_position

    def _looks_like_italian_chord(self, text: str) -> bool:
        """Check if text looks like an Italian chord"""
        if not text:
            return False

        text = text.strip()

        # Handle parentheses chords: "(Sol 7)"
        if text.startswith('(') and text.endswith(')'):
            inner_text = text[1:-1].strip()
            return self._looks_like_italian_chord(inner_text)

        # Check for Italian chord roots
        italian_roots = ['Do', 'Re', 'Mi', 'Fa', 'Sol', 'La', 'Si']

        # Handle merged chords like "Rem", "Dom", "Lam", etc.
        for root in italian_roots:
            if text.startswith(root):
                remaining = text[len(root):]
                if not remaining:
                    # Just the root chord (e.g., "Re")
                    return True
                elif remaining in ['m', 'b', '7', '9', '6', '4', '2', '11', '13', 'maj7', 'dim', 'aug', '+', '°', 'sus4', 'sus2']:
                    # Merged chord like "Rem", "Re7", etc.
                    return True
                elif remaining.startswith('m') and len(remaining) > 1:
                    # Merged minor chord with extension like "Rem9", "Rem7"
                    extension = remaining[1:]
                    if extension in ['7', '9', '6', '4', '2', '11', '13', 'maj7', 'dim', 'aug', '+', '°', 'sus4', 'sus2']:
                        return True
                elif remaining.startswith('#') or remaining.startswith('b'):
                    # Sharp or flat chord like "Re#", "Sib"
                    accidental_remaining = remaining[1:]
                    if not accidental_remaining:
                        return True
                    elif accidental_remaining in ['m', '7', '9', '6', '4', '2', '11', '13', 'maj7', 'dim', 'aug', '+', '°', 'sus4', 'sus2']:
                        return True
                    elif accidental_remaining.startswith('m') and len(accidental_remaining) > 1:
                        extension = accidental_remaining[1:]
                        if extension in ['7', '9', '6', '4', '2', '11', '13', 'maj7', 'dim', 'aug', '+', '°', 'sus4', 'sus2']:
                            return True

        # Check for spaced chords (original logic)
        words = text.split()
        if not words:
            return False

        # First word should be an Italian chord root
        base_chord = words[0]
        if base_chord not in italian_roots:
            return False

        # If there are additional words, they should be valid extensions
        if len(words) > 1:
            for word in words[1:]:
                if word not in ['m', 'b', '7', '9', '6', '4', '2', '11', '13', 'maj7', 'dim', 'aug', '+', '°', 'sus4', 'sus2']:
                    return False

        return True

    def _normalize_merged_italian_chord(self, chord: str) -> str:
        """Normalize merged Italian chords like 'Rem' to 'Re m'"""
        if not chord:
            return chord

        chord = chord.strip()

        # Handle parentheses chords: "(Sol7)" -> "(Sol 7)"
        if chord.startswith('(') and chord.endswith(')'):
            inner_chord = chord[1:-1].strip()
            normalized_inner = self._normalize_merged_italian_chord(inner_chord)
            return f"({normalized_inner})"

        # Check for Italian chord roots
        italian_roots = ['Do', 'Re', 'Mi', 'Fa', 'Sol', 'La', 'Si']

        for root in italian_roots:
            if chord.startswith(root):
                remaining = chord[len(root):]
                if not remaining:
                    # Just the root chord
                    return chord
                elif remaining == 'm':
                    # Already properly spaced
                    return f"{root} m"
                elif remaining.startswith('m') and len(remaining) > 1:
                    # Merged minor chord with extension like "Rem9" -> "Re m 9"
                    extension = remaining[1:]
                    return f"{root} m {extension}"
                elif remaining in ['7', '9', '6', '4', '2', '11', '13']:
                    # Merged major chord with extension like "Re7" -> "Re 7"
                    return f"{root} {remaining}"
                elif remaining in ['maj7', 'dim', 'aug', 'sus4', 'sus2']:
                    # Merged chord with complex extension
                    return f"{root} {remaining}"
                elif remaining.startswith('#') or remaining.startswith('b'):
                    # Sharp or flat chord like "Re#m" -> "Re# m"
                    accidental = remaining[0]
                    accidental_remaining = remaining[1:]
                    if not accidental_remaining:
                        return f"{root}{accidental}"
                    elif accidental_remaining == 'm':
                        return f"{root}{accidental} m"
                    elif accidental_remaining.startswith('m') and len(accidental_remaining) > 1:
                        extension = accidental_remaining[1:]
                        return f"{root}{accidental} m {extension}"
                    else:
                        return f"{root}{accidental} {accidental_remaining}"

        # If no normalization needed, return as-is
        return chord

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

    def _is_italian_subtitle_line(self, text: str) -> bool:
        """Check if a text line is an Italian subtitle (biblical reference or liturgical note)"""
        if not text:
            return False

        text_clean = text.strip().lower()

        # Italian subtitles start with "Cfr." (Confronta/Compare) followed by references
        # They can be biblical references OR liturgical references
        if not text_clean.startswith('cfr.'):
            return False

        # Additional checks for Italian subtitle format
        is_reasonable_length = 10 <= len(text_clean) <= 100  # Reasonable length for references

        # Check for biblical reference format (e.g., "Gen 22,9-10", "Mt 5,1-12") OR
        # liturgical reference format (e.g., "Sequenza di Pasqua", "Targum Neofiti")
        import re
        has_biblical_format = bool(re.search(r'\b\d+,\d+(-\d+)?\b', text_clean))
        has_liturgical_format = any(pattern in text_clean for pattern in [
            'sequenza', 'targum', 'neofiti', 'quaresima', 'avvento', 'pasqua', 'natale', 'ordinario',
            'tempo di', 'antifona', 'responsorio', 'alleluia', 'vangelo'
        ])

        # Must start with "Cfr." and have either biblical or liturgical format
        result = is_reasonable_length and (has_biblical_format or has_liturgical_format)

        if result:
            self.logger.debug(f"🔍 Italian subtitle detected: '{text[:30]}...' | "
                            f"biblical: {has_biblical_format} | liturgical: {has_liturgical_format}")

        return result

    def _normalize_italian_chord_format(self, chord: str) -> str:
        """
        Normalize Italian chord to consistent internal format:
        - Major extensions: "Fa maj 7" -> "Fa maj7" (no spaces in extensions)
        - Minor extensions: "Re m 9" -> "Re m9" (space before m, no space after m)
        - Handle both spaced and merged input formats
        """
        chord = chord.strip()
        if not chord:
            return chord

        # Italian chord roots
        italian_roots = ['Do', 'Re', 'Mi', 'Fa', 'Sol', 'La', 'Si']

        # Find the root chord
        root_chord = None
        accidental = ""
        remaining = ""

        for root in italian_roots:
            if chord.startswith(root):
                root_chord = root
                remaining = chord[len(root):]

                # Check for accidental (#, b)
                if remaining.startswith('#') or remaining.startswith('b'):
                    accidental = remaining[0]
                    remaining = remaining[1:]
                break

        if not root_chord:
            return chord  # Not an Italian chord

        # Clean up remaining part (remove extra spaces)
        remaining = remaining.strip()

        if not remaining:
            # Simple chord like "Fa", "Re#"
            return root_chord + accidental

        # Handle minor chords specially
        if remaining.startswith('m') or remaining.startswith(' m'):
            return self._normalize_minor_chord(root_chord + accidental, remaining)

        # Handle major extensions (maj, dim, aug, sus, add, etc.)
        return self._normalize_major_chord(root_chord + accidental, remaining)

    def _normalize_minor_chord(self, root_with_accidental: str, remaining: str) -> str:
        """
        Normalize minor chord format: "Re m 9" -> "Re m9"
        Keep space before 'm', remove spaces after 'm'
        """
        remaining = remaining.strip()

        # Remove leading space if present
        if remaining.startswith(' m'):
            remaining = remaining[2:]  # Remove ' m'
        elif remaining.startswith('m'):
            remaining = remaining[1:]  # Remove 'm'
        else:
            return root_with_accidental + remaining  # Fallback

        # Clean up extensions after 'm'
        remaining = remaining.strip()

        if not remaining:
            # Simple minor chord "Re m"
            return f"{root_with_accidental} m"

        # Remove all spaces in extensions: "maj 7" -> "maj7", " 9" -> "9"
        import re
        extensions_clean = re.sub(r'\s+', '', remaining)

        return f"{root_with_accidental} m{extensions_clean}"

    def _normalize_major_chord(self, root_with_accidental: str, remaining: str) -> str:
        """
        Normalize major chord format: "Fa maj 7" -> "Fa maj7"
        Remove all spaces in extensions
        """
        remaining = remaining.strip()

        if not remaining:
            return root_with_accidental

        # Remove all spaces in extensions: "maj 7" -> "maj7", "dim 7" -> "dim7"
        import re
        extensions_clean = re.sub(r'\s+', '', remaining)

        return f"{root_with_accidental}{extensions_clean}"


