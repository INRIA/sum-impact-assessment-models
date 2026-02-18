"""
Service for transforming raw database results into Pydantic schemas.
"""
from typing import List, Dict, Any
from ..schemas.core import KPI, Measure, KPILivingLabResult, LivingLab, KPIGroup
from ..utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class AnalysisDataTransformer:
    """
    Transforms raw database query results into Pydantic schema objects
    required for KPIImpactAnalyzer.
    """

    @staticmethod
    def transform_kpis(raw_kpis: List[Dict[str, Any]]) -> List[KPI]:
        """
        Transform raw KPI definitions from database to KPI schema objects.

        Args:
            raw_kpis: List of dictionaries from database query

        Returns:
            List of KPI schema objects

        Note:
            You need to customize the field mapping based on your actual database schema.
            Example mapping (adjust field names as needed):
            - id: kpi definition ID
            - name: KPI name
            - progression_target: expected direction (0=decrease, 1=increase)
            - value_type: type of KPI value
            - value_min: minimum possible value
            - value_max: maximum possible value
        """
        logger.debug(f"Transforming {len(raw_kpis)} KPI definitions")

        kpis = []
        for raw_kpi in raw_kpis:
            kpi_data = {
                'id': str(raw_kpi.get('id')),
                'name': raw_kpi.get('name'),
                'progression_target': raw_kpi.get('progression_target', 1),
                'value_type': raw_kpi.get('metric'),
                'value_min': raw_kpi.get('min_value'),
                'value_max': raw_kpi.get('max_value'),
                'parent_kpi_id': str(raw_kpi.get('parent_kpi_id')) if raw_kpi.get('parent_kpi_id') is not None else None,
                'parent_kpi_name': raw_kpi.get('parent_kpi_name') if raw_kpi.get('parent_kpi_name') is not None else None,
            }

            try:
                kpi = KPI(**kpi_data)
                kpis.append(kpi)
            except Exception as e:
                logger.warning(
                    f"Failed to transform KPI {raw_kpi.get('id')}: {e}")
                continue

        logger.debug(f"Successfully transformed {len(kpis)} KPIs")
        return kpis

    @staticmethod
    def transform_measures(raw_measures: List[Dict[str, Any]]) -> List[Measure]:
        """
        Transform raw measure data from database to Measure schema objects.

        Args:
            raw_measures: List of dictionaries from database query

        Returns:
            List of Measure schema objects

        Note:
            Customize field mapping based on your projects table schema.
        """
        logger.debug(f"Transforming {len(raw_measures)} measures")

        measures = []
        for raw_measure in raw_measures:
            measure_data = {
                'id': str(raw_measure.get('id')),
                'name': raw_measure.get('name'),
            }

            try:
                measure = Measure(**measure_data)
                measures.append(measure)
            except Exception as e:
                logger.warning(
                    f"Failed to transform Measure {raw_measure.get('id')}: {e}")
                continue

        logger.debug(f"Successfully transformed {len(measures)} measures")

        return measures

    @staticmethod
    def transform_kpi_groups(raw_groups: List[Dict[str, Any]]) -> List[KPIGroup]:
        """
        Transform raw KPI group data from database to KPIGroup schema objects.

        Args:
            raw_groups: List of dictionaries containing group data with kpi_ids

        Returns:
            List of KPIGroup schema objects
        """
        logger.debug(f"Transforming {len(raw_groups)} KPI groups")

        distinct_group_id = set()
        for group in raw_groups:
            distinct_group_id.add(group.get('id'))
        logger.debug(f"Distinct KPI group IDs found: {distinct_group_id}")

        kpi_groups = []
        for group_id in distinct_group_id:
            raw_group = next(
                (g for g in raw_groups if g.get('id') == group_id), None)
            kpi_ids = [str(g.get('kpidefinition_id'))
                       for g in raw_groups if g.get('id') == group_id]
            kpis = [{'id': str(g.get('kpidefinition_id')),
                     'name': g.get('kpidefinition_name'),
                     'kpi_number': g.get('kpidefinition_kpi_number'),
                     'progression_target': g.get('kpidefinition_progression_target'),
                     'value_min': g.get('kpidefinition_min_value'),
                     'value_max': g.get('kpidefinition_max_value'),
                     'value_type': g.get('kpidefinition_metric'),
                     'parent_kpi_id': str(g.get('parent_kpi_id')) if g.get('parent_kpi_id') is not None else None,
                     'parent_kpi_name': g.get('parent_kpi_name') if g.get('parent_kpi_name') is not None else None,
                     'parent_kpi_number': g.get('parent_kpi_number') if g.get('parent_kpi_number') is not None else None
                     }
                    for g in raw_groups if g.get('id') == group_id]

            if not raw_group:
                continue

            # Raw groups should already have kpi_ids as a list from the repository
            group_data = {
                'id': str(raw_group.get('id')),
                'name': raw_group.get('name'),
                'kpi_ids': kpi_ids,
                'kpis': kpis
            }

            try:
                kpi_group = KPIGroup(**group_data)
                kpi_groups.append(kpi_group)
            except Exception as e:
                logger.warning(
                    f"Failed to transform KPIGroup {raw_group.get('id')}: {e}")
                continue

        logger.info(f"Successfully transformed {len(kpi_groups)} KPI groups")
        return kpi_groups

    @staticmethod
    def transform_living_labs(
        raw_living_labs: List[Dict[str, Any]],
        raw_lab_measures: List[Dict[str, Any]],
        raw_lab_kpi_results: List[Dict[str, Any]],
    ) -> List[LivingLab]:
        """
        Transform raw living lab data into LivingLab schema objects.

        This method merges three data sources:
        1. Living lab measure implementations
        2. KPI results (before/after values)
        3. KPI definitions (for metadata)

        Args:
            raw_lab_measures: Living lab measure associations from database
            raw_kpi_results: KPI results with before/after values
            kpi_definitions: List of KPI definition objects

        Returns:
            List of LivingLab schema objects with KPIs and measures populated

        Note:
            Customize field mapping based on your database schema.
        """
        logger.debug("Transforming living labs data")

        # Group measures by living lab
        lab_measures_map = {}
        for raw_lab_measure in raw_lab_measures:
            lab_id = str(raw_lab_measure.get('lab_id'))
            measure_id = str(raw_lab_measure.get(
                'project_id'))
            measure_name = raw_lab_measure.get(
                'project_name', 'Unknown')

            if lab_id not in lab_measures_map:
                lab_measures_map[lab_id] = {
                    'id': lab_id,
                    'name': raw_lab_measure.get('lab_name', f'Lab {lab_id}'),
                    'measures': []
                }

            lab_measures_map[lab_id]['measures'].append(
                Measure(id=measure_id, name=measure_name, times_implemented=1
                        ))

        # Group KPI results by living lab
        lab_kpis_result_map = {}
        for raw_kpi_result in raw_lab_kpi_results:
            lab_id = str(raw_kpi_result.get('living_lab_id'))
            kpi_id = str(raw_kpi_result.get('kpidefinition_id'))

            if lab_id not in lab_kpis_result_map:
                lab_kpis_result_map[lab_id] = []

            # Merge KPI definition with living lab specific values
            kpi_living_lab_data = {
                # kpi definition fields
                'id': kpi_id,
                'name': raw_kpi_result.get('name'),
                'parent_kpi_id': str(raw_kpi_result.get('kpi_parent_id')) if raw_kpi_result.get('kpi_parent_id') is not None else None,
                'parent_kpi_name': raw_kpi_result.get('parent_kpi_name') if raw_kpi_result.get('parent_kpi_name') is not None else None,
                'progression_target': raw_kpi_result.get('progression_target', None),
                'value_type': raw_kpi_result.get('metric', None),
                'value_min': raw_kpi_result.get('min_value', None),
                'value_max': raw_kpi_result.get('max_value', None),
                # living lab kpi result
                'living_lab_id': lab_id,
                'value_before': raw_kpi_result.get('value_before'),
                'value_after': raw_kpi_result.get('value_after'),
                'abs_variation': None,
                'variation': None,
                # New fields for transport mode, if applicable (e.g. Modal Split KPIs)
                'transport_mode_id': str(raw_kpi_result.get('transport_mode_id')) if raw_kpi_result.get('transport_mode_id') is not None else None,
                'transport_mode_name': raw_kpi_result.get('transport_mode_name') if raw_kpi_result.get('transport_mode_name') is not None else None,
            }

            try:
                kpi_living_lab = KPILivingLabResult(**kpi_living_lab_data)
                lab_kpis_result_map[lab_id].append(kpi_living_lab)
            except Exception as e:
                logger.warning(
                    f"Failed to create KPILivingLabResult for lab {lab_id}, KPI {kpi_id}: {e}")
                continue

        # Combine into LivingLab objects
        living_labs = []

        for raw_lab_data in raw_living_labs:
            lab_id = str(raw_lab_data.get('id'))
            lab_name = raw_lab_data.get('name', f'Lab {lab_id}')

            living_lab_dict = {
                'id': lab_id,
                'name': lab_name,
                'kpis': lab_kpis_result_map.get(lab_id, []),
                'measures': lab_measures_map.get(lab_id, {}).get('measures', [])
            }

            try:
                living_lab = LivingLab(**living_lab_dict)
                living_labs.append(living_lab)
            except Exception as e:
                logger.warning(f"Failed to create LivingLab {lab_id}: {e}")
                continue

        logger.debug(
            f"Successfully transformed {len(living_labs)} living labs")
        return living_labs
