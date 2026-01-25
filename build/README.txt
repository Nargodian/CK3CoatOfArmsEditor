================================================================================
CK3 Coat of Arms Editor - Distribution Package
================================================================================

CONTENTS
--------
- CoatOfArmsEditor.exe      Main coat of arms editor application
- AssetConverter.exe        CK3 asset extraction utility
- _internal\                Shared libraries and dependencies

SYSTEM REQUIREMENTS
-------------------
- Windows 10 or later
- Crusader Kings III (for asset extraction)
- At least 2GB free disk space

QUICK START GUIDE
-----------------

STEP 1: Extract CK3 Assets
---------------------------
Before using the editor, you need to extract assets from your CK3 installation:

1. Run AssetConverter.exe
2. Click "Browse" and select your CK3 installation folder:
   Example: E:\Program Files (x86)\Steam\steamapps\common\Crusader Kings III
3. Click "Start Conversion"
4. Wait for the process to complete (this may take a few minutes)
5. Assets will be extracted to the "ck3_assets" folder

STEP 2: Use the Editor
-----------------------
1. Run CoatOfArmsEditor.exe
2. Use the toolbar to add layers (patterns, emblems, sub-divisions)
3. Customize colors and properties in the right sidebar
4. Save your coat of arms design
5. Export for use in CK3

FINDING YOUR CK3 INSTALLATION
------------------------------
Common Steam installation paths:
- C:\Program Files (x86)\Steam\steamapps\common\Crusader Kings III
- D:\Steam\steamapps\common\Crusader Kings III
- E:\Program Files (x86)\Steam\steamapps\common\Crusader Kings III

For Epic Games Store:
- C:\Program Files\Epic Games\Crusader Kings III

For Xbox Game Pass:
- C:\XboxGames\Crusader Kings III

FOLDER STRUCTURE AFTER ASSET EXTRACTION
----------------------------------------
Your folder should contain:
- CoatOfArmsEditor.exe
- AssetConverter.exe
- _internal\
- ck3_assets\
  - coa_emblems\
  - coa_patterns\
  - coa_frames\

TROUBLESHOOTING
---------------

Q: AssetConverter shows "Invalid CK3 path"
A: Make sure you select the root CK3 folder, not the "game" subfolder.
   The path should contain both "game" and "launcher" folders.

Q: Editor shows "Missing assets" error
A: Run AssetConverter.exe first to extract CK3 assets.

Q: Application won't start
A: Make sure all files are in the same folder, especially the _internal folder.

Q: Colors look different in-game
A: CK3 applies lighting and shading to coat of arms in-game. The editor shows
   the base colors before game rendering is applied.

SUPPORT & INFORMATION
---------------------
This is a community tool for Crusader Kings III.
Not affiliated with or endorsed by Paradox Interactive.

For issues or questions, check the project repository.

================================================================================
Version: 1.0
Last Updated: January 2026
================================================================================
