from dataclasses import dataclass


@dataclass
class DfCol:
    """Dataclass representing the column names used in the dataframes."""

    REM2: str = "REM2"
    BAUM_INFO_ORIG: str = "BAUMINFO-STAMM_Datenquelle"
    BAUM_NR: str = "_Baumnummer"
    REM1: str = "REM1"
    EASTING: str = "Easting"
    EASTING_UTM = "Easting_UTM"
    ELEVATION: str = "Elevation"
    GATTUNG: str = "_Gattung"
    KRONENDURCHMESSER: str = "_Kronendurchmesser"
    LINE_SEPARATOR = "*" * 150
    NORTHING: str = "Northing"
    POS_X: str = "Position X"
    POS_Y: str = "Position Y"
    STAMMBASIS: str = "_Stammbasis"
    STAMMUMFANG: str = "_Stammumfang"
    STAMMUMFANG_BK: str = "stammumfang"
    REFERENCE_LINE: str = "Referenzlinie"
    TYP: str = "Typ"
    OBJEKT_NR: str = "Objektnummer"
    OBJEKTCODIERUNG: str = "OBJEKTCODIERUNG"
    FARBE = "Farbe"

    LAENGE = "Laenge"
    TIEFE = "Tiefe"
    HOEHE = "Hoehe"
    METHODE = "Methode"
