"""
Tests for container/grouping, merge/split, and layer ordering.

Covers:
- Container creation from layers
- Container UUID assignment and membership queries
- Ungrouping (setting container_uuid = None)
- Contiguity validation and repair
- Container duplication
- Merge layers (into first, validated merge)
- Split layer (multi-instance → individual layers)
- Layer ordering: move above/below, top/bottom, shift up/down
- Layer order before and after grouping/ungrouping
"""
import pytest

from models.coa import CoA
from models.color import Color
from models.transform import Vec2


# ══════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════

def _uuids_in_order(coa):
    """Return list of layer UUIDs bottom→top."""
    return coa.get_all_layer_uuids()


def _add_n_layers(coa, n, prefix="ce_layer"):
    """Add n layers, return list of UUIDs in insertion order."""
    return [coa.add_layer(emblem_path=f"{prefix}_{i}.dds") for i in range(n)]


# ══════════════════════════════════════════════════════════════════════════
# Container Creation
# ══════════════════════════════════════════════════════════════════════════

class TestContainerCreation:
    """Tests for create_container_from_layers and related methods."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    def test_create_container_assigns_uuid(self, coa):
        uuids = _add_n_layers(coa, 3)
        container = coa.create_container_from_layers(uuids[:2], name="Group")
        assert container is not None
        assert container.startswith("container_")
        assert "Group" in container

    def test_grouped_layers_share_container_uuid(self, coa):
        uuids = _add_n_layers(coa, 3)
        container = coa.create_container_from_layers(uuids[:2])
        assert coa.get_layer_container(uuids[0]) == container
        assert coa.get_layer_container(uuids[1]) == container

    def test_ungrouped_layer_has_none_container(self, coa):
        uuids = _add_n_layers(coa, 3)
        coa.create_container_from_layers(uuids[:2])
        assert coa.get_layer_container(uuids[2]) is None

    def test_get_layers_by_container(self, coa):
        uuids = _add_n_layers(coa, 4)
        container = coa.create_container_from_layers([uuids[0], uuids[2]])
        members = coa.get_layers_by_container(container)
        assert set(members) == {uuids[0], uuids[2]}

    def test_get_all_containers(self, coa):
        uuids = _add_n_layers(coa, 5)
        c1 = coa.create_container_from_layers(uuids[:2], name="A")
        c2 = coa.create_container_from_layers(uuids[2:4], name="B")
        all_containers = coa.get_all_containers()
        assert c1 in all_containers
        assert c2 in all_containers

    def test_create_empty_returns_none(self, coa):
        result = coa.create_container_from_layers([])
        assert result is None

    def test_generate_container_uuid_format(self, coa):
        uuid = coa.generate_container_uuid("TestName")
        parts = uuid.split("_", 2)
        assert parts[0] == "container"
        assert parts[2] == "TestName"


# ══════════════════════════════════════════════════════════════════════════
# Ungrouping
# ══════════════════════════════════════════════════════════════════════════

class TestUngrouping:
    """Tests for removing layers from containers."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    def test_set_container_none_removes_layer(self, coa):
        uuids = _add_n_layers(coa, 2)
        container = coa.create_container_from_layers(uuids)
        # Ungroup: set each layer's container to None
        for u in uuids:
            coa.set_layer_container(u, None)
        assert coa.get_layer_container(uuids[0]) is None
        assert coa.get_layer_container(uuids[1]) is None
        assert coa.get_all_containers() == []

    def test_partial_ungroup(self, coa):
        uuids = _add_n_layers(coa, 3)
        container = coa.create_container_from_layers(uuids)
        # Ungroup only the first layer
        coa.set_layer_container(uuids[0], None)
        members = coa.get_layers_by_container(container)
        assert uuids[0] not in members
        assert len(members) == 2

    def test_ungroup_preserves_layer_count(self, coa):
        uuids = _add_n_layers(coa, 3)
        coa.create_container_from_layers(uuids)
        for u in uuids:
            coa.set_layer_container(u, None)
        assert coa.get_layer_count() == 3


# ══════════════════════════════════════════════════════════════════════════
# Layer Order Invariants with Grouping
# ══════════════════════════════════════════════════════════════════════════

class TestLayerOrderWithGrouping:
    """Verifies layer order before and after grouping/ungrouping."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    def test_grouping_makes_layers_contiguous(self, coa):
        """Non-adjacent layers should be moved adjacent when grouped."""
        uuids = _add_n_layers(coa, 4)  # [0, 1, 2, 3]
        # Group layers 0 and 3 (non-adjacent)
        container = coa.create_container_from_layers([uuids[0], uuids[3]])
        # After grouping, both should be adjacent
        all_order = _uuids_in_order(coa)
        i0 = all_order.index(uuids[0])
        i3 = all_order.index(uuids[3])
        assert abs(i0 - i3) == 1

    def test_grouping_preserves_relative_order(self, coa):
        """Grouped layers must be contiguous AND preserve their original relative order."""
        uuids = _add_n_layers(coa, 5)
        # Group 1, 3 (non-adjacent; 1 is before 3 originally)
        container = coa.create_container_from_layers([uuids[1], uuids[3]])
        all_order = _uuids_in_order(coa)
        i1 = all_order.index(uuids[1])
        i3 = all_order.index(uuids[3])
        assert abs(i1 - i3) == 1, "Grouped layers must be contiguous"
        assert i1 < i3, "Original relative order must be preserved (layer 1 before layer 3)"

    def test_ungroup_does_not_change_order(self, coa):
        """Ungrouping layers should not move them — just clear container_uuid."""
        uuids = _add_n_layers(coa, 3)
        container = coa.create_container_from_layers(uuids)
        order_before = _uuids_in_order(coa)
        for u in uuids:
            coa.set_layer_container(u, None)
        order_after = _uuids_in_order(coa)
        assert order_before == order_after

    def test_total_layer_count_stable_through_group_ungroup(self, coa):
        uuids = _add_n_layers(coa, 4)
        assert coa.get_layer_count() == 4
        container = coa.create_container_from_layers(uuids[:3])
        assert coa.get_layer_count() == 4
        for u in uuids[:3]:
            coa.set_layer_container(u, None)
        assert coa.get_layer_count() == 4


# ══════════════════════════════════════════════════════════════════════════
# Container Contiguity Validation
# ══════════════════════════════════════════════════════════════════════════

class TestContainerContiguity:
    """Tests validate_container_contiguity which repairs fragmentation."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    def test_contiguous_container_no_splits(self, coa):
        uuids = _add_n_layers(coa, 3)
        container = coa.create_container_from_layers(uuids)
        splits = coa.validate_container_contiguity()
        assert splits == []

    def test_fragmented_container_gets_split(self, coa):
        """Manually break contiguity, validate should repair."""
        uuids = _add_n_layers(coa, 4)
        container = coa.generate_container_uuid("Test")
        # Assign 0, 2 to same container (skipping 1) → fragmented
        coa.set_layer_container(uuids[0], container)
        coa.set_layer_container(uuids[2], container)
        splits = coa.validate_container_contiguity()
        assert len(splits) == 1
        assert splits[0]["old_container"] == container
        assert splits[0]["layer_count"] == 1

    def test_after_split_no_fragmentation(self, coa):
        uuids = _add_n_layers(coa, 4)
        container = coa.generate_container_uuid("Test")
        coa.set_layer_container(uuids[0], container)
        coa.set_layer_container(uuids[2], container)
        coa.validate_container_contiguity()
        # Second run should find no fragmentation
        splits = coa.validate_container_contiguity()
        assert splits == []


# ══════════════════════════════════════════════════════════════════════════
# Container Duplication
# ══════════════════════════════════════════════════════════════════════════

class TestContainerDuplication:
    """Tests duplicate_container."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    def test_duplicate_creates_new_container(self, coa):
        uuids = _add_n_layers(coa, 2)
        container = coa.create_container_from_layers(uuids)
        new_container = coa.duplicate_container(container)
        assert new_container != container
        assert new_container.startswith("container_")

    def test_duplicate_copies_all_layers(self, coa):
        uuids = _add_n_layers(coa, 2)
        container = coa.create_container_from_layers(uuids)
        count_before = coa.get_layer_count()
        new_container = coa.duplicate_container(container)
        count_after = coa.get_layer_count()
        assert count_after == count_before + 2

    def test_duplicate_layers_are_in_new_container(self, coa):
        uuids = _add_n_layers(coa, 2)
        container = coa.create_container_from_layers(uuids)
        new_container = coa.duplicate_container(container)
        new_members = coa.get_layers_by_container(new_container)
        assert len(new_members) == 2
        # Original layers are still in original container
        old_members = coa.get_layers_by_container(container)
        assert len(old_members) == 2


# ══════════════════════════════════════════════════════════════════════════
# Merge Layers
# ══════════════════════════════════════════════════════════════════════════

class TestMergeLayers:
    """Tests merge_layers and merge_layers_into_first."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    def test_merge_reduces_layer_count(self, coa):
        u1 = coa.add_layer(emblem_path="ce_a.dds")
        u2 = coa.add_layer(emblem_path="ce_a.dds")
        u3 = coa.add_layer(emblem_path="ce_a.dds")
        coa.merge_layers_into_first([u1, u2, u3])
        assert coa.get_layer_count() == 1

    def test_merge_keeps_first_uuid(self, coa):
        u1 = coa.add_layer(emblem_path="ce_a.dds")
        u2 = coa.add_layer(emblem_path="ce_a.dds")
        result = coa.merge_layers_into_first([u1, u2])
        assert result == u1
        assert coa.has_layer_uuid(u1)
        assert not coa.has_layer_uuid(u2)

    def test_merge_combines_instances(self, coa):
        u1 = coa.add_layer(emblem_path="ce_a.dds")
        u2 = coa.add_layer(emblem_path="ce_a.dds")
        coa.add_instance(u2, pos_x=0.3, pos_y=0.4)
        # u1 has 1 instance, u2 has 2
        merged = coa.merge_layers_into_first([u1, u2])
        layer = coa.get_layer_by_index(0)
        assert layer.instance_count == 3

    def test_merge_with_one_uuid_raises(self, coa):
        u1 = coa.add_layer(emblem_path="ce_a.dds")
        with pytest.raises(ValueError, match="at least 2"):
            coa.merge_layers_into_first([u1])

    def test_merge_empty_raises(self, coa):
        with pytest.raises(ValueError, match="empty"):
            coa.merge_layers_into_first([])

    def test_merge_invalid_uuid_raises(self, coa):
        u1 = coa.add_layer(emblem_path="ce_a.dds")
        with pytest.raises(ValueError, match="not found"):
            coa.merge_layers_into_first([u1, "bogus-uuid"])


class TestValidatedMerge:
    """Tests merge_layers (with review_merge validation) and review_merge."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    def test_review_merge_valid(self, coa):
        u1 = coa.add_layer(emblem_path="ce_a.dds")
        u2 = coa.add_layer(emblem_path="ce_a.dds")
        review = coa.review_merge([u1, u2])
        assert review['valid'] is True
        assert review['info']['total_instances'] == 2

    def test_review_merge_texture_mismatch_warns(self, coa):
        u1 = coa.add_layer(emblem_path="ce_a.dds")
        u2 = coa.add_layer(emblem_path="ce_b.dds")
        review = coa.review_merge([u1, u2])
        assert review['valid'] is True  # still valid, just warning
        assert any("texture" in w.lower() for w in review['warnings'])

    def test_review_merge_too_few_layers(self, coa):
        u1 = coa.add_layer(emblem_path="ce_a.dds")
        review = coa.review_merge([u1])
        assert review['valid'] is False

    def test_merge_layers_validated(self, coa):
        u1 = coa.add_layer(emblem_path="ce_a.dds")
        u2 = coa.add_layer(emblem_path="ce_a.dds")
        result = coa.merge_layers([u1, u2])
        assert result == u1
        assert coa.get_layer_count() == 1


# ══════════════════════════════════════════════════════════════════════════
# Split Layer
# ══════════════════════════════════════════════════════════════════════════

class TestSplitLayer:
    """Tests split_layer which breaks multi-instance layers apart."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    def test_split_creates_n_layers(self, coa):
        uuid = coa.add_layer(emblem_path="ce_a.dds")
        coa.add_instance(uuid, pos_x=0.2, pos_y=0.3)
        coa.add_instance(uuid, pos_x=0.5, pos_y=0.6)
        # Now has 3 instances
        new_uuids = coa.split_layer(uuid)
        assert len(new_uuids) == 3
        assert coa.get_layer_count() == 3

    def test_split_removes_original(self, coa):
        uuid = coa.add_layer(emblem_path="ce_a.dds")
        coa.add_instance(uuid, pos_x=0.2, pos_y=0.3)
        new_uuids = coa.split_layer(uuid)
        assert not coa.has_layer_uuid(uuid)
        for u in new_uuids:
            assert coa.has_layer_uuid(u)

    def test_split_each_has_one_instance(self, coa):
        uuid = coa.add_layer(emblem_path="ce_a.dds")
        coa.add_instance(uuid, pos_x=0.2, pos_y=0.3)
        new_uuids = coa.split_layer(uuid)
        for u in new_uuids:
            idx = coa.get_all_layer_uuids().index(u)
            layer = coa.get_layer_by_index(idx)
            assert layer.instance_count == 1

    def test_split_single_instance_raises(self, coa):
        uuid = coa.add_layer(emblem_path="ce_a.dds")
        with pytest.raises(ValueError, match="only 1"):
            coa.split_layer(uuid)

    def test_merge_then_split_round_trip(self, coa):
        """Merge 3 layers → 1, then split → should get 3 back."""
        u1 = coa.add_layer(emblem_path="ce_a.dds")
        u2 = coa.add_layer(emblem_path="ce_a.dds")
        u3 = coa.add_layer(emblem_path="ce_a.dds")
        merged = coa.merge_layers_into_first([u1, u2, u3])
        assert coa.get_layer_count() == 1
        new_uuids = coa.split_layer(merged)
        assert coa.get_layer_count() == 3


# ══════════════════════════════════════════════════════════════════════════
# Layer Ordering
# ══════════════════════════════════════════════════════════════════════════

class TestLayerOrdering:
    """Tests move_layer_above/below, move_to_top/bottom, shift_up/down."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    @pytest.fixture
    def four_layers(self, coa):
        uuids = _add_n_layers(coa, 4)  # bottom → top: [0, 1, 2, 3]
        return uuids

    def test_initial_order_is_insertion_order(self, coa, four_layers):
        assert _uuids_in_order(coa) == four_layers

    # ── move_to_top / move_to_bottom ────────────────────────────────

    def test_move_to_top(self, coa, four_layers):
        u = four_layers[0]
        coa.move_layer_to_top(u)
        assert _uuids_in_order(coa)[-1] == u

    def test_move_to_bottom(self, coa, four_layers):
        u = four_layers[-1]
        coa.move_layer_to_bottom(u)
        assert _uuids_in_order(coa)[0] == u

    def test_move_to_top_already_at_top(self, coa, four_layers):
        """Moving top layer to top should be a no-op."""
        order_before = _uuids_in_order(coa)
        coa.move_layer_to_top(four_layers[-1])
        assert _uuids_in_order(coa) == order_before

    # ── move_layer_above / move_layer_below ─────────────────────────

    def test_move_above(self, coa, four_layers):
        # Move layer 3 above layer 0 (to behind it in render order)
        coa.move_layer_above(four_layers[3], four_layers[0])
        order = _uuids_in_order(coa)
        assert order.index(four_layers[3]) < order.index(four_layers[0])

    def test_move_below(self, coa, four_layers):
        # Move layer 0 below layer 3 (in front of it in render order)
        coa.move_layer_below(four_layers[0], four_layers[3])
        order = _uuids_in_order(coa)
        assert order.index(four_layers[0]) > order.index(four_layers[3])

    # ── shift_up / shift_down ───────────────────────────────────────

    def test_shift_up(self, coa, four_layers):
        success = coa.shift_layer_up(four_layers[0])
        assert success
        order = _uuids_in_order(coa)
        assert order[1] == four_layers[0]

    def test_shift_down(self, coa, four_layers):
        success = coa.shift_layer_down(four_layers[3])
        assert success
        order = _uuids_in_order(coa)
        assert order[2] == four_layers[3]

    def test_shift_up_at_top_returns_false(self, coa, four_layers):
        success = coa.shift_layer_up(four_layers[3])
        assert not success

    def test_shift_down_at_bottom_returns_false(self, coa, four_layers):
        success = coa.shift_layer_down(four_layers[0])
        assert not success

    # ── multi-layer moves ───────────────────────────────────────────

    def test_move_multiple_to_top(self, coa, four_layers):
        coa.move_layer_to_top([four_layers[0], four_layers[1]])
        order = _uuids_in_order(coa)
        assert order[-2:] == [four_layers[0], four_layers[1]]

    def test_move_multiple_to_bottom(self, coa, four_layers):
        coa.move_layer_to_bottom([four_layers[2], four_layers[3]])
        order = _uuids_in_order(coa)
        assert order[:2] == [four_layers[2], four_layers[3]]

    def test_shift_group_up(self, coa, four_layers):
        # Shift [0,1] up together
        success = coa.shift_layer_up([four_layers[0], four_layers[1]])
        assert success
        order = _uuids_in_order(coa)
        # They should now be at indices 1,2
        assert order[1] == four_layers[0]
        assert order[2] == four_layers[1]


# ══════════════════════════════════════════════════════════════════════════
# Grouping + Ordering Integration
# ══════════════════════════════════════════════════════════════════════════

class TestGroupingOrderIntegration:
    """Tests that grouping, ungrouping, and ordering interact correctly."""

    @pytest.fixture
    def coa(self):
        coa = CoA()
        CoA.set_active(coa)
        return coa

    def test_group_then_move_top(self, coa):
        uuids = _add_n_layers(coa, 4)
        container = coa.create_container_from_layers(uuids[:2])
        # Move the group to top
        members = coa.get_layers_by_container(container)
        coa.move_layer_to_top(members)
        order = _uuids_in_order(coa)
        # Both members should be at the end
        for m in members:
            assert m in order[-2:]

    def test_group_ungroup_order_snapshot_undo(self, coa):
        """Group → snapshot → ungroup → restore → verify still grouped."""
        uuids = _add_n_layers(coa, 3)
        container = coa.create_container_from_layers(uuids[:2])
        snap = coa.get_snapshot()

        # Ungroup
        for u in uuids[:2]:
            coa.set_layer_container(u, None)
        assert coa.get_all_containers() == []

        # Undo via snapshot restore
        coa.set_snapshot(snap)
        assert len(coa.get_all_containers()) == 1
        members = coa.get_layers_by_container(container)
        assert len(members) == 2

    def test_duplicate_container_then_reorder(self, coa):
        uuids = _add_n_layers(coa, 2)
        container = coa.create_container_from_layers(uuids)
        new_container = coa.duplicate_container(container)
        new_members = coa.get_layers_by_container(new_container)
        # Move duplicate group to bottom
        coa.move_layer_to_bottom(new_members)
        order = _uuids_in_order(coa)
        for m in new_members:
            assert order.index(m) < 2  # first two positions
