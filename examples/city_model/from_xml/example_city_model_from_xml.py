from ifcfactory import BIMFactoryElement, Extrusion, Polygon

from BIMFabrikHH_core.apps.city.parser import CityGMLParser
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.core.model_creator import IfcModelBuilder
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates


def main():
    xml_path = PathConfig.ASSETS / "LoD1_32_549_5937_1_HH.xml"
    parser = CityGMLParser()
    parser.parse_file(str(xml_path))

    # Use IfcModelBuilder for IFC creation and setup
    model_builder = IfcModelBuilder()
    coordinate_system = CoordinateSystemTemplates.epsg_25832()
    coordinate_operation = CoordinateSystemTemplates.get_default_coordinate_operation()
    model_builder.build_project(
        "CityModelProject", coordinate_system, coordinate_operation, site_name="Site", building_name="Building"
    )
    model = model_builder.model
    building = model_builder.building

    # For each building in the parsed CityGML (limit to first 50)
    for idx, (building_id, building_data) in enumerate(parser.buildings.items()):
        if idx >= 50:
            break
        vertices = building_data.vertices
        face_indices = building_data.faces
        extrusion_depth = getattr(building_data, "height", 10.0) or 10.0
        for face in face_indices:
            # Convert indices to 2D points (ignore Z or use Z for extrusion height)
            points_2d = [(vertices[i][0], vertices[i][1]) for i in face]
            BIMFactoryElement(
                inst=building,
                children=[
                    BIMFactoryElement(
                        type="IfcWall", children=[Extrusion(basis=Polygon(points=points_2d), depth=extrusion_depth)]
                    )
                ],
            ).build(model)

    # Write the model to file
    output_file = PathConfig.OUTPUT / "output_citymodell_generic_from_xml.ifc"
    print()
    model.write(str(output_file))
    print(f"IFC model created successfully: {output_file}")


if __name__ == "__main__":
    main()
