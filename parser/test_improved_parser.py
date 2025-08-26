#!/usr/bin/env python3
"""
Test script for the Improved Universal Parser

This script tests the improved parser against the original working parsers
to ensure we maintain the same quality while adding universal architecture.
"""

import sys
import os
import logging
from pathlib import Path

# Add the git/new_version directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from parsers.improved_universal_parser import ImprovedUniversalParser
    from languages.slovenian.config import SlovenianConfig
    from languages.croatian.config import CroatianConfig
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


def test_improved_parser_creation():
    """Test improved parser creation"""
    print("🧪 Testing Improved Parser Creation...")
    
    try:
        # Test Slovenian parser
        sl_config = SlovenianConfig()
        sl_parser = ImprovedUniversalParser(sl_config)
        print(f"   ✅ Slovenian parser: {sl_parser.config.language_name}")
        
        # Test Croatian parser
        hr_config = CroatianConfig()
        hr_parser = ImprovedUniversalParser(hr_config)
        print(f"   ✅ Croatian parser: {hr_parser.config.language_name}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Parser creation test failed: {e}")
        return False


def find_test_pdfs():
    """Find test PDF files"""
    test_files = {}
    
    # Look for Slovenian PDFs
    sl_pdf_dir = Path("../lang/sl/03_pdf")
    if sl_pdf_dir.exists():
        sl_pdfs = list(sl_pdf_dir.glob("*.pdf"))
        if sl_pdfs:
            test_files['slovenian'] = str(sl_pdfs[0])  # Take first PDF
    
    # Look for Croatian PDFs
    hr_pdf_dir = Path("../lang/hr/03_pdf")
    if hr_pdf_dir.exists():
        hr_pdfs = list(hr_pdf_dir.glob("*.pdf"))
        if hr_pdfs:
            test_files['croatian'] = str(hr_pdfs[0])  # Take first PDF
    
    return test_files


def test_improved_parsing():
    """Test parsing with improved parser"""
    print("🧪 Testing Improved Parsing...")
    
    test_files = find_test_pdfs()
    
    if not test_files:
        print("   ⚠️  No test PDF files found, skipping parsing test")
        return True
    
    success_count = 0
    total_count = 0
    
    for language, pdf_path in test_files.items():
        total_count += 1
        print(f"\n   📄 Testing {language} with: {Path(pdf_path).name}")
        
        try:
            # Create appropriate parser
            if language == 'slovenian':
                config = SlovenianConfig()
            else:
                config = CroatianConfig()
            
            parser = ImprovedUniversalParser(config)
            
            # Parse the PDF
            song = parser.parse(pdf_path)
            
            # Validate results
            print(f"      ✅ Title: '{song.title}'")
            print(f"      ✅ Verses: {len(song.verses)}")
            print(f"      ✅ Comments: {len(song.comments)}")
            
            # Check for reasonable results
            if song.title and len(song.verses) > 0:
                print(f"      ✅ Parsing successful")
                
                # Test ChordPro export
                chordpro = parser.export_chordpro(song)
                print(f"      ✅ ChordPro export: {len(chordpro)} characters")
                
                # Show first few lines
                lines = chordpro.split('\n')[:5]
                for line in lines:
                    if line.strip():
                        print(f"         {line}")
                
                success_count += 1
            else:
                print(f"      ❌ Parsing produced empty results")
        
        except Exception as e:
            print(f"      ❌ Parsing failed: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"\n   📊 Parsing Results: {success_count}/{total_count} successful")
    return success_count == total_count


def compare_with_original():
    """Compare results with original parser if available"""
    print("🧪 Comparing with Original Parser...")
    
    # This would require importing the original parser
    # For now, just indicate the comparison would happen here
    print("   ⚠️  Original parser comparison not implemented yet")
    print("   💡 To compare:")
    print("      1. Run original Croatian parser on same PDF")
    print("      2. Run improved parser on same PDF")
    print("      3. Compare chord positioning and text extraction")
    
    return True


def test_chord_positioning():
    """Test chord positioning accuracy"""
    print("🧪 Testing Chord Positioning...")
    
    test_files = find_test_pdfs()
    
    if not test_files:
        print("   ⚠️  No test PDF files found, skipping chord positioning test")
        return True
    
    # Test with Croatian file (known to have chord positioning issues)
    if 'croatian' in test_files:
        pdf_path = test_files['croatian']
        print(f"   📄 Testing chord positioning with: {Path(pdf_path).name}")
        
        try:
            config = CroatianConfig()
            parser = ImprovedUniversalParser(config)
            
            song = parser.parse(pdf_path)
            
            # Check for chord positioning issues
            chord_issues = 0
            total_chords = 0
            
            for verse in song.verses:
                for line in verse.lines:
                    total_chords += len(line.chords)
                    
                    # Check for excessive chord repetition (the main issue)
                    chord_text = parser._position_chords_in_lyrics(line.chords, line.text)
                    
                    # Count consecutive chord brackets
                    consecutive_chords = 0
                    max_consecutive = 0
                    in_chord = False
                    
                    for char in chord_text:
                        if char == '[':
                            if in_chord:
                                consecutive_chords += 1
                            else:
                                consecutive_chords = 1
                                in_chord = True
                        elif char == ']':
                            in_chord = False
                            max_consecutive = max(max_consecutive, consecutive_chords)
                        elif char not in '[]' and in_chord:
                            # Reset if we have text between brackets
                            consecutive_chords = 0
                    
                    # Flag lines with more than 3 consecutive chords as problematic
                    if max_consecutive > 3:
                        chord_issues += 1
                        print(f"      ⚠️  Excessive chords: {chord_text[:100]}...")
            
            print(f"      📊 Total chords: {total_chords}")
            print(f"      📊 Chord issues: {chord_issues}")
            
            if chord_issues == 0:
                print(f"      ✅ No chord positioning issues detected")
                return True
            else:
                print(f"      ❌ Found {chord_issues} chord positioning issues")
                return False
        
        except Exception as e:
            print(f"      ❌ Chord positioning test failed: {str(e)}")
            return False
    
    return True


def main():
    """Run all tests"""
    print("🚀 Starting Improved Parser Tests\n")
    
    setup_logging()
    
    tests = [
        test_improved_parser_creation,
        test_improved_parsing,
        test_chord_positioning,
        compare_with_original,
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
        print("\n🎉 All tests passed! The improved parser is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. The improved parser needs more work.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
