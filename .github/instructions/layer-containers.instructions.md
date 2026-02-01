---
applyTo: '**'
---

# Layer Containers Implementation Philosophy

**Full planning document:** [docs/layer_containers_plan.txt](../../docs/layer_containers_plan.txt)

AVOID BLOAT TO EXISTING STRUCTURES WHENEVER POSSIBLE.
group features into seperate py files if needed.
BUT THE PLAN COMES FIRST.

## Identity vs Organization
**A layer's UUID is its soul. A container_uuid is just its address.**
- Layer UUID never changes (stable identity)
- Container UUID can change freely (mutable grouping property)
- Don't confuse identity with organization

## Simplicity Wins
**Plain UUID4 beats clever schemes.**
- Layers: plain UUID4, separate name property
- Containers: `container_{uuid}_{name}` string format
- No uuid_generator module, no regeneration on rename

## UUID Regeneration is Rare
**New UUIDs only for new things.**
- Generate new UUID: duplicate, paste operations only
- Rename changes name property, not UUID
- Layer UUID is write-once, read-forever

## Containers Don't Exist
**Containers are queries, not objects.**
- No container arrays, lists, or collections in CoA
- Container = layers sharing same container_uuid property
- UI builds tree by grouping layers, not traversing structures

## Validation Lives Inside Actions
**Snapshots before, validation during, never after.**
- Snapshot captures pre-action state
- Action executes AND validates in one step
- Non-contiguous containers after action = bug

## Selection is Multi-Selection
**Container selection = selecting all its layers. Same action.**
- No special "container selected" state
- Just add all layer UUIDs to selection set
- Operations work on layer UUIDs, always

## Copy Behavior Depends on Intent
**What you select determines what you copy.**
- Select container marker → preserve container_uuid
- Select individual layers → strip container_uuid
- Intent matters, not layer count

## Phase 1 is Sacred
**Stop after Phase 1. Test. Then proceed.**
- Phase 1: name property + visibility API only
- NO UUID format changes in Phase 1
- Phases 2-7 are continuous (planning markers)
