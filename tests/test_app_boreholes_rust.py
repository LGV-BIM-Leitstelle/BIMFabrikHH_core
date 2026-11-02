"""Tests for :class:`BoreholesRustApp` (the IFC write needs ``bimfabrikhh_core_rs``)."""

from __future__ import annotations

from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element
import pytest

from BIMFabrikHH_core.apps.boreholes.generic_rust.app import BoreholesRustApp, _solids
from BIMFabrikHH_core.data_models.boreholes import BoreholeLayer, BoreholeRecord, BoreholeWater
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import Pset_Hyperlink
from BIMFabrikHH_core.data_models.pydantic_psets_boreholes import Pset_Aufschluss_Borehole

pytest.importorskip("bimfabrikhh_core_rs")


def _layer(**overrides) -> BoreholeLayer:
    data = dict(
        layer_id="BDHH_TEST1_1",
        from_depth=0.0,
        to_depth=1.2,
        upper_height=14.3,
        lower_height=13.1,
        thickness=1.2,
        din_color_name="orange",
        visual_rgb=(255, 128, 0),
    )
    data.update(overrides)
    return BoreholeLayer(**data)


def _record(**overrides) -> BoreholeRecord:
    data = dict(
        borehole_id="BDHH_TEST1",
        archive_id="44372",
        aufschlussbezeichnung="B.45",
        easting=565084.16,
        northing=5934034.654,
        ansatzhoehe_nn=14.3,
        groundwater=None,
        layers=[_layer()],
        psets={"Pset_Aufschluss": Pset_Aufschluss_Borehole(aufschlussnummer="B.45")},
    )
    data.update(overrides)
    return BoreholeRecord(**data)


def test_empty_records_returns_none() -> None:
    assert BoreholesRustApp.build_ifc([]) is None


def test_records_without_layers_return_none() -> None:
    record = _record(layers=[], groundwater=BoreholeWater(entry_depth=2.0))
    assert BoreholesRustApp.build_ifc([record]) is None


def test_solids_group_layers_and_groundwater_of_one_borehole() -> None:
    record = _record(
        layers=[_layer(), _layer(layer_id="BDHH_TEST1_2", lower_height=11.9, thickness=1.2)],
        groundwater=BoreholeWater(entry_depth=3.0),
    )
    solids = _solids(
        [record],
        cylinder_radius_m=0.5,
        water_square_length=3.0,
        color=None,
        transparency=0.0,
        include_property_sets=True,
        hyperlink_override=None,
    )
    assert [solid["kind"] if "kind" in solid else "cylinder" for solid in solids] == [
        "cylinder",
        "cylinder",
        "square",
    ]
    assert {solid["borehole"] for solid in solids} == {"BDHH_TEST1"}
    assert {solid["borehole_name"] for solid in solids} == {"B.45"}
    assert solids[0]["name"] == "B.45_BDHH_TEST1_1"
    assert solids[0]["position"] == (565084.16, 5934034.654, 13.1)
    assert solids[0]["height"] == 1.2
    assert solids[0]["color"] == (255, 128, 0)
    assert solids[0]["layer"] == "_Bodenaufschluesse_orange"
    assert solids[0]["psets"]["Pset_Aufschluss"]["_Aufschlussnummer"] == "B.45"
    assert solids[2]["name"] == "B.45_BDHH_TEST1_Grundwasser"
    assert solids[2]["position"][2] == pytest.approx(11.3)
    assert solids[2]["size"] == 3.0


def test_color_override_and_hyperlink_replacement() -> None:
    record = _record()
    solids = _solids(
        [record],
        cylinder_radius_m=0.4,
        water_square_length=3.0,
        color=(1, 2, 3),
        transparency=0.2,
        include_property_sets=True,
        hyperlink_override=Pset_Hyperlink(hyperlink_001="https://example.test"),
    )
    assert solids[0]["color"] == (1, 2, 3)
    assert solids[0]["transparency"] == 0.2
    assert solids[0]["radius"] == 0.4
    assert solids[0]["psets"]["Pset_Hyperlink"]["_Hyperlink_001"] == "https://example.test"


def test_without_property_sets_the_dicts_carry_none() -> None:
    solids = _solids(
        [_record()],
        cylinder_radius_m=0.5,
        water_square_length=3.0,
        color=None,
        transparency=0.0,
        include_property_sets=False,
        hyperlink_override=None,
    )
    assert solids[0]["psets"] == {}


def test_writes_one_assembly_per_borehole(tmp_path: Path) -> None:
    second = _record(
        borehole_id="BDHH_TEST2",
        aufschlussbezeichnung="B.46",
        layers=[_layer(layer_id="BDHH_TEST2_1", din_color_name="gelb")],
    )
    dest = tmp_path / "boreholes.ifc"
    written = BoreholesRustApp.build_ifc([_record(), second], output_path=dest, source_epsg=25832)
    assert written == dest

    model = ifcopenshell.open(str(dest))
    assemblies = {assembly.Name: assembly for assembly in model.by_type("IfcElementAssembly")}
    assert sorted(assemblies) == ["B.45", "B.46"]
    assert {assembly.ObjectType for assembly in assemblies.values()} == {"Bohrung"}

    proxies = {proxy.Name: proxy for proxy in model.by_type("IfcBuildingElementProxy")}
    assert "B.45_BDHH_TEST1_1" in proxies
    assert "B.46_BDHH_TEST2_1" in proxies
    part = proxies["B.45_BDHH_TEST1_1"]
    assert ifcopenshell.util.element.get_psets(part)["Pset_Aufschluss"]["_Aufschlussnummer"] == "B.45"
    assert ifcopenshell.util.element.get_psets(assemblies["B.45"])["Pset_Aufschluss"]["_Aufschlussnummer"] == "B.45"
    layers = {layer.Name for layer in ifcopenshell.util.element.get_layers(model, part)}
    assert "_Bodenaufschluesse_orange" in layers
    assert "25832" in dest.read_text()
