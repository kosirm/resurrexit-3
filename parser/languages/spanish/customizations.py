"""
Spanish Language Customizations for PDF Parser
Handles Spanish-specific text processing, chord normalization, and formatting
"""

import re
import logging
from typing import List, Optional, Dict, Any
from core.models import Verse, VerseLine, ParsedDocument, TextType, ClassifiedText, Chord
from languages.base_language import LanguageCustomizations


class SpanishCustomizations(LanguageCustomizations):
    """Spanish-specific customizations for song parsing"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.language_name = "Spanish"

        # Spanish-specific patterns
        self.spanish_words = [
            'dios', 'señor', 'cristo', 'jesús', 'maría', 'santo', 'santa',
            'amén', 'aleluya', 'gloria', 'hosanna', 'padre', 'hijo', 'espíritu'
        ]

        # Common Spanish abbreviations and expansions
        self.text_expansions = {
            'sto.': 'santo',
            'sta.': 'santa',
            'sr.': 'señor',
            'sra.': 'señora',
        }

        # Spanish-specific role processing
        self.role_synonyms = {
            'S.': ['Solista', 'SOLISTA'],
            'A.': ['Asamblea', 'ASAMBLEA'],
            'P.': ['Presbitero', 'PRESBITERO'],
            'Niños:': ['Niños', 'NIÑOS'],
            'Mujeres:': ['Mujeres', 'MUJERES'],
            'Hombres:': ['Hombres', 'HOMBRES'],
        }

        self.logger.debug("Initialized Spanish customizations")

    def apply_customizations(self, verses: List[Verse], document: ParsedDocument) -> List[Verse]:
        """Apply Spanish-specific customizations to parsed verses"""
        self.logger.info(f"Applying Spanish customizations to {len(verses)} verses")

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

        # Spanish-specific: Fix chord chain positioning issues (only for specific files)
        filename = getattr(document, 'filename', '') or getattr(document, 'title', '')

        # Import Spanish config to check if file needs chord chain processing
        from .config import SpanishConfig
        spanish_config = SpanishConfig()

        if spanish_config.requires_chord_chain_processing(filename):
            self.logger.debug(f"Applying chord chain processing to {filename}")
            customized_verses = self._fix_spanish_chord_chains(customized_verses)
        else:
            self.logger.debug(f"Skipping chord chain processing for {filename}")

        self.logger.info(f"Spanish customizations complete: {len(customized_verses)} verses")
        return customized_verses

    def _customize_line(self, line: VerseLine, role: str) -> Optional[VerseLine]:
        """Apply customizations to a single verse line"""
        text = line.text

        # Apply Spanish text processing
        text = self._apply_spanish_text_fixes(text)
        text = self._apply_text_expansions(text)
        text = self._apply_special_responses(text)
        text = self._normalize_spanish_punctuation(text)

        # Handle special Spanish formatting
        text = self._handle_spanish_special_cases(text, role)

        # Create new line with customized text
        return VerseLine(
            text=text,
            chords=line.chords,  # Keep original chords
            original_line=line.original_line,
            line_type=getattr(line, 'line_type', None)
        )
    
    def _apply_spanish_text_fixes(self, text: str) -> str:
        """Apply Spanish-specific text fixes"""
        if not text:
            return text
        
        # Fix common OCR issues in Spanish
        fixes = {
            # Spanish accented characters
            'á': 'á', 'é': 'é', 'í': 'í', 'ó': 'ó', 'ú': 'ú',
            'Á': 'Á', 'É': 'É', 'Í': 'Í', 'Ó': 'Ó', 'Ú': 'Ú',
            'ñ': 'ñ', 'Ñ': 'Ñ',
            # Common OCR mistakes
            'ã': 'á', 'ê': 'é', 'î': 'í', 'ô': 'ó', 'û': 'ú',
            'Ã': 'Á', 'Ê': 'É', 'Î': 'Í', 'Ô': 'Ó', 'Û': 'Ú',
        }
        
        fixed_text = text
        for old, new in fixes.items():
            fixed_text = fixed_text.replace(old, new)
        
        return fixed_text
    
    def _apply_text_expansions(self, text: str) -> str:
        """Apply Spanish text expansions and abbreviations"""
        # Common Spanish abbreviations in liturgical texts
        expansions = {
            'Sto.': 'Santo',
            'Sta.': 'Santa',
            'Sr.': 'Señor',
            'Sra.': 'Señora',
            'Dios': 'Dios',  # Ensure proper capitalization
        }
        
        expanded_text = text
        for abbrev, full in expansions.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            expanded_text = re.sub(pattern, full, expanded_text, flags=re.IGNORECASE)
        
        return expanded_text
    
    def _apply_special_responses(self, text: str) -> str:
        """Handle Spanish-specific liturgical responses"""
        # Common Spanish liturgical responses
        responses = {
            'Amén': 'Amén',
            'Aleluya': 'Aleluya',
            'Gloria': 'Gloria',
            'Hosanna': 'Hosanna',
        }
        
        processed_text = text
        for response in responses:
            # Ensure proper capitalization for liturgical responses
            pattern = r'\b' + re.escape(response.lower()) + r'\b'
            processed_text = re.sub(pattern, response, processed_text, flags=re.IGNORECASE)
        
        return processed_text
    
    def _normalize_spanish_punctuation(self, text: str) -> str:
        """Normalize Spanish punctuation"""
        if not text:
            return text
        
        # Spanish punctuation rules
        text = re.sub(r'\s+', ' ', text)  # Normalize spaces
        text = re.sub(r'\s*,\s*', ', ', text)  # Comma spacing
        text = re.sub(r'\s*\.\s*', '. ', text)  # Period spacing
        text = re.sub(r'\s*:\s*', ': ', text)  # Colon spacing
        text = re.sub(r'\s*;\s*', '; ', text)  # Semicolon spacing
        
        # Spanish question and exclamation marks
        text = re.sub(r'\s*¿\s*', '¿', text)  # Opening question mark
        text = re.sub(r'\s*\?\s*', '? ', text)  # Closing question mark
        text = re.sub(r'\s*¡\s*', '¡', text)  # Opening exclamation mark
        text = re.sub(r'\s*!\s*', '! ', text)  # Closing exclamation mark
        
        return text.strip()

    def _fix_spanish_chord_chains(self, verses: List[Verse]) -> List[Verse]:
        """Fix Spanish chord chain positioning issues (e.g., Do |Mi |Fa patterns)"""

        fixed_verses = []

        for verse in verses:

            fixed_lines = self._fix_chord_chains_in_verse(verse.lines)

            if fixed_lines:
                fixed_verses.append(Verse(
                    role=verse.role,
                    lines=fixed_lines,
                    verse_type=verse.verse_type
                ))

        return fixed_verses

    def _fix_chord_chains_in_verse(self, lines: List[VerseLine]) -> List[VerseLine]:
        """Fix chord chain positioning within a single verse"""
        if len(lines) < 2:
            return lines



        fixed_lines = []
        i = 0

        while i < len(lines):
            current_line = lines[i]


            # Check if this line has a chord chain pattern
            chord_chain_match = self._extract_chord_chain_from_line(current_line)

            if chord_chain_match:
                self.logger.debug(f"🔍 Found chord chain in line: '{current_line.text[:50]}...'")

            if chord_chain_match:
                chord_chain_part, individual_chords, text = chord_chain_match

                # Fix chord chain positioning for this single line
                fixed_line = self._fix_chord_chain_positioning(current_line, chord_chain_part, individual_chords)
                if fixed_line:
                    fixed_lines.append(fixed_line)
                    i += 1
                    continue

            # No chord chain fix needed, add line as-is
            fixed_lines.append(current_line)
            i += 1

        return fixed_lines

    def _extract_chord_chain_from_line(self, line: VerseLine) -> Optional[tuple]:
        """Extract chord chain from line using chord information"""
        # Check if line has chords
        if not line.chords:
            return None

        # Look for chord chains (chords with | character)
        for chord in line.chords:
            if '|' in chord.chord:
                # This is a chord chain - parse it to separate chain from individual chords
                chord_chain_part, individual_chords = self._parse_chord_chain_content(chord.chord)

                if chord_chain_part and self._looks_like_spanish_chord_chain(chord_chain_part):
                    return (chord_chain_part, individual_chords, line.text.strip())

        return None

    def _extract_pipe_part(self, chord_content: str) -> str:
        """Extract the pipe-separated part from chord content"""
        # Find the core pipe-separated pattern (e.g., "Do |Mi |Fa" from "Do |Mi |Fa        Mi")
        import re

        # Look for pattern like "Do |Mi |Fa" (chord |chord |chord)
        pipe_pattern = r'([A-Za-z#–\-]+\s*\|[^|]*\|[^|]*)'
        match = re.search(pipe_pattern, chord_content)

        if match:
            return match.group(1).strip()

        return chord_content

    def _looks_like_spanish_chord_chain(self, chord_chain: str) -> bool:
        """Check if text looks like a Spanish chord chain (Do |Mi |Fa)"""
        # Split by | and check if parts look like Spanish chords
        parts = [part.strip() for part in chord_chain.split('|')]

        if len(parts) < 2:
            return False

        spanish_chord_pattern = r'^(DO|Do|Re|Mi|Fa|Sol|La|Si)([#b]?)([–\-]?)(\d*)$'
        import re

        for part in parts:
            # Each part can be multiple chords separated by spaces
            words = part.split()
            for word in words:
                if word and not re.match(spanish_chord_pattern, word):
                    return False

        return True

    def _combine_chord_chain_lines(self, lines: List[VerseLine], chord_chain: str) -> Optional[VerseLine]:
        """Combine multiple lines with the same chord chain using X-position mapping"""
        if not lines:
            return None

        # Parse the chord chain to separate chain chords from individual chords
        chain_chords, individual_chords = self._parse_chord_chain_content(chord_chain)

        # Collect text parts and their positions from each line
        text_elements = []

        for line in lines:
            chord_chain_match = self._extract_chord_chain_from_line(line)
            if chord_chain_match:
                _, remaining_text = chord_chain_match
                if remaining_text.strip():
                    # For now, we'll combine text parts sequentially
                    # In a more advanced implementation, we'd use X-positions
                    text_elements.append(remaining_text.strip())

        if not text_elements:
            return None

        # Combine text elements
        combined_text = ' '.join(text_elements)

        # Create the new line with proper chord positioning
        # Place chord chain at the beginning, individual chords positioned in text
        if individual_chords:
            # For now, place individual chords at the end
            # In advanced implementation, use X-position mapping
            new_text = f"[{chain_chords}]{combined_text}"

            # Add individual chords as separate chord objects
            individual_chord_objects = []

            # Estimate position for individual chords (simplified)
            estimated_position = len(f"[{chain_chords}]") + len(combined_text) - 10
            estimated_position = max(estimated_position, len(f"[{chain_chords}]"))

            for chord in individual_chords:
                individual_chord_objects.append(Chord(
                    chord=chord,
                    position=estimated_position,
                    pixel_x=0  # Would need actual X-position from PDF
                ))
        else:
            new_text = f"[{chain_chords}]{combined_text}"
            individual_chord_objects = []

        # Create new VerseLine
        combined_line = VerseLine(
            text=new_text,
            chords=individual_chord_objects,
            original_line=lines[0].original_line,
            line_type=getattr(lines[0], 'line_type', None)
        )

        return combined_line

    def _fix_chord_chain_positioning(self, line: VerseLine, chord_chain_part: str, individual_chords: List[str]) -> Optional[VerseLine]:
        """Fix chord chain positioning using Y-coordinate mapping from PDF data"""
        text = line.text.strip()

        # Start with chord chain at the beginning
        new_text = f"[{chord_chain_part}]{text}"
        new_chords = []

        # Adjust positions to account for the added chord chain at the beginning
        chord_chain_length = len(f"[{chord_chain_part}]")

        # Add individual chords based on Y-coordinate positioning
        if individual_chords:

            # Get Y-coordinate information from original line data
            # This requires access to the original PDF span data
            chord_y_positions = self._extract_chord_y_positions(line)
            text_y_positions = self._extract_text_y_positions(line)

            for individual_chord in individual_chords:
                # Find the Y-coordinate of this individual chord
                chord_y = chord_y_positions.get(individual_chord)

                if chord_y is not None:
                    # Find the character position with the most similar Y-coordinate
                    best_position = self._find_best_character_position(text, chord_y, text_y_positions)
                    # Adjust position to account for the chord chain at the beginning
                    adjusted_position = best_position + chord_chain_length

                    new_chords.append(Chord(
                        chord=individual_chord,
                        position=adjusted_position,
                        pixel_x=0  # Y-coordinate based positioning
                    ))
                else:
                    # Fallback to estimation if Y-coordinate not available
                    estimated_position = self._estimate_individual_chord_position(text, individual_chord)
                    # Adjust position to account for the chord chain at the beginning
                    adjusted_position = estimated_position + chord_chain_length

                    new_chords.append(Chord(
                        chord=individual_chord,
                        position=adjusted_position,
                        pixel_x=0
                    ))

        # Create new VerseLine with fixed chord positioning
        fixed_line = VerseLine(
            text=new_text,
            chords=new_chords,
            original_line=line.original_line,
            line_type=getattr(line, 'line_type', None)
        )

        return fixed_line

    def _estimate_individual_chord_position(self, text: str, chord: str) -> int:
        """Estimate position of individual chord within text"""
        # This is a simplified estimation
        # For "Ave María" with "Mi" chord, position should be around "Marí"

        # For Spanish chord chains, individual chords are often positioned
        # towards the end of the combined text due to the spacing
        text_length = len(text)

        # Estimate position as 70-80% through the text
        # This places "Mi" around "Marí[Mi]a" in "Ave María"
        estimated_position = int(text_length * 0.75)

        # Ensure position is within text bounds
        estimated_position = max(0, min(estimated_position, text_length))

        return estimated_position

    def _extract_chord_y_positions(self, line: VerseLine) -> Dict[str, float]:
        """Extract Y-coordinates of individual chords from original PDF data"""
        chord_y_positions = {}

        # Access original line data if available
        if hasattr(line, 'original_line') and line.original_line:
            original_data = line.original_line

            # Look for spans data that contains chord information
            if isinstance(original_data, dict) and 'spans' in original_data:
                spans = original_data['spans']

                for span in spans:
                    span_text = span.get('text', '').strip()
                    span_y = span.get('bbox', [0, 0, 0, 0])[1]  # Y-coordinate

                    # Check if this span contains individual chords (not chord chains)
                    if span_text and not '|' in span_text:
                        # This might be an individual chord
                        if self._looks_like_spanish_chord(span_text):
                            chord_y_positions[span_text] = span_y

        return chord_y_positions

    def _extract_text_y_positions(self, line: VerseLine) -> Dict[int, float]:
        """Extract Y-coordinates for each character position in the text"""
        text_y_positions = {}
        text = line.text.strip()

        # Access original line data if available
        if hasattr(line, 'original_line') and line.original_line:
            original_data = line.original_line

            # Look for spans data that contains text information
            if isinstance(original_data, dict) and 'spans' in original_data:
                spans = original_data['spans']

                current_position = 0
                for span in spans:
                    span_text = span.get('text', '')
                    span_y = span.get('bbox', [0, 0, 0, 0])[1]  # Y-coordinate

                    # Map each character in this span to the span's Y-coordinate
                    for i, char in enumerate(span_text):
                        if current_position < len(text):
                            text_y_positions[current_position] = span_y
                            current_position += 1

        return text_y_positions

    def _find_best_character_position(self, text: str, chord_y: float, text_y_positions: Dict[int, float]) -> int:
        """Find the character position with Y-coordinate closest to the chord Y-coordinate"""
        if not text_y_positions:
            # Fallback to estimation if no Y-coordinate data
            return int(len(text) * 0.75)

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

    def _parse_chord_chain_content(self, chord_content: str) -> tuple:
        """Parse chord content to separate chain chords (with |) from individual chords"""
        import re

        # Find the chord chain part (chords connected by |)
        chain_pattern = r'([A-Za-z#–\-]+(?:\s*\|\s*[A-Za-z#–\-]+)+)'
        chain_match = re.search(chain_pattern, chord_content)

        if chain_match:
            chain_part = chain_match.group(1).strip()

            # Extract individual chords (everything else)
            remaining = chord_content.replace(chain_part, '').strip()
            individual_chords = [chord.strip() for chord in remaining.split() if chord.strip()]

            return chain_part, individual_chords
        else:
            # No chain found, treat all as individual chords
            individual_chords = [chord.strip() for chord in chord_content.split() if chord.strip()]
            return '', individual_chords
    
    def _handle_spanish_special_cases(self, text: str, role: str) -> str:
        """Handle special Spanish text cases"""
        # Handle religious terms capitalization
        religious_terms = [
            ('dios', 'Dios'),
            ('señor', 'Señor'),
            ('cristo', 'Cristo'),
            ('jesús', 'Jesús'),
            ('maría', 'María'),
            ('espíritu santo', 'Espíritu Santo'),
            ('padre', 'Padre'),
            ('hijo', 'Hijo'),
        ]
        
        for term, capitalized in religious_terms:
            # Capitalize at beginning of sentences or standalone
            pattern = r'\b' + re.escape(term) + r'\b'
            text = re.sub(pattern, capitalized, text, flags=re.IGNORECASE)
        
        # Handle special responses for children (Niños)
        if role == 'Niños:' and 'amén' in text.lower():
            # Ensure proper formatting for children's responses
            text = re.sub(r'\bamen\b', 'Amén', text, flags=re.IGNORECASE)
        
        # Handle Presbitero (P.) special formatting
        if role == 'P.':
            # Presbitero responses might need special formatting
            text = self._format_presbitero_text(text)
        
        return text
    
    def _format_presbitero_text(self, text: str) -> str:
        """Format text for Presbitero (P.) role"""
        # Presbitero texts are typically liturgical formulas
        # Ensure proper capitalization of liturgical terms
        liturgical_terms = [
            ('el señor esté con vosotros', 'El Señor esté con vosotros'),
            ('y con tu espíritu', 'Y con tu espíritu'),
            ('levantemos el corazón', 'Levantemos el corazón'),
            ('lo tenemos levantado hacia el señor', 'Lo tenemos levantado hacia el Señor'),
            ('demos gracias al señor', 'Demos gracias al Señor'),
            ('es justo y necesario', 'Es justo y necesario'),
        ]
        
        formatted_text = text
        for phrase, formatted in liturgical_terms:
            pattern = r'\b' + re.escape(phrase) + r'\b'
            formatted_text = re.sub(pattern, formatted, formatted_text, flags=re.IGNORECASE)
        
        return formatted_text
    

