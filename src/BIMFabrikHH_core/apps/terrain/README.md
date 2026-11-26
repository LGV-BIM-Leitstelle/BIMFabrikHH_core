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
https://api.hamburg.de/datasets/v1/alkis_vereinfacht/collections/Nutzung/items?f=json&bbox=9.9769,53.5478,9.991435,53.55622&crs=http://www.opengis.net/def/crs/EPSG/0/25832
```

The terrain apps do not load it themselves: pass the records as `guide_records`.
The guided examples read `examples/assets/alkis_nutzung_example.geojson`, downloaded
once for the example bbox (delete it to fetch a fresh one). Other callers can use
`load_guide_records_from_oaf(bbox)` from `data_models/streets.py`; with
`write_geojson=True, output_dir=...` it also persists:

- `alkis_nutzung_verkehr.geojson` — traffic types
- `alkis_nutzung_weitere.geojson` — all other types below

**Not used:** `GebaeudeBauwerk` in the same dataset, `lod2_hamburg`, HH-SIB centerlines.

## Typen (`nutzart`)

The guided DGM uses `GUIDE_NUTZARTEN` in `data_models/streets.py`.

**Verkehr**

- `Strassenverkehr` — split further by `bez` into `Fahrbahn`, `Begleitfläche Straßenverkehr`, `Busbahnhof`, `Fußgängerzone`, and `Parkplatz` (the last three use the Begleitfläche colour)
- `Weg`
- `Bahnverkehr`
- `Platz`
- `Schiffsverkehr`

**Siedlung** (merged into one dark-sand `Parcels` object when `merge_parcels=True`, the guided default)

- `Wohnbauflaeche`
- `Industrie Und Gewerbeflaeche`
- `Flaeche Gemischter Nutzung`
- `Flaeche Besonderer Funktionaler Praegung`

Leftover DGM (Gebäude / no Nutzung) stays its own object so gap
triangles do not stitch getrennte Flächen together.
`split_by_landuse=True` keeps one object per type instead. Bruchkanten stay in the TIN.

**Grünfläche**

- `Sport Freizeit Und Erholungsflaeche`

**Gewässer** (shoreline Delaunay, no interior DGM points; triangles outside the ring are dropped). After the split, water rings are cut out of every other part so the Fläche underneath is holed.

- `Stehendes Gewaesser` / `Hafenbecken` / `Meer` / `Fliessgewaesser` / `Schiffsverkehr` — one plane per ring at the **median** shoreline Z; land vertices on that ring snap to the same plane. Opposite Ufer are not allowed to tilt the surface.

**Sonstiges** (also merged into `Parcels` when `merge_parcels=True`)

- `Unland Vegetationslose Flaeche`
