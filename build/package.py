#!/usr/bin/env python3
"""
Package script for CK3 Coat of Arms Editor
- Gets version from git (tags or commit hash)
- Zips the build output with version number
"""
import subprocess
import shutil
import os
import sys
from pathlib import Path
from datetime import datetime


def get_git_version():
    """Get version string from git
    
    Returns version in format:
    - If on a tag: v1.2.3
    - If commits after tag: v1.2.3-5-gabcdef
    - If no tags: 0.0.0-abcdef
    """
    try:
        # Try to get the current tag
        result = subprocess.run(
            ['git', 'describe', '--tags', '--always', '--dirty'],
            capture_output=True,
            text=True,
            check=True
        )
        version = result.stdout.strip()
        
        # Clean up version string
        if version.startswith('v'):
            version = version[1:]  # Remove leading 'v'
        
        return version
    except subprocess.CalledProcessError:
        # Fallback: use short commit hash
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                capture_output=True,
                text=True,
                check=True
            )
            commit = result.stdout.strip()
            return f"0.0.0-{commit}"
        except subprocess.CalledProcessError:
            # Ultimate fallback: use timestamp
            timestamp = datetime.now().strftime("%Y%m%d")
            return f"0.0.0-{timestamp}"


def create_zip(source_dir, output_name):
    """Create a zip file from the source directory
    
    Args:
        source_dir: Path to directory to zip
        output_name: Name of output zip file (without .zip extension)
    """
    print(f"Creating zip: {output_name}.zip")
    
    # Create zip in parent directory of source
    zip_path = Path(source_dir).parent / output_name
    
    # Create the zip file
    shutil.make_archive(
        str(zip_path),
        'zip',
        source_dir
    )
    
    zip_file = f"{zip_path}.zip"
    file_size = os.path.getsize(zip_file) / (1024 * 1024)  # Convert to MB
    
    print(f"✓ Created: {zip_file}")
    print(f"  Size: {file_size:.2f} MB")
    
    return zip_file


def main():
    """Main packaging function"""
    # Get script directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Change to project root for git commands
    os.chdir(project_root)
    
    print("=" * 60)
    print("CK3 Coat of Arms Editor - Package Script")
    print("=" * 60)
    print()
    
    # Get version from git
    version = get_git_version()
    print(f"Version: {version}")
    print()
    
    # Check if merged distribution exists
    merged_dir = script_dir / "dist" / "merged"
    if not merged_dir.exists():
        print("ERROR: dist/merged/ not found!")
        print("Please run build.bat first to create the distribution.")
        sys.exit(1)
    
    # Create output name with version
    output_name = f"CK3CoatOfArmsEditor-v{version}"
    
    # Create the zip file
    try:
        zip_file = create_zip(str(merged_dir), output_name)
        print()
        print("=" * 60)
        print("Packaging Complete!")
        print("=" * 60)
        print()
        print(f"Distribution package: {zip_file}")
        print()
        print("Ready for distribution.")
        
    except Exception as e:
        print(f"ERROR: Failed to create zip: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
