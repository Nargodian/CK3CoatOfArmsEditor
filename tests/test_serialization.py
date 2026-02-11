"""
Tests for CK3 Clausewitz format serialization round-trips.

Verifies:
- Parse → serialize → parse produces equivalent CoA
- Pattern, all 3 base colors, layer count preserved
- Layer properties: texture, colors (1/2/3), positions, scales, rotations
- Instance count per layer
- Multi-layer CoA with varied instances
- Edge cases: default positions, missing color3
"""
import pytest
from models.coa import CoA
from models.color import Color


# ══════════════════════════════════════════════════════════════════════════
# Parsing Verification
# ══════════════════════════════════════════════════════════════════════════

class TestParsing:

    def test_parse_pattern(self, parsed_simple_coa):
        assert parsed_simple_coa.pattern == "pattern_solid.dds"

    def test_parse_base_colors(self, parsed_simple_coa):
        assert parsed_simple_coa.pattern_color1.name == "red"
        assert parsed_simple_coa.pattern_color2.name == "yellow"
        assert parsed_simple_coa.pattern_color3.name == "black"

    def test_parse_layer_count_simple(self, parsed_simple_coa):
        assert parsed_simple_coa.get_layer_count() == 1

    def test_parse_layer_count_multi(self, parsed_multi_coa):
        assert parsed_multi_coa.get_layer_count() == 3

    def test_parse_layer_texture(self, parsed_simple_coa):
        layer = parsed_simple_coa.get_layer_by_index(0)
        assert layer.filename == "ce_fleur.dds"

    def test_parse_layer_color1(self, parsed_simple_coa):
        layer = parsed_simple_coa.get_layer_by_index(0)
        assert layer.color1.name == "yellow"

    def test_parse_three_color_emblem(self, parsed_three_color_coa):
        layer = parsed_three_color_coa.get_layer_by_index(0)
        assert layer.color1.name == "yellow"
        assert layer.color2.name == "red"
        assert layer.color3.name == "blue"

    def test_parse_multi_instances(self, parsed_multi_coa):
        """ce_mena_bend layer (lowest depth 0/1.01) is at front = index 2 after depth sort."""
        layer = parsed_multi_coa.get_layer_by_index(2)
        assert layer.instance_count == 2

    def test_parse_rotation(self, parsed_multi_coa):
        # ce_mena_bend at index 2 (front), first instance has rotation=70
        layer = parsed_multi_coa.get_layer_by_index(2)
        layer.selected_instance = 0
        assert abs(layer.rotation - 70.0) < 0.1

    def test_parse_position(self, parsed_multi_coa):
        # ce_mena_bend at index 2 (front)
        layer = parsed_multi_coa.get_layer_by_index(2)
        layer.selected_instance = 0
        assert abs(layer.pos.x - 0.97) < 0.01
        assert abs(layer.pos.y - 0.56) < 0.01

    def test_depth_ordering(self, parsed_multi_coa):
        """Layers are sorted by depth: highest depth at bottom (index 0), lowest at top."""
        # Index 0 = back: ce_tamgha_oghuz_kayig (depth 3.01)
        assert parsed_multi_coa.get_layer_by_index(0).filename == "ce_tamgha_oghuz_kayig.dds"
        # Index 1 = middle: ce_tamgha_turkic_09 (depth 2.01)
        assert parsed_multi_coa.get_layer_by_index(1).filename == "ce_tamgha_turkic_09.dds"
        # Index 2 = front: ce_mena_bend (depth 0/1.01)
        assert parsed_multi_coa.get_layer_by_index(2).filename == "ce_mena_bend.dds"


# ══════════════════════════════════════════════════════════════════════════
# Round-Trip Serialization
# ══════════════════════════════════════════════════════════════════════════

class TestRoundTrip:
    """Parse CK3 text → CoA → serialize → parse again → verify identical."""

    def test_simple_round_trip_pattern(self, simple_coa_text):
        coa1 = CoA.from_string(simple_coa_text)
        serialized = coa1.to_string()
        coa2 = CoA.from_string(serialized)
        assert coa2.pattern == coa1.pattern

    def test_simple_round_trip_base_colors(self, simple_coa_text):
        coa1 = CoA.from_string(simple_coa_text)
        serialized = coa1.to_string()
        coa2 = CoA.from_string(serialized)
        assert coa2.pattern_color1.name == coa1.pattern_color1.name
        assert coa2.pattern_color2.name == coa1.pattern_color2.name
        assert coa2.pattern_color3.name == coa1.pattern_color3.name

    def test_simple_round_trip_layer_count(self, simple_coa_text):
        coa1 = CoA.from_string(simple_coa_text)
        serialized = coa1.to_string()
        coa2 = CoA.from_string(serialized)
        assert coa2.get_layer_count() == coa1.get_layer_count()

    def test_simple_round_trip_emblem_color(self, simple_coa_text):
        coa1 = CoA.from_string(simple_coa_text)
        serialized = coa1.to_string()
        coa2 = CoA.from_string(serialized)
        l1 = coa1.get_layer_by_index(0)
        l2 = coa2.get_layer_by_index(0)
        assert l1.color1.name == l2.color1.name

    def test_multi_round_trip_layer_count(self, multi_layer_coa_text):
        coa1 = CoA.from_string(multi_layer_coa_text)
        serialized = coa1.to_string()
        coa2 = CoA.from_string(serialized)
        assert coa2.get_layer_count() == 3

    def test_multi_round_trip_textures(self, multi_layer_coa_text):
        coa1 = CoA.from_string(multi_layer_coa_text)
        serialized = coa1.to_string()
        coa2 = CoA.from_string(serialized)
        for i in range(coa1.get_layer_count()):
            assert coa1.get_layer_by_index(i).filename == coa2.get_layer_by_index(i).filename

    def test_multi_round_trip_positions(self, multi_layer_coa_text):
        coa1 = CoA.from_string(multi_layer_coa_text)
        serialized = coa1.to_string()
        coa2 = CoA.from_string(serialized)
        for i in range(coa1.get_layer_count()):
            l1 = coa1.get_layer_by_index(i)
            l2 = coa2.get_layer_by_index(i)
            l1.selected_instance = 0
            l2.selected_instance = 0
            assert abs(l1.pos.x - l2.pos.x) < 0.001
            assert abs(l1.pos.y - l2.pos.y) < 0.001

    def test_multi_round_trip_rotations(self, multi_layer_coa_text):
        coa1 = CoA.from_string(multi_layer_coa_text)
        serialized = coa1.to_string()
        coa2 = CoA.from_string(serialized)
        for i in range(coa1.get_layer_count()):
            l1 = coa1.get_layer_by_index(i)
            l2 = coa2.get_layer_by_index(i)
            l1.selected_instance = 0
            l2.selected_instance = 0
            assert abs(l1.rotation - l2.rotation) < 0.1

    def test_three_color_round_trip(self, three_color_coa_text):
        """All 3 emblem colors survive round-trip."""
        coa1 = CoA.from_string(three_color_coa_text)
        serialized = coa1.to_string()
        coa2 = CoA.from_string(serialized)
        l1 = coa1.get_layer_by_index(0)
        l2 = coa2.get_layer_by_index(0)
        assert l1.color1.name == l2.color1.name
        assert l1.color2.name == l2.color2.name
        assert l1.color3.name == l2.color3.name


# ══════════════════════════════════════════════════════════════════════════
# Serialization Content Checks
# ══════════════════════════════════════════════════════════════════════════

class TestSerializationContent:
    """Verify serialized output contains expected Clausewitz tokens."""

    def test_contains_pattern(self, parsed_simple_coa):
        s = parsed_simple_coa.to_string()
        assert 'pattern = "pattern_solid.dds"' in s

    def test_contains_base_color1(self, parsed_simple_coa):
        s = parsed_simple_coa.to_string()
        assert "color1 = red" in s or "color1 = rgb" in s

    def test_contains_base_color3(self, parsed_simple_coa):
        s = parsed_simple_coa.to_string()
        assert "color3 = black" in s or "color3 = rgb" in s

    def test_contains_colored_emblem(self, parsed_simple_coa):
        s = parsed_simple_coa.to_string()
        assert "colored_emblem" in s

    def test_contains_texture(self, parsed_simple_coa):
        s = parsed_simple_coa.to_string()
        assert 'texture = "ce_fleur.dds"' in s

    def test_contains_instance(self, parsed_simple_coa):
        s = parsed_simple_coa.to_string()
        assert "instance" in s


# ══════════════════════════════════════════════════════════════════════════
# Mutation then Serialization
# ══════════════════════════════════════════════════════════════════════════

class TestMutateThenSerialize:
    """Modify a parsed CoA, serialize, then verify changes persisted."""

    def test_change_base_color3_persists(self, parsed_simple_coa):
        parsed_simple_coa.pattern_color3 = Color.from_name("white")
        s = parsed_simple_coa.to_string()
        coa2 = CoA.from_string(s)
        assert coa2.pattern_color3.name == "white"

    def test_change_layer_color3_persists(self, parsed_three_color_coa):
        layer = parsed_three_color_coa.get_layer_by_index(0)
        uuid = layer.uuid
        parsed_three_color_coa.set_layer_color(uuid, 3, Color.from_name("white"))
        s = parsed_three_color_coa.to_string()
        coa2 = CoA.from_string(s)
        l2 = coa2.get_layer_by_index(0)
        assert l2.color3.name == "white"

    def test_add_layer_then_serialize(self, parsed_simple_coa):
        uuid = parsed_simple_coa.add_layer(emblem_path="ce_lion.dds")
        parsed_simple_coa.set_layer_color(uuid, 1, Color.from_name("red"))
        parsed_simple_coa.set_layer_color(uuid, 2, Color.from_name("blue"))
        parsed_simple_coa.set_layer_color(uuid, 3, Color.from_name("white"))
        s = parsed_simple_coa.to_string()
        coa2 = CoA.from_string(s)
        assert coa2.get_layer_count() == 2
        l2 = coa2.get_layer_by_index(1)
        assert l2.color1.name == "red"
        assert l2.color2.name == "blue"
        assert l2.color3.name == "white"


# ══════════════════════════════════════════════════════════════════════════
# Arbitrary CK3 Key Prefix Loading
# ══════════════════════════════════════════════════════════════════════════

class TestArbitraryKeyPrefixLoading:
    """Verify CoA text with arbitrary key prefixes (e.g., coa_rd_dynasty_*)
    loads correctly, not just coat_of_arms/coa_export/layers_export."""

    def test_dynasty_key_loads_pattern(self):
        text = 'coa_rd_dynasty_12345={\n\tpattern="pattern_solid.dds"\n\tcolor1=red\n\tcolor2=yellow\n\tcolor3=black\n}'
        coa = CoA.from_string(text)
        assert coa.pattern == "pattern_solid.dds"

    def test_dynasty_key_loads_colors(self):
        text = 'coa_rd_dynasty_12345={\n\tpattern="pattern_solid.dds"\n\tcolor1=red\n\tcolor2=yellow\n\tcolor3=black\n}'
        coa = CoA.from_string(text)
        assert coa.pattern_color1.name == "red"
        assert coa.pattern_color2.name == "yellow"
        assert coa.pattern_color3.name == "black"

    def test_dynasty_key_loads_emblems(self):
        text = ('coa_dynasty_28014={\n\tpattern="pattern_solid.dds"\n\tcolor1=red\n\tcolor2=yellow\n\tcolor3=black\n'
                '\tcolored_emblem={\n\t\tcolor1=yellow\n\t\ttexture="ce_fleur.dds"\n\t}\n}')
        coa = CoA.from_string(text)
        assert coa.get_layer_count() == 1
        assert coa.get_layer_by_index(0).filename == "ce_fleur.dds"

    def test_landed_title_key_loads(self):
        text = 'e_byzantium={\n\tpattern="pattern_solid.dds"\n\tcolor1=blue\n\tcolor2=yellow\n\tcolor3=red\n}'
        coa = CoA.from_string(text)
        assert coa.pattern == "pattern_solid.dds"
        assert coa.pattern_color1.name == "blue"

    def test_custom_yes_ignored(self):
        """The custom=yes field should not prevent loading."""
        text = ('coa_rd_dynasty_999={\n\tcustom=yes\n\tpattern="pattern_solid.dds"\n'
                '\tcolor1=white\n\tcolor2=black\n\tcolor3=blue\n}')
        coa = CoA.from_string(text)
        assert coa.pattern == "pattern_solid.dds"
        assert coa.pattern_color1.name == "white"
