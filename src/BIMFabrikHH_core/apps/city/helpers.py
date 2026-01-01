import logging
import time

from BIMFabrikHH_core.config.attribute_map import attribute_map
from BIMFabrikHH_core.data_models.pydantic_psets_city_model import CityModelAttributes

logger = logging.getLogger("city_helpers")


def extract_attributes_from_xml(building_element, ns, lod=None, timing_stats=None) -> CityModelAttributes:
    if timing_stats is not None:
        attr_start = time.perf_counter()

    attributes = CityModelAttributes()
    for field, (xpath, cast) in attribute_map.items():
        value = building_element.xpath(xpath, namespaces=ns)
        if value:
            try:
                raw_value = value[0].text
                setattr(attributes, field, cast(raw_value))
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(f"Could not set {field}: {e}")
    if lod is not None:
        attributes.stadtmodell_lod = lod

    if timing_stats is not None:
        attr_end = time.perf_counter()
        timing_stats["attribute_extraction"] += attr_end - attr_start

    return attributes
