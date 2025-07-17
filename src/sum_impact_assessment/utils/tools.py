import json
from ..schemas.core import LivingLab, Measure, KPI, KPILivingLab


def load_living_labs_from_file(file_path: str, kpi_definitions: list[KPI]) -> list[LivingLab]:
    """
    Load a list of LivingLab instances from a given JSON file path.
    For each lab, convert its kpis to KPILivingLab, extending the definition from kpi_definitions.
    """
    with open(file_path, "r") as f:
        data = json.load(f)

    # Create a mapping from KPI id to KPI definition for easy lookup
    kpi_def_map = {kpi.id: kpi for kpi in kpi_definitions}

    labs = []
    for lab in data:
        kpis = []
        living_lab_id = lab.get("id")
        for kpi_data in lab.get("kpis", []):
            kpi_id = kpi_data.get("id")
            kpi_def = kpi_def_map.get(kpi_id)
            if kpi_def:
                merged_data = {**kpi_def.model_dump(), **kpi_data,
                               'living_lab_id': living_lab_id}
                kpis.append(KPILivingLab(**merged_data))
            else:
                # If no definition, just use the lab data
                kpis.append(KPILivingLab(**kpi_data))
        lab["kpis"] = kpis
        labs.append(LivingLab(**lab))
    return labs


def load_measures_from_file(file_path: str) -> list[Measure]:
    """
    Load a list of Measures instances from a given JSON file path.
    """
    with open(file_path, "r") as f:
        data = json.load(f)
    return [Measure(**m) for m in data]


def load_kpis_from_file(file_path: str) -> list[KPI]:
    """
    Load a list of KPIs instances from a given JSON file path.
    """
    with open(file_path, "r") as f:
        data = json.load(f)
    return [KPI(**m) for m in data]
