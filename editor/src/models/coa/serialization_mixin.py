"""
CoA Serialization Mixin

Provides serialization and parsing methods for the CoA model:
- Parsing CK3 format strings into CoA data
- Serializing CoA data to CK3 format strings
- Layer-specific serialization for clipboard operations

Extracted from coa.py to improve code organization and maintainability.
"""

import re
import logging
from typing import List, Optional
import uuid as uuid_module

from ._internal.layer import Layer
from ._internal.instance import Instance
from constants import (
    DEFAULT_PATTERN_TEXTURE,
    DEFAULT_BASE_COLOR1, DEFAULT_BASE_COLOR2, DEFAULT_BASE_COLOR3,
    DEFAULT_EMBLEM_COLOR1, DEFAULT_EMBLEM_COLOR2, DEFAULT_EMBLEM_COLOR3
)


class CoASerializationMixin:
    """Mixin providing serialization and parsing methods for CoA model"""
    
    def parse(self, ck3_text: str, target_uuid: Optional[str] = None) -> List[str]:
        """Parse CK3 format string and insert layers
        
        Intelligently handles two cases:
        1. Full CoA (has 'pattern' key) → Replaces entire CoA (ignores target_uuid)
        2. Loose layers (just colored_emblem blocks) → Inserts at target_uuid position
        
        Args:
            ck3_text: CK3 format string (full CoA or loose layers)
            target_uuid: If provided, insert loose layers below this UUID (in front of it)
                        Ignored if parsing full CoA.
        
        Returns:
            List of UUIDs for newly created/parsed layers
            
        Example full CoA:
            {
                pattern = "pattern_solid.dds"
                color1 = "white"
                colored_emblem = { ... }
            }
            
        Example loose layers:
            colored_emblem = { texture = "emblem_cross.dds" ... }
            colored_emblem = { texture = "emblem_star.dds" ... }
        """
        from ._internal.coa_parser import CoAParser
        from models.color import Color
        
        # Remove ##META## prefix to expose hidden metadata
        if ck3_text:
            ck3_text = ck3_text.replace('##META##', '')
        
        # If ck3_text is just a list of colored_emblem blocks, wrap it
        if not ck3_text.strip().startswith(('coat_of_arms', 'coa_export', 'layers_export')):
             ck3_text = f"wrapper = {{ {ck3_text} }}"
        
        parser = CoAParser()
        try:
            parsed = parser.parse_string(ck3_text)
        except Exception as e:
            self._logger.error(f"Failed to parse: {e}")
            raise ValueError(f"Invalid CK3 format: {e}")
        
        if not parsed:
            self._logger.warning("Empty parse result")
            return []
        
        coa_key = list(parsed.keys())[0]
        coa_obj = parsed[coa_key]
        
        # Handle arbitrary CK3 key prefixes (e.g., coa_rd_dynasty_12345, e_byzantium)
        # When wrapped, the structure is wrapper -> arbitrary_key -> {pattern, ...}
        if 'pattern' not in coa_obj and 'colored_emblem' not in coa_obj:
            nested_dicts = [v for v in coa_obj.values() if isinstance(v, dict)]
            if len(nested_dicts) == 1 and ('pattern' in nested_dicts[0] or 'colored_emblem' in nested_dicts[0]):
                coa_obj = nested_dicts[0]
        
        # Detect if this is a full CoA (has pattern) or loose layers (only colored_emblem)
        is_full_coa = 'pattern' in coa_obj
        
        new_uuids = []
        
        if is_full_coa:
            # Full CoA: Replace everything (ignore target_uuid)
            self._layers.clear(caller='CoA')
            
            # Set base pattern and colors
            self._pattern = coa_obj.get('pattern', DEFAULT_PATTERN_TEXTURE)
            
            # Parse colors using Color.from_name() which handles both named colors and rgb format
            color1_str = coa_obj.get('color1', DEFAULT_BASE_COLOR1)
            color2_str = coa_obj.get('color2', DEFAULT_BASE_COLOR2)
            color3_str = coa_obj.get('color3', DEFAULT_BASE_COLOR3)
            
            self._pattern_color1 = Color.from_name(color1_str)
            self._pattern_color2 = Color.from_name(color2_str)
            self._pattern_color3 = Color.from_name(color3_str)
            
            # Parse layers and sort by depth (CK3 uses depth for z-ordering:
            # lower depth = closer to camera = drawn in front/on top)
            emblems = coa_obj.get('colored_emblem', [])
            parsed_layers = []
            for emblem in emblems:
                try:
                    layer = Layer.parse(emblem, caller='CoA')
                    # Use minimum instance depth as the layer's sort key
                    min_depth = min(
                        (layer.get_instance(i, caller='CoA').depth for i in range(layer.instance_count)),
                        default=0.0
                    )
                    parsed_layers.append((min_depth, layer))
                except Exception as e:
                    self._logger.error(f"Failed to parse layer: {e}")
                    continue
            
            # Sort descending: highest depth first (background), lowest depth last (foreground)
            parsed_layers.sort(key=lambda x: x[0], reverse=True)
            
            for _, layer in parsed_layers:
                self.add_layer_object(layer, at_front=False)
                new_uuids.append(layer.uuid)
            
            self._logger.debug(f"Parsed full CoA with {len(new_uuids)} layers")
        
        else:
            # Loose layers: Insert at target_uuid position
            # Always regenerate UUIDs for loose layers (paste operations)
            emblems = coa_obj.get('colored_emblem', [])
            
            for emblem in emblems:
                try:
                    layer = Layer.parse(emblem, caller='CoA', regenerate_uuid=True)
                    self.add_layer_object(layer, target_uuid=target_uuid, at_front=(target_uuid is None))
                    new_uuids.append(layer.uuid)
                    # Stack subsequent layers on top of each other
                    target_uuid = layer.uuid
                except Exception as e:
                    self._logger.error(f"Failed to parse layer: {e}")
                    continue
            
            self._logger.debug(f"Inserted {len(new_uuids)} loose layers")
        
        # Track last added for auto-selection
        if new_uuids:
            self._last_added_uuid = new_uuids[-1]
            self._last_added_uuids = new_uuids
        
        return new_uuids
    
    def parse_layers_string(self, ck3_text: str) -> list:
        """Parse raw colored_emblem blocks into this CoA without creating a new instance.
        
        Designed for clipboard operations: properly parses ##META## container tags
        which might be lost during standard wrapping/parsing.
        
        Args:
            ck3_text: CK3 text containing colored_emblem blocks
            
        Returns:
            List of generated layer UUIDs
        """
        from ._internal.coa_parser import CoAParser
        from models.color import Color
        from models.coa import Layer
        
        if not ck3_text or 'colored_emblem' not in ck3_text:
            return []
            
        # Remove ##META## prefix from clipboard content to expose hidden metadata as valid CK3 attributes
        # This allows standard parser to read container_uuid, name, etc. as keys in the emblem dict
        ck3_text = ck3_text.replace('##META##', '')
            
        # Use a generic wrapper that doesn't imply CoA structure
        wrapped_text = f"clipboard_wrapper = {{ {ck3_text} }}"
        
        parser = CoAParser()
        try:
            parsed = parser.parse_string(wrapped_text)
        except Exception as e:
            self._logger.error(f"Failed to parse clipboard layers: {e}")
            return []
            
        if not parsed:
            return []
            
        # Get the wrapper dict
        wrapper_key = list(parsed.keys())[0]
        wrapper_obj = parsed[wrapper_key]
        
        # Get emblems list
        emblems = wrapper_obj.get('colored_emblem', [])
        if isinstance(emblems, dict):
            emblems = [emblems]
            
        new_uuids = []
        for emblem in emblems:
            try:
                # Parse layer (it will pick up container_uuid from emblem dict if parser extracted it)
                layer = Layer.parse(emblem, caller='CoA', regenerate_uuid=True)
                
                # Add to this CoA
                self.add_layer_object(layer, at_front=False)
                new_uuids.append(layer.uuid)
            except Exception as e:
                self._logger.error(f"Failed to parse clipboard layer: {e}")
                continue
                
        return new_uuids

    @classmethod
    def from_string(cls, ck3_text: str) -> 'CoA':
        """Convenience factory: create CoA and parse from CK3 format string
        
        Args:
            ck3_text: CK3 coat of arms definition
            
        Returns:
            New CoA instance populated with parsed data
        """
        coa = cls()
        coa.parse(ck3_text)
        return coa
    
    @classmethod
    def from_layers_string(cls, ck3_text: str) -> 'CoA':
        """Parse colored_emblem blocks into a new CoA with default pattern/colors
        
        This is for clipboard operations where only layer data is copied,
        not the full CoA structure.
        
        Args:
            ck3_text: CK3 colored_emblem blocks
            
        Returns:
            New CoA instance with default pattern and parsed layers
        """
        from ._internal.coa_parser import CoAParser
        import uuid as uuid_module
        
        coa = cls()
        
        # Quick validation: check if text looks like CoA data
        if not ck3_text or 'colored_emblem' not in ck3_text:
            coa._logger.debug(f"Text does not contain colored_emblem blocks, skipping parse")
            return coa  # Return empty CoA
        
        # Wrap the layers in a minimal CoA structure for parsing
        wrapped_text = f"coa_export = {{\n\tpattern = \"{DEFAULT_PATTERN_TEXTURE}\"\n\tcolor1 = \"{DEFAULT_BASE_COLOR1}\"\n\tcolor2 = \"{DEFAULT_BASE_COLOR2}\"\n\tcolor3 = \"{DEFAULT_BASE_COLOR3}\"\n\t{ck3_text}\n}}"
        
        # Parse using the standard parser
        parser = CoAParser()
        try:
            parsed = parser.parse_string(wrapped_text)
        except Exception as e:
            coa._logger.debug(f"Failed to parse layers: {e}")
            return coa  # Return empty CoA
        
        # Extract colored_emblem blocks
        if not parsed:
            return coa
        
        coa_key = list(parsed.keys())[0]
        coa_obj = parsed[coa_key]
        emblems = coa_obj.get('colored_emblem', [])
        
        # Collect all layers with depth for sorting
        layers_with_depth = []
        
        for emblem in emblems:
            filename = emblem.get('texture', '')
            
            # Parse colors from CK3 format (handles both named colors and rgb blocks)
            color1_raw = emblem.get('color1', DEFAULT_EMBLEM_COLOR1)
            color2_raw = emblem.get('color2', DEFAULT_EMBLEM_COLOR2)
            color3_raw = emblem.get('color3', DEFAULT_EMBLEM_COLOR3)
            
            color1 = Color.from_ck3_string(color1_raw) if color1_raw else Color.from_name(DEFAULT_EMBLEM_COLOR1)
            color2 = Color.from_ck3_string(color2_raw) if color2_raw else Color.from_name(DEFAULT_EMBLEM_COLOR2)
            color3 = Color.from_ck3_string(color3_raw) if color3_raw else Color.from_name(DEFAULT_EMBLEM_COLOR3)
            
            # Parse mask
            mask_raw = emblem.get('mask')
            mask = None
            if mask_raw:
                if isinstance(mask_raw, list) and len(mask_raw) == 3:
                    mask = mask_raw
            
            # Parse instances
            instances = emblem.get('instance', [])
            if not instances:
                instances = [{'position': [0.5, 0.5], 'scale': [1.0, 1.0], 'rotation': 0, 'depth': 0}]
            
            # Always generate new UUID for paste operations (avoid duplicate UUIDs)
            layer_uuid = str(uuid_module.uuid4())
            
            # Parse container_uuid (preserve if present)
            container_uuid = emblem.get('container_uuid')
            
            # Parse name (preserve if present, will default in Layer.__init__ if missing)
            layer_name = emblem.get('name', '')
            
            # Create layer data
            layer_data = {
                'uuid': layer_uuid,
                'container_uuid': container_uuid,
                'name': layer_name,
                'filename': filename,
                'colors': 3,
                'color1': color1,
                'color2': color2,
                'color3': color3,
                'mask': mask,
                'instances': [],
                'selected_instance': 0,
                'flip_x': False,
                'flip_y': False
            }
            
            # Parse instances
            for inst in instances:
                position = inst.get('position', [0.5, 0.5])
                scale = inst.get('scale', [1.0, 1.0])
                rotation = inst.get('rotation', 0)
                depth = inst.get('depth', 0)
                
                pos_x = float(position[0]) if len(position) > 0 else 0.5
                pos_y = float(position[1]) if len(position) > 1 else 0.5
                scale_x = float(scale[0]) if len(scale) > 0 else 1.0
                scale_y = float(scale[1]) if len(scale) > 1 else 1.0
                
                instance_obj = Instance({
                    'pos_x': pos_x,
                    'pos_y': pos_y,
                    'scale_x': scale_x,
                    'scale_y': scale_y,
                    'rotation': float(rotation),
                    'depth': float(depth)
                })
                layer_data['instances'].append(instance_obj)
            
            # Store layer with depth for sorting
            min_depth = min(inst.depth for inst in layer_data['instances'])
            layers_with_depth.append((min_depth, layer_data))
        
        # Sort by depth ascending for insert(0): each insert pushes previous to back,
        # so highest depth ends up at index 0 (bottom/behind) and lowest at top (front)
        # CK3 semantics: lower depth = closer to camera = in front
        layers_with_depth.sort(key=lambda x: x[0], reverse=False)
        
        # Add layers to model (back to front)
        for _, layer_data in layers_with_depth:
            # Remove depth from instances (set to 0 since Instance requires it)
            for inst in layer_data['instances']:
                inst.depth = 0.0
            
            # Create Layer and add to collection
            layer = Layer(layer_data, caller='CoA')
            coa.insert_layer_at_index(0, layer)
        
        coa._logger.debug(f"Parsed {coa.get_layer_count()} layers from colored_emblem blocks")
        return coa
    
    def serialize(self) -> str:
        """Export CoA to CK3 format string
        
        Uses mature serialization matching the running application's format.
        Includes mask field support and proper depth ordering.
        
        Note: Symmetry transforms are expanded to instances during serialization
        without mutating the model (transient generation).
        
        Returns:
            CK3 coat of arms definition
        """
        # Check if force RGB mode is enabled
        force_rgb = getattr(self, '_force_rgb_colors', False)
        
        lines = []
        lines.append("coa_export = {")
        
        # Pattern and colors
        lines.append(f'\tpattern = "{self._pattern}"')
        
        # Pattern colors (use Color.to_ck3_string())
        lines.append(f'\tcolor1 = {self._pattern_color1.to_ck3_string(force_rgb=force_rgb)}')
        lines.append(f'\tcolor2 = {self._pattern_color2.to_ck3_string(force_rgb=force_rgb)}')
        lines.append(f'\tcolor3 = {self._pattern_color3.to_ck3_string(force_rgb=force_rgb)}')
        
        # Colored emblems (layers) - use Layer.serialize()
        for layer in self._layers:
            lines.append(layer.serialize(caller='CoA'))
        
        lines.append("}")
        return '\n'.join(lines)
    
    def to_string(self) -> str:
        """Alias for serialize() - export CoA to CK3 format string
        
        Returns:
            CK3 coat of arms definition
        """
        return self.serialize()
    
    def serialize_layers_to_string(self, uuids: list, strip_container_uuid: bool = True) -> str:
        """Export specific layers to CK3 format string
        
        Serializes only the layers with the given UUIDs. Useful for clipboard operations.
        
        Args:
            uuids: List of layer UUIDs to serialize
            strip_container_uuid: If True, remove container_uuid from serialized layers (default for individual copy).
                                  If False, preserve container_uuid (for whole container copy).
            
        Returns:
            CK3 format string containing only the specified layers (colored_emblem blocks)
        """
        lines = []
        
        # Filter and serialize only specified layers using Layer.serialize()
        for layer_uuid in uuids:
            layer = self.get_layer_by_uuid(layer_uuid)
            if not layer:
                continue
            
            # Serialize the layer
            layer_string = layer.serialize(caller='CoA')
            
            # Strip container_uuid META comments if requested
            if strip_container_uuid:
                # Remove the ##META##container_uuid line from serialization
                import re
                layer_string = re.sub(r'\s*##META##container_uuid\s*=\s*"[^"]*"\s*\n', '', layer_string)
                layer_string = re.sub(r'\s*##META##container_symmetry\s*=\s*"[^"]*"\s*\n', '', layer_string)
            
            lines.append(layer_string)
        
        return '\n'.join(lines)
