import time
from pathlib import Path

from BIMFabrikHH import BoundingBoxParams, Component, Container, RequestParams
from BIMFabrikHH.apps.terrain.filtered import process_terrain_folder_to_ifc


def main():
    """Process terrain files to create an optimized DGM."""
    start = time.perf_counter()

    terrain_folder = Path(__file__).parent
    tif_files = [str(Path(__file__).parent.parent / "assets" / "dgm1_32_558_9270_1_hh_2022.tif")]
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

    # Alternative configuration with different parameters:
    # result = process_terrain_folder_to_ifc(
    #     terrain_folder, tif_files, output_file, request_body, min_points=2000, importance_threshold=0.1
    # )

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
