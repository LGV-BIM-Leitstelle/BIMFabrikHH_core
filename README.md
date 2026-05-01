# BIMFabrikHH Core

[![PyPI version](https://badge.fury.io/py/bimfabrikhh-core.svg)](https://pypi.org/project/bimfabrikhh-core/)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-LGPL--2.1-blue.svg)](LICENSE)

## Quick Install

```bash
pip install bimfabrikhh-core
```

## Overview

This package is one of the main components of the BIMFabrikHH project, together with the following packages:

- **BIMFabrikHH_core**  
  - [GitHub](https://github.com/LGV-BIM-Leitstelle/BIMFabrikHH_core)  
  - [OpenCode](https://gitlab.opencode.de/LGV-BIM-Leitstelle/bimfabrikhh_core)
- **ifcfactory**  
  - [GitHub](https://github.com/LGV-BIM-Leitstelle/ifcfactory)  
  - [OpenCode](https://gitlab.opencode.de/LGV-BIM-Leitstelle/ifcfactory)
- **BIMFabrikHH_api**  
  - [GitHub](https://github.com/LGV-BIM-Leitstelle/BIMFabrikHH_api)  
  - [OpenCode](https://gitlab.opencode.de/LGV-BIM-Leitstelle/BIMFabrikHH_api)

These three packages make up the **BIMFabrikHH** Project, enabling automated BIM and IFC workflows as part of the Connected Urban Twins (CUT) project.

BIMFabrikHH is a development by the **Freie und Hansestadt Hamburg, Landesbetrieb Geoinformation und Vermessung,
BIM-Leitstelle** as part of the *Connected Urban Twins (CUT)* project. It provides automated conversion of geospatial
data from heterogeneous formats to IFC (Industry Foundation Classes) format, enabling BIM (Building Information
Modeling) methodology implementation.

Geospatial data such as DGM (Digital Terrain Models), city models, and other infrastructure data are crucial foundations
for construction planning. These data are often available as GIS data, but BIM methodology requires conversion to IFC
format. BIMFabrikHH aims to provide geospatial data in IFC format with relevant information from heterogeneous formats.

### Key Benefits

- **Automation**: Simplifies and standardizes repetitive processes through automation
- **Resource Efficiency**: Saves resources through streamlined workflows
- **BIM Adoption**: Promotes BIM usage within the City of Hamburg (FHH)
- **Usability**: Improves usability in the Master Portal
- **Universal Application**: One application for all geospatial data conversion needs
- **Modular Architecture**: Clean separation of concerns with reusable components

## Features
This project is under intensive development. Features are being added and improved rapidly; users should expect frequent updates, experimental components, and breaking changes as the platform evolves toward a stable and robust release. Feedback and contributions are highly welcome during this phase.

### Supported Data Types

1. **Tree Data (Baum)**
    - Street tree inventory from Hamburg OGC API
    - Automatic tree placement with realistic geometry
    - Support for different tree species and sizes
    - Two record-builder apps sharing a single `TreeRecord` input contract:
      - `TreesBasicApp` (`apps/trees/basic/app.py`): mesh trunk + icosphere crown via `ifcopenshell.api`.
      - `TreesGenericApp` (`apps/trees/generic/app.py`): `ifcfactory.BIMFactoryElement` pipeline.
    - Shared data-processing helpers in `apps/trees/processing.py` (`dataframe_to_records`, `build_tree_psets`, `calculate_tree_height`, `validate_tree_records`, `resolve_tree_dimensions`, `collect_pydantic_psets`). Both apps consume these so their `app.py` files hold only IFC-writing logic.
    - DataFrame column mapping via `TreeColumnSchema` (`apps/trees/column_schema.py`) with presets `DEFAULT_OAF_SCHEMA` (Hamburg OGC API / surveying) and `BAUMKATASTER_SCHEMA` (Strassenbaumkataster).
    - The older generic elevation exporter (`BaumGenericElevationApp`, former `tree_model` dataclasses) was removed; migrate callers to `TreesGenericApp.build_ifc` or `TreesBasicApp.build_ifc`.

2. **Digital Terrain Models (DGM)**
    - GeoTIFF processing and conversion (local paths or HTTP(S) URLs).
    - Feature-preserving adaptive sampling: slope/curvature-based importance, boundary stitching, Delaunay triangulation.
    - Two record-builder apps sharing a single `TerrainMesh` input contract (`data_models/terrain_mesh.py`):
      - `TerrainBasicApp` (`apps/terrain/basic/app.py`): writes the mesh via `ifcopenshell.api`.
      - `TerrainGenericApp` (`apps/terrain/generic/app.py`): writes the mesh via the `ifcfactory.BIMFactoryElement` pipeline (same pattern as `TreesGenericApp`).
    - Shared meshing helpers live in `apps/terrain/processing.py` (`extract_mesh_adaptive`, `adaptive_sampling`, `generate_delaunay_mesh`, `sample_elevations_from_raster`, etc.).
    - `core.georeferencing.bbox_request_params_to_epsg25832` projects the request WGS84 bbox to EPSG:25832. Terrain IFC helpers in `apps/terrain/_ifc_common.py` (`default_terrain_psets`) and `core.geometry.place_basepoint` keep basic and generic consistent; the Nullpunktobjekt is written only when `basepoint_origin` or `RequestParams.bbox` supplies placement (same rule as city apps).
    - Pydantic pset defaults via `Pset_Objektinformation_DGM` and `Pset_Hyperlink` — callers may override by passing their own `psets=[...]`.
    - Convenience one-shot on both apps: `from_geotiffs(tif_files, request_params=...)` chains mesh extraction and IFC export.

3. **City Models (Stadtmodell)**
    - CityGML file parsing and conversion
    - Support for LOD1 and LOD2 building geometries
    - Building information extraction and mapping
    - Refactored parser for better maintainability

4. **Basepoint Objects**
    - Georeferencing basepoints with directional indicators
    - North arrow integration
    - Configurable size and positioning

### Core Capabilities

- **IFC Model Generation**: Creates standardized IFC models with proper structure
- **Georeferencing**: Maintains spatial reference systems (ETRS89-UTM32N)
- **Property Sets**: Adds Hamburg-specific BIM property sets
- **Geometry Processing**: Handles complex 3D geometry creation and optimization
- **API Integration**: Connects to Hamburg's Open Data APIs
- **Utility Functions**: Comprehensive set of reusable geometry and spatial utilities

## Installation

### From PyPI (Recommended)

```bash
pip install bimfabrikhh-core
```

### From Source (Development)

```bash
git clone https://github.com/LGV-BIM-Leitstelle/BIMFabrikHH_core.git
cd BIMFabrikHH_core
poetry install
poetry shell
```

### Prerequisites

- Python 3.11
- pip or Poetry

## Architecture

The project follows a modular architecture:

```mermaid
graph TB
    %% External Libraries
    subgraph external ["External Libraries"]
        ifcopenshell["ifcopenshell<br/>(IFC API)"]
        ifcfactory["ifcfactory<br/>(IFC Geometry)"]
        numpy["numpy"]
        pandas["pandas"]
        pydantic["pydantic"]
        rasterio["rasterio"]
        pyproj["pyproj"]
        lxml["lxml"]
    end
    
    %% Core Infrastructure
    subgraph core ["BIMFabrikHH Core"]
        ifc_modelbuilder["IfcModelBuilder<br/>(Model Creation)"]
        geometry["Geometry Objects<br/>(Box, Tree, etc.)"]
        data_models["Data Models<br/>(RequestParams, etc.)"]
        utils["Utilities<br/>(Math, Spatial, etc.)"]
        city_parser["CityGML Parser"]
        config["Configuration<br/>(Paths, Logging)"]
    end
    
    %% Applications
    subgraph city_apps ["City Model Applications"]
        city_basic["City App<br/>(CityBasicApp)"]
        city_generic["City App<br/>(CityGenericApp)"]
    end
    
    subgraph tree_apps ["Tree Model Applications"]
        trees_basic["Basic Trees<br/>(TreesBasicApp)"]
        trees_generic["Generic Trees<br/>(TreesGenericApp)"]
    end
    
    subgraph terrain_apps ["Terrain Model Applications"]
        terrain_basic["Basic Terrain<br/>(TerrainBasicApp)"]
        terrain_generic["Generic Terrain<br/>(TerrainGenericApp)"]
    end
    
    subgraph basepoint_apps ["Basepoint Applications"]
        basepoint_basic["Basic Basepoint"]
        basepoint_generic["Generic Basepoint"]
    end
    
    %% External to Core dependencies
    ifcopenshell --> ifc_modelbuilder
    ifcopenshell --> geometry
    ifcfactory --> geometry
    numpy --> geometry
    numpy --> utils
    pandas --> data_models
    pydantic --> data_models
    rasterio --> utils
    pyproj --> utils
    lxml --> city_parser
    
    %% Core to Applications - Key relationships
    ifc_modelbuilder -.->|Key Dependency| city_basic
    ifc_modelbuilder -.->|Key Dependency| city_generic
    ifc_modelbuilder -.->|Key Dependency| trees_basic
    ifc_modelbuilder -.->|Key Dependency| terrain_basic
    ifc_modelbuilder -.->|Key Dependency| basepoint_basic
    ifc_modelbuilder -.->|Key Dependency| basepoint_generic
    
    %% Data model dependencies
    data_models -.->|Data Models| city_basic
    data_models -.->|Data Models| city_generic
    data_models -.->|Data Models| trees_basic
    data_models -.->|Data Models| terrain_basic
    data_models -.->|Data Models| basepoint_basic
    data_models -.->|Data Models| basepoint_generic
    
    %% Geometry dependencies
    geometry --> trees_basic
    geometry --> basepoint_basic
    
    %% Utility dependencies
    utils -.->|Utilities| city_basic
    utils -.->|Utilities| city_generic
    utils -.->|Utilities| trees_basic
    utils -.->|Utilities| terrain_basic
    
    %% Configuration dependencies
    config --> city_basic
    config --> city_generic
    config --> trees_basic
    config --> terrain_basic
    config --> basepoint_basic
    config --> basepoint_generic
    
    %% Internal dependencies
    city_parser --> city_basic
    city_parser --> city_generic
    
    %% Styling
    classDef externalStyle fill:#cccccc,stroke:#333,stroke-width:2px
    classDef coreStyle fill:#698cbb,stroke:#333,stroke-width:2px,color:#fff
    classDef appStyle fill:#b0c4de,stroke:#333,stroke-width:2px
    
    class ifcopenshell,ifcfactory,numpy,pandas,pydantic,rasterio,pyproj,lxml externalStyle
    class ifc_modelbuilder,geometry,data_models,utils,city_parser,config coreStyle
    class city_basic,city_generic,trees_basic,trees_generic,terrain_basic,terrain_generic,basepoint_basic,basepoint_generic appStyle
```

### Dependencies

- **Red arrows**: Key dependencies (IfcModelBuilder to all applications)
- **Green arrows**: Data model dependencies
- **Blue arrows**: Geometry and utility dependencies

### Project Structure

```
BIMFabrikHH_core/
├── src/
│   └── BIMFabrikHH_core/
│       ├── apps/                    # Application modules
│       │   ├── city/               # City model processing (refactored)
│       │   │   ├── basic/app.py    # CityBasicApp (ifcopenshell.api)
│       │   │   ├── generic/app.py  # CityGenericApp (ifcfactory)
│       │   │   ├── processing.py   # parse_gml_files → List[Building]
│       │   │   ├── _ifc_common.py  # Shared IFC helpers (basepoint)
│       │   │   ├── parser.py       # CityGML streaming parser
│       │   │   └── helpers.py      # City-specific helpers
│       │   ├── trees/              # Tree modeling application
│       │   │   ├── basic/          # Basic tree processing (TreesBasicApp)
│       │   │   ├── generic/        # TreesGenericApp (IFC trees from TreeRecord + psets)
│       │   │   └── processing.py   # DataFrame→records, psets, height, validation
│       │   ├── terrain/            # Digital terrain modeling
│       │   │   ├── basic/          # Record-builder DGM app (TerrainBasicApp, ifcopenshell.api)
│       │   │   ├── generic/        # Record-builder DGM app (TerrainGenericApp, ifcfactory)
│       │   │   ├── _ifc_common.py  # Shared IFC-adjacent helpers (basepoint, psets, bbox)
│       │   │   └── processing.py   # Shared adaptive-sampling mesh helpers
│       │   └── basepoint/          # Basepoint applications
│       │       ├── basic/          # Basic basepoint
│       │       └── generic/        # Generic basepoint
│       ├── core/                   # Core functionality
│       │   ├── model_creator/      # IFC model creation
│       │   │   ├── ifc_modelbuilder.py
│       │   │   ├── ifc_utils.py
│       │   │   ├── ifc_snippets.py
│       │   │   └── pset_utils.py
│       │   ├── geometry/           # Geometry creation (uses ifcfactory)
│       │   │   ├── advanced_objects.py  # Advanced geometry objects
│       │   │   ├── city_furniture.py    # City furniture objects
│       │   │   ├── standard_profiles.py # Standard profiles
│       │   │   ├── tree_objects.py      # Tree geometry objects
│       │   │   └── tree_objects_generic.py  # Generic tree objects
│       │   ├── utils/              # Utility functions
│       │   │   ├── geometry_utils.py    # Geometry utilities
│       │   │   ├── spatial_utils.py     # Spatial utilities
│       │   │   ├── data_utils.py        # Data processing utilities
│       │   │   └── math_operations.py   # Mathematical operations
│       │   ├── georeferencing/     # Georeferencing functionality
│       │   ├── data_processing/    # Data processing
│       │   └── ogc_extractor/      # OGC API integration
│       ├── data_models/            # Pydantic data models
│       └── config/                 # Configuration files
│       ├── data_models/            # Pydantic data models
│       └── config/                 # Configuration files
├── examples/                       # Usage examples
│   └── all_examples.py            # Run all examples
├── tests/                         # Test suite
│   └── examples/                  # Example tests
│       └── test_examples.py      # Automated example testing
├── output/                        # Generated output files
└── docs/                          # Documentation
```

## Usage

### Basic Usage

Each application module provides a simple interface for converting geospatial data to IFC format.

### Configuration

The project uses Pydantic models for configuration and data validation. Key configuration areas include:

- **Bounding Box Parameters**: Define the area of interest
- **Project Information**: Set project metadata
- **Georeferencing**: Configure coordinate systems
- **Property Sets**: Define Hamburg-specific BIM properties

## API Reference

### Core Classes

#### IfcModelBuilder

Handles IFC model creation and structure.

**Methods:**

- `build_project(project_name, site_name, building_name)`: Creates IFC project structure
- `reset_model()`: Resets the current model
- `get_model()`: Returns the current IFC model

#### CityBasicApp

Record-builder city-model app built on ``ifcopenshell.api``. Parses
CityGML/GML/XML tiles into a list of :class:`Building` records and
writes a single IFC LoD1/LoD2 city model, including
``IfcIndexedPolygonalFaceWithVoids`` for LoD2 courtyards.

**Methods:**

- `build_ifc(buildings, *, request_params, ...)`: Build the IFC from
  pre-parsed :class:`Building` records.
- `from_gml_files(gml_files, *, request_params, ...)`: One-shot
  convenience — parses the files (optionally cropped by
  ``request_params.bbox``) and calls :func:`build_ifc`.

Both methods accept an explicit ``basepoint_origin: Optional[Tuple[float,
float]]`` in EPSG:25832. When ``None`` the app falls back to the
``request_params.bbox`` lower-left (reprojected WGS84 → EPSG:25832).

#### CityGenericApp

Same contract as :class:`CityBasicApp`, but built on the
``ifcfactory`` ``BIMFactoryElement`` pipeline
(:class:`MeshRepresentation` wrapped in :class:`Style`). Shorter code
path, O(n) container assignment via ``BIMFactoryElement.build_in``,
and uniform pset handling via :class:`Pset_Objektinformation_CityModel`
/ :class:`Pset_Hyperlink`. LoD2 voids are passed through as nested
ring lists on a best-effort basis; if strict
``IfcIndexedPolygonalFaceWithVoids`` geometry is required, prefer
:class:`CityBasicApp`.

#### CityGMLParser (internal)

Streaming CityGML parser used by :func:`parse_gml_files`. Kept public
for advanced use but most consumers should go through
:class:`CityBasicApp`.

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

### Testing

Run tests using pytest (requires dev dependencies):

```bash
# Install dev dependencies first (includes pytest)
poetry install --with dev

# Run tests
poetry run pytest
```

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

### Module Responsibilities

- **apps/**: Application-specific logic and workflows
- **core/**: Reusable core functionality
- **core/utils/**: Shared utility functions
- **data_models/**: Data validation and configuration
- **config/**: Configuration files

## License

This project is licensed under the GNU Lesser General Public License v2.1 (LGPL-2.1) - see the [LICENSE](LICENSE) file
for details.

**Copyright © 2026 Freie und Hansestadt Hamburg, Landesbetrieb Geoinformation und Vermessung**
**BIM-Leitstelle, Ahmed Salem <ahmed.salem@gv.hamburg.de>**

## Links

- **PyPI**: https://pypi.org/project/bimfabrikhh-core/
- **GitHub**: https://github.com/LGV-BIM-Leitstelle/BIMFabrikHH_core
- **OpenCode**: https://gitlab.opencode.de/LGV-BIM-Leitstelle/bimfabrikhh_core
- **Issues**: https://github.com/LGV-BIM-Leitstelle/BIMFabrikHH_core/issues
- **ifcfactory** (dependency): https://pypi.org/project/ifcfactory/

For support and questions:

- **Email**: ahmed.salem@gv.hamburg.de
- **Project**: Connected Urban Twins (CUT)
- **Organization**: Freie und Hansestadt Hamburg, Landesbetrieb Geoinformation und Vermessung, BIM-Leitstelle

## Acknowledgments

- Freie und Hansestadt Hamburg for project support
- Connected Urban Twins (CUT) project team
- Open source community for dependencies
- IfcOpenShell (Thomas Krijnen) for support

## Roadmap

### Planned Features

- [ ] Support for additional geospatial formats
- [ ] Enhanced geometry optimization
- [ ] Advanced property set management
- [ ] Support for different coordinate systems (CRS transformation)

### Version History

- **v0.1.0**: Initial release with basic functionality
