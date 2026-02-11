"""
Round-trip stability tests for real CK3 game samples.

Parses each file in examples/game_samples/, exports, re-parses, re-exports,
then compares the two exports (with meta tags stripped) to verify stability.

Accepted differences from the original game text:
- Instance breaking: multi-instance colored_emblem blocks may become separate
  single-instance layers (the editor stores one instance per layer)
- Depth reordering: layers are sorted by depth on export
- Prefix change: game prefixes (coa_dynasty_*, coa_title_*) → coa_export = {
- Meta tags injected by the editor are stripped before comparison
- `custom=yes` is dropped (not part of CoA data model)
- Default color3 may be added if missing in original

Stability means: export(parse(export(parse(game_text)))) == export(parse(game_text))
"""
import os
import re
import glob
import pytest

from models.coa import CoA


# ══════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════

SAMPLES_DIR = os.path.join(
    os.path.dirname(__file__), '..', 'examples', 'game_samples'
)


def _swap_prefix(text: str) -> str:
    """Replace game identifier prefix with coa_export so the parser accepts it.
    
    Game samples use prefixes like ``coa_rd_dynasty_3446239394=``,
    ``coa_dynasty_28014=``, ``coa_title_149=`` — none of which match the
    parser's recognized top-level keys.  We swap to ``coa_export =`` so the
    parse path treats it as a full CoA.
    """
    return re.sub(r'^[a-zA-Z0-9_]+=', 'coa_export =', text.strip(), count=1)

def _get_sample_files():
    """Discover all .txt sample files and return (path, basename) tuples."""
    pattern = os.path.join(SAMPLES_DIR, '*.txt')
    files = sorted(glob.glob(pattern))
    return [(f, os.path.basename(f)) for f in files]


def _strip_meta(text: str) -> str:
    """Remove all ##META## lines from serialized output."""
    return '\n'.join(
        line for line in text.splitlines()
        if '##META##' not in line
    )


def _normalize_whitespace(text: str) -> str:
    """Normalize whitespace for robust comparison.
    
    - Strip trailing whitespace per line
    - Collapse multiple blank lines to one
    - Strip leading/trailing blank lines
    """
    lines = [line.rstrip() for line in text.splitlines()]
    # Collapse consecutive blank lines
    result = []
    prev_blank = False
    for line in lines:
        if line == '':
            if not prev_blank:
                result.append(line)
            prev_blank = True
        else:
            result.append(line)
            prev_blank = False
    return '\n'.join(result).strip()


def _clean_export(text: str) -> str:
    """Strip meta tags and normalize whitespace for comparison."""
    return _normalize_whitespace(_strip_meta(text))


def _parse_emblem_blocks(text: str) -> list:
    """Extract individual colored_emblem blocks from export text.
    
    Returns a list of dicts with keys:
        texture, color1, color2, color3, mask, instances
    where each instance is a dict with position, scale, rotation, depth.
    
    This provides a structural comparison that is insensitive to
    ordering and instance grouping.
    """
    blocks = []
    # Match colored_emblem blocks with regex
    pattern = re.compile(
        r'colored_emblem\s*=\s*\{(.*?)\n\t\}',
        re.DOTALL
    )
    for match in pattern.finditer(text):
        block_text = match.group(1)
        
        texture = ''
        tex_m = re.search(r'texture\s*=\s*"([^"]*)"', block_text)
        if tex_m:
            texture = tex_m.group(1)
        
        color1 = _extract_color(block_text, 'color1')
        color2 = _extract_color(block_text, 'color2')
        color3 = _extract_color(block_text, 'color3')
        
        mask = None
        mask_m = re.search(r'mask\s*=\s*\{\s*([^}]*)\}', block_text)
        if mask_m:
            mask = mask_m.group(1).strip()
        
        instances = _extract_instances(block_text)
        
        blocks.append({
            'texture': texture,
            'color1': color1,
            'color2': color2,
            'color3': color3,
            'mask': mask,
            'instances': instances,
        })
    return blocks


def _extract_color(text: str, color_name: str) -> str:
    """Extract a color value (named or rgb block) from block text."""
    # Match rgb block: color1 = rgb { 25 23 19 }
    rgb_m = re.search(
        rf'(?<!\w){color_name}\s*=\s*(rgb\s*\{{\s*[^}}]*\}})',
        text
    )
    if rgb_m:
        return rgb_m.group(1).strip()
    # Match named: color1 = red
    named_m = re.search(
        rf'(?<!\w){color_name}\s*=\s*(\w+)',
        text
    )
    if named_m:
        return named_m.group(1).strip()
    return ''


def _extract_instances(block_text: str) -> list:
    """Extract instance dicts from a colored_emblem block."""
    instances = []
    inst_pattern = re.compile(
        r'instance\s*=\s*\{(.*?)\n\t\t\t\}',
        re.DOTALL
    )
    for inst_m in inst_pattern.finditer(block_text):
        inst_text = inst_m.group(1)
        inst = {}
        
        pos_m = re.search(r'position\s*=\s*\{\s*([^}]*)\}', inst_text)
        if pos_m:
            inst['position'] = pos_m.group(1).strip()
        
        scale_m = re.search(r'scale\s*=\s*\{\s*([^}]*)\}', inst_text)
        if scale_m:
            inst['scale'] = scale_m.group(1).strip()
        
        rot_m = re.search(r'rotation\s*=\s*(\S+)', inst_text)
        if rot_m:
            inst['rotation'] = rot_m.group(1).strip()
        
        depth_m = re.search(r'depth\s*=\s*(\S+)', inst_text)
        if depth_m:
            inst['depth'] = depth_m.group(1).strip()
        
        instances.append(inst)
    
    if not instances:
        # No explicit instance block — default instance
        instances.append({})
    
    return instances


def _flatten_instances(blocks: list) -> list:
    """Flatten emblem blocks into individual (texture, color, instance) tuples.
    
    This allows comparison even when multi-instance blocks are broken into
    separate single-instance layers. Each tuple is:
        (texture, color1, color2, color3, mask, instance_dict)
    sorted for stable comparison.
    """
    result = []
    for block in blocks:
        for inst in block['instances']:
            result.append((
                block['texture'],
                block['color1'],
                block['color2'],
                block['color3'],
                block['mask'],
                tuple(sorted(inst.items())),
            ))
    return sorted(result)


# ══════════════════════════════════════════════════════════════════════════
# Parametrized Tests
# ══════════════════════════════════════════════════════════════════════════

sample_files = _get_sample_files()

@pytest.mark.parametrize(
    "sample_path, sample_name",
    sample_files,
    ids=[name for _, name in sample_files],
)
class TestGameSampleRoundTrip:
    """Round-trip stability for each game sample file."""

    @staticmethod
    def _load(sample_path: str) -> str:
        """Load sample file and swap game prefix to coa_export."""
        return _swap_prefix(open(sample_path, 'r').read())

    def test_parse_succeeds(self, sample_path, sample_name):
        """Sample parses without error."""
        text = self._load(sample_path)
        coa = CoA.from_string(text)
        assert coa.get_layer_count() > 0, f"{sample_name}: parsed 0 layers"

    def test_export_parses_back(self, sample_path, sample_name):
        """Export text can be parsed again without error."""
        text = self._load(sample_path)
        coa1 = CoA.from_string(text)
        export1 = coa1.to_string()
        coa2 = CoA.from_string(export1)
        assert coa2.get_layer_count() > 0, f"{sample_name}: re-parse produced 0 layers"

    def test_export_stability(self, sample_path, sample_name):
        """Two consecutive round-trips produce identical output (stability).
        
        parse(game) → export1 → parse(export1) → export2
        Verify: clean(export1) == clean(export2)
        """
        text = self._load(sample_path)

        # First round-trip
        coa1 = CoA.from_string(text)
        export1 = coa1.to_string()

        # Second round-trip
        coa2 = CoA.from_string(export1)
        export2 = coa2.to_string()

        clean1 = _clean_export(export1)
        clean2 = _clean_export(export2)

        assert clean1 == clean2, (
            f"{sample_name}: export not stable across round-trips.\n"
            f"--- Export 1 (cleaned) ---\n{clean1}\n"
            f"--- Export 2 (cleaned) ---\n{clean2}"
        )

    def test_pattern_preserved(self, sample_path, sample_name):
        """Pattern texture survives round-trip."""
        text = self._load(sample_path)
        coa1 = CoA.from_string(text)
        export1 = coa1.to_string()
        coa2 = CoA.from_string(export1)
        assert coa2.pattern == coa1.pattern

    def test_base_colors_preserved(self, sample_path, sample_name):
        """Base pattern colors survive round-trip."""
        text = self._load(sample_path)
        coa1 = CoA.from_string(text)
        export1 = coa1.to_string()
        coa2 = CoA.from_string(export1)
        assert coa2.pattern_color1.to_ck3_string() == coa1.pattern_color1.to_ck3_string()
        assert coa2.pattern_color2.to_ck3_string() == coa1.pattern_color2.to_ck3_string()
        assert coa2.pattern_color3.to_ck3_string() == coa1.pattern_color3.to_ck3_string()

    def test_layer_count_stable(self, sample_path, sample_name):
        """Layer count is stable after first export (may differ from original
        due to instance breaking, but must not change on re-export)."""
        text = self._load(sample_path)
        coa1 = CoA.from_string(text)
        export1 = coa1.to_string()
        coa2 = CoA.from_string(export1)
        assert coa2.get_layer_count() == coa1.get_layer_count()

    def test_instance_data_preserved(self, sample_path, sample_name):
        """All instance data (texture, colors, position, scale, rotation)
        survives round-trip when compared structurally.
        
        Instance breaking is fine — we flatten multi-instance blocks and
        compare the full set of (texture, instance) pairs.
        """
        text = self._load(sample_path)
        coa1 = CoA.from_string(text)
        export1 = coa1.to_string()
        coa2 = CoA.from_string(export1)
        export2 = coa2.to_string()

        clean1 = _strip_meta(export1)
        clean2 = _strip_meta(export2)

        blocks1 = _parse_emblem_blocks(clean1)
        blocks2 = _parse_emblem_blocks(clean2)

        flat1 = _flatten_instances(blocks1)
        flat2 = _flatten_instances(blocks2)

        assert flat1 == flat2, (
            f"{sample_name}: structural instance data changed on re-export.\n"
            f"Blocks export1: {len(blocks1)}, Blocks export2: {len(blocks2)}\n"
            f"Flat1 ({len(flat1)} instances): {flat1}\n"
            f"Flat2 ({len(flat2)} instances): {flat2}"
        )

    def test_mask_preserved(self, sample_path, sample_name):
        """Mask values survive round-trip for layers that have them."""
        text = self._load(sample_path)
        coa1 = CoA.from_string(text)
        export1 = coa1.to_string()
        coa2 = CoA.from_string(export1)

        for i in range(coa1.get_layer_count()):
            layer1 = coa1.get_layer_by_index(i)
            layer2 = coa2.get_layer_by_index(i)
            assert layer1.mask == layer2.mask, (
                f"{sample_name} layer {i}: mask changed "
                f"{layer1.mask} → {layer2.mask}"
            )

    def test_texture_filenames_preserved(self, sample_path, sample_name):
        """All texture filenames from the original are present after round-trip."""
        text = self._load(sample_path)
        coa1 = CoA.from_string(text)
        export1 = coa1.to_string()
        coa2 = CoA.from_string(export1)

        textures1 = sorted(
            coa1.get_layer_by_index(i).filename
            for i in range(coa1.get_layer_count())
        )
        textures2 = sorted(
            coa2.get_layer_by_index(i).filename
            for i in range(coa2.get_layer_count())
        )
        assert textures1 == textures2

    def test_flip_preserved(self, sample_path, sample_name):
        """Flip states (encoded as negative scale) survive round-trip."""
        text = self._load(sample_path)
        coa1 = CoA.from_string(text)
        export1 = coa1.to_string()
        coa2 = CoA.from_string(export1)

        for i in range(coa1.get_layer_count()):
            layer1 = coa1.get_layer_by_index(i)
            layer2 = coa2.get_layer_by_index(i)
            assert layer1.flip_x == layer2.flip_x, (
                f"{sample_name} layer {i}: flip_x changed "
                f"{layer1.flip_x} → {layer2.flip_x}"
            )
            assert layer1.flip_y == layer2.flip_y, (
                f"{sample_name} layer {i}: flip_y changed "
                f"{layer1.flip_y} → {layer2.flip_y}"
            )
