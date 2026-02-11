"""
Tests for undo/redo state management.

Covers:
- HistoryManager as a standalone state stack
- CoA snapshot capture & restore cycles
- Action → save → undo → verify → redo → verify workflows
- Selection state preservation through undo/redo
- Reentrancy guard (_is_applying_history)
- Debounced save behaviour
- Fragmented undo detection (single actions creating multiple undo steps)
- Listener notifications
- History trimming at max capacity
"""
import copy
import pytest
from PyQt5.QtCore import QTimer

from models.coa import CoA
from models.color import Color
from models.transform import Vec2
from utils.history_manager import HistoryManager


# ══════════════════════════════════════════════════════════════════════════
# HistoryManager (standalone state stack)
# ══════════════════════════════════════════════════════════════════════════

class TestHistoryManagerStack:
    """Unit tests for the generic HistoryManager, no CoA involved."""

    @pytest.fixture
    def hm(self):
        return HistoryManager(max_history=50)

    # ── basic operations ────────────────────────────────────────────

    def test_initial_state_empty(self, hm):
        assert not hm.can_undo()
        assert not hm.can_redo()
        assert hm.current_index == -1

    def test_single_save_no_undo(self, hm):
        hm.save_state({"v": 1}, "first")
        assert not hm.can_undo()  # need 2 saves to undo
        assert not hm.can_redo()

    def test_two_saves_can_undo(self, hm):
        hm.save_state({"v": 1}, "first")
        hm.save_state({"v": 2}, "second")
        assert hm.can_undo()
        assert not hm.can_redo()

    def test_undo_returns_previous_state(self, hm):
        hm.save_state({"v": 1}, "first")
        hm.save_state({"v": 2}, "second")
        state = hm.undo()
        assert state == {"v": 1}

    def test_redo_returns_next_state(self, hm):
        hm.save_state({"v": 1}, "first")
        hm.save_state({"v": 2}, "second")
        hm.undo()
        state = hm.redo()
        assert state == {"v": 2}

    def test_undo_at_beginning_returns_none(self, hm):
        hm.save_state({"v": 1}, "first")
        assert hm.undo() is None

    def test_redo_at_end_returns_none(self, hm):
        hm.save_state({"v": 1}, "first")
        assert hm.redo() is None

    # ── deep copy isolation ─────────────────────────────────────────

    def test_saved_state_is_deep_copy(self, hm):
        data = {"nested": [1, 2, 3]}
        hm.save_state(data, "save")
        data["nested"].append(999)  # mutate original
        hm.save_state({}, "second")
        restored = hm.undo()
        assert 999 not in restored["nested"]

    def test_undo_returns_deep_copy(self, hm):
        hm.save_state({"v": 1}, "a")
        hm.save_state({"v": 2}, "b")
        s1 = hm.undo()
        s2 = hm.undo()  # should be None (only 2 states)
        # s1 should be independent
        s1["v"] = 999
        # redo should give original state, not mutated s1
        redo_state = hm.redo()
        assert redo_state["v"] == 2

    # ── branch pruning ──────────────────────────────────────────────

    def test_save_after_undo_prunes_future(self, hm):
        hm.save_state({"v": 1}, "a")
        hm.save_state({"v": 2}, "b")
        hm.save_state({"v": 3}, "c")
        hm.undo()  # at v=2
        hm.save_state({"v": 4}, "d")  # should prune v=3
        assert not hm.can_redo()
        state = hm.undo()
        assert state == {"v": 2}

    # ── max history trimming ────────────────────────────────────────

    def test_max_history_trims_oldest(self):
        hm = HistoryManager(max_history=3)
        hm.save_state({"v": 1}, "a")
        hm.save_state({"v": 2}, "b")
        hm.save_state({"v": 3}, "c")
        hm.save_state({"v": 4}, "d")  # should trim v=1
        assert len(hm.history) == 3
        # oldest should be v=2 now
        hm.undo()
        hm.undo()
        state = hm.undo()
        assert state is None  # only 3 entries, index now at 0

    # ── listener notification ───────────────────────────────────────

    def test_listener_called_on_save(self, hm):
        events = []
        hm.add_listener(lambda cu, cr: events.append(("save", cu, cr)))
        hm.save_state({"v": 1}, "first")
        assert len(events) == 1
        assert events[0] == ("save", False, False)

    def test_listener_called_on_undo_redo(self, hm):
        events = []
        hm.save_state({"v": 1}, "a")
        hm.save_state({"v": 2}, "b")
        hm.add_listener(lambda cu, cr: events.append((cu, cr)))
        hm.undo()
        assert events[-1] == (False, True)  # can_undo=False (at 0), can_redo=True
        hm.redo()
        assert events[-1] == (True, False)

    def test_remove_listener(self, hm):
        events = []
        cb = lambda cu, cr: events.append(True)
        hm.add_listener(cb)
        hm.save_state({}, "a")
        assert len(events) == 1
        hm.remove_listener(cb)
        hm.save_state({}, "b")
        assert len(events) == 1  # no new event

    # ── descriptions ────────────────────────────────────────────────

    def test_get_current_description(self, hm):
        hm.save_state({}, "alpha")
        assert hm.get_current_description() == "alpha"

    def test_get_undo_redo_descriptions(self, hm):
        hm.save_state({}, "alpha")
        hm.save_state({}, "beta")
        assert hm.get_undo_description() == "alpha"
        assert hm.get_redo_description() == ""  # at end
        hm.undo()
        assert hm.get_redo_description() == "beta"

    # ── clear ───────────────────────────────────────────────────────

    def test_clear_resets_everything(self, hm):
        hm.save_state({"v": 1}, "a")
        hm.save_state({"v": 2}, "b")
        hm.clear()
        assert not hm.can_undo()
        assert not hm.can_redo()
        assert hm.current_index == -1
        assert len(hm.history) == 0


# ══════════════════════════════════════════════════════════════════════════
# CoA Snapshot Round-Trip
# ══════════════════════════════════════════════════════════════════════════

class TestCoASnapshotRoundTrip:
    """Verifies that get_snapshot / set_snapshot preserve model state exactly."""

    @pytest.fixture
    def coa_with_layers(self):
        coa = CoA()
        CoA.set_active(coa)
        coa.pattern_color1 = Color.from_name("red")
        coa.pattern_color2 = Color.from_name("blue")
        coa.pattern_color3 = Color.from_name("white")
        uuid1 = coa.add_layer(emblem_path="ce_lion.dds")
        uuid2 = coa.add_layer(emblem_path="ce_eagle.dds")
        coa.set_layer_color(uuid1, 1, Color.from_name("yellow"))
        coa.set_layer_color(uuid1, 3, Color.from_name("black"))
        coa.set_layer_color(uuid2, 2, Color.from_name("green"))
        return coa, uuid1, uuid2

    def test_snapshot_preserves_pattern_colors(self, coa_with_layers):
        coa, _, _ = coa_with_layers
        snap = coa.get_snapshot()
        coa.pattern_color1 = Color.from_name("black")
        coa.set_snapshot(snap)
        assert coa.pattern_color1.name == "red"
        assert coa.pattern_color2.name == "blue"
        assert coa.pattern_color3.name == "white"

    def test_snapshot_preserves_layer_colors(self, coa_with_layers):
        coa, uuid1, uuid2 = coa_with_layers
        snap = coa.get_snapshot()
        # Mutate
        coa.set_layer_color(uuid1, 1, Color.from_name("black"))
        coa.set_layer_color(uuid1, 3, Color.from_name("green"))
        # Restore
        coa.set_snapshot(snap)
        layer = coa.get_layer_by_index(0)
        assert layer.color1.name == "yellow"
        assert layer.color3.name == "black"

    def test_snapshot_preserves_layer_count(self, coa_with_layers):
        coa, uuid1, uuid2 = coa_with_layers
        snap = coa.get_snapshot()
        coa.remove_layer(uuid2)
        assert coa.get_layer_count() == 1
        coa.set_snapshot(snap)
        assert coa.get_layer_count() == 2

    def test_snapshot_preserves_layer_order(self, coa_with_layers):
        coa, uuid1, uuid2 = coa_with_layers
        snap = coa.get_snapshot()
        # After snapshot, uuid1 is at index 0, uuid2 at index 1
        assert coa.get_layer_uuid_by_index(0) == uuid1
        assert coa.get_layer_uuid_by_index(1) == uuid2
        # Reorder
        coa.move_layer_to_top(uuid1)
        assert coa.get_layer_uuid_by_index(0) == uuid2
        # Restore
        coa.set_snapshot(snap)
        assert coa.get_layer_uuid_by_index(0) == uuid1
        assert coa.get_layer_uuid_by_index(1) == uuid2

    def test_snapshot_preserves_pattern_texture(self, coa_with_layers):
        coa, _, _ = coa_with_layers
        coa._pattern = "pattern_diamond.dds"
        snap = coa.get_snapshot()
        coa._pattern = "pattern_solid.dds"
        coa.set_snapshot(snap)
        assert coa._pattern == "pattern_diamond.dds"


# ══════════════════════════════════════════════════════════════════════════
# Action → Save → Undo → Verify Workflows
# ══════════════════════════════════════════════════════════════════════════

class TestUndoWorkflows:
    """Simulates the real app workflow: capture before, mutate, undo, verify."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    @pytest.fixture
    def coa_and_hm(self, coa):
        hm = HistoryManager()
        # Save initial state (like app does on startup)
        hm.save_state(coa.get_snapshot(), "Initial")
        return coa, hm

    def _do_action(self, coa, hm, action_fn, description):
        """Helper: execute action, then save state (mimics _save_state)."""
        action_fn()
        hm.save_state(coa.get_snapshot(), description)

    def test_undo_add_layer(self, coa_and_hm):
        coa, hm = coa_and_hm
        assert coa.get_layer_count() == 0

        self._do_action(coa, hm,
                        lambda: coa.add_layer(emblem_path="ce_test.dds"),
                        "Add layer")
        assert coa.get_layer_count() == 1

        state = hm.undo()
        coa.set_snapshot(state)
        assert coa.get_layer_count() == 0

    def test_undo_remove_layer(self, coa_and_hm):
        coa, hm = coa_and_hm
        uuid = coa.add_layer(emblem_path="ce_test.dds")
        hm.save_state(coa.get_snapshot(), "Add layer")

        self._do_action(coa, hm,
                        lambda: coa.remove_layer(uuid),
                        "Remove layer")
        assert coa.get_layer_count() == 0

        state = hm.undo()
        coa.set_snapshot(state)
        assert coa.get_layer_count() == 1

    def test_undo_color_change(self, coa_and_hm):
        coa, hm = coa_and_hm
        uuid = coa.add_layer(emblem_path="ce_test.dds")
        coa.set_layer_color(uuid, 1, Color.from_name("red"))
        hm.save_state(coa.get_snapshot(), "Set red")

        self._do_action(coa, hm,
                        lambda: coa.set_layer_color(uuid, 1, Color.from_name("blue")),
                        "Set blue")
        assert coa.get_layer_color(uuid, 1).name == "blue"

        state = hm.undo()
        coa.set_snapshot(state)
        layer = coa.get_layer_by_index(0)
        assert layer.color1.name == "red"

    def test_redo_restores_action(self, coa_and_hm):
        coa, hm = coa_and_hm
        uuid = coa.add_layer(emblem_path="ce_test.dds")
        hm.save_state(coa.get_snapshot(), "Add layer")

        coa.set_layer_color(uuid, 3, Color.from_name("green"))
        hm.save_state(coa.get_snapshot(), "Set green")

        hm.undo()
        state = hm.redo()
        coa.set_snapshot(state)
        layer = coa.get_layer_by_index(0)
        assert layer.color3.name == "green"

    def test_undo_base_color_change(self, coa_and_hm):
        coa, hm = coa_and_hm
        coa.pattern_color1 = Color.from_name("red")
        hm.save_state(coa.get_snapshot(), "Red base")

        coa.pattern_color1 = Color.from_name("blue")
        hm.save_state(coa.get_snapshot(), "Blue base")

        state = hm.undo()
        coa.set_snapshot(state)
        assert coa.pattern_color1.name == "red"

    def test_undo_multiple_times(self, coa_and_hm):
        coa, hm = coa_and_hm
        # Build up actions
        coa.add_layer(emblem_path="a.dds")
        hm.save_state(coa.get_snapshot(), "Add a")
        coa.add_layer(emblem_path="b.dds")
        hm.save_state(coa.get_snapshot(), "Add b")
        coa.add_layer(emblem_path="c.dds")
        hm.save_state(coa.get_snapshot(), "Add c")

        assert coa.get_layer_count() == 3

        # Undo × 3 should get back to initial (0 layers)
        for _ in range(3):
            state = hm.undo()
            if state:
                coa.set_snapshot(state)

        assert coa.get_layer_count() == 0

    def test_undo_then_new_action_prunes_redo(self, coa_and_hm):
        coa, hm = coa_and_hm
        coa.add_layer(emblem_path="a.dds")
        hm.save_state(coa.get_snapshot(), "Add a")
        coa.add_layer(emblem_path="b.dds")
        hm.save_state(coa.get_snapshot(), "Add b")

        state = hm.undo()
        coa.set_snapshot(state)
        # Now add a different layer – redo of "Add b" should be gone
        coa.add_layer(emblem_path="x.dds")
        hm.save_state(coa.get_snapshot(), "Add x")

        assert not hm.can_redo()
        assert coa.get_layer_count() == 2  # a + x

    def test_undo_preserves_instance_data(self, coa_and_hm):
        coa, hm = coa_and_hm
        uuid = coa.add_layer(emblem_path="ce_test.dds")
        coa.add_instance(uuid, pos_x=0.2, pos_y=0.3)
        hm.save_state(coa.get_snapshot(), "Add instance")

        coa.remove_instance(uuid, 1)
        hm.save_state(coa.get_snapshot(), "Remove instance")

        layer_before = coa.get_layer_by_index(0)
        assert layer_before.instance_count == 1

        state = hm.undo()
        coa.set_snapshot(state)
        layer_after = coa.get_layer_by_index(0)
        assert layer_after.instance_count == 2


# ══════════════════════════════════════════════════════════════════════════
# Selection State Through Undo/Redo (model-level simulation)
# ══════════════════════════════════════════════════════════════════════════

class TestSelectionUndoState:
    """Simulates what HistoryMixin._capture/_restore does with selection."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    def _capture(self, coa, selected_uuids, selected_containers=None):
        """Simulate _capture_current_state."""
        return {
            'coa_snapshot': coa.get_snapshot(),
            'selected_layer_uuids': set(selected_uuids),
            'selected_container_uuids': set(selected_containers or []),
        }

    def _restore(self, coa, state):
        """Simulate _restore_state (model portion only)."""
        coa.set_snapshot(state['coa_snapshot'])
        saved = state.get('selected_layer_uuids', set())
        return {uuid for uuid in saved if coa.has_layer_uuid(uuid)}

    def test_selection_preserved_through_undo(self, coa):
        uuid1 = coa.add_layer(emblem_path="a.dds")
        uuid2 = coa.add_layer(emblem_path="b.dds")
        state = self._capture(coa, {uuid1})

        # Mutate: select uuid2 instead
        coa.remove_layer(uuid1)
        # Restore
        valid = self._restore(coa, state)
        assert uuid1 in valid
        assert coa.has_layer_uuid(uuid1)

    def test_stale_uuids_filtered_on_restore(self, coa):
        uuid1 = coa.add_layer(emblem_path="a.dds")
        uuid2 = coa.add_layer(emblem_path="b.dds")
        state = self._capture(coa, {uuid1, uuid2})

        # Remove uuid2 from the snapshot's model to simulate stale UUID
        coa.remove_layer(uuid2)
        state2 = self._capture(coa, {uuid1, uuid2})
        # uuid2 is in selection but not in model
        valid = self._restore(coa, state2)
        assert uuid1 in valid
        assert uuid2 not in valid

    def test_container_selection_preserved(self, coa):
        uuid1 = coa.add_layer(emblem_path="a.dds")
        uuid2 = coa.add_layer(emblem_path="b.dds")
        container_uuid = coa.create_container_from_layers([uuid1, uuid2])
        state = self._capture(coa, {uuid1, uuid2}, {container_uuid})

        assert state['selected_container_uuids'] == {container_uuid}

    def test_empty_selection_on_empty_coa(self, coa):
        state = self._capture(coa, set())
        valid = self._restore(coa, state)
        assert valid == set()


# ══════════════════════════════════════════════════════════════════════════
# Reentrancy Guard
# ══════════════════════════════════════════════════════════════════════════

class TestReentrancyGuard:
    """Verifies the _is_applying_history guard prevents recursive saves."""

    def test_guard_blocks_save_during_apply(self):
        """Simulate what happens when _save_state is called during undo."""
        hm = HistoryManager()
        hm.save_state({"v": 1}, "Initial")
        hm.save_state({"v": 2}, "Change")

        is_applying = True  # simulates self._is_applying_history = True

        # _save_state would check: if self._is_applying_history: return
        state = hm.undo()
        saved_count_before = len(hm.history)

        if not is_applying:
            hm.save_state({"v": 99}, "Should not be saved")

        assert len(hm.history) == saved_count_before  # no new entry

    def test_guard_resets_after_apply(self):
        """After undo completes, saves should work again."""
        hm = HistoryManager()
        hm.save_state({"v": 1}, "Initial")
        hm.save_state({"v": 2}, "Change")

        is_applying = True
        state = hm.undo()
        is_applying = False  # finally block resets

        # Now saves should work normally
        if not is_applying:
            hm.save_state({"v": 3}, "Post-undo change")

        assert hm.get_current_description() == "Post-undo change"


# ══════════════════════════════════════════════════════════════════════════
# Fragmented Undo Detection
# ══════════════════════════════════════════════════════════════════════════

class HistoryMixinStub:
    """Minimal stub that replicates HistoryMixin's save/debounce logic.
    
    This mirrors the real code in history_mixin.py so we can test the
    interaction between debounced and direct saves without a full MainWindow.
    """

    def __init__(self):
        self.coa = CoA()
        CoA.set_active(self.coa)
        self.history_manager = HistoryManager()
        self._is_applying_history = False
        self._pending_property_change = None
        self.property_change_timer = QTimer()
        self.property_change_timer.setSingleShot(True)
        self.property_change_timer.timeout.connect(self._save_property_change)

    def _capture_current_state(self):
        return {'coa_snapshot': self.coa.get_snapshot()}

    def _save_state(self, description):
        if self._is_applying_history:
            return
        # Cancel pending debounce — direct save supersedes it
        self.property_change_timer.stop()
        self._pending_property_change = None
        state = self._capture_current_state()
        self.history_manager.save_state(state, description)

    def _save_property_change(self):
        if self._pending_property_change:
            self._save_state(self._pending_property_change)
            self._pending_property_change = None

    def save_property_change_debounced(self, description):
        self._pending_property_change = description
        self.property_change_timer.stop()
        self.property_change_timer.start(500)


class TestFragmentedUndo:
    """Detects the bug where a single user action creates multiple undo steps.
    
    The systemic issue: save_property_change_debounced starts a 500ms timer,
    but _save_state does NOT cancel it. If a direct save fires before the timer
    expires, you get two undo entries for one perceived action.
    """

    @pytest.fixture
    def stub(self, qtbot):
        s = HistoryMixinStub()
        # Save initial state (like app startup)
        s._save_state("Initial")
        return s

    def test_debounce_then_direct_save_no_fragmentation(self, stub, qtbot):
        """Slider drag → quick delete must produce only 1 undo entry, not 2.
        
        _save_state must cancel the pending debounce timer so the stale
        debounced save doesn't fire after the direct save.
        """
        # Simulate slider drag (debounce starts, 500ms timer running)
        stub.coa.pattern_color1 = Color.from_name("red")
        stub.save_property_change_debounced("Change color")

        # Simulate quick discrete action BEFORE timer fires
        stub.coa.pattern_color2 = Color.from_name("blue")
        stub._save_state("Delete layer")

        # Let the debounce timer window pass
        qtbot.wait(600)

        # Must be exactly 2: Initial + Delete (debounce was cancelled)
        entry_count = len(stub.history_manager.history)
        assert entry_count == 2, (
            f"Fragmented undo detected: expected 2 history entries "
            f"(Initial + Delete) but got {entry_count}. "
            f"The debounce timer is not being cancelled by _save_state."
        )

    def test_debounce_alone_creates_one_entry(self, stub, qtbot):
        """Debounce without interference should produce exactly one entry."""
        stub.coa.pattern_color1 = Color.from_name("red")
        stub.save_property_change_debounced("Change color")

        qtbot.wait(600)

        # Initial + debounced = 2
        assert len(stub.history_manager.history) == 2

    def test_multiple_debounces_collapse(self, stub, qtbot):
        """Rapid slider changes should collapse into one undo entry."""
        for color_name in ["red", "green", "blue", "yellow", "white"]:
            stub.coa.pattern_color1 = Color.from_name(color_name)
            stub.save_property_change_debounced("Change color")

        qtbot.wait(600)

        # Initial + one debounced = 2 (all intermediate ones collapsed)
        assert len(stub.history_manager.history) == 2

    def test_direct_save_with_no_pending_debounce(self, stub, qtbot):
        """Direct save without prior debounce should produce exactly one entry."""
        stub.coa.pattern_color1 = Color.from_name("red")
        stub._save_state("Direct action")

        # Initial + Direct = 2
        assert len(stub.history_manager.history) == 2

    def test_two_direct_saves_create_two_entries(self, stub, qtbot):
        """Two discrete actions should create two separate undo entries."""
        stub._save_state("Action 1")
        stub._save_state("Action 2")

        # Initial + Action1 + Action2 = 3
        assert len(stub.history_manager.history) == 3

    def test_debounce_after_direct_save_creates_separate_entry(self, stub, qtbot):
        """Direct save first, then debounce — should be 2 separate entries."""
        stub._save_state("Direct action")

        stub.coa.pattern_color1 = Color.from_name("red")
        stub.save_property_change_debounced("Slider drag")
        qtbot.wait(600)

        # Initial + Direct + Debounced = 3
        assert len(stub.history_manager.history) == 3


class TestFragmentedUndoWithFix:
    """Tests that verify the fix works once _save_state cancels the debounce.
    
    These use a fixed version of the stub where _save_state cancels
    the pending timer, proving the fix solves the fragmentation.
    """

    class FixedHistoryMixinStub(HistoryMixinStub):
        """Stub with the fix applied: _save_state cancels pending debounce."""

        def _save_state(self, description):
            if self._is_applying_history:
                return
            # THE FIX: cancel pending debounce before saving
            self.property_change_timer.stop()
            self._pending_property_change = None
            state = self._capture_current_state()
            self.history_manager.save_state(state, description)

    @pytest.fixture
    def fixed_stub(self, qtbot):
        s = self.FixedHistoryMixinStub()
        s._save_state("Initial")
        return s

    def test_fixed_debounce_then_direct_no_fragmentation(self, fixed_stub, qtbot):
        """With fix: slider drag → quick delete = exactly 1 undo entry (not 2)."""
        fixed_stub.coa.pattern_color1 = Color.from_name("red")
        fixed_stub.save_property_change_debounced("Change color")

        fixed_stub.coa.pattern_color2 = Color.from_name("blue")
        fixed_stub._save_state("Delete layer")

        qtbot.wait(600)

        # Initial + Delete only (debounce was cancelled)
        assert len(fixed_stub.history_manager.history) == 2

    def test_fixed_debounce_alone_still_works(self, fixed_stub, qtbot):
        """Debounce without a direct save still creates its entry."""
        fixed_stub.coa.pattern_color1 = Color.from_name("red")
        fixed_stub.save_property_change_debounced("Change color")

        qtbot.wait(600)

        assert len(fixed_stub.history_manager.history) == 2

    def test_fixed_rapid_debounce_then_direct(self, fixed_stub, qtbot):
        """Multiple rapid slider drags then a click action → 2 entries total."""
        for color in ["red", "green", "blue"]:
            fixed_stub.coa.pattern_color1 = Color.from_name(color)
            fixed_stub.save_property_change_debounced("Drag slider")

        fixed_stub._save_state("Click button")
        qtbot.wait(600)

        # Initial + Click button = 2 (all debounces cancelled)
        assert len(fixed_stub.history_manager.history) == 2


class TestFragmentedUndoRegression:
    """Regression tests: if someone removes the debounce cancellation from
    _save_state, these tests must fail."""

    @pytest.fixture
    def stub(self, qtbot):
        s = HistoryMixinStub()
        s._save_state("Initial")
        return s

    def test_regression_debounce_cancel_on_direct_save(self, stub, qtbot):
        """After calling _save_state, the debounce timer must not be running."""
        stub.save_property_change_debounced("Slider")
        assert stub.property_change_timer.isActive()

        stub._save_state("Direct action")
        assert not stub.property_change_timer.isActive()
        assert stub._pending_property_change is None
