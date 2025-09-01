# Chord Normalization in Parser

## Overview

This document describes the chord normalization system implemented in the parser to ensure consistent chord formatting across all languages for future chord conversion and transposition features.

## Design Principles

### 1. Input Flexibility, Output Consistency
- **Accept**: Various input formats from PDF/OCR (spaced, merged, mixed)
- **Output**: Consistent internal standard format for all languages

### 2. Language-Specific Implementation
- Each language has its own chord normalization logic
- Normalization happens in language-specific customization files
- Common patterns can be shared, but implementation is per-language

### 3. Two-Stage Process
1. **Detection**: Identify chord patterns in PDF text
2. **Normalization**: Convert to consistent internal format

## Italian Implementation (Reference)

### Input Formats Accepted
```
PDF Input           → Normalized Output
"Fa maj 7"         → [Fa maj7]
"Fa maj7"          → [Fa maj7]
"Re m 9"           → [Re m9]
"Re m9"            → [Re m9]
"Rem9"             → [Re m9]
"(Sol 7)"          → [(Sol7)]
```

### Normalization Rules

#### Major Chords (no spaces in extensions)
- `maj7`, `dim7`, `aug7`, `sus4`, `add9`
- Examples: `[Fa maj7]`, `[Sol dim7]`, `[La aug7]`

#### Minor Chords (space before 'm', no space after 'm')
- Keep space before `m` for readability
- Remove spaces after `m` in extensions
- Examples: `[Re m]`, `[Mi m7]`, `[La m maj7]`

#### Parentheses Chords
- Normalize internal content, keep parentheses
- Example: `"(Sol 7)"` → `[(Sol7)]`

### Implementation Files

#### 1. Chord Detection (`improved_pdf_extractor.py`)
```python
# Italian-specific chord detection
if self.config.language_code == "it":
    # Handle spaced chord extensions (e.g., "Fa maj 7")
    if len(words) >= 3:
        if self._looks_like_italian_chord(words[0]):
            if words[1] in ['maj', 'min', 'dim'] and words[2].isdigit():
                return True
```

#### 2. Chord Position Finding (`improved_pdf_extractor.py`)
```python
def _find_italian_chord_positions(self, chord_span_text: str):
    # Split by multiple spaces to identify chord units
    chord_units = re.split(r'\s{4,}', text)
    
    for unit in chord_units:
        if self._looks_like_italian_chord_unit(unit):
            normalized_chord = self._normalize_merged_italian_chord_in_extractor(unit)
```

#### 3. Chord Normalization (`italian/customizations.py`)
```python
def _normalize_italian_chord(self, chord_text: str) -> str:
    # Remove brackets, normalize format, return without brackets
    normalized_chord = self._normalize_italian_chord_format(clean_chord)
    return normalized_chord

def _normalize_italian_chord_format(self, chord: str) -> str:
    # Main normalization logic
    if remaining.startswith('m'):
        return self._normalize_minor_chord(root_with_accidental, remaining)
    return self._normalize_major_chord(root_with_accidental, remaining)
```

## Implementation Guide for Other Languages

### Step 1: Update Chord Detection
In `improved_pdf_extractor.py`, add language-specific detection:
```python
if self.config.language_code == "es":  # Spanish
    # Add Spanish chord detection patterns
    pass
```

### Step 2: Add Chord Position Finding
Implement language-specific chord position finding if needed:
```python
def _find_spanish_chord_positions(self, chord_span_text: str):
    # Spanish-specific chord positioning logic
    pass
```

### Step 3: Implement Normalization
In `languages/{lang}/customizations.py`:
```python
def _normalize_{lang}_chord_format(self, chord: str) -> str:
    # Language-specific normalization rules
    pass
```

### Step 4: Define Language Standards
Document the normalization rules for each language:
- Croatian: `{comment: Kapodaster na II polje}` format (existing)
- Spanish: TBD - review existing chord patterns
- Slovenian: TBD - review existing chord patterns

## Testing Approach

### 1. Input Variation Testing
Test all possible input formats:
- Spaced: `"Fa maj 7"`
- Merged: `"Fa maj7"`
- Mixed: `"Fa  maj   7"` (multiple spaces)
- Parentheses: `"(Sol 7)"`

### 2. Output Consistency Testing
Verify all variations produce the same normalized output:
```
"Fa maj 7" → [Fa maj7]
"Fa maj7"  → [Fa maj7]
"Famaj7"   → [Fa maj7]
```

### 3. Chord Summary Verification
Check that chord summaries show normalized format:
```
📊 Chords: Fa, Fa maj7, La m, La7, Mi, Re m
```

## Future Considerations

### Chord Conversion System
The normalized format will enable:
- **Transposition**: `[Fa maj7]` → `[Sol maj7]` (up one tone)
- **Notation Conversion**: `[Fa maj7]` → `[F maj7]` (Italian → English)
- **Chord Analysis**: Consistent format for harmonic analysis

### Cross-Language Pairing
When pairing songs across languages:
- Italian: `[Fa maj7]`
- Croatian: `{comment: Kapodaster na II polje}` → `{capo: 4}`
- Spanish: TBD
- Slovenian: TBD

## Maintenance Notes

### Adding New Chord Types
1. Update detection patterns in PDF extractor
2. Add normalization rules in language customizations
3. Update test cases
4. Document the new format

### Debugging Chord Issues
1. Check PDF extraction logs for chord detection
2. Verify chord positioning in debug output
3. Test normalization with various input formats
4. Validate final ChordPro output

## Status by Language

- ✅ **Italian**: Complete implementation with full normalization
- 🔄 **Croatian**: Existing kapodaster format, needs chord normalization review
- ⏳ **Spanish**: Needs implementation
- ⏳ **Slovenian**: Needs implementation
