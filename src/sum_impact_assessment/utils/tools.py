import json
from ..schemas.core import LivingLab, Measure, KPI, KPILivingLabResult, KPIGroup


def load_living_labs_from_file(file_path: str, kpi_definitions: list[KPI]) -> list[LivingLab]:
    """
    Load a list of LivingLab instances from a given JSON file path.
    For each lab, convert its kpis to KPILivingLabResult, extending the definition from kpi_definitions.
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
                kpis.append(KPILivingLabResult(**merged_data))
            else:
                # If no definition, just use the lab data
                kpis.append(KPILivingLabResult(**kpi_data))
        lab["kpis"] = kpis
        labs.append(LivingLab(**lab))
    return labs


def load_kpi_groups_from_file(file_path: str, kpi_definitions: list[KPI]) -> list[KPIGroup]:
    """
    Load a list of KPIGroup instances from a given JSON file path.
    For each group, populate the kpis field with KPI objects from kpi_definitions matching the group's kpi_ids.
    """
    with open(file_path, "r") as f:
        data = json.load(f)

    # Create a mapping from KPI id to KPI definition for easy lookup
    kpi_def_map = {kpi.id: kpi for kpi in kpi_definitions}

    groups = []
    for group in data:
        kpi_ids = group.get("kpi_ids", [])
        kpis = [kpi_def_map[kpi_id]
                for kpi_id in kpi_ids if kpi_id in kpi_def_map]
        groups.append(KPIGroup(
            id=group["id"],
            name=group["name"],
            kpi_ids=kpi_ids,
            kpis=kpis if kpis else None
        ))

    return groups


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
