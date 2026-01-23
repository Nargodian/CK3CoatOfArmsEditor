"""
Example usage of the CoA Parser/Serializer

This demonstrates how to:
1. Parse existing CoA files
2. Access/modify the data
3. Create new CoA data from scratch
4. Serialize back to file format
"""

import sys
sys.path.insert(0, 'src/utils')

from coa_parser import parse_coa_file, serialize_coa_to_file, serialize_coa_to_string


# Example 1: Parse an existing CoA file
print("=" * 60)
print("Example 1: Parsing an existing CoA file")
print("=" * 60)

coa_data = parse_coa_file("coa_sample_1.txt")

# Get the main CoA object (first key is usually the dynasty/title ID)
coa_id = list(coa_data.keys())[0]
coa = coa_data[coa_id]

print(f"\nCoA ID: {coa_id}")
print(f"Pattern: {coa['pattern']}")
print(f"Colors: {coa['color1']}, {coa['color2']}, {coa['color3']}")
print(f"Custom: {coa['custom']}")
print(f"\nNumber of emblems: {len(coa['colored_emblem'])}")

# Look at first emblem
first_emblem = coa['colored_emblem'][0]
print(f"\nFirst emblem:")
print(f"  Texture: {first_emblem['texture']}")
print(f"  Color1: {first_emblem['color1']}")
print(f"  Instances: {len(first_emblem['instance'])}")

# Look at first instance
first_instance = first_emblem['instance'][0]
print(f"\n  First instance:")
print(f"    Position: {first_instance['position']}")
print(f"    Rotation: {first_instance.get('rotation', 'N/A')}")
print(f"    Depth: {first_instance.get('depth', 'N/A')}")
print(f"    Scale: {first_instance.get('scale', 'N/A')}")


# Example 2: Modify existing CoA data
print("\n" + "=" * 60)
print("Example 2: Modifying CoA data")
print("=" * 60)

# Change the base pattern
coa['pattern'] = "pattern__solid_designer.dds"

# Change colors
coa['color1'] = "red"
coa['color2'] = "yellow"
coa['color3'] = "white"

# Modify the first emblem's position
first_emblem['instance'][0]['position'] = [0.5, 0.5]
first_emblem['instance'][0]['rotation'] = 90

print("\nModified CoA:")
print(serialize_coa_to_string(coa_data))


# Example 3: Create a new CoA from scratch
print("=" * 60)
print("Example 3: Creating a new CoA from scratch")
print("=" * 60)

new_coa = {
	"coa_custom_12345": {
		"custom": True,
		"pattern": "pattern__solid_designer.dds",
		"color1": "green",
		"color2": "gold",
		"color3": "black",
		"colored_emblem": [
			{
				"color1": "gold",
				"texture": "ce_lion.dds",
				"instance": [
					{
						"position": [0.5, 0.5],
						"scale": [1.0, 1.0],
						"rotation": 0,
						"depth": 1.0
					}
				]
			},
			{
				"color1": "black",
				"texture": "ce_crown.dds",
				"instance": [
					{
						"position": [0.5, 0.2],
						"scale": [0.5, 0.5],
						"depth": 2.0
					}
				]
			}
		]
	}
}

print("\nNew CoA created:")
print(serialize_coa_to_string(new_coa))

# Save to file
serialize_coa_to_file(new_coa, "examples/custom_coa_example.txt")
print("\n✓ Saved to examples/custom_coa_example.txt")


# Example 4: Parse complex CoA with multiple instances
print("\n" + "=" * 60)
print("Example 4: Working with complex CoA (multiple emblems)")
print("=" * 60)

complex_coa = parse_coa_file("coa_sample_2.txt")
complex_id = list(complex_coa.keys())[0]
complex = complex_coa[complex_id]

print(f"\nCoA ID: {complex_id}")
print(f"Total emblems: {len(complex['colored_emblem'])}")

for i, emblem in enumerate(complex['colored_emblem'], 1):
	instance_count = len(emblem['instance'])
	print(f"\n  Emblem {i}: {emblem['texture']}")
	print(f"    Color: {emblem['color1']}")
	print(f"    Instances: {instance_count}")
	
	for j, inst in enumerate(emblem['instance'], 1):
		print(f"      Instance {j}:")
		print(f"        Position: {inst.get('position', [0.5, 0.5])}")
		print(f"        Scale: {inst.get('scale', [1.0, 1.0])}")
		print(f"        Rotation: {inst.get('rotation', 0)}°")


print("\n" + "=" * 60)
print("Examples complete!")
print("=" * 60)
