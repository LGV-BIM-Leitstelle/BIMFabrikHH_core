import datetime
from typing import ClassVar, Optional

import pytest
from ifcfactory import PropertySetTemplate, ureg
from ifcfactory._internal.pset_base import Length, Quantity
from pydantic import Field, ValidationError

# Import the data models to test
from BIMFabrikHH_core.core.geometry import basepoint_pset_values
from BIMFabrikHH_core.core.model_creator import psets_to_wire
from BIMFabrikHH_core.data_models.params_bbox import BoundingBoxParams
from BIMFabrikHH_core.data_models.params_tree import Component, Container, ModelParams, ProjectInfos, RequestParams
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateOperation, CoordinateSystem
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import (
    Nullpunktobjekt,
    Pset_Georeferenzierung,
    Pset_Hyperlink,
    Pset_Modellinformation,
    Pset_Objektinformation,
)
from BIMFabrikHH_core.data_models.pydantic_psets_tree import Pset_Bauwerk_Tree, Pset_Objektinformation_Tree


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


class TestCoordinateOperation:
    """Test cases for CoordinateOperation model."""

    def test_valid_coordinate_operation(self):
        """Test valid CoordinateOperation creation."""
        geo_data = {
            "eastings": 3570605.5513,
            "northings": 5937434.3470,
            "orthogonal_height": 10.5,
            "x_axis_abscissa": 1.0,
            "x_axis_ordinate": 0.0,
            "scale": 1.0,
        }

        geo = CoordinateOperation(**geo_data)

        assert geo.eastings == 3570605.5513
        assert geo.northings == 5937434.3470
        assert geo.orthogonal_height == 10.5
        assert geo.scale == 1.0

    def test_rejects_zero_x_axis_direction(self):
        with pytest.raises(ValidationError, match="x-axis direction cannot be the zero vector"):
            CoordinateOperation(x_axis_abscissa=0.0, x_axis_ordinate=0.0)

    @pytest.mark.parametrize("scale", [0.0, -1.0])
    def test_rejects_non_positive_scale(self, scale):
        with pytest.raises(ValidationError, match="scale must be greater than zero"):
            CoordinateOperation(scale=scale)

    def test_validates_assignment(self):
        operation = CoordinateOperation()

        with pytest.raises(ValidationError, match="x-axis direction cannot be the zero vector"):
            operation.x_axis_abscissa = 0.0


class TestCoordinateSystem:
    """Test cases for CoordinateSystem model."""

    def test_valid_coordinate_system(self):
        """Test valid CoordinateSystem creation."""
        crs_data = {
            "name": "EPSG:25832",
            "description": "UTM zone 32N (ETRS89 / UTM zone 32N)",
            "geodetic_datum": "ETRS89",
            "vertical_datum": "DHHN2016",
            "map_projection": "Transverse Mercator",
            "map_zone": "32",
        }

        crs = CoordinateSystem(**crs_data)

        assert crs.name == "EPSG:25832"
        assert crs.description == "UTM zone 32N (ETRS89 / UTM zone 32N)"
        assert crs.geodetic_datum == "ETRS89"
        assert crs.vertical_datum == "DHHN2016"


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

    def test_idebenen_are_required(self):
        with pytest.raises(ValidationError):
            Pset_Objektinformation()


class TestNullpunktobjekt:
    def test_objektinformation_and_hyperlink_are_fixed(self):
        objektinformation, hyperlink = Nullpunktobjekt().psets()

        assert (objektinformation.idebene1, objektinformation.idebene2, objektinformation.idebene3) == (
            "Nullpunktobjekt",
            "Nullpunktobjekt",
            "Nullpunktobjekt",
        )
        assert (hyperlink.hyperlink_001, hyperlink.hyperlink_001_bemerkung) == (
            "www.bim.hamburg.de",
            "Link zur Homepage von BIM.Hamburg",
        )

    def test_psets_keep_the_ifc_order(self):
        georeferenzierung = Pset_Georeferenzierung(
            hoehenstatus="HS170", hoehensystem="DHHN2016", koordinatensystem="ETRS89-UTM32N", lagestatus="LS310"
        )
        psets = Nullpunktobjekt(pset_georeferenzierung=georeferenzierung).psets()

        assert [pset.pset_name for pset in psets] == [
            "Pset_Objektinformation",
            "Pset_Georeferenzierung",
            "Pset_Hyperlink",
        ]


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
        assert pset.erstelldatum == datetime.date(2020, 4, 24)
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
        assert pset.hyperlink_001_bemerkung == "Link zur Homepage von BIM.Hamburg"
        assert pset.pset_name == "Pset_Hyperlink"

    def test_default_bemerkung(self):
        assert Pset_Hyperlink().hyperlink_001_bemerkung == "Link zur Homepage von BIM.Hamburg"

    def test_accepts_lowercase_bemerkung_title(self):
        pset = Pset_Hyperlink(**{"_Hyperlink_001_bemerkung": "Eigener Text"})

        assert pset.hyperlink_001_bemerkung == "Eigener Text"
        assert pset.model_dump(by_alias=True)["_Hyperlink_001_Bemerkung"] == "Eigener Text"


NULLPUNKT_FIXED_PSETS = {
    "Pset_Objektinformation": {
        "_IDEbene1": "Nullpunktobjekt",
        "_IDEbene2": "Nullpunktobjekt",
        "_IDEbene3": "Nullpunktobjekt",
    },
    "Pset_Hyperlink": {
        "_Hyperlink_001": "www.bim.hamburg.de",
        "_Hyperlink_001_Bemerkung": "Link zur Homepage von BIM.Hamburg",
    },
}


class TestBasepointPsetValues:
    """``basepoint_pset_values`` gives the Rust writers the Python Nullpunktobjekt values."""

    def test_none_and_empty_give_the_fixed_psets(self):
        assert basepoint_pset_values(None) == NULLPUNKT_FIXED_PSETS
        assert basepoint_pset_values({}) == NULLPUNKT_FIXED_PSETS

    def test_sent_fixed_psets_are_ignored_and_unknown_psets_dropped(self):
        values = basepoint_pset_values(
            {
                "Pset_Objektinformation": {"_IDEbene1": "A", "_IDEbene2": "B", "_IDEbene3": "C"},
                "Pset_Hyperlink": {"_Hyperlink_001": "https://bim.hamburg.de", "_Hyperlink_001_bemerkung": "Text"},
                "Pset_Unbekannt": {"a": 1},
            }
        )
        assert values == NULLPUNKT_FIXED_PSETS

    def test_sent_psets_are_taken_by_alias(self):
        values = basepoint_pset_values(
            {
                "Pset_Georeferenzierung": {
                    "hoehenstatus": "HS170",
                    "_Hoehensystem": "DHHN2016",
                    "_Koordinatensystem": "ETRS89-UTM32N",
                    "lagestatus": "LS310",
                }
            }
        )
        assert values["Pset_Georeferenzierung"] == {
            "_Hoehenstatus": "HS170",
            "_Hoehensystem": "DHHN2016",
            "_Koordinatensystem": "ETRS89-UTM32N",
            "_Lagestatus": "LS310",
        }


class TestPsetsToWire:
    """``psets_to_wire`` types values the way ifcfactory writes them."""

    def test_python_types_dates_and_quantities(self):
        class Pset_Test(PropertySetTemplate):
            pset_name: ClassVar[str] = "Pset_Test"
            jahr: int = Field(serialization_alias="_Jahr")
            hoehe: float = Field(serialization_alias="_Hoehe")
            durchmesser: Quantity[Length] = Field(serialization_alias="_Durchmesser")
            datum: datetime.date = Field(serialization_alias="_Datum")
            nummer: str = Field(serialization_alias="_Nummer")
            leer: Optional[str] = Field(default=None, serialization_alias="_Leer")

        pset = Pset_Test(
            jahr=1990, hoehe=3.0, durchmesser=50 * ureg.centimeter, datum=datetime.date(2026, 9, 12), nummer="001"
        )
        assert psets_to_wire([pset]) == {
            "Pset_Test": {
                "_Jahr": 1990,
                "_Hoehe": 3.0,
                "_Durchmesser": {"ifc_type": "IfcLengthMeasure", "value": 0.5},
                "_Datum": "2026-09-12",
                "_Nummer": "001",
            }
        }


class TestPsetObjektinformationTree:
    """Test cases for Pset_Objektinformation_Tree model."""

    def test_valid_pset_objektinformation_tree(self):
        """Test valid Pset_Objektinformation_Tree creation."""
        pset_data = {
            "baumnummer": "T001",
            "gattung_deutsch": "Eiche",
            "pflanzjahr": 1990,
            "kronendurchmesser": ureg.Quantity(15.5, "meter"),
        }

        pset = Pset_Objektinformation_Tree(**pset_data)

        assert pset.baumnummer == "T001"
        assert pset.gattung_deutsch == "Eiche"
        assert pset.pflanzjahr == 1990
        assert pset.kronendurchmesser.magnitude == 15.5
        assert pset.pset_name == "Pset_Objektinformation"


class TestPsetBauwerkTree:
    """Test cases for Pset_Bauwerk_Tree model."""

    def test_valid_pset_bauwerk_tree(self):
        """Test valid Pset_Bauwerk_Tree creation."""
        pset_data = {"strassenname": "Musterstraße"}

        pset = Pset_Bauwerk_Tree(**pset_data)

        assert pset.strassenname == "Musterstraße"
        assert pset.pset_name == "Pset_Bauwerk"
