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
    """Get version from VERSION file and git commit count
    
    Returns version in format X.Y.Z where:
    - X.Y from VERSION file in project root (manual)
    - Z is commit count since last tag, or total commits if no tags
    
    Examples:
    - VERSION=1.0, 23 commits since tag → 1.0.23
    - VERSION=2.1, no tags → 2.1.{total_commits}
    """
    # Read major.minor from VERSION file
    version_file = Path(__file__).parent.parent / "VERSION"
    try:
        with open(version_file, 'r') as f:
            major_minor = f.read().strip()
    except:
        major_minor = "1.0"  # Default if file missing
    
    # Get commit count since last tag
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--long'],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            desc = result.stdout.strip()
            # Parse format: v7.0-utils-cleanup-75-gba35617
            # Last two parts are always: commits-hash
            parts = desc.rsplit('-', 2)
            
            if len(parts) == 3:
                commits = parts[1]
                return f"{major_minor}.{commits}"
        
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
            return f"{major_minor}.{total_commits}"
    except:
        pass
    
    return f"{major_minor}.0"


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
