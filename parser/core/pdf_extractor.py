"""
PDF Extractor for Universal Songbook Parser

This module extracts raw text elements from PDF files using PyMuPDF,
providing pixel-precise positioning data for both text and chords.
"""

import fitz  # PyMuPDF
import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

from core.models import PDFTextElement


class PDFExtractor:
    """
    Extracts raw text elements from PDF files with precise positioning.
    
    This class handles the low-level PDF parsing and provides structured
    text elements with pixel coordinates, font information, and formatting.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Font size thresholds for classification hints
        self.title_font_size_threshold = 12.0
        self.text_font_size_threshold = 10.0
        
        # Color detection for special formatting
        self.pink_color_threshold = 0.8  # RGB threshold for pink detection
        
    def extract(self, pdf_path: str) -> List[PDFTextElement]:
        """
        Extract all text elements from PDF with positioning data.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of PDFTextElement objects with positioning and formatting data
        """
        self.logger.info(f"Extracting text from PDF: {pdf_path}")
        
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        elements = []
        
        try:
            # Open PDF document
            doc = fitz.open(pdf_path)
            self.logger.debug(f"Opened PDF with {len(doc)} pages")
            
            # Process each page
            for page_num in range(len(doc)):
                page_elements = self._extract_page_elements(doc[page_num], page_num + 1)
                elements.extend(page_elements)
                self.logger.debug(f"Page {page_num + 1}: extracted {len(page_elements)} elements")
            
            doc.close()
            
        except Exception as e:
            self.logger.error(f"Error extracting from PDF {pdf_path}: {str(e)}")
            raise
        
        self.logger.info(f"Extracted {len(elements)} text elements from PDF")
        return elements
    
    def _extract_page_elements(self, page: fitz.Page, page_number: int) -> List[PDFTextElement]:
        """
        Extract text elements from a single page.
        
        Args:
            page: PyMuPDF page object
            page_number: Page number (1-based)
            
        Returns:
            List of PDFTextElement objects for this page
        """
        elements = []
        
        # Get text with detailed formatting information
        text_dict = page.get_text("dict")
        
        # Process each block
        for block in text_dict["blocks"]:
            if "lines" not in block:
                continue  # Skip image blocks
                
            # Process each line in the block
            for line in block["lines"]:
                # Process each span (text with consistent formatting)
                for span in line["spans"]:
                    element = self._create_text_element(span, page_number)
                    if element and element.text.strip():  # Only add non-empty elements
                        elements.append(element)
        
        return elements
    
    def _create_text_element(self, span: Dict[str, Any], page_number: int) -> Optional[PDFTextElement]:
        """
        Create a PDFTextElement from a PyMuPDF span.
        
        Args:
            span: PyMuPDF span dictionary
            page_number: Page number (1-based)
            
        Returns:
            PDFTextElement or None if invalid
        """
        try:
            # Extract basic text and positioning
            text = span.get("text", "").strip()
            if not text:
                return None
            
            bbox = span.get("bbox", [0, 0, 0, 0])
            x, y, x1, y1 = bbox
            width = x1 - x
            height = y1 - y
            
            # Extract font information
            font_size = span.get("size", 10.0)
            font_family = span.get("font", "")
            flags = span.get("flags", 0)
            
            # Determine formatting
            is_bold = bool(flags & 2**4)  # Bold flag
            
            # Detect pink color (for chord highlighting)
            color = span.get("color", 0)
            is_pink = self._is_pink_color(color)
            
            return PDFTextElement(
                text=text,
                x=float(x),
                y=float(y),
                width=float(width),
                height=float(height),
                font_size=float(font_size),
                font_family=font_family,
                is_bold=is_bold,
                is_pink=is_pink,
                page_number=page_number
            )
            
        except Exception as e:
            self.logger.warning(f"Error creating text element from span: {str(e)}")
            return None
    
    def _is_pink_color(self, color: int) -> bool:
        """
        Determine if a color value represents pink/magenta.
        
        Args:
            color: Color value from PyMuPDF
            
        Returns:
            True if the color is considered pink
        """
        if color == 0:
            return False  # Black text
        
        # Convert color to RGB
        # PyMuPDF uses integer color values
        try:
            # Extract RGB components
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            
            # Normalize to 0-1 range
            r_norm = r / 255.0
            g_norm = g / 255.0
            b_norm = b / 255.0
            
            # Check if it's pinkish (high red, low green, high blue)
            return (r_norm > self.pink_color_threshold and 
                    g_norm < 0.5 and 
                    b_norm > self.pink_color_threshold)
                    
        except Exception:
            return False
    
    def get_page_dimensions(self, pdf_path: str) -> List[Tuple[float, float]]:
        """
        Get dimensions of all pages in the PDF.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of (width, height) tuples for each page
        """
        dimensions = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                rect = page.rect
                dimensions.append((rect.width, rect.height))
            
            doc.close()
            
        except Exception as e:
            self.logger.error(f"Error getting page dimensions: {str(e)}")
            raise
        
        return dimensions
    
    def extract_images(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract image information from PDF (for debugging/analysis).
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of image information dictionaries
        """
        images = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    images.append({
                        'page': page_num + 1,
                        'index': img_index,
                        'xref': img[0],
                        'smask': img[1],
                        'width': img[2],
                        'height': img[3],
                        'bpc': img[4],
                        'colorspace': img[5],
                        'alt': img[6],
                        'name': img[7],
                        'filter': img[8]
                    })
            
            doc.close()
            
        except Exception as e:
            self.logger.error(f"Error extracting images: {str(e)}")
            raise
        
        return images
    
    def get_extraction_stats(self, elements: List[PDFTextElement]) -> Dict[str, Any]:
        """
        Get statistics about extracted elements.
        
        Args:
            elements: List of extracted PDFTextElement objects
            
        Returns:
            Dictionary with extraction statistics
        """
        if not elements:
            return {'total_elements': 0}
        
        # Count elements by page
        pages = {}
        font_sizes = []
        font_families = set()
        bold_count = 0
        pink_count = 0
        
        for element in elements:
            # Page counts
            page = element.page_number
            pages[page] = pages.get(page, 0) + 1
            
            # Font statistics
            font_sizes.append(element.font_size)
            font_families.add(element.font_family)
            
            # Formatting counts
            if element.is_bold:
                bold_count += 1
            if element.is_pink:
                pink_count += 1
        
        return {
            'total_elements': len(elements),
            'pages': len(pages),
            'elements_per_page': pages,
            'font_sizes': {
                'min': min(font_sizes) if font_sizes else 0,
                'max': max(font_sizes) if font_sizes else 0,
                'avg': sum(font_sizes) / len(font_sizes) if font_sizes else 0
            },
            'font_families': list(font_families),
            'bold_elements': bold_count,
            'pink_elements': pink_count,
            'text_length': {
                'min': min(len(e.text) for e in elements) if elements else 0,
                'max': max(len(e.text) for e in elements) if elements else 0,
                'avg': sum(len(e.text) for e in elements) / len(elements) if elements else 0
            }
        }
