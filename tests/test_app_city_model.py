from unittest.mock import MagicMock, patch

import pytest

# Import the function to test
from BIMFabrikHH.apps.city_model.app import process_gml_to_ifc


@pytest.fixture
def mock_model_params():
    class MockBBox:
        min_x = 0
        min_y = 0
        max_x = 1
        max_y = 1

    class MockParams:
        bbox = MockBBox()
        containers = []

    return MockParams()


@patch("BIMFabrikHH.apps.city_model.app.CityGMLParser")
@patch("BIMFabrikHH.apps.city_model.app.IfcModelBuilder")
@patch("BIMFabrikHH.apps.city_model.app.bbox_wgs84_to_epsg25832")
@patch("BIMFabrikHH.apps.city_model.app.extract_project_info")
@patch("BIMFabrikHH.apps.city_model.app.extract_psets_basepoint")
@patch("BIMFabrikHH.apps.city_model.app.BasePoint")
@patch("BIMFabrikHH.apps.city_model.app.PathConfig")
@patch("BIMFabrikHH.apps.city_model.app.IfcFileCreator")
@patch("BIMFabrikHH.apps.city_model.app.context")
@patch("BIMFabrikHH.apps.city_model.app.geometry")
@patch("BIMFabrikHH.apps.city_model.app.pset")
@patch("BIMFabrikHH.apps.city_model.app.root")
@patch("BIMFabrikHH.apps.city_model.app.spatial")
def test_process_gml_to_ifc_smoke(
    mock_spatial,
    mock_root,
    mock_pset,
    mock_geometry,
    mock_context,
    mock_ifcfilecreator,
    mock_pathconfig,
    mock_basepoint,
    mock_extract_psets,
    mock_extract_project,
    mock_bbox,
    mock_builder,
    mock_parser,
    mock_model_params,
    tmp_path,
):
    """Simple smoke test to verify the function can be called without errors."""

    # Setup basic mocks
    mock_bbox.return_value = (0, 0, 1, 1)
    mock_extract_project.return_value = ("Project", "Site", "Building")
    mock_extract_psets.return_value = {}

    # Mock parser to return a building
    parser_instance = mock_parser.return_value

    def parse_file_side_effect(*args, **kwargs):
        parser_instance.buildings = {
            "b1": MagicMock(
                vertices=[(0.5, 0.5, 0)], faces=[[0, 0, 0]], id="b1", height=10.0, stories=3, postcode="12345"
            )
        }

    parser_instance.parse_file.side_effect = parse_file_side_effect

    # Mock IFC model and operations
    mock_model = MagicMock()
    mock_model.by_type.return_value = [MagicMock()]
    mock_builder.return_value.get_model.return_value = mock_model
    mock_builder.return_value.build_project.return_value = None

    # Mock IFC contexts
    mock_context.add_context.return_value = MagicMock()

    # Mock IFC entities and operations
    mock_root.create_entity.return_value = MagicMock()
    mock_pset.add_pset.return_value = MagicMock()
    mock_geometry.add_mesh_representation.return_value = MagicMock()

    # Mock file operations
    mock_pathconfig.OUTPUT = tmp_path
    mock_ifcfilecreator.save_ifc_file.return_value = tmp_path / "output_citymodel.ifc"

    # Call the function
    result = process_gml_to_ifc(
        gml_files=["dummy.gml"],
        model_params=mock_model_params,
        reset_model=False,
        folder_path=tmp_path,
        move_to_origin=False,
    )

    # Assert that an output file path is returned
    assert result == tmp_path / "output_citymodel.ifc"
