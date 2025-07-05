from unittest.mock import MagicMock, patch

import pytest

# Import the classes to test
from BIMFabrikHH.core.ifc_modelbuilder import IfcModelBuilder
from BIMFabrikHH.core.ifc_utils import IfcFileCreator
from BIMFabrikHH.data_models.pydantic_psets_BIMHH import Pset_Hyperlink, Pset_Objektinformation


class TestIfcModelBuilder:
    """Test cases for IfcModelBuilder class."""

    @pytest.fixture
    def builder(self):
        """Fixture to create a fresh IfcModelBuilder instance for each test."""
        return IfcModelBuilder()

    def test_init(self, builder):
        """Test IfcModelBuilder initialization."""
        assert builder is not None
        assert isinstance(builder.ifc_creator, IfcFileCreator)
        assert builder.model is not None
        assert builder.all_psets is None
        assert builder.project is None
        assert builder.site is None
        assert builder.building is None

    def test_reset_model(self, builder):
        """Test model reset functionality."""
        # Set some attributes
        builder.all_psets = ["test"]
        builder.project = MagicMock()
        builder.site = MagicMock()
        builder.building = MagicMock()

        # Reset the model
        builder.reset_model()

        # Verify everything is reset
        assert builder.model is not None  # Should have a new model
        assert builder.all_psets is None
        assert builder.project is None
        assert builder.site is None
        assert builder.building is None

    def test_get_site(self, builder):
        """Test site getter."""
        mock_site = MagicMock()
        builder.site = mock_site
        assert builder.get_site() == mock_site

    def test_get_building(self, builder):
        """Test building getter."""
        mock_building = MagicMock()
        builder.building = mock_building
        assert builder.get_building() == mock_building

    def test_get_model(self, builder):
        """Test model getter."""
        assert builder.get_model() is not None
        assert builder.get_model() == builder.model

    def test_initialize_psets(self, builder):
        """Test property set initialization."""
        test_data1 = {
            "_IDEbene1": "Test Level 1",
            "_IDEbene2": "Test Level 2",
            "_IDEbene3": "Test Level 3",
            "pset_name": "Test1",
        }
        test_data2 = {
            "_Hyperlink_001": "http://test.com",
            "_Hyperlink_001_Bemerkung": "Test Link",
            "pset_name": "Test2",
        }

        psets = builder._initialize_psets(Pset_Objektinformation, test_data1, Pset_Hyperlink, test_data2)

        assert len(psets) == 2
        assert isinstance(psets[0], Pset_Objektinformation)
        assert isinstance(psets[1], Pset_Hyperlink)
        assert psets[0].idebene1 == "Test Level 1"
        assert psets[0].idebene2 == "Test Level 2"
        assert psets[0].idebene3 == "Test Level 3"
        assert psets[1].hyperlink_001 == "http://test.com"
        assert psets[1].hyperlink_001_Bemerkung == "Test Link"

    @patch.object(IfcFileCreator, "create_project")
    @patch.object(IfcFileCreator, "create_units_meter")
    @patch.object(IfcFileCreator, "create_representations")
    def test_build_project_success(self, mock_create_representations, mock_create_units, mock_create_project, builder):
        """Test successful project building."""
        # Setup mocks
        mock_project = MagicMock(name="project")
        mock_site = MagicMock(name="site")
        mock_building = MagicMock(name="building")
        mock_create_project.return_value = (mock_project, mock_site, mock_building)

        mock_model3d = MagicMock(name="model3d")
        mock_plan = MagicMock(name="plan")
        mock_body = MagicMock(name="body")
        mock_create_representations.return_value = (mock_model3d, mock_plan, mock_body)

        # Call the method
        builder.build_project("Test Project", "Test Site", "Test Building")

        # Verify the results
        assert builder.project == mock_project
        assert builder.site == mock_site
        assert builder.building == mock_building
        assert builder.model3d == mock_model3d
        assert builder.plan == mock_plan
        assert builder.body == mock_body

        # Verify method calls
        mock_create_project.assert_called_once_with(builder.model, "Test Project", "Test Site", "Test Building")
        mock_create_units.assert_called_once_with(builder.model)
        mock_create_representations.assert_called_once_with(builder.model)

    @patch.object(IfcFileCreator, "create_project")
    def test_build_project_error(self, mock_create_project, builder):
        """Test project building with error."""
        mock_create_project.side_effect = Exception("Test error")

        with pytest.raises(Exception) as exc_info:
            builder.build_project("Test Project", "Test Site", "Test Building")

        assert str(exc_info.value) == "Test error"

    def test_setup_psets(self, builder):
        """Test property set setup."""
        builder.setup_psets()

        assert builder.pset_classes is not None
        assert len(builder.pset_classes) == 2  # Should have 2 psets based on current implementation
        assert all(hasattr(pset, "pset_name") for pset in builder.pset_classes)
        assert builder.all_psets is not None
        assert len(builder.all_psets) == 2

    @patch.object(IfcFileCreator, "create_georeference")
    @patch.object(IfcFileCreator, "edit_georeference")
    def test_combine_georeferencing(self, mock_edit_georeference, mock_create_georeference, builder):
        """Test georeferencing combination."""
        builder.combine_georeferencing()

        mock_create_georeference.assert_called_once_with(builder.model)
        mock_edit_georeference.assert_called_once_with(builder.model)
