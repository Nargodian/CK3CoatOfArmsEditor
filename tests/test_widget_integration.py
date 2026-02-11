"""
pytest-qt widget integration tests.

Tests the interaction between UI widgets and the CoA model,
specifically the color change workflow that has been a recurring pain point.

These tests use qtbot to:
- Create real Qt widgets
- Simulate the color change flow (bypassing the modal dialog)
- Verify the model updates correctly
- Verify signals fire as expected
"""
import pytest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from models.coa import CoA
from models.color import Color
from models.transform import Vec2


# ══════════════════════════════════════════════════════════════════════════
# PropertySidebar Color Workflow
# ══════════════════════════════════════════════════════════════════════════

class TestPropertySidebarColorFlow:
    """Test the exact code path: button click → _on_layer_color_changed → coa.set_layer_color.
    
    We bypass the ColorPickerDialog (it's modal) and call _on_layer_color_changed's
    internal logic directly, which is what actually crashed.
    """

    @pytest.fixture
    def sidebar_with_coa(self, qtbot):
        """Create a PropertySidebar connected to a CoA with one layer."""
        from components.property_sidebar import PropertySidebar

        coa = CoA()
        CoA.set_active(coa)
        uuid = coa.add_layer(emblem_path="ce_fleur.dds")

        sidebar = PropertySidebar()
        qtbot.addWidget(sidebar)
        sidebar.coa = coa

        return sidebar, coa, uuid

    @pytest.mark.parametrize("color_index", [1, 2, 3])
    def test_set_layer_color_via_coa(self, sidebar_with_coa, color_index):
        """The exact call chain that crashed with color3:
        coa.set_layer_color(uuid, color_index, color) → layer.color3 = color
        """
        sidebar, coa, uuid = sidebar_with_coa
        new_color = Color.from_name("white")

        # This is the call that PropertySidebar._on_layer_color_changed makes
        coa.set_layer_color(uuid, color_index, new_color)

        # Verify it stuck
        result = coa.get_layer_color(uuid, color_index)
        assert result.r == new_color.r
        assert result.g == new_color.g
        assert result.b == new_color.b

    @pytest.mark.parametrize("color_index", [1, 2, 3])
    def test_get_layer_color_returns_color_object(self, sidebar_with_coa, color_index):
        """get_layer_color must return Color objects for all indices."""
        sidebar, coa, uuid = sidebar_with_coa
        result = coa.get_layer_color(uuid, color_index)
        assert isinstance(result, Color)


# ══════════════════════════════════════════════════════════════════════════
# Base Color Tab Workflow
# ══════════════════════════════════════════════════════════════════════════

class TestBaseColorFlow:
    """Test base pattern color changes through the model."""

    @pytest.fixture
    def coa_model(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    @pytest.mark.parametrize("color_index", [1, 2, 3])
    def test_set_base_color(self, coa_model, color_index):
        new_color = Color.from_name("blue")
        coa_model.set_base_color(color_index, new_color)

        attr = f"pattern_color{color_index}"
        result = getattr(coa_model, attr)
        assert result.r == new_color.r
        assert result.g == new_color.g
        assert result.b == new_color.b


# ══════════════════════════════════════════════════════════════════════════
# LayerListWidget Color Buttons
# ══════════════════════════════════════════════════════════════════════════

class TestLayerListColorButtons:
    """Test that color button creation and callback wiring works for all 3 colors."""

    @pytest.fixture
    def layer_list(self, qtbot):
        from components.property_sidebar_widgets import LayerListWidget
        widget = LayerListWidget()
        qtbot.addWidget(widget)
        return widget

    def test_color_callback_wiring(self, layer_list):
        """Verify on_color_changed callback can be set."""
        called_with = []

        def mock_callback(uuid, color_index):
            called_with.append((uuid, color_index))

        layer_list.on_color_changed = mock_callback
        # Simulate what the button lambda does
        layer_list._handle_color_pick("test-uuid", 1)
        layer_list._handle_color_pick("test-uuid", 2)
        layer_list._handle_color_pick("test-uuid", 3)

        assert len(called_with) == 3
        assert called_with[0] == ("test-uuid", 1)
        assert called_with[1] == ("test-uuid", 2)
        assert called_with[2] == ("test-uuid", 3)


# ══════════════════════════════════════════════════════════════════════════
# Full Color Round-Trip: Set → Snapshot → Restore → Verify
# ══════════════════════════════════════════════════════════════════════════

class TestColorUndoRedo:
    """Simulate the undo/redo flow for color changes."""

    def test_undo_color3_change(self, qtbot):
        """Change color3, snapshot, change again, restore → original color3 must return."""
        coa = CoA()
        CoA.set_active(coa)
        uuid = coa.add_layer(emblem_path="ce_test.dds")

        # Set initial colors
        coa.set_layer_color(uuid, 1, Color.from_name("red"))
        coa.set_layer_color(uuid, 2, Color.from_name("blue"))
        coa.set_layer_color(uuid, 3, Color.from_name("white"))

        # Take snapshot (simulates _save_state)
        snapshot = coa.get_snapshot()

        # User changes color3
        coa.set_layer_color(uuid, 3, Color.from_name("black"))
        assert coa.get_layer_color(uuid, 3).name == "black"

        # Undo (restore snapshot)
        coa.set_snapshot(snapshot)

        # Verify color3 is restored
        layer = coa.get_layer_by_index(0)
        assert layer.color3.name == "white"

    def test_undo_base_color3_change(self):
        """Same but for base pattern color3."""
        coa = CoA()
        CoA.set_active(coa)
        coa.pattern_color3 = Color.from_name("blue")
        snap = coa.get_snapshot()

        coa.pattern_color3 = Color.from_name("red")
        assert coa.pattern_color3.name == "red"

        coa.set_snapshot(snap)
        assert coa.pattern_color3.name == "blue"


# ══════════════════════════════════════════════════════════════════════════
# Asset Sidebar Color Integration
# ══════════════════════════════════════════════════════════════════════════

class TestAssetSidebarColors:
    """Test that _get_current_layer_colors returns all 3 colors."""

    def test_default_colors_dict_has_all_keys(self):
        """Even without a main_window, defaults must include all 6 color keys."""
        from components.asset_sidebar import AssetSidebar
        sidebar = AssetSidebar()
        colors = sidebar._get_current_layer_colors()

        assert 'color1' in colors
        assert 'color2' in colors
        assert 'color3' in colors
        assert 'background1' in colors
        assert 'background2' in colors
        assert 'background3' in colors

        for key in colors:
            assert isinstance(colors[key], Color), f"{key} is not a Color object"
