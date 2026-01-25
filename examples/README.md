# Examples

This directory contains code examples and sample coat of arms designs.

## Contents

### Code Examples

- **parser_example.py** - Demonstrates how to use the CK3 CoA parser to read and write coat of arms files

### Game Samples

The `game_samples/` folder contains example coat of arms designs in CK3 format:

- **coa_sample_0.txt** through **coa_sample_7.txt** - Various coat of arms samples from the game
- **custom_coa_example.txt** - Custom coat of arms example
- **superman*.txt** - Superman-themed coat of arms variations
- **supermanFromGame.txt** - Superman design exported from game

## Usage

### Loading in the Editor

1. Run the editor: `python editor/src/main.py`
2. Go to File → Open
3. Navigate to `examples/game_samples/`
4. Select any .txt file to load

### Using the Parser Example

```bash
python examples/parser_example.py
```

This will demonstrate parsing and serializing coat of arms data.

### Creating Your Own Examples

Save your coat of arms designs to this folder for easy reference and sharing. The editor can export to CK3 format (.txt files) that can be loaded back in.
