from BIMFabrikHH.core.ifc_snippets import IfcSnippets
from BIMFabrikHH.core.ifc_utils import IfcFileCreator
from BIMFabrikHH.default.pset_data import pset_objectinfo_data, pset_hyperlinkdata
from BIMFabrikHH.pydantic_models.pydantic_ifcproject import IfcProject
from BIMFabrikHH.pydantic_models.pydantic_psets_BIMHH import (
    Pset_Objektinformation,
    Pset_Hyperlink,
)


class IfcModelBuilder:
    """
    A class to encapsulate the process of creating an IFC model.

    """

    def __init__(self):
        """
        Initializes StadtmobiliarModeller with necessary components and property sets.
        """

        self.ifc_snippets = IfcSnippets()
        self.ifc_creator = IfcFileCreator()
        self.model = self.ifc_creator.create_model("ifc4")

        self.all_psets = None
        self.body = None
        self.building = None
        self.element_manager = None
        self.model3d = None
        self.plan = None
        self.project = None
        self.pset_classes = None
        self.site = None

    def reset_model(self):
        """
        Resets the model and initializes necessary components.
        """
        self.model = self.ifc_creator.create_model("ifc4")
        self.all_psets = None
        self.body = None
        self.building = None
        self.element_manager = None
        self.model3d = None
        self.plan = None
        self.project = None
        self.pset_classes = None
        self.site = None

    @staticmethod
    def _initialize_psets(*args) -> list:
        """
        Initialize property sets based on provided Pset classes and their data.

        Args:
            *args: Alternating Pset classes and their corresponding data dictionaries.

        Returns:
            list: A list of instantiated property set objects.

        Example:
            _initialize_psets(Pset_Objektinformation, pset_objectinfo_data,
                              Pset_Modellinformation, pset_modellinfo_data)
        """
        return [pset_class(**pset_data) for pset_class, pset_data in zip(args[::2], args[1::2])]

    def build_project(self, project_info_dict: dict, site_name: str):
        """
        Builds the IFC project with the given project information and type.

        Returns:
            None
        """

        # step 1 create Project (User input)
        project_info_pyd = IfcProject(**project_info_dict)
        self.project, self.site, self.building = self.ifc_creator.create_project(
            self.model, project_info_pyd, site_name
        )

        # step 2 Add units to the IFC model
        self.ifc_creator.create_units_meter(self.model)

        # step 3 Add contexts for the representation
        self.model3d, self.plan, self.body = self.ifc_creator.create_representations(self.model)

    def setup_psets(self):
        # step 4 Initialize property sets (User input)
        self.pset_classes = self._initialize_psets(
            Pset_Objektinformation,
            pset_objectinfo_data,
            # Pset_Modellinformation,
            # pset_modellinfo_data,
            # Pset_Georeferenzierung,
            # pset_geo_data_utm,
            Pset_Hyperlink,
            pset_hyperlinkdata,
        )

        self.all_psets = [pset.pset_name for pset in self.pset_classes]

    def combine_georeferencing(self):
        # Step 7 Georeferencing (User input)
        self.ifc_creator.create_georeference(self.model)
        self.ifc_creator.edit_georeference(self.model)

    def get_model(self):
        return self.model

    def get_site(self):
        return self.site
