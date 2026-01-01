# Attribute mapping for CityModelAttributes extraction
attribute_map = {
    "funktion_gebaeude": (".//bldg:function", str),
    "anzahl_obergeschoss": (".//bldg:storeysAboveGround", int),
    "relative_hoehe": (".//bldg:measuredHeight", float),
    "dachform": (".//bldg:roofType", str),
}
