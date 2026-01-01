import inspect
from typing import Any, Dict

import ifcopenshell
from ifcopenshell.api.pset import add_pset, edit_pset


def extract_psets_from_row(row: Dict[str, Any], psets_module: Any) -> Dict[str, Dict[str, Any]]:
    """
    Dynamically extract all psets from a flat data row using all Pydantic pset models in the given module.

    This function inspects the provided module for Pydantic classes that have a 'pset_name' attribute
    and attempts to create instances from the row data. Only psets with at least one non-None value
    (excluding the pset_name itself) are included in the result.

    Args:
        row: Dictionary containing flat data with property names as keys.
        psets_module: Module containing Pydantic pset model classes.

    Returns:
        Dictionary mapping pset names to their property dictionaries.
        Format: {pset_name: {property_name: property_value}}
    """
    psets = {}
    for name, pset_cls in inspect.getmembers(psets_module, inspect.isclass):
        if hasattr(pset_cls, "pset_name") and hasattr(pset_cls, "dict"):
            try:
                pset_obj = pset_cls(**row)
                pset_dict = pset_obj.dict(by_alias=True, exclude_unset=True)
                if any(v is not None for k, v in pset_dict.items() if k != "pset_name"):
                    psets[pset_cls.pset_name] = pset_dict
            except (ValueError, TypeError, KeyError):
                pass
    return psets


def assign_psets_to_element(
    model: ifcopenshell.file, element: ifcopenshell.entity_instance, psets: Dict[str, Dict[str, Any]], ifc_snippets: Any
) -> None:
    """
    Assigns all psets (dict of {pset_name: properties}) to the given IFC element.

    This function creates IFC property sets and assigns them to the specified element.
    Each pset in the input dictionary becomes an IfcPropertySet attached to the element.

    Args:
        model: The IFC model instance.
        element: The IFC element to assign property sets to.
        psets: Dictionary mapping pset names to their property dictionaries.
               Format: {pset_name: {property_name: property_value}}
        ifc_snippets: IFC snippets utility object (unused in current implementation).
    """
    for pset_name, props in psets.items():
        pset_ifc = add_pset(model, product=element, name=pset_name)
        edit_pset(model, pset=pset_ifc, properties=props)
