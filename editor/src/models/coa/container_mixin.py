"""
Container Management Mixin for CoA Model

Provides methods for managing layer containers (groups/folders).
Containers are identified by UUID strings and allow hierarchical organization of layers.
"""

import logging
from typing import List, Dict, Optional
from copy import deepcopy


class CoAContainerMixin:
    """Mixin providing container management functionality for CoA model"""
    
    def get_layer_container(self, uuid: str) -> Optional[str]:
        """Get layer's container UUID
        
        Args:
            uuid: Layer UUID
            
        Returns:
            Container UUID string if layer is in a container, None if at root level
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        return layer.container_uuid
    
    def set_layer_container(self, uuid: str, container_uuid: Optional[str]):
        """Set layer's container UUID
        
        Args:
            uuid: Layer UUID
            container_uuid: Container UUID string, or None for root level
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        layer.container_uuid = container_uuid
        self._logger.debug(f"Set layer {uuid} container_uuid: {container_uuid}")
    
    def get_layers_by_container(self, container_uuid: Optional[str]) -> List[str]:
        """Get all layer UUIDs that belong to a specific container
        
        Args:
            container_uuid: Container UUID to search for, or None for root-level layers
            
        Returns:
            List of layer UUIDs that have the matching container_uuid
        """
        matching_uuids = []
        for layer in self._layers:
            if layer.container_uuid == container_uuid:
                matching_uuids.append(layer.uuid)
        return matching_uuids
    
    def get_all_containers(self) -> List[str]:
        """Get list of all unique container UUIDs currently in use
        
        Returns:
            List of unique container UUID strings (excludes None/root layers)
        """
        containers = set()
        for layer in self._layers:
            if layer.container_uuid is not None:
                containers.add(layer.container_uuid)
        return sorted(list(containers))
    
    def generate_container_uuid(self, name: str) -> str:
        """Generate a new container UUID with given name
        
        Args:
            name: Display name for the container
            
        Returns:
            Container UUID string in format "container_{uuid}_{name}"
        """
        import uuid
        return f"container_{uuid.uuid4()}_{name}"
    
    def regenerate_container_uuid(self, old_container_uuid: str) -> str:
        """Regenerate container UUID (new UUID portion, keep name)
        
        Args:
            old_container_uuid: Original container UUID
            
        Returns:
            New container UUID with same name but new UUID portion
        """
        # Parse old UUID to extract name
        parts = old_container_uuid.split('_', 2)
        if len(parts) >= 3:
            name = parts[2]
            return self.generate_container_uuid(name)
        else:
            # Fallback if parsing fails
            return self.generate_container_uuid("Container")
    
    def duplicate_container(self, container_uuid: str) -> str:
        """Duplicate an entire container with all its layers
        
        Args:
            container_uuid: Container UUID to duplicate
            
        Returns:
            New container UUID
        """
        import uuid as uuid_module
        
        # Get all layers in the container
        layer_uuids = self.get_layers_by_container(container_uuid)
        if not layer_uuids:
            self._logger.warning(f"Container {container_uuid} has no layers")
            return container_uuid
        
        # Generate new container UUID (same name, new UUID portion)
        new_container_uuid = self.regenerate_container_uuid(container_uuid)
        
        # Duplicate each layer and assign to new container
        for old_uuid in layer_uuids:
            # Duplicate the layer
            new_uuid = self.duplicate_layer(old_uuid)
            # Assign to new container
            self.set_layer_container(new_uuid, new_container_uuid)
        
        self._logger.info(f"Duplicated container {container_uuid} -> {new_container_uuid} with {len(layer_uuids)} layers")
        return new_container_uuid
    
    def create_container_from_layers(self, layer_uuids: List[str], name: str = "Container") -> str:
        """Create a new container from selected layers and regroup them
        
        Args:
            layer_uuids: List of layer UUIDs to group
            name: Name for the new container
            
        Returns:
            New container UUID
        """
        if not layer_uuids:
            self._logger.warning("Cannot create container from empty layer list")
            return None
        
        # Generate new container UUID
        new_container_uuid = self.generate_container_uuid(name)
        
        # Find the layer with highest position (earliest in z-order, lowest index)
        all_uuids = self.get_all_layer_uuids()
        highest_idx = len(all_uuids)  # Start with lowest priority
        target_uuid = None
        
        for uuid in layer_uuids:
            idx = all_uuids.index(uuid) if uuid in all_uuids else None
            if idx is not None and idx < highest_idx:
                highest_idx = idx
                target_uuid = uuid
        
        if target_uuid is None:
            self._logger.warning("No valid layers found for container creation")
            return None
        
        # Sort layers by current position to maintain relative order
        layer_positions = [(all_uuids.index(uuid), uuid) for uuid in layer_uuids if uuid in all_uuids]
        layer_positions.sort()  # Sort by index
        
        # Move all other layers to be right after the target (maintaining relative order)
        # Skip the first one (it's already at the target position)
        for i in range(1, len(layer_positions)):
            _, uuid = layer_positions[i]
            # Move this layer to be right after the previous layer (higher index)
            prev_uuid = layer_positions[i-1][1]
            self.move_layer_below(uuid, prev_uuid)
        
        # Set container UUID on all layers
        for _, uuid in layer_positions:
            self.set_layer_container(uuid, new_container_uuid)
        
        self._logger.info(f"Created container {new_container_uuid} with {len(layer_uuids)} layers at position {highest_idx}")
        return new_container_uuid
    
    def validate_container_contiguity(self) -> List[Dict[str, any]]:
        """Validate that containers are contiguous, split non-contiguous groups
        
        Scans all layers in order to ensure containers have no gaps. If a container
        is fragmented (layers separated by different container), splits off the
        non-contiguous portion with a new container_uuid.
        
        This is validation WITHIN an action, not after. Called as part of operations
        that change layer positions (reorder, move, paste).
        
        Returns:
            List of split operations: [{"old_container": str, "new_container": str, "layer_count": int}]
        """
        import uuid as uuid_module
        
        splits = []
        all_uuids = self.get_all_layer_uuids()
        
        # Build map of container_uuid -> list of (index, layer_uuid) tuples
        container_positions = {}
        for idx, uuid in enumerate(all_uuids):
            container_uuid = self.get_layer_container(uuid)
            if container_uuid is None:
                continue  # Root layers are always valid
            
            if container_uuid not in container_positions:
                container_positions[container_uuid] = []
            container_positions[container_uuid].append((idx, uuid))
        
        # Check each container for contiguity
        for container_uuid, positions in container_positions.items():
            if len(positions) <= 1:
                continue  # Single layer is always contiguous
            
            # Sort by index
            positions.sort(key=lambda x: x[0])
            
            # Find gaps (non-contiguous groups)
            groups = []
            current_group = [positions[0]]
            
            for i in range(1, len(positions)):
                prev_idx = positions[i-1][0]
                curr_idx = positions[i][0]
                
                # If indices are consecutive, same group
                if curr_idx == prev_idx + 1:
                    current_group.append(positions[i])
                else:
                    # Gap detected! Start new group
                    groups.append(current_group)
                    current_group = [positions[i]]
            
            # Add last group
            groups.append(current_group)
            
            # If more than one group, we need to split
            if len(groups) > 1:
                # Keep first group with original container_uuid
                # Split off remaining groups with new UUIDs
                for i in range(1, len(groups)):
                    group = groups[i]
                    
                    # Generate new container UUID (same name, new UUID portion)
                    new_container_uuid = self.regenerate_container_uuid(container_uuid)
                    
                    # Update all layers in this group
                    for _, uuid in group:
                        self.set_layer_container(uuid, new_container_uuid)
                    
                    splits.append({
                        "old_container": container_uuid,
                        "new_container": new_container_uuid,
                        "layer_count": len(group)
                    })
                    
                    self._logger.info(f"Split non-contiguous container: {container_uuid} -> {new_container_uuid} ({len(group)} layers)")
        
        return splits
