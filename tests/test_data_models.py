import pytest

# Import the data models to test
from BIMFabrikHH.data_models.params_bbox import BoundingBoxParams
from BIMFabrikHH.data_models.params_tree import Component, Container, ModelParams, ProjectInfos, RequestParams
from BIMFabrikHH.data_models.pydantic_georeferencing import GeoreferencingData, ProjectedCRSData
from BIMFabrikHH.data_models.pydantic_psets_BIMHH import (
    Pset_Georeferenzierung,
    Pset_Hyperlink,
    Pset_Modellinformation,
    Pset_Objektinformation,
)
from BIMFabrikHH.data_models.pydantic_psets_tree import Pset_DGM_Tree, Pset_Objektinformation_Tree
from pydantic import ValidationError


class TestBoundingBoxParams:
    """Test cases for BoundingBoxParams model."""

    def test_valid_bbox_params(self):
        """Test valid BoundingBoxParams creation."""
        bbox_data = {"min_x": 9.0, "min_y": 53.5, "max_x": 9.5, "max_y": 53.8}

        bbox = BoundingBoxParams(**bbox_data)

        assert bbox.min_x == 9.0
        assert bbox.min_y == 53.5
        assert bbox.max_x == 9.5
        assert bbox.max_y == 53.8

    def test_bbox_params_invalid_coordinates(self):
        """Test BoundingBoxParams with invalid coordinates."""
        bbox_data = {"min_x": 7.0, "min_y": 53.5, "max_x": 9.5, "max_y": 53.8}  # Below minimum

        with pytest.raises(ValidationError):
            BoundingBoxParams(**bbox_data)

    def test_bbox_params_out_of_range(self):
        """Test BoundingBoxParams with out-of-range coordinates."""
        bbox_data = {"min_x": 9.0, "min_y": 53.5, "max_x": 11.0, "max_y": 53.8}  # Above maximum

        with pytest.raises(ValidationError):
            BoundingBoxParams(**bbox_data)


class TestProjectInfos:
    """Test cases for ProjectInfos model."""

    def test_valid_project_infos(self):
        """Test valid ProjectInfos creation."""
        project_data = {"project_name": "Test Project", "site_name": "Test Site", "building_name": "Test Building"}

        project = ProjectInfos(**project_data)

        assert project.project_name == "Test Project"
        assert project.site_name == "Test Site"
        assert project.building_name == "Test Building"

    def test_project_infos_default_values(self):
        """Test ProjectInfos with default values."""
        project = ProjectInfos()

        assert project.project_name == "IfcProjectName"
        assert project.site_name == "SiteName"
        assert project.building_name == "BuildingName"


class TestModelParams:
    """Test cases for ModelParams model."""

    def test_valid_model_params(self):
        """Test valid ModelParams creation."""
        model_data = {"project_info": ProjectInfos(), "level_of_geom": 2}

        model = ModelParams(**model_data)

        assert model.project_info is not None
        assert model.level_of_geom == 2

    def test_model_params_invalid_level(self):
        """Test ModelParams with invalid level of geometry."""
        model_data = {"level_of_geom": 5}  # Above maximum

        with pytest.raises(ValidationError):
            ModelParams(**model_data)


class TestComponent:
    """Test cases for Component model."""

    def test_valid_component(self):
        """Test valid Component creation."""
        component_data = {"title": "Test Component", "value": "Test Value"}

        component = Component(**component_data)

        assert component.title == "Test Component"
        assert component.value == "Test Value"


class TestContainer:
    """Test cases for Container model."""

    def test_valid_container(self):
        """Test valid Container creation."""
        container_data = {
            "containerTitle": "Test Container",
            "containerId": "test_id",
            "components": {"test": Component()},
        }

        container = Container(**container_data)

        assert container.containerTitle == "Test Container"
        assert container.containerId == "test_id"
        assert container.components is not None


class TestRequestParams:
    """Test cases for RequestParams model."""

    def test_valid_request_params(self):
        """Test valid RequestParams creation."""
        request_data = {
            "bbox": BoundingBoxParams(min_x=9.0, min_y=53.5, max_x=9.5, max_y=53.8),
            "containers": [Container()],
        }

        request = RequestParams(**request_data)

        assert request.bbox is not None
        assert request.containers is not None
        assert len(request.containers) == 1


class TestGeoreferencingData:
    """Test cases for GeoreferencingData model."""

    def test_valid_georeferencing_data(self):
        """Test valid GeoreferencingData creation."""
        geo_data = {
            "Eastings": 3570605.5513,
            "Northings": 5937434.3470,
            "OrthogonalHeight": 10.5,
            "XAxisAbscissa": 0.0,
            "XAxisOrdinate": 0.0,
            "Scale": 1.0,
        }

        geo = GeoreferencingData(**geo_data)

        assert geo.Eastings == 3570605.5513
        assert geo.Northings == 5937434.3470
        assert geo.OrthogonalHeight == 10.5
        assert geo.Scale == 1.0


class TestProjectedCRSData:
    """Test cases for ProjectedCRSData model."""

    def test_valid_projected_crs_data(self):
        """Test valid ProjectedCRSData creation."""
        crs_data = {
            "Name": "EPSG:25832",
            "Description": "UTM zone 32N (ETRS89 / UTM zone 32N)",
            "GeodeticDatum": "ETRS89",
            "VerticalDatum": "DHHN2016",
            "MapProjection": "Transverse Mercator",
            "MapZone": "32",
            "MapUnit": "METRE",
        }

        crs = ProjectedCRSData(**crs_data)

        assert crs.Name == "EPSG:25832"
        assert crs.Description == "UTM zone 32N (ETRS89 / UTM zone 32N)"
        assert crs.GeodeticDatum == "ETRS89"
        assert crs.MapUnit == "METRE"


class TestPsetObjektinformation:
    """Test cases for Pset_Objektinformation model."""

    def test_valid_pset_objektinformation(self):
        """Test valid Pset_Objektinformation creation."""
        pset_data = {"_IDEbene1": "Test Level 1", "_IDEbene2": "Test Level 2", "_IDEbene3": "Test Level 3"}

        pset = Pset_Objektinformation(**pset_data)

        assert pset.idebene1 == "Test Level 1"
        assert pset.idebene2 == "Test Level 2"
        assert pset.idebene3 == "Test Level 3"
        assert pset.pset_name == "Pset_Objektinformation"


class TestPsetModellinformation:
    """Test cases for Pset_Modellinformation model."""

    def test_valid_pset_modellinformation(self):
        """Test valid Pset_Modellinformation creation."""
        pset_data = {
            "_ArtFachmodell": "Ingenieurbau/ Bauwerk",
            "_ArtTeilmodell": "Bruecke",
            "_Auftraggeber": "Test Client",
            "_Ersteller": "Test Creator",
            "_Erstelldatum": "2020-04-24",
            "_GemObjektkatalog": "Allgemein/Master_V004",
            "_Projektname": "Test Project",
            "_Projektnummer": "12345",
        }

        pset = Pset_Modellinformation(**pset_data)

        assert pset.artfachmodell == "Ingenieurbau/ Bauwerk"
        assert pset.artteilmodell == "Bruecke"
        assert pset.auftraggeber == "Test Client"
        assert pset.ersteller == "Test Creator"
        assert pset.erstelldatum == "2020-04-24"
        assert pset.gemobjektkatalog == "Allgemein/Master_V004"
        assert pset.projektname == "Test Project"
        assert pset.projektnummer == "12345"
        assert pset.pset_name == "Pset_Modellinformation"


class TestPsetGeoreferenzierung:
    """Test cases for Pset_Georeferenzierung model."""

    def test_valid_pset_georeferenzierung(self):
        """Test valid Pset_Georeferenzierung creation."""
        pset_data = {
            "_Hoehenstatus": "HS170",
            "_Hoehensystem": "DHHN 16",
            "_Koordinatensystem": "ETRS89-GK",
            "_Lagestatus": "LS320",
        }

        pset = Pset_Georeferenzierung(**pset_data)

        assert pset.hoehenstatus == "HS170"
        assert pset.hoehensystem == "DHHN 16"
        assert pset.koordinatensystem == "ETRS89-GK"
        assert pset.lagestatus == "LS320"
        assert pset.pset_name == "Pset_Georeferenzierung"


class TestPsetHyperlink:
    """Test cases for Pset_Hyperlink model."""

    def test_valid_pset_hyperlink(self):
        """Test valid Pset_Hyperlink creation."""
        pset_data = {
            "_Hyperlink_001": "www.bim.hamburg.de",
            "_Hyperlink_001_Bemerkung": "Link zur Homepage von BIM.Hamburg",
        }

        pset = Pset_Hyperlink(**pset_data)

        assert pset.hyperlink_001 == "www.bim.hamburg.de"
        assert pset.hyperlink_001_Bemerkung == "Link zur Homepage von BIM.Hamburg"
        assert pset.pset_name == "Pset_Hyperlink"


class TestPsetObjektinformationTree:
    """Test cases for Pset_Objektinformation_Tree model."""

    def test_valid_pset_objektinformation_tree(self):
        """Test valid Pset_Objektinformation_Tree creation."""
        pset_data = {
            "baumnummer": "T001",
            "gattung_deutsch": "Eiche",
            "baumid": 12345,
            "art_deutsch": "Stieleiche",
            "sorte_deutsch": "Quercus robur",
            "pflanzjahr": 1990,
            "kronendurchmesser": 15.5,
            "stammumfang": 2.3,
        }

        pset = Pset_Objektinformation_Tree(**pset_data)

        assert pset.baumnummer == "T001"
        assert pset.gattung_deutsch == "Eiche"
        assert pset.baumid == 12345
        assert pset.art_deutsch == "Stieleiche"
        assert pset.sorte_deutsch == "Quercus robur"
        assert pset.pflanzjahr == 1990
        assert pset.kronendurchmesser == 15.5
        assert pset.stammumfang == 2.3
        assert pset.pset_name == "Pset_Objektinformation"


class TestPsetDGMTree:
    """Test cases for Pset_DGM_Tree model."""

    def test_valid_pset_dgm_tree(self):
        """Test valid Pset_DGM_Tree creation."""
        pset_data = {"strasse": "Musterstraße", "stadtteil": "Hamburg-Mitte", "bezirk": "Hamburg"}

        pset = Pset_DGM_Tree(**pset_data)

        assert pset.strasse == "Musterstraße"
        assert pset.stadtteil == "Hamburg-Mitte"
        assert pset.bezirk == "Hamburg"
        assert pset.pset_name == "Pset_DGM"
