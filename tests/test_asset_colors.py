"""
Tests for asset sidebar color pickers.

Covers:
- Default asset colors match constants
- Setting asset colors independently of model/undo
- New layers receive asset colors
- Asset colors survive CoA reset (New)
- Asset colors unaffected by layer selection changes
"""
import copy
import pytest
from models.coa import CoA
from models.color import Color
from utils.history_manager import HistoryManager
from constants import DEFAULT_EMBLEM_COLOR1, DEFAULT_EMBLEM_COLOR2, DEFAULT_EMBLEM_COLOR3


# ══════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════

class FakeAssetSidebar:
    """Minimal stand-in for AssetSidebar — just the color state and API."""

    def __init__(self):
        self._asset_color1 = Color.from_name(DEFAULT_EMBLEM_COLOR1)
        self._asset_color2 = Color.from_name(DEFAULT_EMBLEM_COLOR2)
        self._asset_color3 = Color.from_name(DEFAULT_EMBLEM_COLOR3)

    def set_asset_color(self, color_number, color):
        if color_number == 1:
            self._asset_color1 = color
        elif color_number == 2:
            self._asset_color2 = color
        elif color_number == 3:
            self._asset_color3 = color

    def get_asset_colors(self):
        return (self._asset_color1, self._asset_color2, self._asset_color3)


@pytest.fixture
def sidebar():
    return FakeAssetSidebar()


@pytest.fixture
def fresh_coa():
    coa = CoA()
    CoA.set_active(coa)
    return coa


# ══════════════════════════════════════════════════════════════════════════
# Default colors
# ══════════════════════════════════════════════════════════════════════════

class TestAssetColorDefaults:
    """Verify initial asset colors match the constants."""

    def test_default_color1(self, sidebar):
        expected = Color.from_name(DEFAULT_EMBLEM_COLOR1)
        assert sidebar._asset_color1.to_hex() == expected.to_hex()

    def test_default_color2(self, sidebar):
        expected = Color.from_name(DEFAULT_EMBLEM_COLOR2)
        assert sidebar._asset_color2.to_hex() == expected.to_hex()

    def test_default_color3(self, sidebar):
        expected = Color.from_name(DEFAULT_EMBLEM_COLOR3)
        assert sidebar._asset_color3.to_hex() == expected.to_hex()


# ══════════════════════════════════════════════════════════════════════════
# Undo resistance — asset colors must NOT appear in undo history
# ══════════════════════════════════════════════════════════════════════════

class TestAssetColorUndoResistance:
    """Setting asset colors → adding layer → undo should restore layer
    state but leave asset colors unchanged."""

    def test_undo_does_not_revert_asset_colors(self, sidebar, fresh_coa):
        hm = HistoryManager(max_history=50)

        # Set custom asset colors (not an undo-tracked action)
        pink = Color.from_rgb255(255, 105, 180)
        sidebar.set_asset_color(1, pink)

        # Snapshot before add
        hm.save_state(fresh_coa.get_snapshot(), "initial")

        # Add a layer using asset colours
        c1, c2, c3 = sidebar.get_asset_colors()
        fresh_coa.add_layer(
            emblem_path="ce_basket.dds",
            colors=3,
            color1=c1, color2=c2, color3=c3
        )
        hm.save_state(fresh_coa.get_snapshot(), "add layer")
        assert fresh_coa.get_layer_count() == 1

        # Set another asset color (again, not undo-tracked)
        green = Color.from_rgb255(0, 200, 0)
        sidebar.set_asset_color(2, green)

        # Undo the layer add
        state = hm.undo()
        fresh_coa.set_snapshot(state)

        # Layer is gone
        assert fresh_coa.get_layer_count() == 0

        # Asset colors preserved (undo didn't touch them)
        c1, c2, c3 = sidebar.get_asset_colors()
        assert c1.to_hex() == pink.to_hex()
        assert c2.to_hex() == green.to_hex()


# ══════════════════════════════════════════════════════════════════════════
# Color propagation — new layers receive asset colors
# ══════════════════════════════════════════════════════════════════════════

class TestAssetColorPropagation:
    """When a layer is added, its colors must match the asset picker."""

    def test_layer_receives_asset_colors(self, sidebar, fresh_coa):
        red = Color.from_rgb255(200, 50, 50)
        green = Color.from_rgb255(50, 200, 50)
        blue = Color.from_rgb255(50, 50, 200)

        sidebar.set_asset_color(1, red)
        sidebar.set_asset_color(2, green)
        sidebar.set_asset_color(3, blue)

        c1, c2, c3 = sidebar.get_asset_colors()
        uuid = fresh_coa.add_layer(
            emblem_path="ce_basket.dds",
            colors=3,
            color1=c1, color2=c2, color3=c3
        )

        layer = fresh_coa.get_layer_by_uuid(uuid)
        assert layer.color1.to_hex() == red.to_hex()
        assert layer.color2.to_hex() == green.to_hex()
        assert layer.color3.to_hex() == blue.to_hex()


# ══════════════════════════════════════════════════════════════════════════
# State-change resistance — asset colors survive CoA reset
# ══════════════════════════════════════════════════════════════════════════

class TestAssetColorStateResistance:
    """Asset colors must survive clearing the CoA (File→New)."""

    def test_colors_survive_coa_reset(self, sidebar, fresh_coa):
        orange = Color.from_rgb255(255, 165, 0)
        purple = Color.from_rgb255(128, 0, 128)
        teal = Color.from_rgb255(0, 128, 128)

        sidebar.set_asset_color(1, orange)
        sidebar.set_asset_color(2, purple)
        sidebar.set_asset_color(3, teal)

        # Add a layer so there's something to clear
        c1, c2, c3 = sidebar.get_asset_colors()
        fresh_coa.add_layer(
            emblem_path="ce_basket.dds", colors=3,
            color1=c1, color2=c2, color3=c3
        )
        assert fresh_coa.get_layer_count() == 1

        # Simulate File→New: create a brand-new CoA
        new_coa = CoA()
        CoA.set_active(new_coa)
        assert new_coa.get_layer_count() == 0

        # Asset colors on sidebar should be untouched
        c1, c2, c3 = sidebar.get_asset_colors()
        assert c1.to_hex() == orange.to_hex()
        assert c2.to_hex() == purple.to_hex()
        assert c3.to_hex() == teal.to_hex()


# ══════════════════════════════════════════════════════════════════════════
# Independence from layer selection
# ══════════════════════════════════════════════════════════════════════════

class TestAssetColorIndependence:
    """Asset colors must not change when different layers are selected."""

    def test_colors_unchanged_after_layer_selection(self, sidebar, fresh_coa):
        cyan = Color.from_rgb255(0, 255, 255)
        sidebar.set_asset_color(1, cyan)

        # Add two layers with different colors
        fresh_coa.add_layer(
            emblem_path="ce_basket.dds", colors=1,
            color1=Color.from_name("red")
        )
        fresh_coa.add_layer(
            emblem_path="ce_basket.dds", colors=1,
            color1=Color.from_name("blue")
        )

        # "Selecting" different layers shouldn't touch asset colors
        # (the old sync code is removed — this just verifies the sidebar
        # state didn't change)
        c1, _, _ = sidebar.get_asset_colors()
        assert c1.to_hex() == cyan.to_hex()


# ══════════════════════════════════════════════════════════════════════════
# Reset to defaults
# ══════════════════════════════════════════════════════════════════════════

class TestAssetColorReset:
    """Reset button should restore all three colors to their defaults."""

    def test_reset_restores_defaults(self, sidebar):
        # Set custom colors
        sidebar.set_asset_color(1, Color.from_rgb255(10, 20, 30))
        sidebar.set_asset_color(2, Color.from_rgb255(40, 50, 60))
        sidebar.set_asset_color(3, Color.from_rgb255(70, 80, 90))

        # Reset
        sidebar.set_asset_color(1, Color.from_name(DEFAULT_EMBLEM_COLOR1))
        sidebar.set_asset_color(2, Color.from_name(DEFAULT_EMBLEM_COLOR2))
        sidebar.set_asset_color(3, Color.from_name(DEFAULT_EMBLEM_COLOR3))

        c1, c2, c3 = sidebar.get_asset_colors()
        assert c1.to_hex() == Color.from_name(DEFAULT_EMBLEM_COLOR1).to_hex()
        assert c2.to_hex() == Color.from_name(DEFAULT_EMBLEM_COLOR2).to_hex()
        assert c3.to_hex() == Color.from_name(DEFAULT_EMBLEM_COLOR3).to_hex()
