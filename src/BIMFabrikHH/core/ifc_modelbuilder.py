from typing import Optional

from ..default.pset_data import pset_hyperlinkdata, pset_objectinfo_data
from ..pydantic_models.pydantic_psets_BIMHH import Pset_Hyperlink, Pset_Objektinformation
from .ifc_snippets import IfcSnippets
from .ifc_utils import IfcFileCreator


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

    def get_site(self):
        return self.site

    def get_building(self):
        return self.building

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

    def build_project(self, project_name: str, site_name: Optional[str], building_name: Optional[str]):
        """
        Builds the IFC project with the given project information and type.

        Arguments:
            site_name (Optional[str]): The name of the site (optional).
            building_name (Optional[str]): The name of the building (optional).

        Returns:
            None
        """
        try:

            # create project in the IFC model using the creator's method
            self.project, self.site, self.building = self.ifc_creator.create_project(
                self.model, project_name, site_name, building_name
            )

            # Add units to the IFC model (e.g., meters)
            self.ifc_creator.create_units_meter(self.model)

            # Add contexts for the representation (3D, plan, body)
            self.model3d, self.plan, self.body = self.ifc_creator.create_representations(self.model)

        except Exception as e:
            print(f"Error during project creation: {e}")
            raise

    def setup_psets(self):
        # Initialize property sets (User input)
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
        # Georeferencing (User input)
        self.ifc_creator.create_georeference(self.model)
        self.ifc_creator.edit_georeference(self.model)

    def get_model(self):
        return self.model
