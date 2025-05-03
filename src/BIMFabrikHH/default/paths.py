from pathlib import Path


class PathConfig:
    """
    Configuration class for managing file paths and constants.
    """

    # Get parent and grandparent paths
    parent = Path(__file__).parent
    parent_parent = Path(__file__).parent.parent
    parent_parent_parent = Path(__file__).parent.parent.parent
    PATH_STATIC = parent_parent_parent / "static_BIMFabrikHH"
    #
    # PATH_APP_VERSION = (
    #     "© 2025 Landesbetrieb Geoinformation und Vermessung | BIM-Leitstelle G42 | BIMFabrikHH | " "Version 24.001"
    # )
    # PATH_URL_FOOTER = "https://bim.hamburg.de/bim-lgv-612078"

    PATH_WORKFLOW_SMOBI = parent / "workflows" / "workflow_smobi.json"
    PATH_WORKFLOW_SBAUMK = parent / "workflows" / "workflow_strassenbk.json"
    PATH_WORKFLOW_ALLG = parent / "workflows" / "workflow_allgemein.json"

    PATH_LOG_TREE_01 = PATH_STATIC / "tree_001.png"
    PATH_LOG_TREE_02 = PATH_STATIC / "tree_002.png"
    PATH_LOG_TREE_03 = PATH_STATIC / "tree_003.png"
    PATH_LOG_TREE_04 = PATH_STATIC / "tree_004.png"
    PATH_LOG_TREE_05 = PATH_STATIC / "tree_005.png"

    PATH_STADTMODELL_LOD1 = PATH_STATIC / "lod1.png"
    PATH_STADTMODELL_LOD2 = PATH_STATIC / "lod2.png"
    PATH_STADTMODELL_LOD3 = PATH_STATIC / "lod3.png"

    # PROFILES_STADTMOBILIAR = parent / "profile_stadtmobiliar.xlsx"
    PROFILES_STADTMOBILIAR = r"C:\_Lokale_Daten_ungesichert\__GitHubProjects\BIMFabrikHH_intern\src\BIMFabrikHH_intern\default\profile_stadtmobiliar.xlsx"

    LOGO_HAMBURG = PATH_STATIC / "icons" / "Logo_Hamburg.png"

    LOGO_BIMFABRIK = PATH_STATIC / "Logo_BIMFabrik.png"
    LOGO_SMOBI = PATH_STATIC / "Logo_Stadtmobiliar.png"
    LOGO_BAUMMANAGER = PATH_STATIC / "Logo_BaumManager.png"
    LOGO_DGM = PATH_STATIC / "Logo_DGM.png"
    LOGO_STADTMODELL = PATH_STATIC / "Logo_Stadtmodell.png"
    KONZEPT_BIMFABRIK = PATH_STATIC / "konzept_bimfabrik.png"

    SAMPLES = Path(__file__).resolve().parents[3] / "samples"
    OUTPUT = Path(__file__).resolve().parents[3] / "output"

    # Workflow Stadtmobiliar example Sievekingsalleebruecke
    CODE_FILES_SIEVERKINGSALLEE = PATH_STATIC / "samples" / "Sieverkingsallee"
    IFC_DGM_01 = SAMPLES / "Sievekingsalleebruecke" / "dgms" / "merged_bricscad.ifc"
    IFC_DGM_02 = SAMPLES / "Sievekingsalleebruecke" / "dgms" / "13544_105_VM_B_MF_012_--_o_TM_DGM-Bruecke.ifc"
    IFC_DGM_03 = SAMPLES / "Sievekingsalleebruecke" / "dgms" / "13544_105_VM_B_MF_008_--_o_TM_DGM.ifc"

    # Workflow Stadtmobiliar example Buschwerder_HD
    CODE_FILES_BUSCHWERDER_HD = PATH_STATIC / "samples" / "Buschwerder_HD"
    IFC_DGM_BUSCHWERDER_HD = SAMPLES / "Buschwerder_HD" / "14364_BWH_VM_B_MF_002_-_o_TM_DGM.ifc"

    EXCEL_COORDINATES = SAMPLES / "excelliste.xlsx"


if __name__ == "__main__":
    PathConfig()
    print(PathConfig.SAMPLES)
