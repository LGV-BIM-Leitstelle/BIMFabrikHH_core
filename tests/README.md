# BIMFabrikHH Testing Guide

## Quick Start

```bash
# Install dependencies
poetry install --with dev

# Run all tests
pytest

# Run with coverage
pytest --cov=BIMFabrikHH --cov-report=html
```

## What to Test

### Priority Order

1. **Core modules** (`src/BIMFabrikHH/core/`) - Unit tests for main logic
2. **Utility functions** (`src/BIMFabrikHH/utils/`) - Simple function tests
3. **Apps** (`src/BIMFabrikHH/apps/`) - Integration tests for workflows

### Test Files

- `test_data_processing.py` - DataProcessor class
- `test_utils.py` - MathTool and utilities
- `test_geometry_creator.py` - Geometry creation (with IFC mocking)

## Writing Tests

### Basic Structure

```python
from BIMFabrikHH.core.data_processing.data_processor import DataProcessor

def test_data_processor_valid_input(self):
    """Test data processing with valid input."""
    # Arrange
    input_data = {"features": [{"id": "1", "geometry": {"type": "Point", "coordinates": [123, 456]}}]}
    
    # Act  
    result = DataProcessor.raw_data_to_dataframe(input_data)
    
    # Assert
    assert len(result) == 1
    assert result.iloc[0]['id'] == "1"
```

### Mocking IFC

```python
from unittest.mock import patch, Mock
from BIMFabrikHH.core.geometry_creator import GeometryCreator

@patch('BIMFabrikHH.core.geometry_creator.ifcopenshell.api.geometry.assign_representation')
def test_geometry_creation(self, mock_assign_geometry):
    """Test geometry creation with mocked IFC."""
    # Arrange
    mock_model = Mock()
    mock_body = Mock()
    creator = GeometryCreator(mock_model)
    
    # Act
    _result = creator.create_extrude(mock_body, "IfcBuildingElementType")
    
    # Assert
    mock_assign_geometry.assert_called_once()
```

## Common Commands

```bash
# Run specific test file
pytest tests/test_data_processing.py

# Run tests verbosely
pytest -v

# Stop on first failure
pytest -x

# Run specific test
pytest tests/test_data_processing.py::TestDataProcessor::test_method_name
``` 