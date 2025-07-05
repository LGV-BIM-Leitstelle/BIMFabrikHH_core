# Combined Tree Export Example

This example demonstrates how to use different tree export capabilities in one place. It combines the functionality of basic trees, generic trees, and optimized trees into a single unified interface.

## Features

- Export basic trees (simple representation)
- Export generic trees (parametric representation)
- Export optimized trees (performance-optimized representation)
- Uses Python dictionary for input data
- Configurable output paths and parameters

## Usage

1. Prepare your tree data as a Python dictionary with the following structure:
   ```python
   tree_data = {
       "trees": [
           {
               "BAUM_NR": "100001",  # Tree number
               "GATTUNG": "Ahorn",    # Genus
               "KRONENDURCHMESSER": 5.8,  # Crown diameter
               "STAMMUMFANG": 1.0,    # Trunk circumference
               "Easting": 558553.52,  # Position X
               "Northing": 5927499.96,  # Position Y
               "Elevation": 17.0,     # Position Z
               "art_deutsch": "Spitz-Ahorn",  # Species (German)
               "sorte_deutsch": "Spitz-Ahorn",  # Variety (German)
               "pflanzjahr": 1990     # Planting year
           },
           # ... more trees ...
       ]
   }
   ```

2. Run the example:
   ```python
   python example_app_trees_combined.py
   ```

3. Check the output directory for the generated IFC files:
   - `output_trees_basic.ifc`: Basic tree representation
   - `output_trees_generic.ifc`: Generic parametric tree representation
   - `output_trees_optimized.ifc`: Optimized tree representation

## Configuration

You can modify the tree parameters in the code:
- Tree height
- Trunk height
- Crown height
- Crown radius
- Trunk radius

## Example Data

An example tree data dictionary is included in the code (`EXAMPLE_TREES`). You can use this as a template for your own data or modify it directly in the code.

## Dependencies

All required dependencies are handled through the main project's dependency management. Make sure you have installed all project requirements before running the example. 