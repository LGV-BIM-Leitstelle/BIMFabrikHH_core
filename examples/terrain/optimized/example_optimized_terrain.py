import time
from pathlib import Path

from BIMFabrikHH_core.apps.terrain.filtered import process_terrain_folder_to_ifc
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.data_models.params_bbox import BoundingBoxParams
from BIMFabrikHH_core.data_models.params_tree import Component, Container, RequestParams


def main():
    """Process terrain files to create an optimized DGM."""
    start = time.perf_counter()

    terrain_folder = Path(__file__).parent
    tif_name = str(PathConfig.ASSETS / "dgm1_32_558_9270_1_hh_2022.tif")
    # tif_path = terrain_folder / tif_name

    tif_files = [tif_name]

    output_file = terrain_folder / "example_dgm.ifc"

    container = Container(
        containerTitle="DGM_Container_Optimized",
        containerId="dgm_optimized",
        components={
            "description": Component(title="Description", value="Digital Ground Model Component - Optimized"),
            "optimization": Component(title="Optimization", value="Using point cloud optimization"),
        },
    )

    request_body = RequestParams(
        bbox=BoundingBoxParams(min_x=9.9756, min_y=53.5522, max_x=9.9789, max_y=53.5536), containers=[container]
    )

    result = process_terrain_folder_to_ifc(terrain_folder, tif_files, 5000, 0.05, request_body)

    end = time.perf_counter()
    print(f"Total process time: {end - start:.2f} seconds")

    if result:
        if isinstance(result, bytes):
            with open(output_file, "wb") as f:
                f.write(result)
            print(f"✓ Successfully created {output_file.name}\n{output_file.parent}")
        else:
            print(f"✓ Successfully created {result}")
    else:
        print(f"✗ Failed to create {output_file.name}")


if __name__ == "__main__":
    main()
