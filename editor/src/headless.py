"""Headless CoA Renderer — CLI entry point.

Reads CK3 coat-of-arms text files (single or multi-CoA), renders each CoA
to a 256x256 PNG of the raw CoA texture (pattern + emblems, no frame).

Usage:
    python -m editor.src.headless <input_file> [-o OUTPUT_DIR] [--use-filenames]

Examples:
    python -m editor.src.headless examples/game_samples/coa_sample_1.txt
    python -m editor.src.headless my_coas.txt -o renders/
    python -m editor.src.headless my_coas.txt --use-filenames
"""

import sys
import os
import argparse
import logging

# Add editor/src to path so imports work
_src_dir = os.path.dirname(os.path.abspath(__file__))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# Also add project root so asset_converter is importable
_project_root = os.path.dirname(os.path.dirname(_src_dir))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def _parse_multi_coa_file(file_path: str) -> dict:
    """Parse a CK3 file that may contain one or many CoA definitions.

    Uses asset_converter's CK3Parser which handles multi-block files natively.

    Args:
        file_path: Path to the input text file.

    Returns:
        Dict mapping CoA name → parsed data dict.
    """
    from asset_converter.src.ck3_parser import CK3Parser

    with open(file_path, "r", encoding="utf-8-sig") as f:
        text = f.read()

    parser = CK3Parser(text)
    return parser.parse_file()


def _dict_to_ck3_string(name: str, data: dict) -> str:
    """Reconstruct a single-CoA CK3 string from a parsed dict.

    This produces a string that CoA.from_string() can consume through
    its normal parsing path.

    Args:
        name: Top-level identifier (e.g. "coa_dynasty_28014").
        data: Parsed dict for that CoA.

    Returns:
        CK3-format string.
    """
    lines = [f'{name} = {{']
    _serialize_dict(data, lines, indent=1)
    lines.append('}')
    return '\n'.join(lines)


def _serialize_dict(d: dict, lines: list, indent: int):
    """Recursively serialize a parsed dict back to CK3 text format."""
    prefix = '\t' * indent
    for key, value in d.items():
        if isinstance(value, list):
            # Distinguish duplicate keys (list of dicts) from inline arrays (list of scalars)
            if value and isinstance(value[0], dict):
                # Duplicate keys — multiple blocks with the same key
                for item in value:
                    lines.append(f'{prefix}{key} = {{')
                    _serialize_dict(item, lines, indent + 1)
                    lines.append(f'{prefix}}}')
            else:
                # Inline array — e.g. position = { 0.5 0.5 }
                parts = ' '.join(_format_value(item) for item in value)
                lines.append(f'{prefix}{key} = {{ {parts} }}')
        elif isinstance(value, dict):
            # Color type dicts (rgb/hsv/hsv360) are leaf values, not nested blocks
            if 'type' in value and 'values' in value:
                lines.append(f'{prefix}{key} = {_format_value(value)}')
            else:
                lines.append(f'{prefix}{key} = {{')
                _serialize_dict(value, lines, indent + 1)
                lines.append(f'{prefix}}}')
        else:
            lines.append(f'{prefix}{key} = {_format_value(value)}')


def _format_value(v) -> str:
    """Format a single value for CK3 serialization."""
    if isinstance(v, bool):
        return 'yes' if v else 'no'
    elif isinstance(v, dict):
        # Color type: {'type': 'rgb', 'values': [74, 201, 202]}
        if 'type' in v and 'values' in v:
            parts = ' '.join(_format_value(c) for c in v['values'])
            return f'{v["type"]} {{ {parts} }}'
        # Shouldn't happen in normal flow, but handle gracefully
        return str(v)
    elif isinstance(v, str):
        return f'"{v}"'
    elif isinstance(v, float):
        return f'{v:.6f}'
    elif isinstance(v, int):
        return str(v)
    elif isinstance(v, list):
        # Inline array: { 0.5 0.5 }
        parts = ' '.join(_format_value(item) for item in v)
        return f'{{ {parts} }}'
    else:
        return str(v)


def main():
    parser = argparse.ArgumentParser(
        description='Render CK3 coats of arms to PNG images (headless).',
    )
    parser.add_argument(
        'input_file',
        help='Path to CK3 CoA text file (single or multi-CoA).',
    )
    parser.add_argument(
        '-o', '--output',
        default='./output',
        help='Output directory for PNG files (default: ./output).',
    )
    parser.add_argument(
        '-f', '--use-filenames',
        action='store_true',
        help='Name output PNGs after the input filename instead of the CoA key.',
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging.',
    )
    args = parser.parse_args()

    # Logging
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    input_path = os.path.abspath(args.input_file)
    output_dir = os.path.abspath(args.output)

    if not os.path.isfile(input_path):
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    # Parse all CoA definitions from the file
    print(f"Parsing {input_path} ...")
    parsed = _parse_multi_coa_file(input_path)

    if not parsed:
        print("No CoA definitions found in the input file.")
        sys.exit(1)

    # Filter to actual CoA blocks (dicts). Handle duplicate keys (list of dicts).
    coa_entries = []  # list of (name, data_dict)
    for k, v in parsed.items():
        if isinstance(v, dict):
            coa_entries.append((k, v))
        elif isinstance(v, list):
            # Duplicate keys → list of dicts; render each with a suffix
            dicts = [item for item in v if isinstance(item, dict)]
            if len(dicts) == 1:
                coa_entries.append((k, dicts[0]))
            else:
                for i, item in enumerate(dicts):
                    coa_entries.append((f"{k}_{i}", item))

    if not coa_entries:
        print("No CoA definitions found in the input file.")
        sys.exit(1)

    print(f"Found {len(coa_entries)} coat(s) of arms.")

    # Boot headless renderer (OpenGL context, shaders, atlases — once)
    from services.headless_renderer import HeadlessRenderer
    from models.coa import CoA

    renderer = HeadlessRenderer()
    os.makedirs(output_dir, exist_ok=True)

    # Determine output naming
    input_stem = os.path.splitext(os.path.basename(input_path))[0]

    rendered = 0
    failed = 0
    for idx, (name, data) in enumerate(coa_entries):
        try:
            # Use 'coa_export' as the top-level key so CoA.parse() recognises it
            # (it only accepts coat_of_arms / coa_export / layers_export prefixes)
            ck3_text = _dict_to_ck3_string('coa_export', data)
            coa = CoA.from_string(ck3_text)

            if args.use_filenames:
                if len(coa_entries) == 1:
                    out_name = input_stem
                else:
                    out_name = f"{input_stem}_{idx}"
            else:
                out_name = name

            out_file = os.path.join(output_dir, f"{out_name}.png")
            renderer.render_coa(coa, out_file)
            rendered += 1
            print(f"  [{rendered}/{len(coa_entries)}] {out_name}.png")
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {name}: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()

    renderer.cleanup()

    print(f"\nDone. Rendered {rendered} image(s) to {output_dir}/")
    if failed:
        print(f"  ({failed} failed)")


if __name__ == '__main__':
    main()
