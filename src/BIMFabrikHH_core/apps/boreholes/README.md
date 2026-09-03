# Baugrundaufschlüsse (Boreholes)

Portierung der `boreholes`-App aus `BIMFabrikHH_intern` nach `BIMFabrikHH_core`.

Die App erzeugt aus Hamburger Bohrdaten ein IFC-Modell: pro Bodenschicht einer
Bohrung ein gestapelter Zylinder (`IfcBuildingElementProxy`), eingefärbt nach
DIN 4023 und beschriftet mit den BIM.Hamburg-Property-Sets.

Im Unterschied zur intern-App liest diese Version **keine SQLite-Datenbank und
kein HTML** mehr, sondern ausschließlich eine **WFS-Antwort im Format
BoreholeML 3.0**.

---

## Datenquelle

Dienst: [
`HH_WFS_BoreholeML3`](https://geodienste.hamburg.de/HH_WFS_BoreholeML3?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities)

```text
https://geodienste.hamburg.de/HH_WFS_BoreholeML3
  ?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature
  &TYPENAMES=bml:Borehole&COUNT=5
  &bbox=9.98,53.54,10.00,53.56,EPSG:4326
```

Das Abrufen ist **nicht** Teil der App: Die
API holt die Antwort und übergibt sie an `records_from_boreholeml()`. Das
Beispiel liest dieselbe XML-Datei stattdessen im Assets-Ordner.

### Warum EPSG:5555 und nicht EPSG:25832 oder WGS84?

`EPSG:5555` ist die `DefaultCRS` des Dienstes und ein **zusammengesetztes CRS**:
ETRS89 / UTM Zone 32N **plus** DHHN-Höhe. Der horizontale Anteil *ist* exakt
EPSG:25832 — die Ost- und Nordwerte sind identisch.

`EPSG:25832` und `EPSG:4326` werden zwar als `OtherCRS` angeboten, sind aber
beide zweidimensional. Fordert man sie an, liefert der Dienst eine 2D-`gml:pos`
und **die Ansatzhöhe fehlt**:

| `SRSNAME`               | gelieferte `gml:pos`            |
|-------------------------|---------------------------------|
| *(Default)* `EPSG:5555` | `565084.160 5934034.654 14.300` |
| `EPSG:25832`            | `565084.160 5934034.654`        |
| `EPSG:4326`             | `9.982378 53.551164`            |

Die Ansatzhöhe ist die Bezugsgröße für die gesamte Schichtstapelung, deshalb ist
`EPSG:5555` die einzige sinnvolle Anfrage: Lage **und** Höhe in einem Request.
Es findet **keine Koordinatentransformation** statt, die Werte werden direkt als
Meterkoordinaten übernommen (Konvention von `BIMFabrikHH_core`).

---

## Aufbau

| Datei                            | Inhalt                                                       |
|----------------------------------|--------------------------------------------------------------|
| `processing.py`                  | BoreholeML-Parser, DIN-Mappings, Hyperlink-Aufbau            |
| `generic/app.py`                 | `BoreholesGenericApp.build_ifc()` — Zylinder und IFC-Ausgabe |
| `assets/soil_type_mapping.json`  | Bodenarten nach DIN EN ISO 14688-1                           |
| `assets/color_code_mapping.json` | Farbcodes und DIN-4023-Darstellungsfarben                    |

Zugehörig außerhalb dieses Ordners:

| Datei                                     | Inhalt                                                                                         |
|-------------------------------------------|------------------------------------------------------------------------------------------------|
| `data_models/boreholes.py`                | `BoreholeRecord`, `BoreholeLayer`, `collect_borehole_psets()`                                  |
| `data_models/pydantic_psets_boreholes.py` | `Pset_Aufschluss`, `Pset_Aufschlussbereich`, `Pset_Schicht`, `Pset_Objektinformation_Borehole` |
| `examples/boreholes/generic/`             | Beispielskript und WFS-Fixture                                                                 |
| `tests/test_app_boreholes.py`             | 46 Tests                                                                                       |

Die beiden JSON-Tabellen liegen **im App-Ordner** und werden über den
Modulpfad geladen (`ASSETS_DIR`), nicht über `PathConfig`. Dafür sind **keine
Einträge in `pyproject.toml` nötig**: Poetry nimmt über
`packages = [{ include = "BIMFabrikHH_core", from = "src" }]` alle Dateien im
Paketverzeichnis mit, nicht nur `*.py`. Ein explizites `include` wäre nur bei
setuptools erforderlich (`package_data` / `MANIFEST.in`).

Zu beachten ist lediglich, dass Poetry Dateien überspringt, die von
`.gitignore` erfasst werden. Für `*.json` ist das nicht der Fall. Ein Asset mit
der Endung `.ifc` würde dagegen stillschweigend im Wheel fehlen, weil `*.ifc`
ignoriert wird — dann wäre ein `include`-Eintrag tatsächlich nötig.

### Verwendung

```python
from BIMFabrikHH_core.apps.boreholes.generic import (
    BoreholesGenericApp,
    load_borehole_records,
)

records = load_borehole_records("response_WFS_boreholes_generic.xml")
BoreholesGenericApp.build_ifc(records, request_params=request_params)
```

---

## Was funktioniert

**Parsen.** Aus der Fixture werden 5 Bohrungen mit 23 Schichten gelesen:
Kopfdaten (`bml:id`, `fullName`, Lage, Ansatzhöhe, `totalLength`,
`drillingDate`, `drillingMethod`, `project`) und pro `bml:Interval` die
Schichtdaten.

**Höhenlage.** Die Tiefen `from`/`to` werden von der Ansatzhöhe nach unten
gerechnet (`upper_height = ansatzhoehe_nn - from_depth`). Die Schichten stapeln
sich lückenlos; bei Bohrung `B.52` von 5,66 m NHN bis −1,64 m NHN. Schichten
ohne Mächtigkeit werden protokolliert und übersprungen. Negative Ansatzhöhen
(z. B. −2,25 m NHN) sind unproblematisch.

**Bodenart aus `bml:rockCode`.** Der Hauptgemengteil wird aus `rockCode`
gelesen, **nicht** aus `bml:lithology/rockName`. Grund: Der dominante Anteil hat
oft *keinen* Eintrag in der `RockNameList` und damit einen leeren `rockName` —
eine Schicht der Fixture besteht zu 64 % aus `F` (Mudde) mit leerem Code, sodass
ein Lesen von `rockName` den 36-%-Sand zum Hauptgemengteil befördert hätte.
`rockCode` liefert korrekt `F(s4, hz4, ht2)`. Beide Schreibweisen werden
unterstützt:

| `rockCode`        | Haupt | Neben          |
|-------------------|-------|----------------|
| `F(s4, hz4, ht2)` | `F`   | `s4, hz4, ht2` |
| `ffS(x)`          | `ffS` | `x`            |
| `mS, yy`          | `mS`  | `yy`           |
| `H`               | `H`   | —              |

Fällt `rockCode` weg, dient `bml:lithology` als Rückfallebene, sortiert nach
`percentage`.

**DIN-Mapping.** Bodenkürzel werden zu `"Code (Bedeutung)"` aufgelöst, z. B.
`mS (Mittelsand)`, `ffS (Feinstsand)`, `uS (schluffiger Sand)`,
`F (Mudde (Faulschlamm))`. Unbekannte Codes werden unverändert durchgereicht.

**Einfärbung.** Die Darstellungsfarbe kommt — wie in der intern-App — aus dem
**Hauptgemengteil** nach DIN 4023, nicht aus dem `farbe`-Code. Sand wird orange,
Ton violett, Schluff oliv, Torf dunkelbraun. Pro DIN-Farbe entsteht ein
`IfcPresentationLayerAssignment` (`_Bodenaufschluesse_orange` usw.), pro
Kombination aus `farbe`-Code und DIN-Farbe ein `IfcMaterial`
(`_Bodenaufschluesse_undefiniert_orange`, `_Bodenaufschluesse_h8_orange` …).
Die Fixture ergibt 5 Layer und 6 Materialien.

**Property-Sets.** Jeder Zylinder trägt fünf Psets: `Pset_Aufschluss` (Bohrung),
`Pset_Aufschlussbereich`, `Pset_Schicht`, `Pset_Objektinformation` (Schicht) und
`Pset_Hyperlink` (Bohrung). Serialisiert mit den BIM.Hamburg-Aliassen
(`_Bodenart`, `_HoeheAnsatzpunkt` …).

**Ausgabe.** Das Beispiel schreibt die IFC-Datei und prüft sie mit
`python -m ifcopenshell.validate --rules` — ohne Befunde. Nullpunktobjekt wird
über `place_basepoint()` gesetzt. Ausgabe erfolgt über `logging`, nicht über
`print`.

---

## Was nicht funktioniert

### Der Hyperlink führt ins Leere

Der Link wird wie in der intern-App aufgebaut (feste Basis + `sid` + ID):

# funktioniert nicht
```text
https://geodienste.hamburg.de/app/render?sid=0x960470caL0x71973d4cL&id=BDHH_6434B1
```
# funkktioniert
```text
https://geodienste.hamburg.de/app/render?sid=0x960470caL0x71973d4cL&id=44372
```


Beim Aufruf antwortet das Portal jedoch mit HTTP 500:

```json
{
  "error": "The input string 'BDHH_6434B1' was not in a correct format."
}
```

**Ursache:** Der Parameter `id` wird serverseitig als **Ganzzahl** geparst,
*bevor* überhaupt gesucht wird. Zwei verschiedene Fehlermeldungen belegen das:

| gesendete `id`                  | Antwort                                                        |
|---------------------------------|----------------------------------------------------------------|
| `44381`                         | HTTP 200, Bohrung wird angezeigt                               |
| `1`, `6434`, `999999999`        | HTTP 500 — `Bohrloch 6434 not found in this service.`          |
| `BDHH_6434B1`, `6434B1`, `B100` | HTTP 500 — `The input string ... was not in a correct format.` |

Numerische, aber unbekannte Werte scheitern erst bei der *Suche*; unser Wert
erreicht die Datenbank nie.

`id` ist die **Archivnummer** der Bohrdatenbank Hamburg. Die funktionierende
Seite zu `44381` zeigt „Bohrloch 44381“ mit den Feldern `Archivnummer: 44381`,
`DK5: 6428`, `Bohrungsbezeichnung: B.IX/182` — genau die Bohrung aus dem
Docstring-Beispiel der intern-App. Deren Link funktionierte, weil die
SQLite-Spalte `id_stammdaten` diese Archivnummer enthielt.

`BDHH_6434B1` ist dagegen die GML-Feature-ID des WFS aus einem anderen
Nummernsystem: Präfix `BDHH_` (= `bml:databaseSource`), danach eine
DK5-Blattnummer und ein Zähler innerhalb des Blattes — alle fünf Bohrungen der
Fixture teilen `6434` und unterscheiden sich nur in `B1`, `B10`, `B100`, `B1000`.
Die Archivnummer ist eine flache globale Ganzzahl ohne Blattnummer oder
Bezeichnung darin (Bohrung 44381 liegt auf Blatt 6428 und heißt `B.IX/182`).
**Es gibt also keine Umrechnung zwischen beiden IDs**, und der WFS liefert die
Archivnummer nirgends — es ist keine numerische ID im Feature vorhanden.

**Was zur Behebung fehlt:** eine externe Zuordnung `BoreholeML-ID →
Archivnummer`. `build_borehole_hyperlink(..., portal_id="44381")` nimmt die
Nummer bereits an, sobald es eine Quelle dafür gibt.

Der `sid` ist nicht die Ursache und sollte als Konstante bleiben: ein falscher
`sid` liefert HTTP 500, ein fehlender HTTP 400. Er ist also erforderlich und
wertspezifisch — nicht gebietsabhängig, wie das TODO der intern-App vermutete.

### Farbcodes lassen sich nicht auflösen

BoreholeML nutzt eine eigene `RockColorList` mit Werten wie `h8`. Diese hat
**keine gemeinsame Grundlage** mit der DIN-Tabelle der intern-App (`we`, `ge`,
`gr`, `bn` …), die aus der SQLite-/HTML-Quelle stammt. Unbekannte Codes werden
unverändert durchgereicht, `_Farbe` zeigt also z. B. `h8` statt `h8 (…)`.

Die Geometrie ist davon **nicht** betroffen, weil die Einfärbung aus dem
Hauptgemengteil kommt. Zur Behebung wäre die `RockColorList`-Codeliste nötig.

### Stratigraphie teils unaufgelöst

Die Tabelle in `processing.py` kennt `qh`, `qp`, `q`, `y`, `t`, `k`, `j`, `tr`.
Der Dienst liefert aber auch `nb` und `Q1`, die unverändert durchgereicht
werden. Zur Behebung wäre die `ChronoStratigraphyList`-Codeliste nötig.

### Weitere Einschränkungen

- **Nebengemengteil-Codes** wie `yy`, `s4`, `hz4`, `x` fehlen in der
  Bodentabelle und werden durchgereicht. Der Klartext steht aber in
  `Pset_Schicht._GeologischeBezeichnung` (aus `bml:rockNameText`), z. B.
  „Mudde (stark sandig, viel Holzreste, schwach torfig)“.
- **Schichten ohne Bodenart:** Enthält ein Interval weder `rockCode` noch
  gefüllte `rockName`, entsteht ein weißer Zylinder mit `_Bodenart =
  undefiniert`. Das ist echte Datenlage, kein Parserfehler.
- **Mehrere `IntervalSeries`:** Es wird die Serie mit der höchsten `version`
  verwendet (aktuellste Ansprache). In der Fixture existiert nur eine
  (`Ersterfassung`, Version 0), dieser Zweig ist also nicht mit echten Daten
  geprüft.
- **`bml:boreholePath`** wird ignoriert; alle Zylinder stehen senkrecht.
  Abweichungen über `boreholeSegment` (`azimuth`, `inclination`) werden nicht
  ausgewertet — in der Fixture sind beide 0.
- **Grundwasser** (`bml:groundwater`, `groundwaterObservation`) wird nicht
  ausgewertet, obwohl teilweise Daten vorliegen: In der Fixture hat Bohrung
  `BDHH_6434B100` `entryDepth = 4.3` und `groundwaterLevel = 4.2`. Diese Werte
  gehen derzeit verloren — die intern-App hat sie ebenfalls nicht ins IFC
  geschrieben.

---

## Tests

```bash
pytest tests/test_app_boreholes.py          # 46 Tests
python examples/boreholes/generic/example_boreholes_generic.py
```

Die 46 Tests decken die DIN-Mappings, das Aufsplitten von `rockCode`, das
Parsen inklusive Höhenumrechnung und Sortierung, die Psets sowie den
Hyperlink-Aufbau ab. Das Beispiel wird zusätzlich automatisch von
`tests/examples/test_examples.py` gefunden und ausgeführt.
