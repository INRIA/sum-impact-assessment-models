"""
KPI Results Simulation Service - Generates mock KPI data for testing.
"""
from typing import List, Dict, Any
from datetime import date
from sqlalchemy import text
from sqlalchemy.orm import Session
import random
from ..database.models.kpi_result import KpiResult
from ..utils.logger import get_logger

logger = get_logger(__name__)


class KpiResultsSimulationService:
    """
    Service for generating mock KPI results data for testing purposes.

    This service:
    1. Cleans up existing results for the target year
    2. Retrieves baseline KPI results from a specified year
    3. Applies random variations to baseline values
    4. Saves new mock results with a target year date
    """

    def __init__(self, session: Session):
        """
        Initialize the simulation service.

        Args:
            session: Database session for queries and inserts
        """
        self.session = session

    def _delete_results_by_year(self, target_year: int) -> int:
        """
        Delete all KPI results for the specified year to avoid duplicates.

        Args:
            target_year: Year for which to delete all results

        Returns:
            Number of records deleted
        """
        logger.info(f"Deleting existing KPI results for year {target_year}")

        query = text("""
            DELETE FROM kpiresults 
            WHERE YEAR(date) = :target_year
        """)

        result = self.session.execute(query, {"target_year": target_year})
        self.session.commit()

        deleted_count = result.rowcount
        logger.info(
            f"Deleted {deleted_count} existing records for year {target_year}")

        return deleted_count

    def _get_results_by_year(self, year: int) -> List[Dict[str, Any]]:
        """
        Retrieve all KPI results for a specific year.

        Args:
            year: Year to retrieve results from

        Returns:
            List of KPI result dictionaries with keys:
                kpidefinition_id, living_lab_id, transport_mode_id, value
        """
        logger.debug(f"Fetching KPI results for year {year}")

        query = text("""
            SELECT 
                kpidefinition_id,
                living_lab_id,
                transport_mode_id,
                value
            FROM kpiresults
            WHERE YEAR(date) = :year
        """)

        result = self.session.execute(query, {"year": year})
        columns = result.keys()
        results = [dict(zip(columns, row)) for row in result.fetchall()]

        logger.debug(f"Fetched {len(results)} KPI results for year {year}")
        return results

    def _generate_mock_results(
        self,
        baseline_results: List[Dict[str, Any]],
        target_year: int,
        min_variation: float,
        max_variation: float
    ) -> List[KpiResult]:
        """
        Generate mock KPI results by applying random variations to baseline values.

        Args:
            baseline_results: List of baseline KPI result dictionaries
            target_year: Year to assign to the new mock results
            min_variation: Minimum variation multiplier (e.g., 0.5 for -50%)
            max_variation: Maximum variation multiplier (e.g., 1.5 for +50%)

        Returns:
            List of KpiResult ORM objects ready to be saved
        """
        logger.info(
            f"Generating mock results with variation range [{min_variation}, {max_variation}]"
        )

        mock_results = []
        target_date = date(target_year, 12, 1)  # December 1st of target year

        for baseline in baseline_results:
            # Apply random variation
            variation_factor = random.uniform(min_variation, max_variation)
            new_value = baseline['value'] * variation_factor

            # Create new KpiResult object
            mock_result = KpiResult(
                kpidefinition_id=baseline['kpidefinition_id'],
                living_lab_id=baseline['living_lab_id'],
                transport_mode_id=baseline['transport_mode_id'],
                value=new_value,
                date=target_date
            )
            mock_results.append(mock_result)

        logger.debug(f"Generated {len(mock_results)} mock KPI results")
        return mock_results

    def _save_results(self, mock_results: List[KpiResult]) -> int:
        """
        Save mock KPI results to the database using bulk insert.

        Args:
            mock_results: List of KpiResult ORM objects to save

        Returns:
            Number of records saved
        """
        logger.info(f"Saving {len(mock_results)} mock KPI results to database")

        self.session.bulk_save_objects(mock_results)
        self.session.commit()

        logger.info(f"Successfully saved {len(mock_results)} mock results")
        return len(mock_results)

    def run(
        self,
        baseline_years: List[int] = [2017, 2023, 2024],
        target_year: int = 2025,
        min_variation: float = 0.5,
        max_variation: float = 1.5
    ) -> Dict[str, Any]:
        """
        Execute the full KPI results simulation workflow.

        This method:
        1. Validates input parameters
        2. Cleans up existing results for the target year
        3. Retrieves baseline results from the baseline year
        4. Generates mock results with random variations
        5. Saves the new results to the database

        Args:
            baseline_year: Year to use as baseline for simulation (default: 2023)
            target_year: Year to assign to generated results (default: 2025)
            min_variation: Minimum variation multiplier (default: 0.5 for -50%)
            max_variation: Maximum variation multiplier (default: 1.5 for +50%)

        Returns:
            Dictionary with summary:
                {
                    "deleted": int,
                    "baseline_year": int,
                    "target_year": int,
                    "generated": int
                }

        Raises:
            ValueError: If parameters are invalid (e.g., baseline_year >= target_year,
                       min_variation >= max_variation, negative values)
        """
        # Validate parameters
        for baseline_year in baseline_years:
            if baseline_year >= target_year:
                raise ValueError(
                    f"baseline_year ({baseline_year}) must be less than target_year ({target_year})"
                )

        if min_variation >= max_variation:
            raise ValueError(
                f"min_variation ({min_variation}) must be less than max_variation ({max_variation})"
            )

        if min_variation <= 0 or max_variation <= 0:
            raise ValueError(
                f"Variation values must be positive (min: {min_variation}, max: {max_variation})"
            )

        try:
            # Step 1: Clean up existing target year results
            deleted_count = self._delete_results_by_year(target_year)

            baseline_results = []
            for baseline_year in baseline_years:
                logger.info(
                    f"Starting KPI results simulation",
                    extra={
                        "baseline_year": baseline_year,
                        "target_year": target_year,
                        "min_variation": min_variation,
                        "max_variation": max_variation
                    }
                )

                # Step 2: Retrieve baseline year results
                baseline_r_year = self._get_results_by_year(baseline_year)
                if not baseline_r_year:
                    logger.warning(
                        f"No baseline results found for year {baseline_year}")
                    return {
                        "deleted": deleted_count,
                        "baseline_year": baseline_year,
                        "target_year": target_year,
                        "generated": 0
                    }
                baseline_results.extend(baseline_r_year)

            # Step 3: Generate mock results with variations
            mock_results = self._generate_mock_results(
                baseline_results=baseline_results,
                target_year=target_year,
                min_variation=min_variation,
                max_variation=max_variation
            )

            # Step 4: Save to database
            generated_count = self._save_results(mock_results)

            summary = {
                "deleted": deleted_count,
                "baseline_year": baseline_year,
                "target_year": target_year,
                "generated": generated_count
            }

            logger.info(
                "KPI results simulation completed successfully",
                extra=summary
            )

            return summary

        except Exception as e:
            logger.error(
                f"KPI results simulation failed: {str(e)}",
                exc_info=True
            )
            self.session.rollback()
            raise
