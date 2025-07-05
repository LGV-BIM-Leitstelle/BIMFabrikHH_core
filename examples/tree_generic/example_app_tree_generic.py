from pathlib import Path

import pandas as pd
from BIMFabrikHH.apps.trees.generic.app import BaumGenericElevationApp
from BIMFabrikHH.core.georeferencing.extract_elevation import extract_elevation_df_from_geotiff

tree_data = [
    {
        "Easting": 558406.01,
        "Northing": 5927514.51,
        "kronendurchmesser": 58.0,
        "stammumfang": 1,
        "detail": 1,
        "segments": 8,
        "baumnummer": "100001",
        "gattung_deutsch": "Ahorn",
        "baumid": 1,
        "art_deutsch": "Spitz-Ahorn",
        "sorte_deutsch": "Spitz-Ahorn",
        "strasse": "Example Street",
        "stadtteil": "Demo-Stadtteil",
        "bezirk": "Altona",
        "pflanzjahr": 1990,
    },
    {
        "Easting": 558553.52,
        "Northing": 5927499.96,
        "kronendurchmesser": 6.0,
        "stammumfang": 1.5,
        "detail": 2,
        "segments": 8,
        "height": 15.0,
        "baumnummer": "100002",
        "gattung_deutsch": "Eiche",
        "baumid": 2,
        "art_deutsch": "Stiel-Eiche",
        "sorte_deutsch": "Stiel-Eiche",
        "strasse": "Musterweg",
        "stadtteil": "Demo-Stadtteil",
        "bezirk": "Bergedorf",
        "pflanzjahr": 1980,
    },
    {
        "Easting": 558501.93,
        "Northing": 5927581.88,
        "kronendurchmesser": 1,
        "stammumfang": 0.45,
        "baumnummer": "120220",
        "gattung_deutsch": "Linde",
        "baumid": 3,
        "art_deutsch": "Winter-Linde",
        "sorte_deutsch": "Winter-Linde",
        "strasse": "Musterweg",
        "stadtteil": "Demo-Stadtteil",
        "bezirk": "Bramfeld",
        "pflanzjahr": 1985,
        "detail": 3,
        "segments": 8,
    },
    {
        "Easting": 558502.19,
        "Northing": 5927596.83,
        "kronendurchmesser": 2,
        "stammumfang": 0.45,
        "detail": 4,
        "segments": 8,
        "height": 17.0,
        "baumnummer": "100004",
        "gattung_deutsch": "Birke",
        "baumid": 4,
        "art_deutsch": "Hänge-Birke",
        "sorte_deutsch": "Hänge-Birke",
        "strasse": "Birkenweg",
        "stadtteil": "Demo-Stadtteil",
        "bezirk": "Harburg",
        "pflanzjahr": 1995,
    },
]

# Reference the local GeoTIFF file
tif_path = str(Path(__file__).parent.parent.parent / "assets" / "dgm1_32_558_9270_1_hh_2022.tif")

# Convert to DataFrame for batch elevation processing
df = pd.DataFrame(tree_data)
df = extract_elevation_df_from_geotiff(df, tif_path, "Easting", "Northing", "Elevation")

# Add elevation data and position tuples to tree_data
for row, elevation in zip(tree_data, df["Elevation"]):
    row["position"] = (row["Easting"], row["Northing"], elevation)

# Generate IFC model
BaumGenericElevationApp.build_ifc_from_tree_data(tree_data)
