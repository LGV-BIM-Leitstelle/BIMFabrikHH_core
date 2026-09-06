"""
Generic Terrain App
===================

Build an IFC DGM from a :class:`TerrainMesh` using the ``ifcfactory``
``BIMFactoryElement`` pipeline. Mirrors the open-house tutorial terrain
pattern (``MeshRepresentation`` wrapped in ``Style``) and lets callers
attach Pydantic property-set templates (``Pset_Objektinformation_DGM``
+ ``Pset_Hyperlink`` by default).

Shares the pure meshing pipeline (``extract_mesh_adaptive``) and the
IFC-adjacent helpers (basepoint placement, bbox resolution, default
psets) with :class:`TerrainBasicApp`.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import ifcopenshell
from ifcfactory import BIMFactoryElement, MeshRepresentation, Style
from ifcopenshell.util.shape_builder import ShapeBuilder
from pydantic import BaseModel

from BIMFabrikHH_core.apps.terrain._ifc_common import default_terrain_psets
from BIMFabrikHH_core.apps.terrain.landxml import terrain_mesh_to_landxml
from BIMFabrikHH_core.apps.terrain.processing import (
    DEFAULT_GUIDE_EDGE_SPACING_M,
    NUTZART_ORDER,
    collect_guide_rings,
    extract_mesh_adaptive,
    split_mesh_by_nutzart,
)
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import default_bim_hamburg_hyperlink
from BIMFabrikHH_core.data_models.streets import load_guide_records_from_oaf, pset_for_nutzung_group
from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.core.geometry import place_basepoint
from BIMFabrikHH_core.core.georeferencing import bbox_request_params_to_epsg25832
from BIMFabrikHH_core.core.model_creator import init_ifc_project
from BIMFabrikHH_core.core.ogc_extractor.ogc_values_extractor import (
    extract_psets_basepoint,
)
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_psets_terrain import (
    Pset_Objektinformation_DGM,
)
from BIMFabrikHH_core.data_models.terrain_mesh import TerrainMesh

logger = get_logger("terrain_generic_app")

RgbTuple = Union[Tuple[float, float, float], Tuple[int, int, int]]

_DEFAULT_TERRAIN_RGB: RgbTuple = (220, 40, 40)
_DEFAULT_TERRAIN_LAYER: str = "_BIM_DGM_Gelaende"
# Land-use types share a magenta ramp (light → dark). Grünfläche is park green.
_NUTZART_RGB: dict[str, RgbTuple] = {
    "DGM": (220, 40, 40),
    "Strassenverkehr": (110, 110, 115),
    "Strassenverkehr|Fahrbahn": (55, 55, 60),
    "Strassenverkehr|Begleitfläche Straßenverkehr": (175, 175, 180),
    "Weg": (230, 120, 40),
    "Bahnverkehr": (90, 75, 75),
    "Platz": (236, 186, 220),
    "Wohnbauflaeche": (228, 168, 210),
    "Flaeche Gemischter Nutzung": (220, 154, 202),
    "Industrie Und Gewerbeflaeche": (212, 140, 194),
    "Flaeche Besonderer Funktionaler Praegung": (204, 128, 186),
    "Sport Freizeit Und Erholungsflaeche": (36, 150, 52),
    "Fliessgewaesser": (198, 226, 245),
    "Stehendes Gewaesser": (198, 226, 245),
    "Hafenbecken": (170, 210, 235),
    "Meer": (170, 210, 235),
    "Schiffsverkehr": (170, 210, 235),
    "Unland Vegetationslose Flaeche": (242, 241, 239),
}
_NUTZART_LAYER: dict[str, str] = {
    "Strassenverkehr": "_BIM_DGM_Strassenverkehr",
    "Strassenverkehr|Fahrbahn": "_BIM_DGM_Fahrbahn",
    "Strassenverkehr|Begleitfläche Straßenverkehr": "_BIM_DGM_Begleitflaeche",
    "Weg": "_BIM_DGM_Weg",
    "Bahnverkehr": "_BIM_DGM_Bahnverkehr",
    "Platz": "_BIM_DGM_Platz",
    "Wohnbauflaeche": "_BIM_DGM_Wohnbau",
    "Industrie Und Gewerbeflaeche": "_BIM_DGM_Gewerbe",
    "Flaeche Gemischter Nutzung": "_BIM_DGM_GemischteNutzung",
    "Flaeche Besonderer Funktionaler Praegung": "_BIM_DGM_FunktionalePraegung",
    "Sport Freizeit Und Erholungsflaeche": "_BIM_DGM_Freizeit",
    "Fliessgewaesser": "_BIM_DGM_Fliessgewaesser",
    "Stehendes Gewaesser": "_BIM_DGM_StehendesGewaesser",
    "Hafenbecken": "_BIM_DGM_Hafenbecken",
    "Meer": "_BIM_DGM_Meer",
    "Schiffsverkehr": "_BIM_DGM_Schiffsverkehr",
    "Unland Vegetationslose Flaeche": "_BIM_DGM_Unland",
}
_DEFAULT_OUTPUT_NAME: str = "output_dgm_generic.ifc"
_DEFAULT_BASEPOINT_SIZE: float = 5.0


class TerrainGenericApp:
    """Record-builder terrain app built on ``ifcfactory``.

    ``build_ifc`` takes a prepared :class:`TerrainMesh` and writes the DGM
    as a single ``IfcBuildingElementProxy`` with a ``MeshRepresentation``
    styled via :class:`ifcfactory.Style`, then places the project
    basepoint quad. :meth:`from_geotiffs` combines mesh extraction and
    IFC building in one call.
    """

    @staticmethod
    def build_ifc(
        mesh: TerrainMesh,
        *,
        request_params: RequestParams,
        psets: Optional[Sequence[BaseModel]] = None,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        basepoint_size: float = _DEFAULT_BASEPOINT_SIZE,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        color: RgbTuple = _DEFAULT_TERRAIN_RGB,
        cad_layer: str = _DEFAULT_TERRAIN_LAYER,
        name: str = "DGM",
        transparency: float = 0.0,
        parts: Optional[Sequence[Tuple[str, TerrainMesh, Optional[Sequence[BaseModel]]]]] = None,
    ) -> Optional[Path]:
        """Build an IFC file from a prepared :class:`TerrainMesh`.

        Args:
            mesh: Triangulated terrain mesh in the project CRS (EPSG:25832).
            request_params: Project metadata and pset containers.
            psets: Pydantic pset models to attach to the DGM element.
                Defaults to :class:`Pset_Objektinformation_DGM` and
                :class:`Pset_Hyperlink` with their template defaults.
            output_path: Full path to write the IFC to. When ``None``,
                the file is written to ``PathConfig.OUTPUT / output_name``.
            output_name: Default filename when ``output_path`` is ``None``.
            basepoint_size: Edge length of the basepoint quad (meters).
            basepoint_origin: Explicit ``(x, y)`` origin in EPSG:25832 for
                the basepoint quad. When ``None``, placement uses the request
                WGS84 bbox lower-left (via :attr:`RequestParams.bbox_as_wgs84_tuple`)
                if ``bbox`` is set; otherwise no Nullpunktobjekt is written.
            color: RGB as ``(R, G, B)`` in 0-255 **or** normalized 0-1 floats.
            cad_layer: CAD layer name assigned to the terrain mesh.
            name: IFC element name for the DGM.
            transparency: 0.0 = opaque, 1.0 = fully transparent.
            parts: Optional ``(label, mesh, psets)`` pieces from ``trennen``.
                Each Nutzung type becomes one object (all Flächen of that type
                together) plus leftover DGM. When ``None``, one mesh is written.

        Returns:
            Path to the saved IFC file, or ``None`` on failure.
        """
        if parts:
            export_parts: List[Tuple[str, TerrainMesh, Optional[Sequence[BaseModel]]]] = list(parts)
        else:
            export_parts = [(name, mesh, psets)]
        if not export_parts or all(part.is_empty() for _, part, _ in export_parts):
            logger.warning("No valid terrain data to convert.")
            return None

        try:
            n_faces = sum(len(part.faces) for _, part, _ in export_parts if not part.is_empty())
            logger.info("Creating IFC model with %d part(s), %d faces…", len(export_parts), n_faces)

            builder = init_ifc_project(request_params=request_params, building_name="DGM")
            model = builder.model
            if model is None:
                logger.error("Failed to create IFC model")
                return None

            default_psets = list(psets) if psets is not None else default_terrain_psets()
            elements: List[BIMFactoryElement] = []
            for label, part, part_psets in export_parts:
                if part.is_empty():
                    continue
                part_color = _color_for_label(label, color)
                part_layer = _NUTZART_LAYER.get(label, cad_layer if label == "DGM" else f"_BIM_DGM_{_safe_label(label)}")
                part_name = name if label == "DGM" else f"{name}_{_safe_label(label)}"
                elements.append(
                    _terrain_element_from_mesh(
                        mesh=part,
                        name=part_name,
                        color=part_color,
                        cad_layer=part_layer,
                        transparency=transparency,
                        psets=list(part_psets) if part_psets is not None else default_psets,
                    )
                )

            BIMFactoryElement.build_in(model, inst=builder.site, items=elements)

            place_basepoint(
                model=model,
                site=builder.site,
                basepoint_origin=basepoint_origin,
                bbox_wgs84=(None if basepoint_origin is not None else request_params.bbox_as_wgs84_tuple),
                size=basepoint_size,
                psets=extract_psets_basepoint(request_params.containers or []),
            )

            logger.info("Saving IFC model...")
            return builder.save_ifc_to_output(output_name, output_path=output_path)

        except Exception as e:
            logger.error(f"Error creating IFC model: {e}")
            import traceback

            traceback.print_exc()
            return None

    @classmethod
    def from_geotiffs(
        cls,
        tif_files: Iterable[Union[str, Path]],
        *,
        request_params: RequestParams,
        psets: Optional[Sequence[BaseModel]] = None,
        folder_path: Optional[Union[str, Path]] = None,
        min_points: int = 1000,
        importance_threshold: float = 0.1,
        move_to_origin: bool = False,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        basepoint_size: float = _DEFAULT_BASEPOINT_SIZE,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        color: RgbTuple = _DEFAULT_TERRAIN_RGB,
        cad_layer: str = _DEFAULT_TERRAIN_LAYER,
        guide_records: Optional[Sequence[Any]] = None,
        guide_edge_spacing_m: float = DEFAULT_GUIDE_EDGE_SPACING_M,
        trennen: bool = False,
        guide_from_oaf: bool = False,
        write_geojson: bool = False,
        export_landxml: bool = False,
        landxml_path: Optional[Union[str, Path]] = None,
    ) -> Optional[Path]:
        """One-shot: extract a mesh from GeoTIFFs, then build the IFC.

        Combines :func:`extract_mesh_adaptive` and :meth:`build_ifc`.
        The bbox from ``request_params`` (WGS84) is projected to
        EPSG:25832 before extraction.

        ``guide_records`` is optional. When set (ALKIS ``Nutzung`` street
        polygons), their outlines become Bruchkanten in a constrained
        Delaunay TIN. Omit it for the original unconstrained mesh.

        ``trennen`` (guided only) splits the TIN into one IFC object per
        Nutzung type (all Flächen of that type together) plus leftover DGM.
        ALKIS attributes go on each part as ``Pset_Objektinformation``.

        ``guide_from_oaf`` pulls ALKIS ``Nutzung`` from the Hamburg OAF for
        the request bbox. ``write_geojson`` (default ``False``) optionally
        writes ``alkis_nutzung_verkehr.geojson`` and
        ``alkis_nutzung_weitere.geojson`` next to ``output_path``.

        ``export_landxml`` (default ``False``) additionally writes a LandXML
        1.2 TIN with one ``<Surface>`` per part (DGM + each Nutzung type),
        the exact same triangles as the IFC. ``landxml_path`` overrides the
        destination; otherwise it is the IFC path with a ``.xml`` suffix.
        """
        if guide_from_oaf and guide_records is None:
            bbox_wgs84 = request_params.bbox_as_wgs84_tuple
            if bbox_wgs84 is None:
                logger.warning("guide_from_oaf=True needs RequestParams.bbox")
            else:
                geojson_dir = Path(output_path).parent if output_path is not None else None
                if write_geojson and geojson_dir is None:
                    logger.warning("write_geojson=True needs output_path to know where to save")
                guide_records = load_guide_records_from_oaf(
                    bbox_wgs84,
                    write_geojson=bool(write_geojson and geojson_dir is not None),
                    output_dir=geojson_dir,
                )
        elif write_geojson:
            logger.warning("write_geojson=True is ignored unless guide_from_oaf fetches Nutzung")

        bbox_utm = bbox_request_params_to_epsg25832(request_params)
        t0 = time.perf_counter()
        water_meshes: Dict[str, TerrainMesh] = {}
        mesh = extract_mesh_adaptive(
            tif_files,
            folder_path=folder_path,
            min_points=min_points,
            importance_threshold=importance_threshold,
            bbox_utm=bbox_utm,
            move_to_origin=move_to_origin,
            guide_records=guide_records,
            guide_edge_spacing_m=guide_edge_spacing_m,
            water_meshes=water_meshes,
        )
        parts: Optional[List[Tuple[str, TerrainMesh, Optional[Sequence[BaseModel]]]]] = None
        if trennen:
            if not guide_records:
                logger.warning("trennen=True needs guide_records; writing a single DGM")
            else:
                rings = collect_guide_rings(
                    guide_records, spacing=guide_edge_spacing_m, bbox_utm=bbox_utm
                )
                split = split_mesh_by_nutzart(mesh, rings)
                for key, water_mesh in water_meshes.items():
                    if not water_mesh.is_empty():
                        split[key] = water_mesh
                        logger.info(
                            "Water triangles %s: %d face(s), %d vertices",
                            key,
                            len(water_mesh.faces),
                            len(water_mesh.vertices),
                        )
                hyperlink = default_bim_hamburg_hyperlink()
                ordered = [key for key in ("DGM", *NUTZART_ORDER) if key in split]
                ordered.extend(sorted(key for key in split if key not in ordered))
                parts = []
                for key in ordered:
                    if key == "DGM":
                        part_psets: Optional[Sequence[BaseModel]] = (
                            list(psets) if psets is not None else default_terrain_psets()
                        )
                    else:
                        part_psets = [pset_for_nutzung_group(guide_records, label=key), hyperlink]
                    parts.append((key, split[key], part_psets))
        mesh_s = time.perf_counter() - t0
        t1 = time.perf_counter()
        result = cls.build_ifc(
            mesh,
            request_params=request_params,
            psets=psets,
            output_path=output_path,
            output_name=output_name,
            basepoint_size=basepoint_size,
            basepoint_origin=basepoint_origin,
            color=color,
            cad_layer=cad_layer,
            parts=parts,
        )
        ifc_s = time.perf_counter() - t1
        logger.info(
            "Timing: mesh %.3f s | IFC %.3f s | total %.3f s",
            mesh_s,
            ifc_s,
            mesh_s + ifc_s,
        )

        if export_landxml and result is not None:
            surfaces: List[Tuple[str, TerrainMesh]] = (
                [(label, part) for label, part, _ in parts]
                if parts
                else [("DGM", mesh)]
            )
            xml_dest = Path(landxml_path) if landxml_path is not None else Path(result).with_suffix(".xml")
            try:
                terrain_mesh_to_landxml(surfaces, xml_dest)
            except Exception as e:  # keep IFC result even if LandXML fails
                logger.error("LandXML export failed: %s", e)
        elif export_landxml and result is None:
            logger.warning("Skipping LandXML export because IFC build failed")

        return result


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _safe_label(label: str) -> str:
    return label.replace("|", "_").replace(" ", "_")[:80]


def _color_for_label(label: str, fallback: RgbTuple) -> RgbTuple:
    if label in _NUTZART_RGB:
        return _NUTZART_RGB[label]
    base = label.split("|", 1)[0]
    return _NUTZART_RGB.get(base, fallback)


class _TerrainMeshRepresentation(MeshRepresentation):
    """Terrain (incl. water) as a single ``IfcTriangulatedFaceSet``.

    Every part is triangle-only, so the IFC and the LandXML export describe
    the exact same geometry.
    """

    def build(self, model: ifcopenshell.file):
        builder = ShapeBuilder(model)
        return builder.triangulated_face_set(self.vertices, self.faces)


def _terrain_element_from_mesh(
    *,
    mesh: TerrainMesh,
    name: str,
    color: RgbTuple,
    cad_layer: str,
    transparency: float,
    psets: List[BaseModel],
) -> BIMFactoryElement:
    """Wrap the terrain mesh in a styled ``BIMFactoryElement`` ready for ``build_in``."""
    vertices: List[Tuple[float, float, float]] = [(float(v[0]), float(v[1]), float(v[2])) for v in mesh.vertices]

    mesh_item = _TerrainMeshRepresentation(vertices=vertices, faces=mesh.faces)
    styled_mesh = Style(
        item=mesh_item,
        rgb=color,
        transparency=transparency,
        cad_layer=cad_layer,
    )

    return BIMFactoryElement(
        type="IfcBuildingElementProxy",
        name=name,
        qsets=False,
        children=[styled_mesh],
        psets=psets,
    )


__all__ = ["TerrainGenericApp", "Pset_Objektinformation_DGM"]
