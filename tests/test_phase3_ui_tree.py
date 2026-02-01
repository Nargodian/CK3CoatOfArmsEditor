"""
Test Phase 3: UI Tree View

This test verifies Phase 3 implementation by manually creating
a CoA with containers and checking the structure.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'editor', 'src'))

from models.coa import CoA


def test_manual_container_creation():
	"""Create a CoA with containers for manual testing in the UI"""
	print("\n=== Creating CoA with Containers for Manual Testing ===")
	
	coa = CoA()
	
	# Create some layers
	lion1 = coa.add_layer(emblem_path="ce_lion.dds")
	lion2 = coa.add_layer(emblem_path="ce_lion.dds")
	cross1 = coa.add_layer(emblem_path="ce_cross.dds")
	cross2 = coa.add_layer(emblem_path="ce_cross.dds")
	star = coa.add_layer(emblem_path="ce_star.dds")
	
	# Assign to containers
	import uuid
	animals_container = f"container_{uuid.uuid4()}_Animals"
	symbols_container = f"container_{uuid.uuid4()}_Symbols"
	
	coa.set_layer_container(lion1, animals_container)
	coa.set_layer_container(lion2, animals_container)
	coa.set_layer_container(cross1, symbols_container)
	coa.set_layer_container(cross2, symbols_container)
	# star stays at root
	
	# Set names
	coa.set_layer_name(lion1, "Lion Front")
	coa.set_layer_name(lion2, "Lion Back")
	coa.set_layer_name(cross1, "Cross Main")
	coa.set_layer_name(cross2, "Cross Accent")
	coa.set_layer_name(star, "Star Solo")
	
	print(f"Created {len(coa.get_all_layer_uuids())} layers")
	print(f"Containers: {coa.get_all_containers()}")
	
	# Export to file for manual testing
	output_path = os.path.join(os.path.dirname(__file__), "test_containers_output.txt")
	coa_text = coa.to_string()
	with open(output_path, 'w') as f:
		f.write(coa_text)
	
	print(f"✓ Exported to: {output_path}")
	print("\nTo test UI:")
	print("1. Run the editor: python editor/src/main.py")
	print("2. Click Import and load the test_containers_output.txt file")
	print("3. Verify:")
	print("   - 'Animals' container with 2 lion layers (indented)")
	print("   - 'Symbols' container with 2 cross layers (indented)")
	print("   - 1 star layer at root level (not indented)")
	print("   - Click [-] to collapse containers")
	print("   - Double-click container names to rename")
	print("   - Test visibility/duplicate/delete buttons")
	
	return True


if __name__ == "__main__":
	success = test_manual_container_creation()
	sys.exit(0 if success else 1)
