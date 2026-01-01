from unittest.mock import MagicMock, patch

import pytest

from BIMFabrikHH_core.core.model_creator.ifc_utils import IfcModelMethods


class TestIfcModelMethods:
    """Test cases for IfcModelMethods class."""

    def test_init(self):
        """Test IfcModelMethods initialization."""
        creator = IfcModelMethods()
        assert creator is not None

    @patch("BIMFabrikHH.core.model_creator.ifc_utils.ifcopenshell.file")
    def test_create_model_success(self, mock_ifcopenshell_file):
        """Test successful IFC model creation."""
        # Mock IFC model
        mock_model = MagicMock()
        mock_ifcopenshell_file.return_value = mock_model

        result = IfcModelMethods.create_model("IFC4")

        # Verify the model was created
        mock_ifcopenshell_file.assert_called_once_with(schema="IFC4")
        assert result == mock_model

    @patch("BIMFabrikHH.core.model_creator.ifc_utils.ifcopenshell.file")
    def test_create_model_invalid_schema(self, mock_ifcopenshell_file):
        """Test IFC model creation with invalid schema."""
        mock_ifcopenshell_file.side_effect = Exception("Invalid schema")

        with pytest.raises(Exception):
            IfcModelMethods.create_model("INVALID_SCHEMA")

    @patch("BIMFabrikHH.core.model_creator.ifc_utils.run")
    def test_create_project_entity_success(self, mock_run):
        """Test successful project entity creation."""
        # Mock IFC project
        mock_project = MagicMock(name="project")
        mock_run.return_value = mock_project

        mock_model = MagicMock()

        result = IfcModelMethods.create_project_entity(mock_model, "Test Project")

        # Verify the project was created
        assert result == mock_project

        # Verify method calls
        mock_run.assert_called_once_with("root.create_entity", mock_model, ifc_class="IfcProject", name="Test Project")

    @patch("BIMFabrikHH.core.model_creator.ifc_utils.create_entity")
    @patch("BIMFabrikHH.core.model_creator.ifc_utils.aggregate")
    def test_create_site_success(self, mock_aggregate, mock_create_entity):
        """Test successful site creation."""
        # Mock IFC entities
        mock_site = MagicMock(name="site")
        mock_project = MagicMock(name="project")
        mock_create_entity.return_value = mock_site

        mock_model = MagicMock()

        result = IfcModelMethods.create_site(mock_model, "Test Site", mock_project)

        # Verify the site was created
        assert result == mock_site

        # Verify method calls
        mock_create_entity.assert_called_once_with(mock_model, ifc_class="IfcSite", name="Test Site")
        mock_aggregate.assign_object.assert_called_once_with(
            mock_model, products=[mock_site], relating_object=mock_project
        )
