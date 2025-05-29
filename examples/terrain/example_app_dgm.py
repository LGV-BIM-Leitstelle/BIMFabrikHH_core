from BIMFabrikHH.apps.dgm.app import process_terrain_folder_to_ifc

from BIMFabrikHH.core.folder_utils import check_folder_exists
from BIMFabrikHH.core.request_oaf import HamburgOGCAPI
from BIMFabrikHH.core.request_ogc import request_body_example


x1 = 9.9664
y1 = 53.5517
x2 = 9.9764
y2 = 53.5572


tif_files = HamburgOGCAPI.get_tiles(x1, y1, x2, y2, model_type="dgm")
print(tif_files)


folder = check_folder_exists("dgm_hamburg")

# Process the folder and create the IFC file
ifc_bytes = process_terrain_folder_to_ifc(folder_path=folder, tif_files=tif_files, input_data=request_body_example)


file_path = "example_dgm.ifc"

with open(file_path, "wb") as file:
    file.write(ifc_bytes)

print(f"IFC file „{file_path}“ has been saved successfully.")
