"""
Base class for file-specific customizations

This allows us to handle special cases for specific PDF files without
cluttering the main parser with edge case logic.
"""

from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod


class BaseCustomization(ABC):
    """Base class for file-specific parsing customizations"""
    
    def __init__(self, language_code: str):
        self.language_code = language_code
    
    @abstractmethod
    def applies_to_file(self, filename: str) -> bool:
        """Check if this customization applies to the given filename"""
        pass
    
    def customize_span_data(self, span_data: Dict) -> Dict:
        """Customize the extracted span data before parsing"""
        return span_data
    
    def customize_text_lines(self, text_lines: List[Dict]) -> List[Dict]:
        """Customize text lines after extraction"""
        return text_lines
    
    def customize_verse_text(self, text: str, line_data: Dict) -> str:
        """Customize individual verse text lines"""
        return text
    
    def customize_song(self, song: Any) -> Any:
        """Customize the final song object"""
        return song
    
    def get_description(self) -> str:
        """Get a description of what this customization does"""
        return f"Base customization for {self.language_code}"


class CustomizationManager:
    """Manages file-specific customizations"""
    
    def __init__(self):
        self.customizations = []
    
    def register_customization(self, customization: BaseCustomization):
        """Register a new customization"""
        self.customizations.append(customization)
    
    def get_customization_for_file(self, filename: str) -> Optional[BaseCustomization]:
        """Get the appropriate customization for a file"""
        for customization in self.customizations:
            if customization.applies_to_file(filename):
                return customization
        return None
    
    def list_customizations(self) -> List[str]:
        """List all registered customizations"""
        return [c.get_description() for c in self.customizations]


# Global customization manager
customization_manager = CustomizationManager()
