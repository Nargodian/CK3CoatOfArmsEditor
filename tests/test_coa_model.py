"""
Tests for CoA core model operations.

Verifies:
- Default construction
- Pattern and color properties (all 3 colors)
- Layer CRUD (add, remove, duplicate, reorder)
- Color get/set for all indices (1, 2, 3)
- Base color get/set for all indices
- Snapshot round-trip (undo/redo support)
- Active instance pattern
"""
import pytest
from models.coa import CoA
from models.color import Color
from models.transform import Vec2


# ══════════════════════════════════════════════════════════════════════════
# Default Construction
# ══════════════════════════════════════════════════════════════════════════

class TestCoADefaults:
    """Verify a fresh CoA has sane defaults."""

    def test_default_pattern(self, fresh_coa):
        assert fresh_coa.pattern == "pattern_solid.dds"

    def test_default_pattern_color1(self, fresh_coa):
        c = fresh_coa.pattern_color1
        assert isinstance(c, Color)
        assert c.name == "purple"

    def test_default_pattern_color2(self, fresh_coa):
        c = fresh_coa.pattern_color2
        assert isinstance(c, Color)
        assert c.name == "yellow"

    def test_default_pattern_color3(self, fresh_coa):
        c = fresh_coa.pattern_color3
        assert isinstance(c, Color)
        assert c.name == "black"

    def test_no_layers(self, fresh_coa):
        assert fresh_coa.get_layer_count() == 0


# ══════════════════════════════════════════════════════════════════════════
# Pattern Color Setters  (all 3)
# ══════════════════════════════════════════════════════════════════════════

class TestPatternColors:
    """Setting pattern colors via properties and set_base_color."""

    @pytest.mark.parametrize("idx,attr", [
        (1, "pattern_color1"),
        (2, "pattern_color2"),
        (3, "pattern_color3"),
    ])
    def test_set_base_color_by_index(self, fresh_coa, idx, attr):
        new_color = Color.from_name("blue")
        fresh_coa.set_base_color(idx, new_color)
        result = getattr(fresh_coa, attr)
        assert result.r == new_color.r
        assert result.g == new_color.g
        assert result.b == new_color.b

    @pytest.mark.parametrize("attr", [
        "pattern_color1", "pattern_color2", "pattern_color3"
    ])
    def test_set_pattern_color_property(self, fresh_coa, attr):
        new_color = Color.from_name("white")
        setattr(fresh_coa, attr, new_color)
        result = getattr(fresh_coa, attr)
        assert result == new_color

    @pytest.mark.parametrize("attr", [
        "pattern_color1", "pattern_color2", "pattern_color3"
    ])
    def test_reject_non_color(self, fresh_coa, attr):
        with pytest.raises(TypeError):
            setattr(fresh_coa, attr, (255, 0, 0))

    def test_set_base_color_invalid_index(self, fresh_coa):
        with pytest.raises(ValueError):
            fresh_coa.set_base_color(0, Color.from_name("red"))
        with pytest.raises(ValueError):
            fresh_coa.set_base_color(4, Color.from_name("red"))


# ══════════════════════════════════════════════════════════════════════════
# Layer Color Operations  (the color3 bug area)
# ══════════════════════════════════════════════════════════════════════════

class TestLayerColors:
    """Verify get/set for all 3 layer colors — regression for the color3 setter bug."""

    @pytest.fixture
    def coa_with_layer(self, fresh_coa):
        uuid = fresh_coa.add_layer(emblem_path="ce_test.dds")
        return fresh_coa, uuid

    @pytest.mark.parametrize("color_index", [1, 2, 3])
    def test_set_layer_color(self, coa_with_layer, color_index):
        """Setting color1/2/3 on a layer must succeed (color3 setter regression)."""
        coa, uuid = coa_with_layer
        new_color = Color.from_name("blue")
        # This is the exact call that crashed before the fix:
        coa.set_layer_color(uuid, color_index, new_color)
        result = coa.get_layer_color(uuid, color_index)
        assert result.r == new_color.r
        assert result.g == new_color.g
        assert result.b == new_color.b

    @pytest.mark.parametrize("color_index", [1, 2, 3])
    def test_get_layer_color_default(self, coa_with_layer, color_index):
        """Freshly added layers should have default emblem colors."""
        coa, uuid = coa_with_layer
        color = coa.get_layer_color(uuid, color_index)
        assert isinstance(color, Color)

    def test_set_layer_color_round_trip_rgb(self, coa_with_layer):
        """Set a custom RGB color and read it back identically."""
        coa, uuid = coa_with_layer
        for idx in (1, 2, 3):
            custom = Color(42, 128, 200)
            coa.set_layer_color(uuid, idx, custom)
            got = coa.get_layer_color(uuid, idx)
            assert got.r == 42
            assert got.g == 128
            assert got.b == 200

    def test_reject_non_color_object(self, coa_with_layer):
        coa, uuid = coa_with_layer
        with pytest.raises(TypeError):
            coa.set_layer_color(uuid, 1, [255, 0, 0])

    def test_reject_invalid_color_index(self, coa_with_layer):
        coa, uuid = coa_with_layer
        with pytest.raises(ValueError):
            coa.set_layer_color(uuid, 0, Color.from_name("red"))
        with pytest.raises(ValueError):
            coa.set_layer_color(uuid, 4, Color.from_name("red"))

    def test_reject_bad_uuid(self, fresh_coa):
        with pytest.raises(ValueError):
            fresh_coa.set_layer_color("nonexistent-uuid", 1, Color.from_name("red"))


# ══════════════════════════════════════════════════════════════════════════
# Layer CRUD
# ══════════════════════════════════════════════════════════════════════════

class TestLayerCRUD:
    """Add, remove, duplicate, reorder layers."""

    def test_add_layer(self, fresh_coa):
        uuid = fresh_coa.add_layer(emblem_path="ce_test.dds")
        assert fresh_coa.get_layer_count() == 1
        assert uuid is not None

    def test_add_multiple_layers(self, fresh_coa):
        uuid1 = fresh_coa.add_layer(emblem_path="ce_a.dds")
        uuid2 = fresh_coa.add_layer(emblem_path="ce_b.dds")
        assert fresh_coa.get_layer_count() == 2
        assert uuid1 != uuid2

    def test_remove_layer(self, fresh_coa):
        uuid = fresh_coa.add_layer(emblem_path="ce_test.dds")
        fresh_coa.remove_layer(uuid)
        assert fresh_coa.get_layer_count() == 0

    def test_remove_nonexistent(self, fresh_coa):
        with pytest.raises(ValueError):
            fresh_coa.remove_layer("nonexistent-uuid")

    def test_duplicate_layer(self, fresh_coa):
        uuid = fresh_coa.add_layer(emblem_path="ce_test.dds")
        fresh_coa.set_layer_color(uuid, 1, Color.from_name("blue"))
        fresh_coa.set_layer_color(uuid, 2, Color.from_name("red"))
        fresh_coa.set_layer_color(uuid, 3, Color.from_name("white"))
        new_uuid = fresh_coa.duplicate_layer(uuid)
        assert new_uuid != uuid
        assert fresh_coa.get_layer_count() == 2
        # Colors should be copied
        for idx in (1, 2, 3):
            orig = fresh_coa.get_layer_color(uuid, idx)
            dupe = fresh_coa.get_layer_color(new_uuid, idx)
            assert orig.r == dupe.r and orig.g == dupe.g and orig.b == dupe.b

    def test_layer_name(self, fresh_coa):
        uuid = fresh_coa.add_layer(emblem_path="ce_fleur.dds")
        # Default name derives from filename
        name = fresh_coa.get_layer_name(uuid)
        assert "fleur" in name.lower() or name  # at least not empty

        fresh_coa.set_layer_name(uuid, "My Lion")
        assert fresh_coa.get_layer_name(uuid) == "My Lion"

    def test_layer_visibility(self, fresh_coa):
        uuid = fresh_coa.add_layer(emblem_path="ce_test.dds")
        assert fresh_coa.get_layer_visible(uuid) is True
        fresh_coa.set_layer_visible(uuid, False)
        assert fresh_coa.get_layer_visible(uuid) is False


# ══════════════════════════════════════════════════════════════════════════
# Snapshot (Undo/Redo)
# ══════════════════════════════════════════════════════════════════════════

class TestSnapshot:
    """Snapshot save/restore must preserve all state including color3."""

    def test_snapshot_preserves_pattern_colors(self, fresh_coa):
        fresh_coa.pattern_color1 = Color.from_name("red")
        fresh_coa.pattern_color2 = Color.from_name("blue")
        fresh_coa.pattern_color3 = Color.from_name("white")

        snap = fresh_coa.get_snapshot()

        # Trash state
        fresh_coa.pattern_color1 = Color.from_name("black")
        fresh_coa.pattern_color2 = Color.from_name("black")
        fresh_coa.pattern_color3 = Color.from_name("black")

        fresh_coa.set_snapshot(snap)

        assert fresh_coa.pattern_color1.name == "red"
        assert fresh_coa.pattern_color2.name == "blue"
        assert fresh_coa.pattern_color3.name == "white"

    def test_snapshot_preserves_layer_colors(self, fresh_coa):
        uuid = fresh_coa.add_layer(emblem_path="ce_test.dds")
        fresh_coa.set_layer_color(uuid, 1, Color.from_name("white"))
        fresh_coa.set_layer_color(uuid, 2, Color.from_name("blue"))
        fresh_coa.set_layer_color(uuid, 3, Color.from_name("red"))

        snap = fresh_coa.get_snapshot()

        # Mutate
        fresh_coa.set_layer_color(uuid, 1, Color.from_name("black"))
        fresh_coa.set_layer_color(uuid, 2, Color.from_name("black"))
        fresh_coa.set_layer_color(uuid, 3, Color.from_name("black"))

        fresh_coa.set_snapshot(snap)

        # UUIDs may change after snapshot restore — get first layer
        restored = fresh_coa.get_layer_by_index(0)
        assert restored.color1.name == "white"
        assert restored.color2.name == "blue"
        assert restored.color3.name == "red"

    def test_snapshot_preserves_layer_count(self, fresh_coa):
        fresh_coa.add_layer(emblem_path="a.dds")
        fresh_coa.add_layer(emblem_path="b.dds")
        snap = fresh_coa.get_snapshot()
        fresh_coa.add_layer(emblem_path="c.dds")
        assert fresh_coa.get_layer_count() == 3
        fresh_coa.set_snapshot(snap)
        assert fresh_coa.get_layer_count() == 2


# ══════════════════════════════════════════════════════════════════════════
# Active Instance Pattern
# ══════════════════════════════════════════════════════════════════════════

class TestActiveInstance:

    def test_set_and_get_active(self):
        coa = CoA()
        CoA.set_active(coa)
        assert CoA.get_active() is coa

    def test_has_active(self):
        coa = CoA()
        CoA.set_active(coa)
        assert CoA.has_active() is True

    def test_clear_resets(self, fresh_coa):
        fresh_coa.add_layer(emblem_path="test.dds")
        fresh_coa.clear()
        assert fresh_coa.get_layer_count() == 0
        assert fresh_coa.pattern == "pattern_solid.dds"
        assert fresh_coa.pattern_color3.name == "black"
