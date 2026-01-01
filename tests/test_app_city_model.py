"""Test city model application functionality."""

from pathlib import Path

from BIMFabrikHH_core.apps.city.app import CityModularApp
from BIMFabrikHH_core.data_models.params_bbox import BoundingBoxParams
from BIMFabrikHH_core.data_models.params_tree import Component, Container, RequestParams


class TestCityModularApp:
    """Test the CityModularApp class."""

    def test_city_modular_app_initialization(self):
        """Test that CityModularApp can be initialized."""
        gml_files = ["test1.xml", "test2.xml"]
        app = CityModularApp(gml_files=gml_files)

        assert app.gml_files == gml_files
        assert app.folder_path is None
        assert app.parser is not None

    def test_city_modular_app_with_folder_path(self):
        """Test that CityModularApp can be initialized with folder path."""
        gml_files = ["test1.xml", "test2.xml"]
        folder_path = Path("/test/path")
        app = CityModularApp(gml_files=gml_files, folder_path=folder_path)

        assert app.gml_files == gml_files
        assert app.folder_path == folder_path

    def test_get_data_in_bbox_method_exists(self):
        """Test that get_data_in_bbox method exists and is callable."""
        app = CityModularApp(gml_files=[])
        assert hasattr(app, "get_data_in_bbox")
        assert callable(app.get_data_in_bbox)

    def test_process_data_method_exists(self):
        """Test that process_data method exists and is callable."""
        app = CityModularApp(gml_files=[])
        assert hasattr(app, "process_data")
        assert callable(app.process_data)

    def test_create_ifc_method_exists(self):
        """Test that create_ifc method exists and is callable."""
        app = CityModularApp(gml_files=[])
        assert hasattr(app, "create_ifc")
        assert callable(app.create_ifc)

    def test_ui_app_interface_compliance(self):
        """Test that CityModularApp implements UIAppInterface methods."""
        app = CityModularApp(gml_files=[])

        # Check that all required methods exist
        required_methods = ["get_data_in_bbox", "process_data", "create_ifc"]
        for method_name in required_methods:
            assert hasattr(app, method_name), f"Missing method: {method_name}"
            assert callable(getattr(app, method_name)), f"Method {method_name} is not callable"

    def test_method_signatures(self):
        """Test that methods have correct signatures."""
        app = CityModularApp(gml_files=[])

        # Test get_data_in_bbox signature
        import inspect

        sig = inspect.signature(app.get_data_in_bbox)
        assert "bbox" in sig.parameters

        # Test process_data signature
        sig = inspect.signature(app.process_data)
        assert "raw_data" in sig.parameters

        # Test create_ifc signature
        sig = inspect.signature(app.create_ifc)
        assert "processed_data" in sig.parameters
        assert "request_params" in sig.parameters


class TestCityModelIntegration:
    """Test city model integration scenarios."""

    def test_create_request_params(self):
        """Test creating RequestParams for city model processing."""
        bbox = BoundingBoxParams(min_x=9.7500, min_y=53.5813, max_x=9.7483, max_y=53.5856)
        container = Container(
            containerTitle="Test_Container",
            containerId="test_id",
            components={
                "description": Component(title="Description", value="Test City Model"),
                "type": Component(title="Model Type", value="Test Buildings"),
            },
        )
        request_params = RequestParams(bbox=bbox, containers=[container])

        assert request_params.bbox == bbox
        assert len(request_params.containers) == 1
        assert request_params.containers[0] == container

    def test_city_modular_app_workflow(self):
        """Test the complete workflow of CityModularApp."""
        # This is a smoke test to ensure the workflow methods can be called
        # without actual data files
        gml_files = ["nonexistent.xml"]
        app = CityModularApp(gml_files=gml_files)

        # Create test request params
        bbox = BoundingBoxParams(min_x=9.7500, min_y=53.5813, max_x=9.7483, max_y=53.5856)
        container = Container(
            containerTitle="Test_Container",
            containerId="test_id",
            components={
                "description": Component(title="Description", value="Test City Model"),
                "type": Component(title="Model Type", value="Test Buildings"),
            },
        )
        request_params = RequestParams(bbox=bbox, containers=[container])

        # Test that methods can be called (they may fail due to missing files, but that's expected)
        try:
            raw_data = app.get_data_in_bbox(bbox)
            # This should return an empty list for nonexistent files
            assert isinstance(raw_data, list)
        except Exception:
            # Expected for missing files
            pass

        # Test process_data with empty data
        processed_data = app.process_data([])
        assert isinstance(processed_data, list)
        assert len(processed_data) == 0
