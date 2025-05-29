from BIMFabrikHH.pydantic_models.params_bbox import BoundingBoxParams
from BIMFabrikHH.pydantic_models.params_tree import RequestParams, Container, Component

inputs = {
    "containers": [
        {
            "containerId": "Projektinformationen",
            "containerTitle": "Projektinformationen",
            "components": {
                "projectname": {"title": "Projektname", "value": "Default_Projektname"},
                "ifc_site": {"title": "IfcSite", "value": "Default_Site"},
                "ifc_building": {"title": "IfcBuilding", "value": "Default_Gebaeude"},
            },
        },
        {
            "containerId": "Pset_Georeferenzierung",
            "containerTitle": "Pset_Georeferenzierung",
            "components": {
                "hoehenstatus": {"title": "_Hoehenstatus", "value": "HS170"},
                "hoehensystem": {"title": "_Hoehensystem", "value": "DHHN2016"},
                "koordinatensystem": {"title": "_Koordinatensystem", "value": "ETRS89-UTM32N"},
                "lagestatus": {"title": "_Lagestatus", "value": "LS310"},
            },
        },
        {
            "containerId": "Pset_Objektinformation",
            "containerTitle": "Pset_Objektinformation",
            "components": {
                "idebene1": {"title": "_IDEbene1", "value": "Nullpunktobjekt"},
                "idebene2": {"title": "_IDEbene2", "value": "Nullpunktobjekt"},
                "idebene3": {"title": "_IDEbene3", "value": "Nullpunktobjekt"},
            },
        },
        {
            "containerId": "Pset_Modellinformation",
            "containerTitle": "Pset_Modellinformation",
            "components": {
                "artfachmodell": {"title": "_ArtFachmodell", "value": "Ingenieurbau/Bauwerk"},
                "artteilmodell": {"title": "_ArtTeilmodell", "value": "Bruecke"},
                "auftraggeber": {"title": "_Auftraggeber", "value": "Musterfirma"},
                "ersteller": {"title": "_Ersteller", "value": "Ahmed Salem"},
                "erstelldatum": {"title": "_Erstelldatum", "value": "2024-08-12"},
                "gemobjektkatalog": {"title": "_GemObjektkatalog", "value": "Allgemein/Master_V004"},
                "projektname": {"title": "_Projektname", "value": "Musterprojekt"},
                "projektnummer": {"title": "_Projektnummer", "value": "12345"},
            },
        },
        {
            "containerId": "Pset_Hyperlink",
            "containerTitle": "Pset_Hyperlink",
            "components": {
                "hyperlink1": {"title": "_Hyperlink_001", "value": "www.bim.hamburg.de"},
                "hyperlink1bem": {"title": "_Hyperlink_001_bemerkung", "value": "LinkZurHomepageVonBIM.Hamburg"},
            },
        },
        {
            "containerId": "level_of_geometry",
            "containerTitle": "Level Of Geometry",
            "components": {"level_of_geom": {"title": "Level Of Geometry", "value": 2}},
        },
    ],
    "bbox": {
        "min_x": 9.98869392179191,
        "min_y": 53.55224907342103,
        "max_x": 9.991053234280601,
        "max_y": 53.55408464712294,
    },
}

bbox_params = BoundingBoxParams(
    min_x=inputs["bbox"]["min_x"],
    min_y=inputs["bbox"]["min_y"],
    max_x=inputs["bbox"]["max_x"],
    max_y=inputs["bbox"]["max_y"],
)

containers = []
for c in inputs["containers"]:
    components = {key: Component(title=val["title"], value=val["value"]) for key, val in c["components"].items()}
    containers.append(
        Container(containerId=c["containerId"], containerTitle=c["containerTitle"], components=components)
    )


request_body_example = RequestParams(bbox=bbox_params, containers=containers)

if __name__ == "__main__":
    from pprint import pprint
    from BIMFabrikHH.core.ogc_values_extractor import extract_psets_basepoint

    pprint(request_body_example.model_dump(), width=120, sort_dicts=False)
    print("*" * 200)
    pset_groups = extract_psets_basepoint(inputs["containers"])
    pprint(pset_groups)
