#!/usr/bin/env python3
"""
Universal Songbook Parser CLI

Command-line interface for the new universal parser architecture.
Integrates with existing work.sh workflow for seamless migration.
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from typing import Optional

# Add the git/new_version directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parsers.universal_parser import UniversalParser
from languages.slovenian.config import SlovenianConfig
from languages.croatian.config import CroatianConfig


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Reduce noise from some modules
    logging.getLogger('fitz').setLevel(logging.WARNING)


def get_parser_for_language(language: str) -> UniversalParser:
    """Get parser instance for specified language"""
    language_map = {
        'sl': SlovenianConfig,
        'slovenian': SlovenianConfig,
        'hr': CroatianConfig,
        'croatian': CroatianConfig,
    }
    
    config_class = language_map.get(language.lower())
    if not config_class:
        raise ValueError(f"Unsupported language: {language}")
    
    return UniversalParser(config_class())


def determine_output_path(input_path: str, output_path: Optional[str], 
                         format_type: str, song_name: Optional[str] = None) -> str:
    """Determine the output file path"""
    if output_path:
        # If output path is provided, use it
        if os.path.isdir(output_path):
            # Output is a directory, generate filename
            if song_name:
                filename = f"{song_name}.{format_type}"
            else:
                input_name = Path(input_path).stem
                filename = f"{input_name}.{format_type}"
            return os.path.join(output_path, filename)
        else:
            # Output is a file path
            return output_path
    else:
        # Generate output path based on input
        input_path_obj = Path(input_path)
        return str(input_path_obj.with_suffix(f'.{format_type}'))


def parse_single_file(args) -> int:
    """Parse a single PDF file"""
    try:
        # Get parser for language
        parser = get_parser_for_language(args.language)
        
        # Parse the PDF
        print(f"🎵 Parsing {args.input} with {args.language} parser...")
        song = parser.parse(args.input, args.song_name)
        
        # Validate the parsed song
        issues = parser.validate_song(song)
        if issues:
            print("⚠️  Validation issues found:")
            for issue in issues:
                print(f"   - {issue}")
        
        # Export based on format
        if args.format in ['chordpro', 'both']:
            chordpro_path = determine_output_path(args.input, args.output, 'chordpro', song.title)
            parser.save_chordpro(song, chordpro_path)
            print(f"✅ ChordPro saved to: {chordpro_path}")
        
        if args.format in ['html', 'both']:
            html_path = determine_output_path(args.input, args.output, 'html', song.title)
            parser.save_html(song, html_path)
            print(f"✅ HTML saved to: {html_path}")
        
        # Print statistics if verbose
        if args.verbose:
            stats = parser.get_processing_stats()
            print(f"\n📊 Processing Statistics:")
            for key, value in stats.items():
                print(f"   {key}: {value}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error parsing {args.input}: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def parse_folder(args) -> int:
    """Parse all PDF files in a folder"""
    input_dir = Path(args.input)
    if not input_dir.is_dir():
        print(f"❌ Input path is not a directory: {args.input}")
        return 1
    
    # Find all PDF files
    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ No PDF files found in: {args.input}")
        return 1
    
    print(f"🎵 Found {len(pdf_files)} PDF files to process")
    
    # Create output directory if needed
    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get parser for language
    parser = get_parser_for_language(args.language)
    
    # Process each file
    processed = 0
    failed = 0
    
    for pdf_file in pdf_files:
        try:
            print(f"\n🎵 Processing: {pdf_file.name}")
            
            # Parse the PDF
            song = parser.parse(str(pdf_file), args.song_name)
            
            # Export based on format
            if args.format in ['chordpro', 'both']:
                chordpro_path = determine_output_path(str(pdf_file), args.output, 'chordpro', song.title)
                parser.save_chordpro(song, chordpro_path)
                print(f"   ✅ ChordPro: {Path(chordpro_path).name}")
            
            if args.format in ['html', 'both']:
                html_path = determine_output_path(str(pdf_file), args.output, 'html', song.title)
                parser.save_html(song, html_path)
                print(f"   ✅ HTML: {Path(html_path).name}")
            
            processed += 1
            
        except Exception as e:
            print(f"   ❌ Failed: {str(e)}")
            failed += 1
            if args.verbose:
                import traceback
                traceback.print_exc()
    
    # Print summary
    print(f"\n📊 Batch Processing Complete:")
    print(f"   ✅ Processed: {processed} files")
    print(f"   ❌ Failed: {failed} files")
    print(f"   📁 Output: {args.output or 'same as input'}")
    
    return 0 if failed == 0 else 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Universal Songbook PDF Parser",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse single Slovenian PDF to ChordPro
  %(prog)s -i song.pdf -l sl -f chordpro
  
  # Parse Croatian PDF to both formats
  %(prog)s -i song.pdf -l hr -f both -o output/
  
  # Parse folder of Slovenian PDFs
  %(prog)s -i pdfs/ -l sl -f chordpro -o chordpro_output/
  
  # Integration with work.sh (replace old parser calls)
  %(prog)s -i "$input_file" -l sl -f chordpro -o "$output_file"
        """
    )
    
    # Input/Output arguments
    parser.add_argument("--input", "-i", required=True,
                       help="Input PDF file or directory")
    parser.add_argument("--output", "-o",
                       help="Output file or directory (optional)")
    
    # Language selection
    parser.add_argument("--language", "-l", default="sl",
                       choices=["sl", "slovenian", "hr", "croatian"],
                       help="Language for parsing (default: sl)")
    
    # Format selection
    parser.add_argument("--format", "-f", default="chordpro",
                       choices=["chordpro", "html", "both"],
                       help="Output format (default: chordpro)")
    
    # Optional parameters
    parser.add_argument("--song-name", "-s",
                       help="Override song name")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    
    # Batch processing
    parser.add_argument("--batch", "-b", action="store_true",
                       help="Process all PDFs in input directory")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Validate input
    if not os.path.exists(args.input):
        print(f"❌ Input path does not exist: {args.input}")
        return 1
    
    # Determine processing mode
    if args.batch or os.path.isdir(args.input):
        return parse_folder(args)
    else:
        return parse_single_file(args)


if __name__ == "__main__":
    sys.exit(main())
