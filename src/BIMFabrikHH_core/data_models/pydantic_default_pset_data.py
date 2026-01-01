from typing import ClassVar

from pydantic import BaseModel, Field


class DefaultPsetObjektinformation(BaseModel):
    """Default property set data for object information."""

    pset_name: ClassVar[str] = "Pset_Objektinformation"
    idebene1: str = Field(default="Nullpunktobjekt", alias="_IDEbene1")
    idebene2: str = Field(default="Nullpunktobjekt", alias="_IDEbene2")
    idebene3: str = Field(default="Nullpunktobjekt", alias="_IDEbene3")


class DefaultPsetModellinformation(BaseModel):
    """Default property set data for model information."""

    pset_name: ClassVar[str] = "Pset_Modellinformation"
    artfachmodell: str = Field(default="Ingenieurbau/Bauwerk", alias="_ArtFachmodell")
    artteilmodell: str = Field(default="Bruecke", alias="_ArtTeilmodell")
    auftraggeber: str = Field(default="Musterfirma", alias="_Auftraggeber")
    ersteller: str = Field(default="Musterfirma", alias="_Ersteller")
    erstelldatum: str = Field(default="2024-08-12", alias="_Erstelldatum")
    gemobjektkatalog: str = Field(default="Allgemein/Master_V004", alias="_GemObjektkatalog")
    projektname: str = Field(default="Musterprojekt", alias="_Projektname")
    projektnummer: str = Field(default="12345", alias="_Projektnummer")


class DefaultPsetGeoreferenzierungGK(BaseModel):
    """Default property set data for georeferencing (GK coordinate system)."""

    pset_name: ClassVar[str] = "Pset_Georeferenzierung"
    hoehenstatus: str = Field(default="HS170", alias="_Hoehenstatus")
    hoehensystem: str = Field(default="DHHN2016", alias="_Hoehensystem")
    koordinatensystem: str = Field(default="ETRS89-GK", alias="_Koordinatensystem")
    lagestatus: str = Field(default="LS320", alias="_Lagestatus")


class DefaultPsetGeoreferenzierungUTM(BaseModel):
    """Default property set data for georeferencing (UTM coordinate system)."""

    pset_name: ClassVar[str] = "Pset_Georeferenzierung"
    hoehenstatus: str = Field(default="HS170", alias="_Hoehenstatus")
    hoehensystem: str = Field(default="DHHN2016", alias="_Hoehensystem")
    koordinatensystem: str = Field(default="ETRS89-UTM32N", alias="_Koordinatensystem")
    lagestatus: str = Field(default="LS310", alias="_Lagestatus")


class DefaultPsetHyperlink(BaseModel):
    """Default property set data for hyperlinks."""

    pset_name: ClassVar[str] = "Pset_Hyperlink"
    hyperlink_001: str = Field(default="www.bim.hamburg.de", alias="_Hyperlink_001")
    hyperlink_001_Bemerkung: str = Field(default="LinkZurHomepageVonBIM.Hamburg", alias="_Hyperlink_001_Bemerkung")


class DefaultPsetData(BaseModel):
    """Complete default property set data container."""

    pset_objektinformation: DefaultPsetObjektinformation = DefaultPsetObjektinformation()
    pset_modellinformation: DefaultPsetModellinformation = DefaultPsetModellinformation()
    pset_georeferenzierung_gk: DefaultPsetGeoreferenzierungGK = DefaultPsetGeoreferenzierungGK()
    pset_georeferenzierung_utm: DefaultPsetGeoreferenzierungUTM = DefaultPsetGeoreferenzierungUTM()
    pset_hyperlink: DefaultPsetHyperlink = DefaultPsetHyperlink()


# Convenience functions to get default data as dictionaries
def get_default_pset_objektinfo_data() -> dict:
    """Get default object information data as dictionary."""
    return DefaultPsetObjektinformation().model_dump(by_alias=True)


def get_default_pset_modellinfo_data() -> dict:
    """Get default model information data as dictionary."""
    return DefaultPsetModellinformation().model_dump(by_alias=True)


def get_default_pset_geo_data_gk() -> dict:
    """Get default georeferencing data (GK) as dictionary."""
    return DefaultPsetGeoreferenzierungGK().model_dump(by_alias=True)


def get_default_pset_geo_data_utm() -> dict:
    """Get default georeferencing data (UTM) as dictionary."""
    return DefaultPsetGeoreferenzierungUTM().model_dump(by_alias=True)


def get_default_pset_hyperlinkdata() -> dict:
    """Get default hyperlink data as dictionary."""
    return DefaultPsetHyperlink().model_dump(by_alias=True)


def get_all_default_pset_data() -> dict:
    """Get all default property set data as dictionary."""
    return DefaultPsetData().model_dump(by_alias=True)


if __name__ == "__main__":
    # Test the models
    print("Default Pset Objektinformation:")
    print(get_default_pset_objektinfo_data())

    print("\nDefault Pset Modellinformation:")
    print(get_default_pset_modellinfo_data())

    print("\nDefault Pset Georeferenzierung (GK):")
    print(get_default_pset_geo_data_gk())

    print("\nDefault Pset Georeferenzierung (UTM):")
    print(get_default_pset_geo_data_utm())

    print("\nDefault Pset Hyperlink:")
    print(get_default_pset_hyperlinkdata())

    print("\nAll Default Pset Data:")
    print(get_all_default_pset_data())
