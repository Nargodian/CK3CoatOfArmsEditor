"""
Tests for group/container UI operations and ScaleEditor unified-scale state.

Covers:
- Container collapse/expand state tracking
- Deleting collapsed groups
- Deleting expanded groups
- Group selection (regular, ctrl-click)
- Group visibility toggling
- Group duplication
- Container rename → collapsed state migration
- Group creation from selection
- Stale collapsed UUIDs after deletion

ScaleEditor:
- Unified mode default state
- Toggle unified → separate and back
- Y-slider visibility tied to unified mode
- X-change syncs Y in unified mode
- X-change independent of Y in separate mode
- Scale label text changes with mode
- set_scale_values / get_scale_values round-trip
- Flip checkbox state
- Auto-detection of non-uniform scales (unchecks unified)
"""
import pytest
from unittest.mock import MagicMock, patch

from models.coa import CoA
from models.color import Color
from models.transform import Vec2


# ══════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════

def _add_n_layers(coa, n, prefix="ce_layer"):
    """Add n layers, return list of UUIDs."""
    return [coa.add_layer(emblem_path=f"{prefix}_{i}.dds") for i in range(n)]


def _make_group(coa, uuids, name="TestGroup"):
    """Group layers and return container UUID."""
    return coa.create_container_from_layers(uuids, name=name)


def _make_layer_list_widget(coa, qtbot):
    """Create a LayerListWidget wired to a CoA (no MainWindow needed)."""
    from components.property_sidebar_widgets.layer_list_widget import LayerListWidget

    widget = LayerListWidget()
    qtbot.addWidget(widget)
    widget.coa = coa
    # Provide a mock main_window with _save_state
    widget.main_window = MagicMock()
    widget.main_window._save_state = MagicMock()
    widget.main_window.coa = coa
    # Stub callbacks so they can be asserted
    widget.on_selection_changed = MagicMock()
    return widget


# ══════════════════════════════════════════════════════════════════════════
# Container Collapse / Expand
# ══════════════════════════════════════════════════════════════════════════

class TestContainerCollapse:
    """Tests for collapsing and expanding container groups."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    def test_default_not_collapsed(self, coa, qtbot):
        """New containers start expanded (not in collapsed set)."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        assert container not in widget.collapsed_containers

    def test_toggle_collapse(self, coa, qtbot):
        """Toggling collapse adds container to collapsed set."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._toggle_container_collapse(container)
        assert container in widget.collapsed_containers

    def test_toggle_expand(self, coa, qtbot):
        """Toggling twice returns to expanded."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._toggle_container_collapse(container)
        widget._toggle_container_collapse(container)
        assert container not in widget.collapsed_containers

    def test_collapsed_hides_child_buttons(self, coa, qtbot):
        """When collapsed, child layer buttons are not in the button list."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        # Expanded: child buttons present
        button_uuids = {u for u, _ in widget.layer_buttons}
        assert uuids[0] in button_uuids
        assert uuids[1] in button_uuids

        # Collapse
        widget._toggle_container_collapse(container)
        button_uuids_after = {u for u, _ in widget.layer_buttons}
        assert uuids[0] not in button_uuids_after
        assert uuids[1] not in button_uuids_after
        # Root layer still present
        assert uuids[2] in button_uuids_after

    def test_container_marker_survives_collapse(self, coa, qtbot):
        """Container marker widget is still present when collapsed."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._toggle_container_collapse(container)
        marker_uuids = {cu for cu, _ in widget.container_markers}
        assert container in marker_uuids

    def test_multiple_containers_independent_collapse(self, coa, qtbot):
        """Collapsing one container does not affect others."""
        uuids = _add_n_layers(coa, 6)
        c1 = _make_group(coa, uuids[:2], name="GroupA")
        c2 = _make_group(coa, uuids[2:4], name="GroupB")
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._toggle_container_collapse(c1)
        assert c1 in widget.collapsed_containers
        assert c2 not in widget.collapsed_containers

        # GroupB children still visible
        button_uuids = {u for u, _ in widget.layer_buttons}
        assert uuids[2] in button_uuids
        assert uuids[3] in button_uuids


# ══════════════════════════════════════════════════════════════════════════
# Deleting Groups (Including Collapsed)
# ══════════════════════════════════════════════════════════════════════════

class TestDeleteGroup:
    """Tests for deleting container groups."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    def test_delete_expanded_group(self, coa, qtbot):
        """Deleting an expanded group removes all contained layers."""
        uuids = _add_n_layers(coa, 4)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._handle_container_delete(container)
        assert coa.get_layer_count() == 2
        remaining = coa.get_all_layer_uuids()
        assert uuids[0] not in remaining
        assert uuids[1] not in remaining
        assert uuids[2] in remaining
        assert uuids[3] in remaining

    def test_delete_collapsed_group(self, coa, qtbot):
        """Deleting a collapsed group still removes all contained layers."""
        uuids = _add_n_layers(coa, 4)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        # Collapse, then delete
        widget._toggle_container_collapse(container)
        widget._handle_container_delete(container)

        assert coa.get_layer_count() == 2
        remaining = coa.get_all_layer_uuids()
        assert uuids[0] not in remaining
        assert uuids[1] not in remaining

    def test_delete_group_saves_undo(self, coa, qtbot):
        """Deleting a group triggers a single undo save."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._handle_container_delete(container)
        widget.main_window._save_state.assert_called_once_with("Delete Container")

    def test_delete_group_clears_selected_container(self, coa, qtbot):
        """Deleting a selected group clears it from selected_container_uuids."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        # Select the container, then delete it
        widget._select_container(container)
        assert container in widget.selected_container_uuids

        widget._handle_container_delete(container)
        assert container not in widget.selected_container_uuids

    def test_delete_group_clears_selected_layers(self, coa, qtbot):
        """Deleting a selected group removes contained layers from selection."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._select_container(container)
        assert uuids[0] in widget.selected_layer_uuids

        widget._handle_container_delete(container)
        assert uuids[0] not in widget.selected_layer_uuids
        assert uuids[1] not in widget.selected_layer_uuids

    def test_delete_collapsed_group_no_buttons_remain(self, coa, qtbot):
        """After deleting a collapsed group, UI shows no buttons for deleted layers."""
        uuids = _add_n_layers(coa, 4)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._toggle_container_collapse(container)
        widget._handle_container_delete(container)

        button_uuids = {u for u, _ in widget.layer_buttons}
        assert uuids[0] not in button_uuids
        assert uuids[1] not in button_uuids
        # Remaining root layers still show
        assert uuids[2] in button_uuids
        assert uuids[3] in button_uuids

    def test_delete_group_no_container_marker(self, coa, qtbot):
        """After deleting a group, its container marker is gone."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._handle_container_delete(container)
        marker_uuids = {cu for cu, _ in widget.container_markers}
        assert container not in marker_uuids

    def test_delete_empty_group_noop(self, coa, qtbot):
        """Deleting a group with no layers is a no-op."""
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()
        # Pass a bogus container UUID
        widget._handle_container_delete("container_fake_NoLayers")
        # Should not crash, save state should not be called
        widget.main_window._save_state.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════
# Container Selection
# ══════════════════════════════════════════════════════════════════════════

class TestContainerSelection:
    """Tests for selecting/deselecting container groups."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    def test_select_container_adds_all_layers(self, coa, qtbot):
        """Clicking a container selects all its child layers."""
        uuids = _add_n_layers(coa, 4)
        container = _make_group(coa, uuids[:3])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._select_container(container)
        assert uuids[0] in widget.selected_layer_uuids
        assert uuids[1] in widget.selected_layer_uuids
        assert uuids[2] in widget.selected_layer_uuids
        # Root layer not selected
        assert uuids[3] not in widget.selected_layer_uuids

    def test_select_container_sets_container_uuid(self, coa, qtbot):
        """Selecting a container adds it to selected_container_uuids."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._select_container(container)
        assert container in widget.selected_container_uuids

    def test_deselect_container_on_reclick(self, coa, qtbot):
        """Clicking an already-selected container deselects everything."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._select_container(container)
        widget._select_container(container)
        assert len(widget.selected_container_uuids) == 0
        assert len(widget.selected_layer_uuids) == 0

    def test_select_container_deselects_other(self, coa, qtbot):
        """Selecting a container replaces any previous selection."""
        uuids = _add_n_layers(coa, 5)
        c1 = _make_group(coa, uuids[:2], name="A")
        c2 = _make_group(coa, uuids[2:4], name="B")
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._select_container(c1)
        widget._select_container(c2)
        assert c1 not in widget.selected_container_uuids
        assert c2 in widget.selected_container_uuids
        # Only c2's layers should be selected
        assert uuids[0] not in widget.selected_layer_uuids
        assert uuids[2] in widget.selected_layer_uuids

    def test_select_collapsed_container(self, coa, qtbot):
        """Selecting a collapsed container still selects all its layers."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._toggle_container_collapse(container)
        widget._select_container(container)
        assert uuids[0] in widget.selected_layer_uuids
        assert uuids[1] in widget.selected_layer_uuids

    def test_selection_callback_on_container_select(self, coa, qtbot):
        """Selection callback fires when container is selected."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget.on_selection_changed.reset_mock()
        widget._select_container(container)
        widget.on_selection_changed.assert_called()

    def test_clear_selection_clears_containers(self, coa, qtbot):
        """clear_selection() clears container selection too."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._select_container(container)
        widget.clear_selection()
        assert len(widget.selected_container_uuids) == 0
        assert len(widget.selected_layer_uuids) == 0


# ══════════════════════════════════════════════════════════════════════════
# Container Visibility
# ══════════════════════════════════════════════════════════════════════════

class TestContainerVisibility:
    """Tests for toggling visibility on entire groups."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    def test_toggle_visibility_hides_all(self, coa, qtbot):
        """Toggling visibility when layers are visible hides them all."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        # All layers start visible
        assert all(coa.get_layer_visible(u) for u in uuids[:2])

        widget._handle_container_visibility_toggle(container)
        assert all(not coa.get_layer_visible(u) for u in uuids[:2])

    def test_toggle_visibility_shows_all(self, coa, qtbot):
        """Second toggle restores visibility."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._handle_container_visibility_toggle(container)
        widget._handle_container_visibility_toggle(container)
        assert all(coa.get_layer_visible(u) for u in uuids[:2])

    def test_visibility_toggle_mixed(self, coa, qtbot):
        """If some layers visible, some not, toggle hides all first."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        coa.set_layer_visible(uuids[0], False)  # One hidden
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._handle_container_visibility_toggle(container)
        # Should hide all (since at least one was visible)
        assert all(not coa.get_layer_visible(u) for u in uuids[:2])


# ══════════════════════════════════════════════════════════════════════════
# Container Duplication
# ══════════════════════════════════════════════════════════════════════════

class TestContainerDuplicate:
    """Tests for duplicating container groups."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    def test_duplicate_container_creates_new_layers(self, coa, qtbot):
        """Duplicating a container creates new layers."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()
        count_before = coa.get_layer_count()

        widget._handle_container_duplicate(container)
        assert coa.get_layer_count() == count_before + 2

    def test_duplicate_container_new_uuid(self, coa, qtbot):
        """Duplicated container has a different container UUID."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._handle_container_duplicate(container)
        all_containers = coa.get_all_containers()
        assert len(all_containers) == 2
        assert container in all_containers

    def test_duplicate_selects_new_container(self, coa, qtbot):
        """After duplicating, the new container's layers are selected."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._handle_container_duplicate(container)
        # Original layers should not be in selection
        assert uuids[0] not in widget.selected_layer_uuids
        assert uuids[1] not in widget.selected_layer_uuids
        # New layers should be selected
        assert len(widget.selected_layer_uuids) == 2

    def test_duplicate_saves_undo(self, coa, qtbot):
        """Duplicating a group saves undo state."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._handle_container_duplicate(container)
        widget.main_window._save_state.assert_called_once_with("Duplicate Container")


# ══════════════════════════════════════════════════════════════════════════
# Group Creation from Selection
# ══════════════════════════════════════════════════════════════════════════

class TestGroupCreation:
    """Tests for creating groups from selected layers."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    def test_create_group_from_selection(self, coa, qtbot):
        """Creating a group from 2+ selected layers assigns container."""
        uuids = _add_n_layers(coa, 4)
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget.selected_layer_uuids = {uuids[0], uuids[1]}
        widget._create_container_from_selection()

        # Both layers should now belong to the same container
        c0 = coa.get_layer_container(uuids[0])
        c1 = coa.get_layer_container(uuids[1])
        assert c0 is not None
        assert c0 == c1

    def test_create_group_too_few_layers_noop(self, coa, qtbot):
        """Creating a group from <2 layers does nothing."""
        uuids = _add_n_layers(coa, 3)
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget.selected_layer_uuids = {uuids[0]}
        widget._create_container_from_selection()

        assert coa.get_layer_container(uuids[0]) is None

    def test_create_group_selects_container(self, coa, qtbot):
        """After grouping, the new container is selected."""
        uuids = _add_n_layers(coa, 4)
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget.selected_layer_uuids = {uuids[0], uuids[1]}
        widget._create_container_from_selection()

        assert len(widget.selected_container_uuids) == 1

    def test_create_group_saves_undo(self, coa, qtbot):
        """Grouping triggers undo save."""
        uuids = _add_n_layers(coa, 4)
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget.selected_layer_uuids = {uuids[0], uuids[1]}
        widget._create_container_from_selection()
        widget.main_window._save_state.assert_called_once_with("Create Container")


# ══════════════════════════════════════════════════════════════════════════
# Stale Collapsed State
# ══════════════════════════════════════════════════════════════════════════

class TestStaleCollapsedState:
    """Tests for stale entries in collapsed_containers after deletion."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    def test_collapsed_uuid_orphaned_after_delete(self, coa, qtbot):
        """Deleting a collapsed group leaves its UUID in collapsed_containers.
        This is a known harmless leak — the test documents the behavior."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._toggle_container_collapse(container)
        widget._handle_container_delete(container)

        # Document: collapsed_containers is NOT cleaned up
        assert container in widget.collapsed_containers

    def test_stale_collapsed_uuid_harmless_on_rebuild(self, coa, qtbot):
        """A stale UUID in collapsed_containers doesn't cause errors on rebuild."""
        uuids = _add_n_layers(coa, 3)
        container = _make_group(coa, uuids[:2])
        widget = _make_layer_list_widget(coa, qtbot)
        widget.rebuild()

        widget._toggle_container_collapse(container)
        widget._handle_container_delete(container)

        # Rebuild again — should not crash
        widget.rebuild()
        assert coa.get_layer_count() == 1


# ══════════════════════════════════════════════════════════════════════════
# ScaleEditor — Unified Scale State
# ══════════════════════════════════════════════════════════════════════════

class TestScaleEditorUnifiedState:
    """Tests for ScaleEditor unified/separate mode and value tracking."""

    @pytest.fixture
    def editor(self, qtbot):
        from components.property_sidebar_widgets.property_editors import ScaleEditor
        ed = ScaleEditor()
        qtbot.addWidget(ed)
        return ed

    def test_default_unified_mode(self, editor):
        """ScaleEditor starts in unified mode."""
        assert editor.unified_mode is True
        assert editor.unified_check.isChecked()

    def test_y_slider_hidden_in_unified(self, editor):
        """Y-slider is hidden in unified mode."""
        assert editor.scale_y_slider.isHidden()

    def test_toggle_to_separate(self, editor):
        """Unchecking unified makes Y-slider visible."""
        editor.unified_check.setChecked(False)
        assert editor.unified_mode is False
        # Use isHidden() since isVisible() requires the entire widget tree to be shown
        assert not editor.scale_y_slider.isHidden()

    def test_toggle_back_to_unified(self, editor):
        """Re-checking unified hides Y-slider and syncs Y to X."""
        editor.unified_check.setChecked(False)
        editor.scale_x_slider.setValue(0.7)
        editor.scale_y_slider.setValue(0.3)

        editor.unified_check.setChecked(True)
        assert editor.unified_mode is True
        assert editor.scale_y_slider.isHidden()
        # Y should have been synced to X
        assert abs(editor.scale_y_slider.value() - 0.7) < 0.02

    def test_label_text_unified(self, editor):
        """Label reads 'Scale:' in unified mode."""
        assert "Scale" in editor.scale_x_slider.label.text()
        # Should not say "Scale X" in unified
        assert "X" not in editor.scale_x_slider.label.text()

    def test_label_text_separate(self, editor):
        """Label reads 'Scale X:' in separate mode."""
        editor.unified_check.setChecked(False)
        assert "Scale X" in editor.scale_x_slider.label.text()

    def test_x_change_syncs_y_in_unified(self, editor):
        """Changing X updates Y in unified mode."""
        # Drive the underlying QSlider directly so signals fire (setValue blocks them)
        editor.scale_x_slider.slider.setValue(int(0.8 * 100))
        assert abs(editor.scale_y_slider.value() - 0.8) < 0.02

    def test_x_change_independent_in_separate(self, editor):
        """Changing X does not affect Y in separate mode."""
        editor.unified_check.setChecked(False)
        editor.scale_y_slider.setValue(0.3)
        editor.scale_x_slider.setValue(0.9)
        assert abs(editor.scale_y_slider.value() - 0.3) < 0.02

    def test_get_set_round_trip(self, editor):
        """set_scale_values / get_scale_values round-trips correctly."""
        editor.set_scale_values(0.6, 0.4, True, False)
        sx, sy, fx, fy = editor.get_scale_values()
        assert abs(sx - 0.6) < 0.02
        assert abs(sy - 0.4) < 0.02
        assert fx is True
        assert fy is False

    def test_flip_x_state(self, editor):
        """Flip X checkbox tracks correctly."""
        assert not editor.flip_x_check.isChecked()
        editor.flip_x_check.setChecked(True)
        _, _, flip_x, _ = editor.get_scale_values()
        assert flip_x is True

    def test_flip_y_state(self, editor):
        """Flip Y checkbox tracks correctly."""
        editor.flip_y_check.setChecked(True)
        _, _, _, flip_y = editor.get_scale_values()
        assert flip_y is True

    def test_set_scale_does_not_emit(self, editor, qtbot):
        """set_scale_values blocks signals so no spurious valueChanged."""
        with qtbot.assertNotEmitted(editor.valueChanged):
            editor.set_scale_values(0.5, 0.5, False, False)

    def test_value_changed_on_x_slider(self, editor, qtbot):
        """Moving X slider emits valueChanged."""
        with qtbot.waitSignal(editor.valueChanged, timeout=1000):
            # Drive underlying QSlider directly so signals fire
            editor.scale_x_slider.slider.setValue(int(0.9 * 100))

    def test_value_changed_on_flip_toggle(self, editor, qtbot):
        """Toggling flip emits valueChanged."""
        with qtbot.waitSignal(editor.valueChanged, timeout=1000):
            editor.flip_x_check.setChecked(True)


# ══════════════════════════════════════════════════════════════════════════
# ScaleEditor — Auto-Detection of Non-Uniform Scales
# ══════════════════════════════════════════════════════════════════════════

class TestScaleEditorAutoDetect:
    """Tests simulating the auto-detection logic from PropertySidebar._load_layer_properties.
    
    When scales differ or are 'Mixed', the unified checkbox should be unchecked.
    """

    @pytest.fixture
    def editor(self, qtbot):
        from components.property_sidebar_widgets.property_editors import ScaleEditor
        ed = ScaleEditor()
        qtbot.addWidget(ed)
        return ed

    def test_uncheck_when_scales_differ(self, editor):
        """Unified checkbox unchecked when scale_x != scale_y by > 0.01."""
        editor.unified_check.setChecked(True)
        scale_x = 0.5
        scale_y = 0.8

        # Simulate the auto-detection from _load_layer_properties
        editor.unified_check.blockSignals(True)
        if abs(abs(scale_x) - abs(scale_y)) > 0.01:
            editor.unified_check.setChecked(False)
        editor.unified_check.blockSignals(False)

        assert not editor.unified_check.isChecked()

    def test_stay_checked_when_scales_equal(self, editor):
        """Unified checkbox stays checked when scales are equal."""
        editor.unified_check.setChecked(True)
        scale_x = 0.7
        scale_y = 0.7

        editor.unified_check.blockSignals(True)
        if abs(abs(scale_x) - abs(scale_y)) > 0.01:
            editor.unified_check.setChecked(False)
        editor.unified_check.blockSignals(False)

        assert editor.unified_check.isChecked()

    def test_uncheck_on_mixed(self, editor):
        """Unified checkbox unchecked when value is 'Mixed'."""
        editor.unified_check.setChecked(True)
        scale_x_raw = 'Mixed'

        editor.unified_check.blockSignals(True)
        if scale_x_raw == 'Mixed':
            editor.unified_check.setChecked(False)
        editor.unified_check.blockSignals(False)

        assert not editor.unified_check.isChecked()

    def test_nearly_equal_stays_checked(self, editor):
        """Scales within 0.01 tolerance are treated as equal."""
        editor.unified_check.setChecked(True)
        scale_x = 0.500
        scale_y = 0.505

        editor.unified_check.blockSignals(True)
        if abs(abs(scale_x) - abs(scale_y)) > 0.01:
            editor.unified_check.setChecked(False)
        editor.unified_check.blockSignals(False)

        assert editor.unified_check.isChecked()

    def test_negative_scales_treated_by_abs(self, editor):
        """Negative scales (flips) use absolute value for comparison."""
        editor.unified_check.setChecked(True)
        scale_x = -0.7
        scale_y = 0.7

        editor.unified_check.blockSignals(True)
        if abs(abs(scale_x) - abs(scale_y)) > 0.01:
            editor.unified_check.setChecked(False)
        editor.unified_check.blockSignals(False)

        # Same absolute value → stays checked
        assert editor.unified_check.isChecked()

    def test_block_signals_during_autodetect(self, editor, qtbot):
        """Auto-detection should not emit valueChanged."""
        editor.unified_check.setChecked(True)

        with qtbot.assertNotEmitted(editor.valueChanged, wait=100):
            editor.unified_check.blockSignals(True)
            editor.unified_check.setChecked(False)
            editor.unified_check.blockSignals(False)
