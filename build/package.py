#!/usr/bin/env python3
"""
Package script for CK3 Coat of Arms Editor
- Creates version-numbered zip file
"""
import subprocess
import shutil
import os
import sys
from pathlib import Path


def get_version():
    """Get version from git tag and commits since tag
    
    Returns version in format X.Y.Z where:
    - X.Y from git tag (manual, e.g., v1.0)
    - Z is commit count since that tag (automatic)
    
    Examples:
    - v1.0 tag with 23 commits after → 1.0.23
    - v1.2 tag with 0 commits → 1.2.0
    - No tags → 0.1.{total_commits}
    """
    try:
        # Get tag with commit count: "v1.0-23-gabcdef" or "v1.0-suffix-23-gabcdef"
        result = subprocess.run(
            ['git', 'describe', '--tags', '--long'],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            desc = result.stdout.strip()
            # Parse format: v7.0-utils-cleanup-75-gba35617
            # Last two dash-separated parts are always: commits-hash
            parts = desc.rsplit('-', 2)  # Split from right, max 2 splits
            
            if len(parts) == 3:
                tag_with_suffix = parts[0]  # "v7.0-utils-cleanup"
                commits = parts[1]           # "75"
                # hash = parts[2]            # "gba35617" (unused)
                
                # Remove 'v' prefix and extract just the version number
                if tag_with_suffix.startswith('v'):
                    tag_with_suffix = tag_with_suffix[1:]
                
                # Extract version (first part before any dash)
                # "7.0-utils-cleanup" → "7.0"
                version_part = tag_with_suffix.split('-')[0]
                
                return f"{version_part}.{commits}"
        
    except:
        pass
    
    # Fallback: no tags, use total commit count
    try:
        result = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD'],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            total_commits = result.stdout.strip()
            return f"0.1.{total_commits}"
    except:
        pass
    
    return "0.1.0"


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
    
    # Get version
    version = get_version()
    print(f"Version: {version}")
    print()
    
    # Check if merged distribution exists
    merged_dir = script_dir / "dist" / "merged"
    if not merged_dir.exists():
        print("ERROR: dist/merged/ not found!")
        print("Please run build.bat first to create the distribution.")
        sys.exit(1)
    
    # Create output name with version
    output_name = f"COAEditor_{version}"
    
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
