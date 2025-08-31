#!/usr/bin/env python3
"""
Download Italian PDF files from Risuscito website
"""

import os
import re
import requests
import time
from pathlib import Path
from urllib.parse import urlparse

def extract_pdf_urls_from_search_file(search_file_path):
    """Extract PDF URLs from the code-search results file"""
    pdf_urls = []
    
    with open(search_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all PDF URLs using regex
    pdf_pattern = r'https://cdn\.risuscito\.it/risuscito-it/media/[^"]+\.pdf'
    urls = re.findall(pdf_pattern, content)
    
    # Remove duplicates while preserving order
    seen = set()
    for url in urls:
        if url not in seen:
            pdf_urls.append(url)
            seen.add(url)
    
    return pdf_urls

def get_song_name_from_url(url):
    """Extract song name from PDF URL for filename"""
    # Extract filename from URL
    filename = os.path.basename(urlparse(url).path)
    # Remove .pdf extension
    song_name = filename.replace('.pdf', '')
    return song_name

def download_pdf(url, output_dir, index):
    """Download a single PDF file"""
    try:
        song_name = get_song_name_from_url(url)
        
        # Create filename with Italian prefix and index
        filename = f"IT - {index:03d} - {song_name.upper()}.pdf"
        output_path = os.path.join(output_dir, filename)
        
        # Skip if file already exists
        if os.path.exists(output_path):
            print(f"⏭️  Skipping {filename} (already exists)")
            return True
        
        print(f"📥 Downloading {filename}...")
        
        # Download with headers to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Save the PDF file
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ Downloaded {filename} ({len(response.content)} bytes)")
        return True
        
    except Exception as e:
        print(f"❌ Failed to download {url}: {str(e)}")
        return False

def main():
    """Main function to download all PDF files"""
    # Paths
    script_dir = Path(__file__).parent
    search_file = script_dir / "02_source" / "RISUSCITO" / "pdf_files.code-search"
    output_dir = script_dir / "03_pdf"
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    print("🎵 Italian PDF Downloader for Risuscito Songs")
    print("=" * 50)
    
    # Extract PDF URLs
    print(f"📖 Reading PDF URLs from: {search_file}")
    pdf_urls = extract_pdf_urls_from_search_file(search_file)
    
    print(f"🔍 Found {len(pdf_urls)} unique PDF files to download")
    print(f"📁 Output directory: {output_dir}")
    print()
    
    # Download each PDF
    successful_downloads = 0
    failed_downloads = 0
    
    for i, url in enumerate(pdf_urls, 1):
        if download_pdf(url, output_dir, i):
            successful_downloads += 1
        else:
            failed_downloads += 1
        
        # Small delay to be respectful to the server
        time.sleep(0.5)
    
    # Summary
    print()
    print("📊 Download Summary:")
    print(f"   ✅ Successful: {successful_downloads}")
    print(f"   ❌ Failed: {failed_downloads}")
    print(f"   📁 Output directory: {output_dir}")
    
    if successful_downloads > 0:
        print()
        print("🎉 Downloads completed! You can now use these files with the Italian parser.")
        print("   Next steps:")
        print("   1. Check the downloaded files in git/lang/it/03_pdf/")
        print("   2. Run: ./work.sh parsefolder it")

if __name__ == "__main__":
    main()
