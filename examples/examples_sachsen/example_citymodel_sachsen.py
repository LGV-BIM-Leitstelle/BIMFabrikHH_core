"""
Sachsen city model example — LoD1 and LoD2.

Parses the CityGML tiles from examples/assets/data_sachsen and writes two
separate IFC files, one per LoD. Uses EPSG:25833 (UTM zone 33N, Sachsen).

Outputs:
    output/output_citymodel_sachsen_lod1.ifc
    output/output_citymodel_sachsen_lod2.ifc
"""
import time
from pathlib import Path

import numpy as np
import ifcopenshell.api.owner.settings as owner_settings
from ifcopenshell.api import context, geometry, pset, root, spatial

from BIMFabrikHH_core.apps.city.app import create_combined_representation
from BIMFabrikHH_core.apps.city.parser import CityGMLParser
from BIMFabrikHH_core.config import get_logger
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.core.model_creator import IfcModelBuilder
from BIMFabrikHH_core.core.model_creator.ifc_snippets import IfcSnippets
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates

logger = get_logger()

# ---------------------------------------------------------------------------
# Export controls — edit these before running
# ---------------------------------------------------------------------------
# Which LoD(s) to export: "lod1" | "lod2" | "both"
EXPORT_LOD: str = "lod2"
# Restrict export to a single building ID, or None for all buildings
FILTER_BUILDING_ID: str | None = "DESNATPU1000C1qE"  # e.g. "DESNATPU1000C1qE"
# ---------------------------------------------------------------------------

# Input GML files
SACHSEN_DATA = PathConfig.ASSETS / "data_sachsen"

LOD_CONFIG = {
    "lod1": {
        "gml": SACHSEN_DATA / "lod1_33410_5652_2_sn_citygml" / "lod1_33410_5652_2_sn.gml",
        "output": PathConfig.OUTPUT / "output_citymodel_sachsen_lod1.ifc",
        "project_name": "Sachsen_CityModel_LoD1",
        "color": (1.0, 1.0, 0.498),  # yellow
    },
    "lod2": {
        "gml": SACHSEN_DATA / "lod2_33410_5652_2_sn_citygml" / "lod2_33410_5652_2_sn.gml",
        "output": PathConfig.OUTPUT / "output_citymodel_sachsen_lod2.ifc",
        "project_name": "Sachsen_CityModel_LoD2",
        "color": (1.0, 0.8, 0.4),  # orange-ish to distinguish from LoD1
    },
}


def build_ifc_for_lod(lod_name: str, cfg: dict, building_id: str | None = None) -> bool:
    """
    Parse one CityGML file and write a single IFC output.

    Args:
        lod_name: "lod1" or "lod2" (used only for logging)
        cfg: dict with keys gml, output, project_name, color
        building_id: if given, export only this building ID

    Returns:
        True if the IFC file was written successfully.
    """
    gml_path: Path = cfg["gml"]
    color = cfg["color"]

    logger.info(f"[{lod_name.upper()}] Parsing {gml_path.name} ...")

    parser = CityGMLParser()
    parser.parse_file(str(gml_path), building_id_filter=building_id)

    if not parser.buildings:
        msg = f"Building ID '{building_id}' not found" if building_id else "No buildings found"
        logger.error(f"[{lod_name.upper()}] {msg} — skipping.")
        return False

    logger.info(f"[{lod_name.upper()}] {len(parser.buildings)} buildings parsed.")

    output_path: Path = cfg["output"]
    if building_id is not None:
        output_path = output_path.with_stem(output_path.stem + f"_{building_id}")

    # IFC model
    model_builder = IfcModelBuilder()
    model_builder.build_project(
        project_name=cfg["project_name"],
        coordinate_system=CoordinateSystemTemplates.epsg_25833(),
        coordinate_operation=CoordinateSystemTemplates.get_default_coordinate_operation(),
        site_name="Sachsen_Site",
        building_name=f"Sachsen_{lod_name.upper()}",
    )
    model = model_builder.model
    building_container = model_builder.building

    model3d = context.add_context(model, context_type="Model")
    body = context.add_context(
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model3d,
    )

    identity = np.eye(4)
    representations = []
    _orig_get_user = owner_settings.get_user
    _orig_get_app = owner_settings.get_application
    owner_settings.get_user = lambda *_: None
    owner_settings.get_application = lambda *_: None

    elements = []
    for building_id, building_data in parser.buildings.items():
        vertices = building_data.vertices
        face_indices = building_data.faces

        if not vertices or not face_indices:
            continue

        element = root.create_entity(model, ifc_class="IfcBuildingElementProxy", name=building_id)

        # Property sets
        if building_data.attributes:
            pset_ifc = pset.add_pset(model, product=element, name="Pset_Objektinformation")
            props = building_data.attributes.to_dict_with_labels(by_alias=True)
            pset.edit_pset(model, pset=pset_ifc, properties={k: v for k, v in props.items() if v is not None})

        # Geometry — prefer full void-face representation when available (LoD2)
        if hasattr(building_data, "faces_with_voids") and building_data.faces_with_voids:
            representation = create_combined_representation(
                model,
                context=body,
                vertices=vertices,
                faces=face_indices,
                faces_with_voids=building_data.faces_with_voids,
            )
        else:
            representation = geometry.add_mesh_representation(
                model,
                context=body,
                vertices=[vertices],
                faces=[face_indices],
                edges=[[]],
            )

        IfcSnippets.assign_color_to_representation(model, representation, color, 0.0)
        representations.append(representation)
        geometry.assign_representation(model, product=element, representation=representation)
        elements.append(element)

    # Batch container assignment before placements: assign_container internally re-localizes
    # placements for any element that already has an ObjectPlacement. By assigning the container
    # first (while elements have no placement), we skip that redundant internal edit_object_placement
    # call and avoid the O(n²) RelatedElements set-growth from n separate single-element calls.
    spatial.assign_container(model, relating_structure=building_container, products=elements)
    for element in elements:
        geometry.edit_object_placement(model, product=element, matrix=identity)

    owner_settings.get_user = _orig_get_user
    owner_settings.get_application = _orig_get_app

    IfcSnippets.batch_assign_layer_to_representations(model, representations, "_BIM_Stadtmodell", color)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    saved = model_builder.save_ifc_to_path(output_path)

    if saved:
        logger.info(f"[{lod_name.upper()}] ✓ Saved to {output_path}", extra={"debug_category": "success"})
        return True
    else:
        logger.error(f"[{lod_name.upper()}] ✗ Failed to save.", extra={"debug_category": "error"})
        return False


def main():
    total_start = time.perf_counter()

    lods = list(LOD_CONFIG.keys()) if EXPORT_LOD == "both" else [EXPORT_LOD]

    for lod_name in lods:
        cfg = LOD_CONFIG[lod_name]
        t = time.perf_counter()
        ok = build_ifc_for_lod(lod_name, cfg, building_id=FILTER_BUILDING_ID)
        elapsed = time.perf_counter() - t
        status = "✓" if ok else "✗"
        print(f"{status} {lod_name.upper()}: {elapsed:.2f}s  →  {cfg['output']}")

    print(f"\nTotal: {time.perf_counter() - total_start:.2f}s")


if __name__ == "__main__":
    main()
