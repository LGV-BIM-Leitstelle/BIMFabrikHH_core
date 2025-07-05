"""
Unit tests for geometry creation functionality.
"""

from unittest.mock import Mock, patch

import pytest
from BIMFabrikHH.core.geometry_creator import GeometryCreator


class TestGeometryCreator:
    """Test cases for GeometryCreator class."""

    @pytest.fixture
    def mock_model(self):
        """Create a mock IFC model."""
        mock = Mock()
        mock.create_entity.return_value = Mock()
        return mock

    @pytest.fixture
    def geometry_creator(self, mock_model):
        """Create a GeometryCreator instance with mocked dependencies."""
        with patch("BIMFabrikHH.core.geometry_creator.IfcSnippets"), patch(
            "BIMFabrikHH.core.geometry_creator.ShapeBuilder"
        ), patch("BIMFabrikHH.core.geometry_creator.DfParser"):
            creator = GeometryCreator(mock_model)
            creator.builder = Mock()
            creator.ifc_snippets = Mock()
            return creator

    def test_init(self, mock_model):
        """Test GeometryCreator initialization."""
        with patch("BIMFabrikHH.core.geometry_creator.IfcSnippets"), patch(
            "BIMFabrikHH.core.geometry_creator.ShapeBuilder"
        ), patch("BIMFabrikHH.core.geometry_creator.DfParser"):
            creator = GeometryCreator(mock_model)

            assert creator.model == mock_model
            assert creator.idx_element == 0
            assert creator.geometry_creator is None

    def test_create_profile_centered(self, geometry_creator):
        """Test create_profile method with centered alignment."""
        laenge = 10.0
        hoehe = 5.0
        is_centered = True

        result = geometry_creator.create_profile(laenge, hoehe, is_centered)

        # Verify the builder.polyline was called with correct coordinates
        geometry_creator.builder.polyline.assert_called_once()
        call_args = geometry_creator.builder.polyline.call_args[0][0]

        # Check that the polyline starts at -laenge/2 (centered)
        assert call_args[0][0] == -5.0  # start_x = -10.0/2
        assert call_args[0][1] == 0.0  # y coordinate
        assert call_args[0][2] == 0.0  # z coordinate

    def test_create_profile_not_centered(self, geometry_creator):
        """Test create_profile method with non-centered alignment."""
        laenge = 10.0
        hoehe = 5.0
        is_centered = False

        result = geometry_creator.create_profile(laenge, hoehe, is_centered)

        # Verify the builder.polyline was called with correct coordinates
        geometry_creator.builder.polyline.assert_called_once()
        call_args = geometry_creator.builder.polyline.call_args[0][0]

        # Check that the polyline starts at 0.0 (not centered)
        assert call_args[0][0] == 0.0  # start_x = 0.0
        assert call_args[0][1] == 0.0  # y coordinate
        assert call_args[0][2] == 0.0  # z coordinate
