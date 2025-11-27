#!/usr/bin/env python3
"""
Create a zip archive of the entire project.
Run this on PythonAnywhere, then download the zip file.
"""
import os
import zipfile
from pathlib import Path
from datetime import datetime

def create_project_archive():
    # Get current directory (project root)
    project_dir = Path.cwd()
    project_name = project_dir.name
    
    # Create archive name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"{project_name}_backup_{timestamp}.zip"
    
    print(f"📦 Creating archive: {archive_name}")
    print(f"📁 From directory: {project_dir}")
    print()
    
    # Files/dirs to exclude
    exclude_patterns = {
        '__pycache__',
        '.git',
        '.pytest_cache',
        'venv',
        'env',
        '.venv',
        '*.pyc',
        '.DS_Store',
        'temp_media',
        '*.log'
    }
    
    # Create zip file
    with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        file_count = 0
        
        for root, dirs, files in os.walk(project_dir):
            # Remove excluded directories from walk
            dirs[:] = [d for d in dirs if d not in exclude_patterns and not d.startswith('.')]
            
            # Calculate relative path
            rel_root = Path(root).relative_to(project_dir)
            
            for file in files:
                # Skip excluded files
                if file in exclude_patterns or file.startswith('.'):
                    continue
                if file.endswith('.pyc') or file.endswith('.log'):
                    continue
                
                file_path = Path(root) / file
                arc_name = rel_root / file
                
                try:
                    zipf.write(file_path, arc_name)
                    file_count += 1
                    if file_count % 10 == 0:
                        print(f"  Added {file_count} files...")
                except Exception as e:
                    print(f"  ⚠️  Skipped {file_path}: {e}")
        
        print(f"\n✅ Archive created successfully!")
        print(f"📊 Total files: {file_count}")
        print(f"💾 Archive size: {os.path.getsize(archive_name) / (1024*1024):.2f} MB")
        print(f"\n📥 Download this file from PythonAnywhere:")
        print(f"   {archive_name}")
        print(f"\n🔗 Path: /home/abdurakhmon70/telegram-addresser/{archive_name}")

if __name__ == "__main__":
    create_project_archive()

