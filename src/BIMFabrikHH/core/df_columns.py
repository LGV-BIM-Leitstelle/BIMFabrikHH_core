from dataclasses import dataclass


@dataclass
class DfCol:
    """
    Dataclass representing the column names used in BIMFabrikHH DataFrames.
    Each attribute corresponds to a specific column name used for data processing and transformation.
    """

    BAUM_INFO_ORIG: str = "BAUMINFO-STAMM_Datenquelle"
    BAUM_NR: str = "_Baumnummer"
    EASTING: str = "Easting"
    EASTING_UTM = "Easting_UTM"
    ELEVATION: str = "Elevation"
    FARBE = "Farbe"
    GATTUNG: str = "_Gattung"
    HOEHE = "Hoehe"
    KRONENDURCHMESSER: str = "_Kronendurchmesser"
    LAENGE = "Laenge"
    LINE_SEPARATOR = "*" * 150
    METHODE = "Methode"
    NORTHING: str = "Northing"
    OBJEKTCODIERUNG: str = "OBJEKTCODIERUNG"
    OBJEKT_NR: str = "Objektnummer"
    POS_X: str = "Position X"
    POS_Y: str = "Position Y"
    REFERENCE_LINE: str = "Referenzlinie"
    REM1: str = "REM1"
    REM2: str = "REM2"
    STAMMBASIS: str = "_Stammbasis"
    STAMMUMFANG: str = "_Stammumfang"
    STAMMUMFANG_BK: str = "stammumfang"
    TIEFE = "Tiefe"
    TYP: str = "Typ"
