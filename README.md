# BIMFabrikHH - Hamburg BIM Factory

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/poetry-1.0+-blue.svg)](https://python-poetry.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Overview

**BIMFabrikHH** is a development by the City of Hamburg as part of the *Connected Urban Twins (CUT)* project. It
provides automated conversion of geospatial data from heterogeneous formats to IFC (Industry Foundation Classes) format,
enabling BIM (Building Information Modeling) methodology implementation.

Geospatial data such as DGM (Digital Terrain Models), city models, and other infrastructure data are crucial foundations
for construction planning. These data are often available as GIS data, but BIM methodology requires conversion to IFC
format. BIMFabrikHH aims to provide geospatial data in IFC format with relevant information from heterogeneous formats.

### Key Benefits

- **Automation**: Simplifies and standardizes repetitive processes through automation
- **Resource Efficiency**: Saves resources through streamlined workflows
- **BIM Adoption**: Promotes BIM usage within the City of Hamburg (FHH)
- **Usability**: Improves usability in the Master Portal
- **Universal Application**: One application for all geospatial data conversion needs

## Features

### Supported Data Types

1. **Tree Data (Baum)**
    - Street tree inventory from Hamburg OGC API
    - Automatic tree placement with realistic geometry
    - Support for different tree species and sizes

2. **Digital Terrain Models (DGM)**
    - GeoTIFF processing and conversion
    - TIN (Triangulated Irregular Network) generation
    - Optimized mesh creation for large datasets

3. **City Models (Stadtmodell)**
    - CityGML file parsing and conversion
    - Support for LOD1 and LOD2 building geometries
    - Building information extraction and mapping

### Core Capabilities

- **IFC Model Generation**: Creates standardized IFC models with proper structure
- **Georeferencing**: Maintains spatial reference systems (ETRS89-UTM32N)
- **Property Sets**: Adds Hamburg-specific BIM property sets
- **Geometry Processing**: Handles complex 3D geometry creation and optimization
- **API Integration**: Connects to Hamburg's Open Data APIs

## Installation

### Prerequisites

- Python 3.11 or higher
- Poetry (for dependency management)
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd BIMFabrikHH_core
   ```

2. **Install dependencies using Poetry**
   ```bash
   poetry install
   ```

3. **Activate the virtual environment**
   ```bash
   poetry shell
   ```

### Dependencies

The project uses the following key dependencies:

- **ifcopenshell**: IFC file creation and manipulation
- **pandas**: Data processing and manipulation
- **pyvista**: 3D mesh processing and visualization
- **rasterio**: Geospatial raster data processing
- **pydantic**: Data validation and settings management
- **lxml**: XML parsing for CityGML files
- **numpy**: Numerical computing
- **requests**: HTTP API communication

## Project Structure

```
BIMFabrikHH_core/
├── src/
│   └── BIMFabrikHH/
│       ├── apps/                    # Application modules
│       │   ├── baum/               # Tree modeling application
│       │   ├── dgm/                # Digital terrain modeling
│       │   └── stadtmodell/        # City model processing
│       ├── core/                   # Core functionality
│       │   ├── ifc_modelbuilder.py # IFC model creation
│       │   ├── geometry_creator.py # 3D geometry generation
│       │   ├── request_oaf.py      # OGC API communication
│       │   └── ...                 # Other core modules
│       ├── pydantic_models/        # Data validation models
│       └── default/                # Configuration and constants
├── examples/                       # Usage examples
├── tests/                         # Test suite
├── samples/                       # Sample data files
├── output/                        # Generated output files
└── docs/                          # Documentation
```

## Usage

### Basic Usage

Each application module provides a simple interface for converting geospatial data to IFC format.

#### Tree Modeling Example

```python
from src.BIMFabrikHH.apps.baum.app import BaumModeller
from src.BIMFabrikHH.core.request_ogc import request_body_example

# Create tree modeler
baum_modeller = BaumModeller()

# Create IFC model
ifc_bytes = baum_modeller.create_tree_model(request_body_example)

# Save to file
with open("trees.ifc", "wb") as f:
    f.write(ifc_bytes)
```

#### Digital Terrain Model Example

```python
from src.BIMFabrikHH.apps.dgm.app import process_terrain_folder_to_ifc
from pathlib import Path

# Process GeoTIFF files
tif_files = ["terrain1.tif", "terrain2.tif"]
folder_path = Path("terrain_data")

ifc_bytes = process_terrain_folder_to_ifc(
    folder_path=folder_path,
    tif_files=tif_files,
    downsample_factor=4,
    target_reduction=0.9,
    input_data=request_body_example
)
```

#### City Model Example

```python
from src.BIMFabrikHH.apps.stadtmodell.app import process_gml_to_ifc

# Process CityGML files
gml_files = ["buildings.gml"]
ifc_bytes = process_gml_to_ifc(
    gml_files=gml_files,
    model_params=request_body_example
)
```

### Configuration

The project uses Pydantic models for configuration and data validation. Key configuration areas include:

- **Bounding Box Parameters**: Define the area of interest
- **Project Information**: Set project metadata
- **Georeferencing**: Configure coordinate systems
- **Property Sets**: Define Hamburg-specific BIM properties

## API Reference

### Core Classes

#### BaumModeller

Main class for tree modeling operations.

**Methods:**

- `create_tree_model(model_params)`: Creates IFC model from tree data
- `get_oaf_tree_df(x1, y1, x2, y2)`: Fetches tree data from OGC API

#### IfcModelBuilder

Handles IFC model creation and structure.

**Methods:**

- `build_project(project_name, site_name, building_name)`: Creates IFC project structure
- `reset_model()`: Resets the current model
- `get_model()`: Returns the current IFC model

#### GeometryCreator

Manages 3D geometry creation and processing.

**Methods:**

- `create_mapped_objects()`: Creates IFC objects from geometry data
- `process_geometry()`: Processes and optimizes geometry

### Data Models

#### RequestParams

Main configuration model for all applications.

**Fields:**

- `bbox`: BoundingBoxParams - Area of interest
- `containers`: List[Container] - Configuration containers

#### BoundingBoxParams

Defines the spatial extent for data processing.

**Fields:**

- `min_x, min_y, max_x, max_y`: float - Bounding box coordinates

## Development

### Code Style

The project follows PEP 8 guidelines with the following tools:

- **Black**: Code formatting (line length: 120)
- **isort**: Import sorting
- **autoflake**: Unused import removal
- **Ruff**: Fast Python linter

### Testing

Run tests using pytest:

```bash
poetry run pytest
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Development Setup

```bash
# Install development dependencies
poetry install --with dev

# Run linting
poetry run black src/ tests/
poetry run isort src/ tests/
poetry run autoflake --in-place --remove-all-unused-imports src/ tests/

# Run tests
poetry run pytest
```

## Architecture

### Design Patterns

The project follows several design patterns:

1. **Factory Pattern**: IfcModelBuilder creates IFC models
2. **Strategy Pattern**: Different geometry creation strategies
3. **Builder Pattern**: Step-by-step model construction
4. **Repository Pattern**: Data access abstraction

### Module Responsibilities

- **apps/**: Application-specific logic and workflows
- **core/**: Reusable core functionality
- **pydantic_models/**: Data validation and configuration
- **default/**: Default configurations and constants

### Data Flow

1. **Input**: Geospatial data (API, files, etc.)
2. **Processing**: Data parsing and geometry creation
3. **Model Building**: IFC structure creation
4. **Output**: IFC file generation

## Performance Considerations

### Optimization Strategies

- **Mesh Decimation**: Reduces geometry complexity for large datasets
- **Lazy Loading**: Loads data only when needed
- **Memory Management**: Efficient handling of large datasets
- **Parallel Processing**: Where applicable for independent operations

### Memory Usage

- Large terrain datasets may require significant memory
- Consider using chunked processing for very large files
- Monitor memory usage during processing

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're in the correct virtual environment
2. **Memory Issues**: Reduce dataset size or use chunked processing
3. **API Errors**: Check network connectivity and API endpoints
4. **Geometry Errors**: Verify input data format and coordinate systems

### Debug Mode

Enable debug logging for detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions:

- **Email**: ahmed.salem@gv.hamburg.de
- **Project**: Connected Urban Twins (CUT)
- **Organization**: City of Hamburg

## Acknowledgments

- City of Hamburg for project support
- Connected Urban Twins (CUT) project team
- Open source community for dependencies
- IFC OpenShell team for IFC support

## Roadmap

### Planned Features

- [ ] Support for additional geospatial formats
- [ ] Enhanced geometry optimization
- [ ] Web interface for data processing
- [ ] Integration with additional Hamburg APIs
- [ ] Advanced property set management
- [ ] Real-time data processing capabilities

### Version History

- **v0.1.0**: Initial release with basic functionality
    - Tree modeling support
    - DGM processing
    - City model conversion
    - IFC model generation

---

**Note**: This project is actively developed as part of the Connected Urban Twins initiative. For the latest updates and
features, please refer to the project repository.
