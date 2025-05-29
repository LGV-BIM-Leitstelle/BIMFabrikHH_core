from pprint import pprint

from BIMFabrikHH.core.request_ogc import request_body_example
from src.BIMFabrikHH.apps.baum.app import BaumModeller

baum_modeller = BaumModeller()

pprint(request_body_example.model_dump(), width=75, sort_dicts=False)

try:
    ifc_bytes = baum_modeller.create_tree_model(request_body_example)

    file_path = "example_trees.ifc"

    with open(file_path, "wb") as file:
        file.write(ifc_bytes)

    print(f"IFC file „{file_path}“ has been saved successfully.")

except Exception as e:
    print(f"BaumModeller model is not initialized.\nError: {e}")
