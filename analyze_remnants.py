import re
import os
from datetime import datetime

files = [
    r'editor\src\main.py',
    r'editor\src\components\property_sidebar.py',
    r'editor\src\components\canvas_widget.py',
    r'editor\src\components\canvas_area.py',
    r'editor\src\components\asset_sidebar.py',
    r'editor\src\components\property_sidebar_widgets\layer_list_widget.py',
    r'editor\src\services\layer_operations.py',
    r'editor\src\services\file_operations.py',
    r'editor\src\services\coa_serializer.py',
    r'editor\src\utils\coa_parser.py',
    r'editor\src\actions\layer_transform_actions.py',
    r'editor\src\actions\clipboard_actions.py'
]

patterns = [
    (r"layer\['", 'Dict access: layer[key]'),
    (r"layer\.get\(", 'Dict access: layer.get()'),
    (r"layers\[.*\]\['", 'Nested dict access'),
    (r"'instances'", 'Instance list reference'),
    (r"'filename'", 'Filename dict key'),
    (r"'pos_x'|'pos_y'", 'Position dict keys'),
    (r"'scale_x'|'scale_y'", 'Scale dict keys'),
    (r"'rotation'", 'Rotation dict key'),
    (r"'color1'|'color2'|'color3'", 'Color dict keys'),
    (r"dict\(layer\)", 'Dict copy'),
    (r"layers\.append\(", 'Layer list append'),
    (r"layers = \[\]", 'Layer list reset'),
    (r"layer_dict", 'layer_dict variable'),
    (r"'flip_x'|'flip_y'", 'Flip dict keys'),
    (r"'mask'", 'Mask dict key'),
    (r"'depth'", 'Depth dict key'),
    (r"'uuid'", 'UUID dict key'),
    (r"instance_count", 'Instance count reference'),
    (r"selected_instance", 'Selected instance reference'),
]

report = f'# OLD DICTIONARY-BASED LAYER SYSTEM REMNANTS\n'
report += f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n'
report += 'This report identifies remnants of the old dictionary-based layer system that need\n'
report += 'to be migrated to the new CoA object-based system.\n\n'
report += '## KEY PATTERNS IDENTIFIED:\n\n'
report += '1. **Dictionary access**: `layer[\'key\']`, `layer.get(\'key\')`\n'
report += '2. **Instance lists**: `layer[\'instances\']`, `instance_count`\n'
report += '3. **Dict creation**: `{\'filename\': ..., \'pos_x\': ...}`\n'
report += '4. **Layer list ops**: `layers.append()`, `layers[idx] = {...}`\n'
report += '5. **Deep copies**: `dict(layer)`, `[dict(l) for l in layers]`\n\n'
report += '---\n\n'

total_files = 0
total_matches = 0

for filepath in files:
    if os.path.exists(filepath):
        print(f'Analyzing {filepath}...')
        total_files += 1
        report += f'## FILE: {filepath}\n\n'
        
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        matches = []
        for i, line in enumerate(lines, 1):
            for pattern, desc in patterns:
                if re.search(pattern, line):
                    trimmed = line.strip()
                    if len(trimmed) > 120:
                        trimmed = trimmed[:120] + '...'
                    matches.append((i, desc, trimmed))
                    break
        
        if matches:
            total_matches += len(matches)
            report += f'**Found {len(matches)} dictionary-based patterns:**\n\n'
            for linenum, desc, line in matches:
                report += f'- **Line {linenum}** [{desc}]:\n  ```python\n  {line}\n  ```\n\n'
        else:
            report += '*✓ No dictionary-based patterns found - file appears clean.*\n\n'
        
        report += '---\n\n'

report += f'\n## SUMMARY\n\n'
report += f'- **Total files analyzed**: {total_files}\n'
report += f'- **Total dictionary patterns found**: {total_matches}\n'
report += f'- **Files needing migration**: {sum(1 for f in files if os.path.exists(f))}\n\n'
report += '## NEXT STEPS\n\n'
report += '1. Replace dictionary access with CoA model property access\n'
report += '2. Update layer creation to use Layer objects instead of dicts\n'
report += '3. Replace instance lists with Layer object properties\n'
report += '4. Update layer list operations to use CoA model methods\n'
report += '5. Remove dict conversion/copy operations\n'

with open('OLD_LAYER_SYSTEM_REMNANTS.md', 'w', encoding='utf-8') as f:
    f.write(report)

print(f'\n✓ Report generated: OLD_LAYER_SYSTEM_REMNANTS.md')
print(f'✓ Total files analyzed: {total_files}')
print(f'✓ Total patterns found: {total_matches}')
