"""
Spanish Language Customizations for PDF Parser
Handles Spanish-specific text processing, chord normalization, and formatting
"""

import re
import logging
from typing import List, Optional, Dict, Any
from core.models import Verse, VerseLine, ParsedDocument, TextType, ClassifiedText
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
    

