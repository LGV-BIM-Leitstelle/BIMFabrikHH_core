from pathlib import Path

from BIMFabrikHH.apps.basepoint.with_north.app import BasepointNorthApp
from BIMFabrikHH.data_models.pydantic_psets_BIMHH import (
    Nullpunktobjekt,
    Pset_Objektinformation,
    Pset_Modellinformation,
    Pset_Georeferenzierung,
    Pset_Hyperlink,
)

OUTPUT_PATH = Path(__file__).parent.parent.parent / "output" / "output_basepoint_north_pydantic.ifc"


def main():
    """Create a basepoint with arrow using basepoint object property sets."""

    # Create basepoint object with all property sets
    nullpunkt_objekt = Nullpunktobjekt(
        pset_objektinformation=Pset_Objektinformation(
            _IDEbene1="Nullpunktobjekt",
            _IDEbene2="Nullpunktobjekt",
            _IDEbene3="Nullpunktobjekt",
        ),
        pset_modellinformation=Pset_Modellinformation(
            _ArtFachmodell="Ingenieurbau/ Bauwerk",
            _ArtTeilmodell="Bruecke",
            _Auftraggeber="Musterfirma_Mustermann",
            _Ersteller="Musterfirma_Musterfrau",
            _Erstelldatum="2020-04-24",
            _GemObjektkatalog="Allgemein/Master_V004",
            _Projektname="Musterprojekt",
            _Projektnummer="12345",
        ),
        pset_georeferenzierung=Pset_Georeferenzierung(
            _Hoehenstatus="HS170",
            _Hoehensystem="DHHN 16",
            _Koordinatensystem="ETRS89-GK",
            _Lagestatus="LS320",
        ),
        pset_hyperlink=Pset_Hyperlink(
            _Hyperlink_001="www.bim.hamburg.de",
            _Hyperlink_001_Bemerkung="Link zur Homepage von BIM.Hamburg",
        ),
    )

    # Convert basepoint object to property sets dictionary
    psets_data = {}

    if nullpunkt_objekt.pset_objektinformation:
        psets_data["Pset_Objektinformation"] = nullpunkt_objekt.pset_objektinformation.model_dump(by_alias=True)

    if nullpunkt_objekt.pset_modellinformation:
        psets_data["Pset_Modellinformation"] = nullpunkt_objekt.pset_modellinformation.model_dump(by_alias=True)

    if nullpunkt_objekt.pset_georeferenzierung:
        psets_data["Pset_Georeferenzierung"] = nullpunkt_objekt.pset_georeferenzierung.model_dump(by_alias=True)

    if nullpunkt_objekt.pset_hyperlink:
        psets_data["Pset_Hyperlink"] = nullpunkt_objekt.pset_hyperlink.model_dump(by_alias=True)

    # Create a single basepoint with arrow
    BasepointNorthApp.build_basepoint_north(
        position=(0, 0, 0),
        size=3.0,
        output_path=OUTPUT_PATH,
        psets=psets_data,
    )

    print(f"✓ Created {OUTPUT_PATH}")
    print("  - Base is red (hardcoded)")
    print("  - Arrow and 'N' are dark gray (hardcoded)")
    print("  - Aggregated as IfcElementAssembly")
    print("  - Added property sets using basepoint object class:")
    print("    * Pset_Objektinformation")
    print("    * Pset_Modellinformation")
    print("    * Pset_Georeferenzierung")
    print("    * Pset_Hyperlink")
    print("    * BasePoint_Properties")


if __name__ == "__main__":
    main()
