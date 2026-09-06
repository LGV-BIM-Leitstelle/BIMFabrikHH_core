# Terrain (DGM)

Guided DGM Bruchkanten come from Hamburg **OGC API Features (OAF)**, not from HH-SIB and not from Gebäude footprints.

## OAF Dienst

| | |
| --- | --- |
| Dataset | [ALKIS – Liegenschaften und Verwaltungseinheiten](https://api.hamburg.de/datasets/v1/alkis_vereinfacht) (`alkis_vereinfacht`) |
| Collection | [Nutzung](https://api.hamburg.de/datasets/v1/alkis_vereinfacht/collections/Nutzung) (Tatsächliche Nutzung) |
| Items | https://api.hamburg.de/datasets/v1/alkis_vereinfacht/collections/Nutzung/items |
| HTML API | https://api.hamburg.de/datasets/v1/alkis_vereinfacht/api?f=html |

Query the collection with a WGS84 `bbox` and ask for coordinates in **EPSG:25832** (collection `storageCrs`):

```
https://api.hamburg.de/datasets/v1/alkis_vereinfacht/collections/Nutzung/items?f=json&bbox=9.9769,53.5478,10.0031,53.5564&crs=http://www.opengis.net/def/crs/EPSG/0/25832
```

The guided example fetches this live (`guide_from_oaf=True`). Writing the
OAF response as GeoJSON is **off by default** (`write_geojson=False`).
Set `write_geojson=True` to persist:

- `alkis_nutzung_verkehr.geojson` — traffic types
- `alkis_nutzung_weitere.geojson` — all other types below

**Not used:** `GebaeudeBauwerk` in the same dataset, `lod2_hamburg`, HH-SIB centerlines.

## Typen (`nutzart`)

The guided DGM uses `GUIDE_NUTZARTEN` in `data_models/streets.py`. The standalone streets example is in `__local_dev/streets` (not part of the DGM app).

**Verkehr**

- `Strassenverkehr` — split further by `bez` into `Fahrbahn` and `Begleitfläche Straßenverkehr`
- `Weg`
- `Bahnverkehr`
- `Platz`
- `Schiffsverkehr`

**Siedlung**

- `Wohnbauflaeche`
- `Industrie Und Gewerbeflaeche`
- `Flaeche Gemischter Nutzung`
- `Flaeche Besonderer Funktionaler Praegung`

**Grünfläche**

- `Sport Freizeit Und Erholungsflaeche`

**Gewässer** (one n-gon per Fläche, no interior DGM points)

- `Fliessgewaesser` — shoreline Z kept
- `Stehendes Gewaesser` — one plane Z (median shoreline)
- `Hafenbecken`
- `Meer`

**Sonstiges**

- `Unland Vegetationslose Flaeche`
