from pprint import pprint

from BIMFabrikHH.core.folder_utils import check_folder_exists
from BIMFabrikHH.core.request_ogc import request_body_example
from src.BIMFabrikHH.apps.stadtmodell.app import process_gml_to_ifc

gml_files = ["LoD1_32_550_5935_1_HH.xml"]

pprint(request_body_example.model_dump(), width=75, sort_dicts=False)

folder = check_folder_exists("LoD1-DE_HH_2023-04-01")

# Process the GML files and generate IFC
stadtmodell = process_gml_to_ifc(gml_files, request_body_example, reset_model=True, folder_path=folder)

file_path = "example_citymodell.ifc"

with open(file_path, "wb") as file:
    file.write(stadtmodell)

print(f"Data has been written to {file_path}")
