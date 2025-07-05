from typing import ClassVar, Optional

from pydantic import BaseModel, Field


class BasePsetModel(BaseModel):
    pset_name: ClassVar[str]


class Pset_Objektinformation(BaseModel):
    pset_name: ClassVar[str] = "Pset_Objektinformation"
    idebene1: str = Field(alias="_IDEbene1")
    idebene2: str = Field(alias="_IDEbene2")
    idebene3: str = Field(alias="_IDEbene3")


class Pset_Modellinformation(BaseModel):
    pset_name: ClassVar[str] = "Pset_Modellinformation"
    artfachmodell: str = Field(alias="_ArtFachmodell")
    artteilmodell: str = Field(alias="_ArtTeilmodell")
    auftraggeber: str = Field(alias="_Auftraggeber")
    ersteller: str = Field(alias="_Ersteller")
    erstelldatum: str = Field(alias="_Erstelldatum")
    gemobjektkatalog: str = Field(alias="_GemObjektkatalog")
    projektname: str = Field(alias="_Projektname")
    projektnummer: str = Field(alias="_Projektnummer")


class Pset_Georeferenzierung(BaseModel):
    pset_name: ClassVar[str] = "Pset_Georeferenzierung"
    hoehenstatus: str = Field(alias="_Hoehenstatus")
    hoehensystem: str = Field(alias="_Hoehensystem")
    koordinatensystem: str = Field(alias="_Koordinatensystem")
    lagestatus: str = Field(alias="_Lagestatus")


class Pset_Hyperlink(BaseModel):
    pset_name: ClassVar[str] = "Pset_Hyperlink"
    hyperlink_001: str = Field(alias="_Hyperlink_001")
    hyperlink_001_Bemerkung: str = Field(alias="_Hyperlink_001_Bemerkung")


class Nullpunktobjekt(BaseModel):
    pset_objektinformation: Optional[Pset_Objektinformation] = None
    pset_modellinformation: Optional[Pset_Modellinformation] = None
    pset_georeferenzierung: Optional[Pset_Georeferenzierung] = None
    pset_hyperlink: Optional[Pset_Hyperlink] = None


def print_aliases(model):
    for field_name, field in model.__fields__.items():
        print(f"Field name: {field_name}, Alias: {field.alias}")


if __name__ == "__main__":
    objekt_information_data = {
        "_IDEbene1": "Nullpunktobjekt",
        "_IDEbene2": "Nullpunktobjekt",
        "_IDEbene3": "Nullpunktobjekt",
    }

    modell_information_data = {
        "_ArtFachmodell": "Ingenieurbau/ Bauwerk",
        "_ArtTeilmodell": "Bruecke",
        "_Auftraggeber": "Musterfirma_Mustermann",
        "_Ersteller": "Musterfirma_Musterfrau",
        "_Erstelldatum": "2020-04-24",
        "_GemObjektkatalog": "Allgemein/Master_V004",
        "_Projektname": "Musterprojekt",
        "_Projektnummer": "12345",
    }

    georeferenzierung_data = {
        "_Hoehenstatus": "HS170",
        "_Hoehensystem": "DHHN 16",
        "_Koordinatensystem": "ETRS89-GK",
        "_Lagestatus": "LS320",
    }

    hyperlink_data = {
        "_Hyperlink_001": "www.bim.hamburg.de",
        "_Hyperlink_001_Bemerkung": "Link zur Homepage von BIM.Hamburg",
        "_Hyperlink_002": "www.example.com",
        "_Hyperlink_002_Bemerkung": "Example website",
    }

    objekt_info = Pset_Objektinformation(**objekt_information_data)
    modell_info = Pset_Modellinformation(**modell_information_data)
    georeferenzierung = Pset_Georeferenzierung(**georeferenzierung_data)
    hyperlink = Pset_Hyperlink(**hyperlink_data)

    print("Pset_Objektinformation:")
    print(objekt_info)
    print("\nPset_Modellinformation:")
    print(modell_info)
    print("\nPset_Georeferenzierung:")
    print(georeferenzierung)
    print("\nPset_Hyperlink:")
    print(hyperlink)

    print("Printing aliases for Pset_Objektinformation:")
    print_aliases(Pset_Objektinformation)

    print("\nPrinting aliases for Pset_Modellinformation:")
    print_aliases(Pset_Modellinformation)

    print("\nPrinting aliases for Pset_Georeferenzierung:")
    print_aliases(Pset_Georeferenzierung)

    print("\nPrinting aliases for Pset_Hyperlink:")
    print_aliases(Pset_Hyperlink)
