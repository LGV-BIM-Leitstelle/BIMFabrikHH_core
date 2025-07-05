from unittest.mock import MagicMock, patch

import pytest
from BIMFabrikHH.core.ifc_utils import IfcFileCreator


class TestIfcFileCreator:
    """Test cases for IfcFileCreator class."""

    def test_init(self):
        """Test IfcFileCreator initialization."""
        creator = IfcFileCreator()
        assert creator is not None

    @patch("BIMFabrikHH.core.ifc_utils.Path")
    def test_save_ifc_file_success(self, mock_path):
        """Test successful IFC file saving."""
        # Mock IFC model
        mock_model = MagicMock()

        # Mock path operations
        mock_output_path = MagicMock()
        mock_path.return_value = mock_output_path
        mock_output_path.mkdir.return_value = None

        # Test saving
        result = IfcFileCreator.save_ifc_file(mock_model, "test_output.ifc")

        # Verify the file was written
        mock_model.write.assert_called_once()
        assert isinstance(result, MagicMock)

    @patch("BIMFabrikHH.core.ifc_utils.Path")
    def test_save_ifc_file_with_directory_creation(self, mock_path):
        """Test IFC file saving with directory creation."""
        # Mock IFC model
        mock_model = MagicMock()

        # Mock path operations
        mock_output_path = MagicMock()
        mock_path.return_value = mock_output_path
        mock_output_path.mkdir.return_value = None

        # Test saving
        result = IfcFileCreator.save_ifc_file(mock_model, "test_output.ifc")

        # Verify directory was created and file was written
        mock_output_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_model.write.assert_called_once()
        assert isinstance(result, MagicMock)

    @patch("BIMFabrikHH.core.ifc_utils.Path")
    def test_save_ifc_file_io_error(self, mock_path):
        """Test IFC file saving with IO error."""
        # Mock IFC model
        mock_model = MagicMock()

        # Mock path operations to raise error
        mock_output_path = MagicMock()
        mock_path.return_value = mock_output_path
        mock_output_path.mkdir.side_effect = IOError("Permission denied")

        # Test saving should raise IOError
        with pytest.raises(IOError):
            IfcFileCreator.save_ifc_file(mock_model, "test_output.ifc")

    def test_save_ifc_file_invalid_model(self):
        """Test IFC file saving with invalid model."""
        # Test with None model
        with pytest.raises(IOError):
            IfcFileCreator.save_ifc_file(None, "test_output.ifc")

    def test_save_ifc_file_empty_path(self):
        """Test IFC file saving with empty path."""
        # Mock IFC model
        mock_model = MagicMock()

        # Test with empty path
        with pytest.raises(IOError):
            IfcFileCreator.save_ifc_file(mock_model, "")

    @patch("BIMFabrikHH.core.ifc_utils.ifcopenshell.file")
    def test_create_model_success(self, mock_ifcopenshell_file):
        """Test successful IFC model creation."""
        # Mock IFC model
        mock_model = MagicMock()
        mock_ifcopenshell_file.return_value = mock_model

        result = IfcFileCreator.create_model("IFC4")

        # Verify the model was created
        mock_ifcopenshell_file.assert_called_once_with(schema="IFC4")
        assert result == mock_model

    @patch("BIMFabrikHH.core.ifc_utils.ifcopenshell.file")
    def test_create_model_invalid_schema(self, mock_ifcopenshell_file):
        """Test IFC model creation with invalid schema."""
        mock_ifcopenshell_file.side_effect = Exception("Invalid schema")

        with pytest.raises(Exception):
            IfcFileCreator.create_model("INVALID_SCHEMA")

    @patch("BIMFabrikHH.core.ifc_utils.run")
    @patch("BIMFabrikHH.core.ifc_utils.create_entity")
    @patch("BIMFabrikHH.core.ifc_utils.aggregate")
    def test_create_project_success(self, mock_aggregate, mock_create_entity, mock_run):
        """Test successful project creation."""
        # Mock IFC entities
        mock_project = MagicMock(name="project")
        mock_site = MagicMock(name="site")
        mock_building = MagicMock(name="building")

        mock_run.return_value = mock_project
        mock_create_entity.side_effect = [mock_site, mock_building]

        mock_model = MagicMock()

        result = IfcFileCreator.create_project(mock_model, "Test Project", "Test Site", "Test Building")

        # Verify the project was created
        assert len(result) == 3
        assert result[0] == mock_project
        assert result[1] == mock_site
        assert result[2] == mock_building

        # Verify method calls
        mock_run.assert_called_once_with("root.create_entity", mock_model, ifc_class="IfcProject", name="Test Project")
        mock_create_entity.assert_any_call(mock_model, ifc_class="IfcSite", name="Test Site")
        mock_create_entity.assert_any_call(mock_model, ifc_class="IfcBuilding", name="Test Building")
        assert mock_aggregate.assign_object.call_count == 2

    @patch("BIMFabrikHH.core.ifc_utils.run")
    @patch("BIMFabrikHH.core.ifc_utils.create_entity")
    @patch("BIMFabrikHH.core.ifc_utils.aggregate")
    def test_create_project_without_building(self, mock_aggregate, mock_create_entity, mock_run):
        """Test project creation without building."""
        # Mock IFC entities
        mock_project = MagicMock(name="project")
        mock_site = MagicMock(name="site")

        mock_run.return_value = mock_project
        mock_create_entity.return_value = mock_site

        mock_model = MagicMock()

        result = IfcFileCreator.create_project(mock_model, "Test Project", "Test Site", None)

        # Verify the project was created without building
        assert len(result) == 3
        assert result[0] == mock_project
        assert result[1] == mock_site
        assert result[2] is None

        # Verify method calls
        mock_run.assert_called_once_with("root.create_entity", mock_model, ifc_class="IfcProject", name="Test Project")
        mock_create_entity.assert_called_once_with(mock_model, ifc_class="IfcSite", name="Test Site")
        mock_aggregate.assign_object.assert_called_once_with(
            mock_model, products=[mock_site], relating_object=mock_project
        )
