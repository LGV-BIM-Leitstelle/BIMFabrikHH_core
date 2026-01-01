from __future__ import annotations

import datetime

from ifcfactory import Material

from BIMFabrikHH_core.core.geometry import ProjectBasePointNorthMesh
from BIMFabrikHH_core.core.model_creator import IfcModelBuilder
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import (
    Pset_Georeferenzierung,
    Pset_Hyperlink,
    Pset_Modellinformation,
    Pset_Objektinformation,
)

if __name__ == "__main__":
    model_builder = IfcModelBuilder()
    model_builder.build_project(
        project_name="my_project",
        coordinate_system=CoordinateSystemTemplates.epsg_25832(),
        coordinate_operation=CoordinateSystemTemplates.get_default_coordinate_operation(),
        site_name="my_site",
        building_name="my_building",
    )
    model = model_builder.model

    concrete = Material(name="CON01", category="concrete", rgb=(120 / 255, 111 / 255, 51 / 255))
    wood = Material(name="WOOD01", category="wood", rgb=(0.65, 0.50, 0.30))
    glass = Material(name="GLASS01", category="glass", rgb=(0.6, 0.9, 0.8), transparency=0.6)

    model_info = Pset_Modellinformation(
        artfachmodell="Gebäudemodell",
        artteilmodell="Tragwerksplanung",
        auftraggeber="Freie und Hansestadt Hamburg, Behörde für Stadtentwicklung und Wohnen",
        ersteller="Ingenieurbüro Müller GmbH",
        erstelldatum=datetime.date(2025, 7, 15),
        gemobjektkatalog="BIM-Katalog Hamburg 2025",
        projektname="Neubau Schulzentrum Altona",
        projektnummer="HH-2025-0731",
    )

    geo_info = Pset_Georeferenzierung(
        hoehenstatus="HS170",
        hoehensystem="DHHN 16",
        koordinatensystem="ETRS89-GK",
        lagestatus="LS320",
    )

    objekt_info = Pset_Objektinformation(
        idebene1="Nullpunktobjekt",
        idebene2="Nullpunktobjekt",
        idebene3="Nullpunktobjekt",
    )

    hyperlink = Pset_Hyperlink(
        hyperlink_001="https://www.hamburg.de/basispunkt-info",
        hyperlink_001_bemerkung="Weitere Informationen zum Projekt-Basispunkt",
    )

    site = model.by_type("IfcSite")[0]

    # Create basepoint with property sets as input
    ProjectBasePointNorthMesh(size=1, psets=[model_info, objekt_info, geo_info, hyperlink], container=site).build(model)

    model.write("basepoint_generic.ifc")
