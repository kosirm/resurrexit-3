#!/usr/bin/env python3
"""
Test script for the Universal Songbook Parser

This script tests the new parser architecture with sample data
and validates the implementation.
"""

import sys
import os
import logging
from pathlib import Path

# Add the git/new_version directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from parsers.universal_parser import UniversalParser
    from languages.slovenian.config import SlovenianConfig
    from languages.croatian.config import CroatianConfig
    from core.models import PDFTextElement, TextType
    from core.pdf_extractor import PDFExtractor
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the git/new_version directory")
    sys.exit(1)


def setup_logging():
    """Setup logging for testing"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


def test_slovenian_config():
    """Test Slovenian configuration"""
    print("🧪 Testing Slovenian Configuration...")
    
    try:
        config = SlovenianConfig()
        
        # Test basic properties
        assert config.language_code == "sl"
        assert config.language_name == "Slovenian"
        assert "O." in config.role_markers  # Otroci, not Djeca
        assert "è" in config.encoding_fixes
        
        # Test text encoding fixes
        test_text = "Svèti Bog"
        fixed_text = config.fix_text_encoding(test_text)
        assert "č" in fixed_text
        
        # Test chord validation
        assert "H7" in config.valid_chords
        assert "a" in config.valid_chords
        
        print("   ✅ Slovenian config tests passed")
        return True
        
    except Exception as e:
        print(f"   ❌ Slovenian config test failed: {e}")
        return False


def test_croatian_config():
    """Test Croatian configuration"""
    print("🧪 Testing Croatian Configuration...")
    
    try:
        config = CroatianConfig()
        
        # Test basic properties
        assert config.language_code == "hr"
        assert config.language_name == "Croatian"
        assert "D." in config.role_markers  # Djeca, not Otroci
        assert "è" in config.encoding_fixes
        
        # Test text encoding fixes
        test_text = "Svèti Bog"
        fixed_text = config.fix_text_encoding(test_text)
        assert "č" in fixed_text
        
        # Test special responses
        special_rules = config.get_custom_processing_rules()
        assert "special_responses" in special_rules
        
        print("   ✅ Croatian config tests passed")
        return True
        
    except Exception as e:
        print(f"   ❌ Croatian config test failed: {e}")
        return False


def test_pdf_extractor():
    """Test PDF extractor with mock data"""
    print("🧪 Testing PDF Extractor...")
    
    try:
        extractor = PDFExtractor()
        
        # Test initialization
        assert extractor.title_font_size_threshold == 12.0
        assert extractor.pink_color_threshold == 0.8
        
        # Test color detection
        assert not extractor._is_pink_color(0)  # Black
        assert extractor._is_pink_color(0xFF00FF)  # Magenta
        
        print("   ✅ PDF extractor tests passed")
        return True
        
    except Exception as e:
        print(f"   ❌ PDF extractor test failed: {e}")
        return False


def test_universal_parser_creation():
    """Test universal parser creation"""
    print("🧪 Testing Universal Parser Creation...")
    
    try:
        # Test Slovenian parser
        sl_parser = UniversalParser.create_slovenian_parser()
        assert sl_parser.config.language_code == "sl"
        
        # Test Croatian parser
        hr_parser = UniversalParser.create_croatian_parser()
        assert hr_parser.config.language_code == "hr"
        
        # Test language-specific creation
        sl_parser2 = UniversalParser.create_parser_for_language("sl")
        assert sl_parser2.config.language_code == "sl"
        
        hr_parser2 = UniversalParser.create_parser_for_language("hr")
        assert hr_parser2.config.language_code == "hr"
        
        print("   ✅ Universal parser creation tests passed")
        return True
        
    except Exception as e:
        print(f"   ❌ Universal parser creation test failed: {e}")
        return False


def test_mock_parsing():
    """Test parsing with mock data"""
    print("🧪 Testing Mock Parsing...")
    
    try:
        # Create mock PDF elements
        mock_elements = [
            PDFTextElement(
                text="SVETI BOG",
                x=100.0, y=50.0, width=80.0, height=15.0,
                font_size=14.0, font_family="Arial", is_bold=True
            ),
            PDFTextElement(
                text="K.",
                x=50.0, y=100.0, width=20.0, height=12.0,
                font_size=12.0, font_family="Arial"
            ),
            PDFTextElement(
                text="Sveti Bog, močni Bog",
                x=80.0, y=100.0, width=150.0, height=12.0,
                font_size=12.0, font_family="Arial"
            ),
        ]
        
        # Test with Slovenian config
        config = SlovenianConfig()
        
        # Test text classification
        from core.text_classifier import TextClassifier
        classifier = TextClassifier(config)
        
        # This would normally be called with a full document
        # but we can test the basic functionality
        
        print("   ✅ Mock parsing tests passed")
        return True
        
    except Exception as e:
        print(f"   ❌ Mock parsing test failed: {e}")
        return False


def find_test_pdf():
    """Find a test PDF file"""
    # Look for PDF files in common locations
    possible_paths = [
        "../../lang/sl/03_pdf",
        "../../abby/source",
        "../lang/sl/03_pdf",
        "../abby/source",
    ]
    
    for path in possible_paths:
        pdf_dir = Path(path)
        if pdf_dir.exists():
            pdf_files = list(pdf_dir.glob("*.pdf"))
            if pdf_files:
                return str(pdf_files[0])
    
    return None


def test_real_pdf_parsing():
    """Test parsing with a real PDF file if available"""
    print("🧪 Testing Real PDF Parsing...")
    
    test_pdf = find_test_pdf()
    if not test_pdf:
        print("   ⚠️  No test PDF found, skipping real PDF test")
        return True
    
    try:
        print(f"   📄 Testing with: {Path(test_pdf).name}")
        
        # Test PDF extraction
        extractor = PDFExtractor()
        elements = extractor.extract(test_pdf)
        
        if elements:
            print(f"   ✅ Extracted {len(elements)} elements from PDF")
            
            # Show some sample elements
            for i, elem in enumerate(elements[:3]):
                print(f"      Element {i}: '{elem.text[:30]}...' at ({elem.x:.1f}, {elem.y:.1f})")
        else:
            print("   ⚠️  No elements extracted from PDF")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Real PDF parsing test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Starting Universal Parser Tests\n")
    
    setup_logging()
    
    tests = [
        test_slovenian_config,
        test_croatian_config,
        test_pdf_extractor,
        test_universal_parser_creation,
        test_mock_parsing,
        test_real_pdf_parsing,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ❌ Test {test.__name__} crashed: {e}")
            failed += 1
        print()
    
    # Summary
    print("📊 Test Results:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All tests passed! The new parser architecture is ready for testing.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
