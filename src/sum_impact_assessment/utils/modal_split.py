"""
Utilities for Modal Split KPI-group expansion.
"""
from typing import Dict, List
from ..schemas.core import KPIGroup, LivingLab

MODAL_SPLIT_GROUP_NAME = "modal split"
MODAL_SPLIT_KPI_NUMBERS = {"15", "15a", "15b", "15c"}

# Configure the transport-mode subgrouping for Modal Split analysis here.
# Key: subgroup label suffix in the group name
# Value: one or more transport mode types used as filter
MODAL_SPLIT_TRANSPORT_MODE_GROUPS: Dict[str, List[str]] = {
    "NSM": ["NSM"],
    "All private modes": ["PRIVATE", "PRIVATE_SUSTAINABLE", "PRIVATE_CAR"],
    "Sustainable private modes": ["PRIVATE_SUSTAINABLE"],
    "Private car": ["PRIVATE_CAR"],
    "Public transport": ["PUBLIC_TRANSPORT"],
    "Public Transport with NSM": ["NSM", "PUBLIC_TRANSPORT"],
}


def _normalize(value: str) -> str:
    return value.strip().lower()


def is_modal_split_group(kpi_group: KPIGroup) -> bool:
    """
    Identify Modal Split group by group name or KPI number (15 / 15a / 15b / 15c).
    """
    if _normalize(kpi_group.name) == MODAL_SPLIT_GROUP_NAME:
        return True

    for kpi in (kpi_group.kpis or []):
        kpi_number = getattr(kpi, "kpi_number", None)
        if kpi_number and _normalize(kpi_number) in MODAL_SPLIT_KPI_NUMBERS:
            return True

    return False


def _has_transport_mode_data(
    group: KPIGroup,
    mode_types: List[str],
    living_labs: List[LivingLab]
) -> bool:
    """Return True if any living lab has KPI data for the group and at least one requested mode type."""
    normalized_modes = {_normalize(mode_type) for mode_type in mode_types}

    for lab in living_labs:
        for kpi in lab.kpis:
            if kpi.id in group.kpi_ids and _normalize(kpi.transport_mode_type or "") in normalized_modes:
                return True
    return False


def expand_modal_split_groups(kpi_groups: List[KPIGroup], living_labs: List[LivingLab]) -> List[KPIGroup]:
    """
    Expand each Modal Split group into configured transport-mode sub-groups.
    Sub-groups without any matching transport-mode KPI data are skipped.

    Non-modal groups are returned unchanged.
    """
    expanded_groups: List[KPIGroup] = []

    for group in kpi_groups:
        if not is_modal_split_group(group):
            expanded_groups.append(group)
            continue

        for subgroup_label, mode_types in MODAL_SPLIT_TRANSPORT_MODE_GROUPS.items():
            if not _has_transport_mode_data(group, mode_types, living_labs):
                continue

            mode_suffix = _normalize(subgroup_label).replace(" ", "_")
            expanded_groups.append(
                KPIGroup(
                    id=f"{group.id}__{mode_suffix}",
                    name=f"{group.name} - {subgroup_label}",
                    kpi_ids=group.kpi_ids,
                    kpis=group.kpis,
                    transport_mode_type_filter=[
                        _normalize(mode_type)
                        for mode_type in mode_types
                    ],
                )
            )

    return expanded_groups
