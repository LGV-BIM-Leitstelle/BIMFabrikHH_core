from pathlib import Path

from BIMFabrikHH.apps.basepoint.with_north.app import BasepointNorthApp

OUTPUT_PATH = Path(__file__).parent.parent.parent / "output" / "output_basepoint_north.ifc"


def main():
    """Create a basepoint with arrow using the proper app structure."""

    # Define property sets data for basepoint object
    psets_data = {
        "Pset_Objektinformation": {
            "_IDEbene1": "Nullpunktobjekt",
            "_IDEbene2": "Nullpunktobjekt",
            "_IDEbene3": "Nullpunktobjekt",
        },
        "Pset_Modellinformation": {
            "_ArtFachmodell": "Ingenieurbau/ Bauwerk",
            "_ArtTeilmodell": "Bruecke",
            "_Auftraggeber": "Musterfirma_Mustermann",
            "_Ersteller": "Musterfirma_Musterfrau",
            "_Erstelldatum": "2020-04-24",
            "_GemObjektkatalog": "Allgemein/Master_V004",
            "_Projektname": "Musterprojekt",
            "_Projektnummer": "12345",
        },
        "Pset_Georeferenzierung": {
            "_Hoehenstatus": "HS170",
            "_Hoehensystem": "DHHN 16",
            "_Koordinatensystem": "ETRS89-GK",
            "_Lagestatus": "LS320",
        },
        "Pset_Hyperlink": {
            "_Hyperlink_001": "www.bim.hamburg.de",
            "_Hyperlink_001_Bemerkung": "Link zur Homepage von BIM.Hamburg",
        },
    }

    # Create basepoint with north
    BasepointNorthApp.build_basepoint_north(
        position=(0, 0, 0),
        size=3.0,
        output_path=OUTPUT_PATH,
        psets=psets_data,
    )

    BasepointNorthApp.build_basepoint_north(
        position=(10, 10, 0),
        size=5.0,
        output_path=OUTPUT_PATH,
        psets=psets_data,
    )

    print(f"✓ Created {OUTPUT_PATH}")
    print("  - Base is red (hardcoded)")
    print("  - Arrow and 'N' are dark gray (hardcoded)")
    print("  - Aggregated as IfcElementAssembly")
    print("  - Added psets: Pset_Objektinformation, Pset_Modellinformation, Pset_Georeferenzierung, Pset_Hyperlink")


if __name__ == "__main__":
    main()
