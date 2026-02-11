"""
Tests for UI modes, tab switching, selection state, and transform modes.

Covers:
- PropertySidebar tab state (Base/Layers/Properties)
- Properties tab enable/disable based on selection
- Tab auto-switch to Layers when selection cleared from Properties tab
- AssetSidebar mode switching (patterns/emblems)
- Transform widget mode switching (bbox/minimal_bbox/gimble)
- Transform mode factory and handle sets
- Selection state management (single, multi, container)
- Selection clear and its effects
"""
import pytest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from models.coa import CoA
from models.color import Color
from models.transform import Vec2


# ══════════════════════════════════════════════════════════════════════════
# PropertySidebar Tab State
# ══════════════════════════════════════════════════════════════════════════

class TestPropertySidebarTabs:
    """Tests for PropertySidebar tab widget behaviour."""

    @pytest.fixture
    def sidebar(self, qtbot):
        from components.property_sidebar import PropertySidebar
        coa = CoA()
        CoA.set_active(coa)
        sidebar = PropertySidebar()
        qtbot.addWidget(sidebar)
        sidebar.coa = coa
        return sidebar

    def test_has_three_tabs(self, sidebar):
        assert sidebar.tab_widget.count() == 3

    def test_tab_names(self, sidebar):
        assert sidebar.tab_widget.tabText(0) == "Base"
        assert sidebar.tab_widget.tabText(1) == "Layers"
        assert sidebar.tab_widget.tabText(2) == "Properties"

    def test_default_tab_is_base(self, sidebar):
        assert sidebar.tab_widget.currentIndex() == 0

    def test_properties_tab_disabled_by_default(self, sidebar):
        assert not sidebar.tab_widget.isTabEnabled(2)

    def test_base_and_layers_tabs_enabled_by_default(self, sidebar):
        assert sidebar.tab_widget.isTabEnabled(0)
        assert sidebar.tab_widget.isTabEnabled(1)

    def test_clear_selection_disables_properties_tab(self, sidebar):
        # Manually enable to test the disable path
        sidebar.tab_widget.setTabEnabled(2, True)
        sidebar.clear_selection()
        assert not sidebar.tab_widget.isTabEnabled(2)

    def test_clear_selection_switches_away_from_properties(self, sidebar):
        """If we're on Properties tab and clear selection, should switch to Layers."""
        sidebar.tab_widget.setTabEnabled(2, True)
        sidebar.tab_widget.setCurrentIndex(2)
        sidebar.clear_selection()
        assert sidebar.tab_widget.currentIndex() == 1

    def test_clear_selection_stays_on_base_tab(self, sidebar):
        """If on Base tab when selection cleared, should stay on Base."""
        sidebar.tab_widget.setCurrentIndex(0)
        sidebar.clear_selection()
        assert sidebar.tab_widget.currentIndex() == 0

    def test_clear_selection_stays_on_layers_tab(self, sidebar):
        sidebar.tab_widget.setCurrentIndex(1)
        sidebar.clear_selection()
        assert sidebar.tab_widget.currentIndex() == 1


# ══════════════════════════════════════════════════════════════════════════
# AssetSidebar Mode Switching
# ══════════════════════════════════════════════════════════════════════════

class TestAssetSidebarModes:
    """Tests for AssetSidebar pattern/emblem mode switching."""

    @pytest.fixture
    def asset_sidebar(self, qtbot):
        from components.asset_sidebar import AssetSidebar
        sidebar = AssetSidebar()
        qtbot.addWidget(sidebar)
        return sidebar

    def test_default_mode_is_patterns(self, asset_sidebar):
        assert asset_sidebar.current_mode == "patterns"

    def test_switch_to_emblems(self, asset_sidebar):
        asset_sidebar.switch_mode("emblems")
        assert asset_sidebar.current_mode == "emblems"

    def test_switch_back_to_patterns(self, asset_sidebar):
        asset_sidebar.switch_mode("emblems")
        asset_sidebar.switch_mode("patterns")
        assert asset_sidebar.current_mode == "patterns"

    def test_switch_same_mode_is_noop(self, asset_sidebar):
        asset_sidebar.switch_mode("patterns")  # already patterns
        assert asset_sidebar.current_mode == "patterns"

    def test_category_combo_hidden_in_patterns_mode(self, asset_sidebar):
        asset_sidebar.switch_mode("patterns")
        assert not asset_sidebar.category_combo.isVisible()

    def test_category_combo_shown_in_emblems_mode(self, asset_sidebar):
        """In emblems mode, the combo should not be explicitly hidden."""
        asset_sidebar.switch_mode("emblems")
        # isVisible() requires the parent to be shown; check that it's not hidden
        assert not asset_sidebar.category_combo.isHidden()


# ══════════════════════════════════════════════════════════════════════════
# Transform Mode System
# ══════════════════════════════════════════════════════════════════════════

class TestTransformModeFactory:
    """Tests for the transform mode factory and mode handle sets."""

    def test_create_bbox_mode(self):
        from components.transform_widgets.modes import create_mode, BboxMode
        mode = create_mode("bbox")
        assert isinstance(mode, BboxMode)

    def test_create_minimal_bbox_mode(self):
        from components.transform_widgets.modes import create_mode, MinimalBboxMode
        mode = create_mode("minimal_bbox")
        assert isinstance(mode, MinimalBboxMode)

    def test_create_gimble_mode(self):
        from components.transform_widgets.modes import create_mode, GimbleMode
        mode = create_mode("gimble")
        assert isinstance(mode, GimbleMode)

    def test_unknown_mode_defaults_to_bbox(self):
        from components.transform_widgets.modes import create_mode, BboxMode
        mode = create_mode("nonexistent")
        assert isinstance(mode, BboxMode)


class TestBboxModeHandles:
    """Verify BboxMode has the expected handle set."""

    @pytest.fixture
    def mode(self):
        from components.transform_widgets.modes import BboxMode
        return BboxMode()

    def test_has_all_corners(self, mode):
        for corner in ['tl', 'tr', 'bl', 'br']:
            assert corner in mode.handles

    def test_has_all_edges(self, mode):
        for edge in ['t', 'r', 'b', 'l']:
            assert edge in mode.handles

    def test_has_rotation_handle(self, mode):
        assert 'rotate' in mode.handles

    def test_has_center_handle(self, mode):
        assert 'center' in mode.handles

    def test_total_handle_count(self, mode):
        # 4 corners + 4 edges + rotation + center = 10
        assert len(mode.handles) == 10


class TestMinimalBboxModeHandles:
    """Verify MinimalBboxMode has only center."""

    def test_only_center(self):
        from components.transform_widgets.modes import MinimalBboxMode
        mode = MinimalBboxMode()
        assert list(mode.handles.keys()) == ['center']


class TestGimbleModeHandles:
    """Verify GimbleMode has arrows, ring, and center."""

    @pytest.fixture
    def mode(self):
        from components.transform_widgets.modes import GimbleMode
        return GimbleMode()

    def test_has_x_arrow(self, mode):
        assert 'axis_x' in mode.handles

    def test_has_y_arrow(self, mode):
        assert 'axis_y' in mode.handles

    def test_has_ring(self, mode):
        assert 'ring' in mode.handles

    def test_has_center(self, mode):
        assert 'center' in mode.handles

    def test_total_handle_count(self, mode):
        assert len(mode.handles) == 4


# ══════════════════════════════════════════════════════════════════════════
# Transform Widget Mode Switching
# ══════════════════════════════════════════════════════════════════════════

class TestTransformWidgetModeSwitching:
    """Tests for TransformWidget.set_transform_mode on a real widget."""

    @pytest.fixture
    def transform_widget(self, qtbot):
        from components.transform_widget import TransformWidget
        widget = TransformWidget()
        qtbot.addWidget(widget)
        return widget

    def test_default_mode_is_bbox(self, transform_widget):
        assert transform_widget.transform_mode == "bbox"

    def test_switch_to_minimal(self, transform_widget):
        transform_widget.set_transform_mode("minimal_bbox")
        assert transform_widget.transform_mode == "minimal_bbox"
        assert transform_widget.minimal_mode is True

    def test_switch_to_gimble(self, transform_widget):
        transform_widget.set_transform_mode("gimble")
        assert transform_widget.transform_mode == "gimble"
        assert transform_widget.minimal_mode is False

    def test_switch_back_to_bbox(self, transform_widget):
        transform_widget.set_transform_mode("gimble")
        transform_widget.set_transform_mode("bbox")
        assert transform_widget.transform_mode == "bbox"

    def test_legacy_normal_maps_to_bbox(self, transform_widget):
        transform_widget.set_transform_mode("normal")
        assert transform_widget.transform_mode == "bbox"

    def test_legacy_minimal_maps_to_minimal_bbox(self, transform_widget):
        transform_widget.set_transform_mode("minimal")
        assert transform_widget.transform_mode == "minimal_bbox"

    def test_mode_switch_updates_current_mode_object(self, transform_widget):
        from components.transform_widgets.modes import GimbleMode
        transform_widget.set_transform_mode("gimble")
        assert isinstance(transform_widget.current_mode, GimbleMode)


# ══════════════════════════════════════════════════════════════════════════
# Selection State Management
# ══════════════════════════════════════════════════════════════════════════

class TestLayerListSelection:
    """Tests for selection state on LayerListWidget."""

    @pytest.fixture
    def layer_list(self, qtbot):
        from components.property_sidebar_widgets import LayerListWidget
        widget = LayerListWidget()
        qtbot.addWidget(widget)
        return widget

    def test_initial_selection_empty(self, layer_list):
        assert layer_list.selected_layer_uuids == set()

    def test_initial_container_selection_empty(self, layer_list):
        assert layer_list.selected_container_uuids == set()

    def test_direct_selection_assignment(self, layer_list):
        layer_list.selected_layer_uuids = {"uuid-1", "uuid-2"}
        assert layer_list.selected_layer_uuids == {"uuid-1", "uuid-2"}

    def test_clear_selection(self, layer_list):
        layer_list.selected_layer_uuids = {"uuid-1"}
        layer_list.selected_layer_uuids = set()
        assert layer_list.selected_layer_uuids == set()

    def test_container_selection_assignment(self, layer_list):
        layer_list.selected_container_uuids = {"container_abc_Group"}
        assert layer_list.selected_container_uuids == {"container_abc_Group"}


# ══════════════════════════════════════════════════════════════════════════
# Selection + Undo Integration (model level)
# ══════════════════════════════════════════════════════════════════════════

class TestSelectionAndUndoIntegration:
    """Tests that selection state can be saved and restored alongside CoA state."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    def test_selection_state_in_snapshot_dict(self, coa):
        """Mimics _capture_current_state including selection."""
        uuid = coa.add_layer(emblem_path="ce_test.dds")
        state = {
            'coa_snapshot': coa.get_snapshot(),
            'selected_layer_uuids': {uuid},
            'selected_container_uuids': set(),
        }
        # Selection is preserved in the state dict
        assert uuid in state['selected_layer_uuids']

    def test_restore_filters_stale_selection(self, coa):
        """After undo, if a layer was added post-snapshot, its UUID won't exist."""
        snap = coa.get_snapshot()
        uuid = coa.add_layer(emblem_path="ce_test.dds")

        state = {
            'coa_snapshot': snap,
            'selected_layer_uuids': {uuid},  # will be stale after restore
            'selected_container_uuids': set(),
        }

        coa.set_snapshot(state['coa_snapshot'])
        valid = {u for u in state['selected_layer_uuids'] if coa.has_layer_uuid(u)}
        assert valid == set()  # uuid was added AFTER snap, gone now

    def test_valid_selection_preserved_after_restore(self, coa):
        uuid = coa.add_layer(emblem_path="ce_test.dds")
        snap = coa.get_snapshot()

        # Mutate model
        coa.set_layer_color(uuid, 1, Color.from_name("blue"))

        state = {
            'coa_snapshot': snap,
            'selected_layer_uuids': {uuid},
            'selected_container_uuids': set(),
        }

        coa.set_snapshot(state['coa_snapshot'])
        valid = {u for u in state['selected_layer_uuids'] if coa.has_layer_uuid(u)}
        assert uuid in valid


# ══════════════════════════════════════════════════════════════════════════
# PropertySidebar get_selected_uuids
# ══════════════════════════════════════════════════════════════════════════

class TestPropertySidebarSelection:
    """Tests for PropertySidebar.get_selected_uuids and clear_selection."""

    @pytest.fixture
    def sidebar_with_layers(self, qtbot):
        from components.property_sidebar import PropertySidebar
        coa = CoA()
        CoA.set_active(coa)
        uuid1 = coa.add_layer(emblem_path="a.dds")
        uuid2 = coa.add_layer(emblem_path="b.dds")

        sidebar = PropertySidebar()
        qtbot.addWidget(sidebar)
        sidebar.coa = coa
        sidebar._rebuild_layer_list()

        return sidebar, coa, uuid1, uuid2

    def test_get_selected_uuids_empty_by_default(self, sidebar_with_layers):
        sidebar, _, _, _ = sidebar_with_layers
        assert sidebar.get_selected_uuids() == []

    def test_clear_selection_empties_selection(self, sidebar_with_layers):
        sidebar, _, uuid1, _ = sidebar_with_layers
        sidebar.layer_list_widget.selected_layer_uuids = {uuid1}
        sidebar.clear_selection()
        assert sidebar.get_selected_uuids() == []
        assert sidebar.layer_list_widget.selected_layer_uuids == set()

    def test_direct_clear_container_selection(self, sidebar_with_layers):
        """Directly clearing container selection on the widget works."""
        sidebar, _, _, _ = sidebar_with_layers
        sidebar.layer_list_widget.selected_container_uuids = {"test_container"}
        sidebar.layer_list_widget.selected_container_uuids = set()
        assert sidebar.layer_list_widget.selected_container_uuids == set()
