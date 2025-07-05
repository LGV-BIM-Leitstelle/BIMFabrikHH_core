import inspect


def extract_psets_from_row(row, psets_module):
    """
    Dynamically extract all psets from a flat data row using all Pydantic pset models in the given module.
    Returns a dict: {pset_name: dict_of_properties}
    """
    psets = {}
    for name, pset_cls in inspect.getmembers(psets_module, inspect.isclass):
        if hasattr(pset_cls, "pset_name") and hasattr(pset_cls, "dict"):
            try:
                pset_obj = pset_cls(**row)
                pset_dict = pset_obj.dict(by_alias=True, exclude_unset=True)
                if any(v is not None for k, v in pset_dict.items() if k != "pset_name"):
                    psets[pset_cls.pset_name] = pset_dict
            except Exception:
                pass
    return psets


def assign_psets_to_element(model, element, psets, ifc_snippets):
    """
    Assigns all psets (dict of {pset_name: properties}) to the given IFC element.
    """
    import ifcopenshell.api.pset as pset_api

    for pset_name, props in psets.items():
        pset_ifc = ifc_snippets.add_psets(model, element, pset_name)
        pset_api.edit_pset(model, pset=pset_ifc, properties=props)
