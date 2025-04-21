from BIMFabrikHH.apps.stadtmodell.app import process_gml_to_ifc

if __name__ == "__main__":
    gml_files = [
        "LoD1_32_549_5937_1_HH.xml",
        # "LoD1_32_563_5943_1_HH.xml",
        # "LoD1_32_570_5946_1_HH.xml",
    ]
    gml_files = [
        "C:\_Lokale_Daten_ungesichert\__GitHubProjects\converter_ifc-to-xbau\local_files\stadtmodell\LoD2_32_565_5925_1_HH.xml",
        # "C:\_Lokale_Daten_ungesichert\__GitHubProjects\converter_ifc-to-xbau\local_files\stadtmodell\LoD2_32_565_5926_1_HH.xml",
        # "C:\_Lokale_Daten_ungesichert\__GitHubProjects\converter_ifc-to-xbau\local_files\stadtmodell\LoD2_32_566_5925_1_HH.xml",
        # "C:\_Lokale_Daten_ungesichert\__GitHubProjects\converter_ifc-to-xbau\local_files\stadtmodell\LoD2_32_566_5926_1_HH.xml",
    ]
    gml_files = [
        # "C:\_Lokale_Daten_ungesichert\__GitHubProjects\converter_ifc-to-xbau\local_files\stadtmodell\LoD2_32_565_5925_1_HH_transformiert.xml",
        "C:\_Lokale_Daten_ungesichert\__GitHubProjects\converter_ifc-to-xbau\local_files\stadtmodell\LoD2_32_565_5926_1_HH_transformiert.xml",
        "C:\_Lokale_Daten_ungesichert\__GitHubProjects\converter_ifc-to-xbau\local_files\stadtmodell\LoD2_32_566_5925_1_HH_transformiert.xml",
        "C:\_Lokale_Daten_ungesichert\__GitHubProjects\converter_ifc-to-xbau\local_files\stadtmodell\LoD2_32_566_5926_1_HH_transformiert.xml",
    ]
    folder_path = r"C:\Users\SalemAh\Downloads\Workshop CityGML\cityGML-ifc"
    # gml_files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

    # gml_files = ["LoD1_32_549_5937_1_HH.xml"]
    gml_files = [r"C:\_Lokale_Daten_ungesichert\CityGML_Hamburg\LoD1-DE_HH_2023-04-01\LoD1_32_565_5934_1_HH.xml"]

    stadtmodell = process_gml_to_ifc(gml_files, "Hamburg Buildings", "Hamburg Site", reset_model=True)
    print(f"Processed file: {gml_files}")
