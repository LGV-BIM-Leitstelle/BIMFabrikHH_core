"""Tests for reading the project information of the workflow form."""

from __future__ import annotations

from BIMFabrikHH_core.core.ogc_extractor import extract_project_info
from BIMFabrikHH_core.data_models.params_tree import Component, Container


def _project_info(**titles_and_values: str) -> Container:
    return Container(
        containerId="Projektinformationen",
        containerTitle="Projektinformationen",
        components={title.lower(): Component(title=title, value=value) for title, value in titles_and_values.items()},
    )


def test_project_site_and_building_names_are_read_from_their_ifc_titles() -> None:
    containers = [_project_info(IfcProject="Elbbrücke", IfcSite="Wilhelmsburg", IfcBuilding="Brücke")]

    assert extract_project_info(containers) == ("Elbbrücke", "Wilhelmsburg", "Brücke")


def test_empty_project_information_keeps_the_defaults() -> None:
    assert extract_project_info([_project_info(IfcProject="")]) == ("IfcProjectName", "SiteName", "BuildingName")
