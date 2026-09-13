from unittest.mock import MagicMock, patch

import pytest

# Import the classes to test
from BIMFabrikHH_core.core.model_creator import IfcModelBuilder, IfcModelMethods
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import Pset_Hyperlink, Pset_Objektinformation


class TestIfcModelBuilder:
    """Test cases for IfcModelBuilder class."""

    @pytest.fixture
    def builder(self):
        """
        Fixture to create a fresh IfcModelBuilder instance for each test.

        Returns:
            IfcModelBuilder: A new instance of IfcModelBuilder for testing.
        """
        return IfcModelBuilder()

    def test_init(self, builder):
        """
        Test IfcModelBuilder initialization.

        Verifies that all required components are properly initialized:
        - ifc_creator is an instance of IfcModelMethods
        - model is created and not None
        - all optional attributes start as None
        """
        assert builder is not None
        assert isinstance(builder.ifc_creator, IfcModelMethods)
        assert builder.model is not None
        assert builder.all_psets is None
        assert builder.project is None
        assert builder.site is None
        assert builder.building is None

    def test_reset_model(self, builder):
        """
        Test model reset functionality.

        Verifies that calling reset_model() properly clears all model-related
        attributes and creates a fresh model instance while preserving
        the ifc_creator and logger instances.
        """
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

    def test_site_attribute(self, builder):
        """
        Test site attribute access.

        Verifies that the site attribute can be set and retrieved correctly.
        """
        mock_site = MagicMock()
        builder.site = mock_site
        assert builder.site == mock_site

    def test_building_attribute(self, builder):
        """
        Test building attribute access.

        Verifies that the building attribute can be set and retrieved correctly.
        """
        mock_building = MagicMock()
        builder.building = mock_building
        assert builder.building == mock_building

    def test_model_attribute(self, builder):
        """
        Test model attribute access.

        Verifies that the model attribute is properly initialized and accessible.
        """
        assert builder.model is not None
        assert builder.model == builder.model

    def test_initialize_psets(self, builder):
        """
        Test property set initialization with multiple Pydantic models.

        Verifies that the _initialize_psets method correctly creates property set
        objects from raw data using Pydantic models for validation and type conversion.
        Tests both Objektinformation and Hyperlink property sets.
        """
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
        assert psets[1].hyperlink_001_bemerkung == "Test Link"

    @patch.object(IfcModelMethods, "edit_georeference")
    @patch.object(IfcModelMethods, "create_georeference")
    @patch.object(IfcModelMethods, "create_contexts")
    @patch.object(IfcModelMethods, "create_building")
    @patch.object(IfcModelMethods, "create_site")
    @patch.object(IfcModelMethods, "create_project_entity")
    @patch.object(IfcModelMethods, "create_units_meter")
    @patch.object(IfcModelMethods, "create_model")
    @patch.object(IfcModelMethods, "create_storey")
    def test_build_project_success(
        self,
        mock_create_storey,
        mock_create_model,
        mock_create_units,
        mock_create_project_entity,
        mock_create_site,
        mock_create_building,
        mock_create_contexts,
        mock_create_georeference,
        mock_edit_georeference,
        builder,
    ):
        # Setup all mocks
        mock_project = MagicMock(name="project")
        mock_site = MagicMock(name="site")
        mock_building = MagicMock(name="building")
        mock_storey = MagicMock(name="storey")
        mock_model = MagicMock(name="model")
        mock_model3d = MagicMock(name="model3d")
        mock_plan = MagicMock(name="plan")
        mock_body = MagicMock(name="body")

        # Configure return values
        mock_create_project_entity.return_value = mock_project
        mock_create_site.return_value = mock_site
        mock_create_building.return_value = mock_building
        mock_create_storey.return_value = mock_storey
        mock_create_model.return_value = mock_model
        mock_create_contexts.return_value = (mock_model3d, mock_plan, mock_body)

        builder.model = mock_model

        from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates

        coordinate_system = CoordinateSystemTemplates.epsg_25832()
        coordinate_operation = CoordinateSystemTemplates.get_default_coordinate_operation()

        builder.build_project(
            project_name="Test Project",
            coordinate_system=coordinate_system,
            coordinate_operation=coordinate_operation,
            site_name="Test Site",
            building_name="Test Building",
            storey_name="Test Storey",
        )

        # Verify all calls were made
        mock_create_project_entity.assert_called_once_with(mock_model, "Test Project")
        mock_create_units.assert_called_once_with(mock_model)
        mock_create_site.assert_called_once_with(mock_model, "Test Site", mock_project)
        mock_create_building.assert_called_once_with(mock_model, "Test Building", mock_site)
        mock_create_storey.assert_called_once_with(mock_model, "Test Storey", mock_building)
        mock_create_contexts.assert_called_once_with(mock_model)
        mock_create_georeference.assert_called_once_with(mock_model)
        mock_edit_georeference.assert_called_once_with(mock_model, coordinate_system, coordinate_operation)
        assert builder.project == mock_project
        assert builder.site == mock_site
        assert builder.building == mock_building
        assert builder.model3d == mock_model3d
        assert builder.plan == mock_plan
        assert builder.body == mock_body

    @patch.object(IfcModelMethods, "create_project_entity")
    def test_build_project_error(self, mock_create_project_entity, builder):
        """
        Test project building with error handling.

        Verifies that exceptions during project creation are properly propagated
        and not silently caught, ensuring that build failures are visible to
        the calling code.
        """
        mock_create_project_entity.side_effect = Exception("Test error")

        with pytest.raises(Exception) as exc_info:
            # Provide a valid coordinate_operation for the test
            from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates

            coordinate_system = CoordinateSystemTemplates.epsg_25832()
            coordinate_operation = CoordinateSystemTemplates.get_default_coordinate_operation()
            builder.build_project("Test Project", coordinate_system, coordinate_operation)

        assert str(exc_info.value) == "Test error"

    @patch.object(IfcModelMethods, "create_georeference")
    @patch.object(IfcModelMethods, "edit_georeference")
    def test_georeferencing_in_build_project(self, mock_edit_georeference, mock_create_georeference, builder):
        """
        Test georeferencing workflow in build_project method.

        Verifies that build_project() correctly calls both the creation
        and editing of georeferencing information in the proper sequence:
        1. First creates basic georeferencing
        2. Then edits it with specific coordinate system settings
        """
        from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates

        coordinate_system = CoordinateSystemTemplates.epsg_25832()
        coordinate_operation = CoordinateSystemTemplates.get_default_coordinate_operation()
        builder.build_project(
            "Test Project", coordinate_system, coordinate_operation, "Test Site", "Test Building", "Test Storey"
        )

        mock_create_georeference.assert_called_once_with(builder.model)
        mock_edit_georeference.assert_called_once_with(builder.model, coordinate_system, coordinate_operation)
