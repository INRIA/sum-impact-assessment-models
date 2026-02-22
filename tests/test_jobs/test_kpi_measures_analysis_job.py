"""
Unit tests for KpiMeasuresAnalysisJob.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import numpy as np
from src.sum_impact_assessment.services.kpi_measures_analysis_job import KpiMeasuresAnalysisJob
from src.sum_impact_assessment.schemas.job import JobStatusEnum
from src.sum_impact_assessment.schemas.impact_analysis import KPIGroupImpactOutput, MeasureImpactCoefficient
from src.sum_impact_assessment.schemas.core import KPIGroup, KPI, LivingLab, Measure, KPILivingLabResult
from src.sum_impact_assessment.utils.modal_split import MODAL_SPLIT_TRANSPORT_MODE_GROUPS


class TestKpiMeasuresAnalysisJob:
    """Test suite for KpiMeasuresAnalysisJob."""

    @patch("src.sum_impact_assessment.services.kpi_measures_analysis_job.KPIImpactAnalyzer")
    @patch("src.sum_impact_assessment.services.analysis_data_service.AnalysisDataRepository")
    @patch("src.sum_impact_assessment.services.kpi_measures_analysis_job.JobRepository")
    def test_job_runs_successfully(
        self,
        mock_job_repo_class,
        mock_analysis_repo_class,
        mock_analyzer_class
    ):
        """Test that the job executes successfully and updates status correctly."""
        # Setup mocks
        mock_db = Mock()
        job_id = "test-job-123"

        # Mock JobRepository
        mock_job_repo = Mock()
        mock_job_repo_class.return_value = mock_job_repo

        # Mock AnalysisDataRepository
        mock_analysis_repo = Mock()
        mock_analysis_repo.get_kpi_groups.return_value = []
        mock_analysis_repo.get_kpi_definitions.return_value = []
        mock_analysis_repo.get_measures.return_value = []
        mock_analysis_repo.get_living_lab_measures.return_value = []
        mock_analysis_repo.get_living_lab_kpi_results.return_value = []
        mock_analysis_repo.get_living_labs.return_value = []
        mock_analysis_repo_class.return_value = mock_analysis_repo

        # Mock KPIImpactAnalyzer
        mock_analyzer = Mock()
        mock_result = Mock(spec=KPIGroupImpactOutput)
        mock_analyzer.run_analysis.return_value = [mock_result]
        mock_analyzer_class.return_value = mock_analyzer

        # Run the job
        KpiMeasuresAnalysisJob.run(job_id, mock_db)

        # Verify job status updates
        assert mock_job_repo.update_job_status.call_count == 2

        # Verify STARTED status update
        first_call = mock_job_repo.update_job_status.call_args_list[0]
        assert first_call[1]["job_id"] == job_id
        assert first_call[1]["status"] == JobStatusEnum.STARTED
        assert "started_at" in first_call[1]

        # Verify SUCCESS status update
        second_call = mock_job_repo.update_job_status.call_args_list[1]
        assert second_call[1]["job_id"] == job_id
        assert second_call[1]["status"] == JobStatusEnum.SUCCESS
        assert "completed_at" in second_call[1]
        assert second_call[1]["message"].startswith("Analysis completed")

        # Verify repository methods were called
        mock_analysis_repo.get_kpi_definitions.assert_called_once()
        mock_analysis_repo.get_measures.assert_called_once()
        mock_analysis_repo.get_kpi_groups.assert_called_once()
        mock_analysis_repo.get_living_lab_measures.assert_called_once()
        mock_analysis_repo.get_living_lab_kpi_results.assert_called_once()
        mock_analysis_repo.get_living_labs.assert_called_once()

        # run analysis was not called since no kpi groups
        mock_analyzer.run_analysis_group.assert_not_called()

    @patch("src.sum_impact_assessment.services.analysis_data_service.AnalysisDataRepository")
    @patch("src.sum_impact_assessment.services.kpi_measures_analysis_job.JobRepository")
    def test_job_handles_database_error(
        self,
        mock_job_repo_class,
        mock_analysis_repo_class
    ):
        """Test that the job handles database errors and updates status to FAILURE."""
        # Setup mocks
        mock_db = Mock()
        job_id = "test-job-456"

        # Mock JobRepository
        mock_job_repo = Mock()
        mock_job_repo_class.return_value = mock_job_repo

        # Mock AnalysisDataRepository to raise an exception
        mock_analysis_repo = Mock()
        mock_analysis_repo.get_kpi_definitions.side_effect = Exception(
            "Database connection error")
        mock_analysis_repo_class.return_value = mock_analysis_repo

        # Run the job
        KpiMeasuresAnalysisJob.run(job_id, mock_db)

        # Verify job status updates
        assert mock_job_repo.update_job_status.call_count == 2

        # Verify STARTED status update
        first_call = mock_job_repo.update_job_status.call_args_list[0]
        assert first_call[1]["status"] == JobStatusEnum.STARTED

        # Verify FAILURE status update
        second_call = mock_job_repo.update_job_status.call_args_list[1]
        assert second_call[1]["job_id"] == job_id
        assert second_call[1]["status"] == JobStatusEnum.FAILURE
        assert "Database connection error" in second_call[1]["message"]
        assert "completed_at" in second_call[1]

    @patch("src.sum_impact_assessment.services.kpi_measures_analysis_job.KPIImpactAnalyzer")
    @patch("src.sum_impact_assessment.services.analysis_data_service.AnalysisDataRepository")
    @patch("src.sum_impact_assessment.services.kpi_measures_analysis_job.JobRepository")
    def test_job_saves_input_output_data_structure(
        self,
        mock_job_repo_class,
        mock_analysis_repo_class,
        mock_analyzer_class
    ):
        """
        Test that input and output data are correctly saved with proper structure.

        Test scenario:
        - 2 KPI definitions (Air Quality Index, Public Transport Usage)
        - 1 measure (Bike Lane Expansion)
        - 1 KPI group (Environmental Impact) with 1 KPI
        - 1 living lab (Paris Living Lab)
        - 1 KPI result for the lab
        """
        # Setup mocks
        mock_db = Mock()
        job_id = "integration-test-123"

        # Mock JobRepository
        mock_job_repo = Mock()
        mock_job_repo_class.return_value = mock_job_repo

        # Prepare realistic test data - 2 KPI definitions
        raw_kpi_definitions = [
            {
                "id": 1,
                "name": "Air Quality Index",
                "progression_target": 0,  # Lower is better
                "metric": "score",
                "min_value": 0.0,
                "max_value": 500.0
            },
            {
                "id": 2,
                "name": "Public Transport Usage",
                "progression_target": 1,  # Higher is better
                "metric": "percentage",
                "min_value": 0.0,
                "max_value": 100.0
            }
        ]

        # 1 measure
        raw_measures = [
            {"id": 101, "name": "Bike Lane Expansion"}
        ]

        # 1 KPI group with 1 KPI
        raw_kpi_groups = [
            {
                "id": 201,
                "name": "Environmental Impact",
                "kpidefinition_id": 1,
                "kpidefinition_name": "Air Quality Index",
                "kpidefinition_progression_target": 0,
                "kpidefinition_min_value": 0.0,
                "kpidefinition_max_value": 500.0,
                "kpidefinition_metric": "score"
            }
        ]

        # 1 living lab
        raw_living_labs = [
            {"id": 301, "name": "Paris Living Lab"}
        ]

        # Lab implements the measure
        raw_lab_measures = [
            {
                "lab_id": 301,
                "lab_name": "Paris Living Lab",
                "project_id": 101,
                "project_name": "Bike Lane Expansion"
            }
        ]

        # 1 KPI result for the lab
        raw_kpi_results = [
            {
                "kpidefinition_id": 1,
                "transport_mode_id": 1,
                "transport_mode_name": "Bicycle",
                "transport_mode_type": "NSM",
                "living_lab_id": 301,
                "value_before": 150.0,
                "date_before": datetime(2023, 1, 1),
                "value_after": 120.0,
                "date_after": datetime(2023, 12, 31),
                "name": "Air Quality Index",
                "progression_target": 0,
                "min_value": 0.0,
                "max_value": 500.0,
                "metric": "score"
            }
        ]

        # Mock AnalysisDataRepository
        mock_analysis_repo = Mock()
        mock_analysis_repo.get_kpi_definitions.return_value = raw_kpi_definitions
        mock_analysis_repo.get_measures.return_value = raw_measures
        mock_analysis_repo.get_kpi_groups.return_value = raw_kpi_groups
        mock_analysis_repo.get_living_labs.return_value = raw_living_labs
        mock_analysis_repo.get_living_lab_measures.return_value = raw_lab_measures
        mock_analysis_repo.get_living_lab_kpi_results.return_value = raw_kpi_results
        mock_analysis_repo_class.return_value = mock_analysis_repo

        # Mock KPIImpactAnalyzer - returns a mocked KPIGroupImpactOutput
        mock_analyzer = Mock()
        mock_coef = MeasureImpactCoefficient(
            id="101",
            name="Bike Lane Expansion",
            kpi_group_id="201",
            coefficient=-0.25  # Negative coefficient (reduces air pollution)
        )
        mock_result = KPIGroupImpactOutput(
            id="201",
            name="Environmental Impact",
            kpi_ids=["1"],
            measure_coefficients=[mock_coef],
            msqe=0.05,
            variation_under_no_measures=0.1,
            living_labs_analysis=None
        )
        mock_analyzer.run_analysis_group.return_value = mock_result
        mock_analyzer_class.return_value = mock_analyzer

        # Run the job
        KpiMeasuresAnalysisJob.run(job_id, mock_db)

        # Verify update_job_data was called twice (input and output)
        update_data_calls = mock_job_repo.update_job_data.call_args_list
        assert len(
            update_data_calls) == 2, "Should save both input and output data"

        # ===== Verify INPUT data structure =====
        input_call = update_data_calls[0]
        assert input_call[1]['job_id'] == job_id
        input_data = input_call[1]['input_data']

        # Check top-level structure
        assert 'kpis' in input_data
        assert 'measures' in input_data
        assert 'kpi_groups' in input_data
        assert 'living_labs' in input_data
        assert 'timestamp' in input_data

        # Verify counts
        assert len(input_data['kpis']) == 2, "Should have 2 KPI definitions"
        assert len(input_data['measures']) == 1, "Should have 1 measure"
        assert len(input_data['kpi_groups']) == 1, "Should have 1 KPI group"
        assert len(input_data['living_labs']) == 1, "Should have 1 living lab"

        # Verify KPI structure
        kpi1 = input_data['kpis'][0]
        assert kpi1['id'] == '1'
        assert kpi1['name'] == 'Air Quality Index'
        assert kpi1['progression_target'] == 0
        assert kpi1['value_type'] == 'score'
        assert kpi1['value_min'] == 0.0
        assert kpi1['value_max'] == 500.0

        # Verify measure structure
        measure = input_data['measures'][0]
        assert measure['id'] == '101'
        assert measure['name'] == 'Bike Lane Expansion'

        # Verify KPI group structure
        group = input_data['kpi_groups'][0]
        assert group['id'] == '201'
        assert group['name'] == 'Environmental Impact'
        assert group['kpi_ids'] == ['1']

        # Verify living lab structure
        living_lab = input_data['living_labs'][0]
        assert living_lab['id'] == '301'
        assert living_lab['name'] == 'Paris Living Lab'
        assert 'kpis' in living_lab
        assert 'measures' in living_lab

        # Verify living lab has the KPI result
        assert len(living_lab['kpis']) == 1
        lab_kpi = living_lab['kpis'][0]
        assert lab_kpi['id'] == '1'
        assert lab_kpi['living_lab_id'] == '301'
        assert lab_kpi['value_before'] == 150.0
        assert lab_kpi['value_after'] == 120.0

        # Verify living lab has the measure
        assert len(living_lab['measures']) == 1
        lab_measure = living_lab['measures'][0]
        assert lab_measure['id'] == '101'
        assert lab_measure['name'] == 'Bike Lane Expansion'

        # ===== Verify OUTPUT data structure =====
        output_call = update_data_calls[1]
        assert output_call[1]['job_id'] == job_id
        output_data = output_call[1]['output_data']

        # Check top-level structure
        assert 'success' in output_data
        assert 'errors' in output_data
        assert 'timestamp' in output_data

        # Verify successful results
        assert len(output_data['success']
                   ) == 1, "Should have 1 successful group analysis"
        assert len(output_data['errors']) == 0, "Should have no errors"

        success_result = output_data['success'][0]
        assert success_result['group_id'] == '201'
        assert success_result['group_name'] == 'Environmental Impact'
        assert 'results' in success_result

        # Verify full KPIGroupImpactOutput structure in results
        results = success_result['results']
        assert results['id'] == '201'
        assert results['name'] == 'Environmental Impact'
        assert results['kpi_ids'] == ['1']

        # Verify analysis metrics
        assert 'msqe' in results
        assert results['msqe'] == 0.05
        assert 'variation_under_no_measures' in results
        assert results['variation_under_no_measures'] == 0.1

        # Verify measure coefficients
        assert 'measure_coefficients' in results
        assert len(results['measure_coefficients']) == 1

        coef = results['measure_coefficients'][0]
        assert coef['id'] == '101'
        assert coef['name'] == 'Bike Lane Expansion'
        assert coef['coefficient'] == -0.25
        assert coef['kpi_group_id'] == '201'

        # Verify job status was updated to SUCCESS
        status_calls = mock_job_repo.update_job_status.call_args_list
        final_status_call = status_calls[-1]
        assert final_status_call[1]['status'] == JobStatusEnum.SUCCESS
        assert 'Analysis completed for 1/1 KPI groups' in final_status_call[1]['message']

    @patch("src.sum_impact_assessment.services.kpi_measures_analysis_job.KPIImpactAnalyzer")
    @patch("src.sum_impact_assessment.services.analysis_data_service.AnalysisDataRepository")
    @patch("src.sum_impact_assessment.services.kpi_measures_analysis_job.JobRepository")
    def test_job_handles_partial_failures(
        self,
        mock_job_repo_class,
        mock_analysis_repo_class,
        mock_analyzer_class
    ):
        """Test that errors are properly tracked when some groups fail analysis."""
        # Setup mocks
        mock_db = Mock()
        job_id = "test-partial-failure"

        # Mock JobRepository
        mock_job_repo = Mock()
        mock_job_repo_class.return_value = mock_job_repo

        # Setup two groups
        mock_analysis_repo = Mock()
        mock_analysis_repo.get_kpi_definitions.return_value = []
        mock_analysis_repo.get_measures.return_value = []
        mock_analysis_repo.get_kpi_groups.return_value = [
            {
                "id": 1,
                "name": "Group Success",
                "kpidefinition_id": 1,
                "kpidefinition_name": "Air Quality Index",
                "kpidefinition_progression_target": 0,
                "kpidefinition_min_value": 0.0,
                "kpidefinition_max_value": 500.0,
                "kpidefinition_metric": "score"
            },
            {
                "id": 2,
                "name": "Group Failure",
                "kpidefinition_id": 1,
                "kpidefinition_name": "Air Quality Index",
                "kpidefinition_progression_target": 0,
                "kpidefinition_min_value": 0.0,
                "kpidefinition_max_value": 500.0,
                "kpidefinition_metric": "score"
            }
        ]
        mock_analysis_repo.get_living_labs.return_value = []
        mock_analysis_repo.get_living_lab_measures.return_value = []
        mock_analysis_repo.get_living_lab_kpi_results.return_value = []
        mock_analysis_repo_class.return_value = mock_analysis_repo

        # Mock analyzer: first succeeds, second fails
        mock_analyzer = Mock()
        mock_success_result = KPIGroupImpactOutput(
            id="1",
            name="Group Success",
            kpi_ids=["1"],
            measure_coefficients=[],
            msqe=0.1,
            variation_under_no_measures=0.0
        )
        mock_analyzer.run_analysis_group.side_effect = [
            mock_success_result,
            ValueError("Not enough living labs")
        ]
        mock_analyzer_class.return_value = mock_analyzer

        # Run the job
        KpiMeasuresAnalysisJob.run(job_id, mock_db)

        # Get output data
        update_data_calls = mock_job_repo.update_job_data.call_args_list
        output_call = [
            c for c in update_data_calls if c[1].get('output_data')][0]
        output_data = output_call[1]['output_data']

        # Verify both success and errors are tracked
        assert len(output_data['success']) == 1
        assert len(output_data['errors']) == 1

        # Verify success entry
        assert output_data['success'][0]['group_id'] == '1'
        assert output_data['success'][0]['group_name'] == 'Group Success'

        # Verify error entry
        assert output_data['errors'][0]['group_id'] == '2'
        assert output_data['errors'][0]['group_name'] == 'Group Failure'
        assert 'Not enough living labs' in output_data['errors'][0]['error']

        # Job should still succeed overall
        status_calls = mock_job_repo.update_job_status.call_args_list
        final_status = status_calls[-1]
        assert final_status[1]['status'] == JobStatusEnum.SUCCESS

    @patch("src.sum_impact_assessment.services.kpi_measures_analysis_job.KPIImpactAnalyzer")
    @patch("src.sum_impact_assessment.services.kpi_measures_analysis_job.AnalysisDataService")
    def test_run_kpi_impact_analysis_expands_modal_split_into_three_modes(
        self,
        mock_data_service_class,
        mock_analyzer_class,
    ):
        """Modal Split group should be expanded according to configured transport-mode sub-groups."""
        mock_db = Mock()

        modal_group = KPIGroup(
            id="3",
            name="Modal Split",
            kpi_ids=["15"],
            kpis=[
                KPI(
                    id="15",
                    name="Modal Split KPI",
                    kpi_number="15a",
                    progression_target=1,
                    value_type="percentage",
                    value_min=0,
                    value_max=1,
                )
            ],
        )

        living_lab = LivingLab(
            id="lab1",
            name="Lab 1",
            measures=[Measure(id="m1", name="Measure 1", times_implemented=1)],
            kpis=[
                KPILivingLabResult(
                    id="15",
                    name="Modal Split KPI",
                    progression_target=1,
                    value_type="percentage",
                    value_min=0,
                    value_max=1,
                    living_lab_id="lab1",
                    transport_mode_type="NSM",
                    value_before=0.3,
                    value_after=0.4,
                ),
                KPILivingLabResult(
                    id="15",
                    name="Modal Split KPI",
                    progression_target=1,
                    value_type="percentage",
                    value_min=0,
                    value_max=1,
                    living_lab_id="lab1",
                    transport_mode_type="PRIVATE",
                    value_before=0.5,
                    value_after=0.45,
                ),
                KPILivingLabResult(
                    id="15",
                    name="Modal Split KPI",
                    progression_target=1,
                    value_type="percentage",
                    value_min=0,
                    value_max=1,
                    living_lab_id="lab1",
                    transport_mode_type="PUBLIC_TRANSPORT",
                    value_before=0.2,
                    value_after=0.15,
                ),
            ],
        )

        mock_data_service = mock_data_service_class.return_value
        mock_data_service.get_analysis_input_data.return_value = (
            [],
            [Measure(id="m1", name="Measure 1")],
            [modal_group],
            [living_lab],
        )

        mock_analyzer = mock_analyzer_class.return_value
        mock_analyzer.run_analysis_group.side_effect = [
            KPIGroupImpactOutput(
                id="3__nsm", name="Modal Split - NSM", kpi_ids=["15"]),
            KPIGroupImpactOutput(
                id="3__private", name="Modal Split - Private", kpi_ids=["15"]),
            KPIGroupImpactOutput(
                id="3__public_transport", name="Modal Split - Public transport", kpi_ids=["15"]),
            KPIGroupImpactOutput(
                id="3__sustainable_modes", name="Modal Split - Sustainable modes", kpi_ids=["15"]),
        ]

        input_snapshot, successful_results, error_results = KpiMeasuresAnalysisJob.run_kpi_impact_analysis(
            db=mock_db,
            kpi_group_filter=None,
        )

        assert len(input_snapshot["kpi_groups"]) == len(
            MODAL_SPLIT_TRANSPORT_MODE_GROUPS)
        assert len(successful_results) == len(
            MODAL_SPLIT_TRANSPORT_MODE_GROUPS)
        assert len(error_results) == 0
        assert mock_analyzer.run_analysis_group.call_count == len(
            MODAL_SPLIT_TRANSPORT_MODE_GROUPS)

        analyzed_names = [
            call.args[0].name for call in mock_analyzer.run_analysis_group.call_args_list]
        assert "Modal Split - NSM" in analyzed_names
        assert "Modal Split - Private" in analyzed_names
        assert "Modal Split - Public transport" in analyzed_names
        assert "Modal Split - Sustainable modes" in analyzed_names

        analyzed_groups = [call.args[0]
                           for call in mock_analyzer.run_analysis_group.call_args_list]
        sustainable_group = next(
            g for g in analyzed_groups if g.name == "Modal Split - Sustainable modes"
        )
        assert sorted(sustainable_group.transport_mode_type_filter) == [
            "nsm", "public_transport"]

    @patch("src.sum_impact_assessment.services.kpi_measures_analysis_job.KPIImpactAnalyzer")
    @patch("src.sum_impact_assessment.services.kpi_measures_analysis_job.AnalysisDataService")
    def test_run_kpi_impact_analysis_does_not_expand_modal_split_for_mcda_goals(
        self,
        mock_data_service_class,
        mock_analyzer_class,
    ):
        """MCDA_GOALS runs must keep original groups (no transport-mode split)."""
        mock_db = Mock()

        modal_group = KPIGroup(
            id="3",
            name="Modal Split",
            kpi_ids=["15"],
            kpis=[
                KPI(
                    id="15",
                    name="Modal Split KPI",
                    kpi_number="15",
                    progression_target=1,
                    value_type="percentage",
                    value_min=0,
                    value_max=1,
                )
            ],
        )

        mock_data_service = mock_data_service_class.return_value
        mock_data_service.get_analysis_input_data.return_value = (
            [],
            [Measure(id="m1", name="Measure 1")],
            [modal_group],
            [],
        )

        mock_analyzer = mock_analyzer_class.return_value
        mock_analyzer.run_analysis_group.return_value = KPIGroupImpactOutput(
            id="3",
            name="Modal Split",
            kpi_ids=["15"],
        )

        input_snapshot, successful_results, error_results = KpiMeasuresAnalysisJob.run_kpi_impact_analysis(
            db=mock_db,
            kpi_group_filter="MCDA_GOALS",
        )

        assert len(input_snapshot["kpi_groups"]) == 1
        assert len(successful_results) == 1
        assert len(error_results) == 0
        mock_analyzer.run_analysis_group.assert_called_once()
        assert mock_analyzer.run_analysis_group.call_args.args[0].name == "Modal Split"

    @patch("src.sum_impact_assessment.services.kpi_measures_analysis_job.KPIImpactAnalyzer")
    @patch("src.sum_impact_assessment.services.kpi_measures_analysis_job.AnalysisDataService")
    def test_run_kpi_impact_analysis_modal_split_only_nsm_keeps_nsm_and_sustainable_modes(
        self,
        mock_data_service_class,
        mock_analyzer_class,
    ):
        """
        Given Modal Split analysis and only NSM KPI data in living labs,
        then only NSM and Sustainable modes sub-groups are analyzed.
        """
        mock_db = Mock()

        modal_group = KPIGroup(
            id="3",
            name="Modal Split",
            kpi_ids=["15"],
            kpis=[
                KPI(
                    id="15",
                    name="Modal Split KPI",
                    kpi_number="15",
                    progression_target=1,
                    value_type="percentage",
                    value_min=0,
                    value_max=1,
                )
            ],
        )

        living_lab = LivingLab(
            id="lab1",
            name="Lab 1",
            measures=[Measure(id="m1", name="Measure 1", times_implemented=1)],
            kpis=[
                KPILivingLabResult(
                    id="15",
                    name="Modal Split KPI",
                    progression_target=1,
                    value_type="percentage",
                    value_min=0,
                    value_max=1,
                    living_lab_id="lab1",
                    transport_mode_type="NSM",
                    value_before=0.3,
                    value_after=0.4,
                ),
            ],
        )

        mock_data_service = mock_data_service_class.return_value
        mock_data_service.get_analysis_input_data.return_value = (
            [],
            [Measure(id="m1", name="Measure 1")],
            [modal_group],
            [living_lab],
        )

        mock_analyzer = mock_analyzer_class.return_value
        mock_analyzer.run_analysis_group.side_effect = [
            KPIGroupImpactOutput(
                id="3__nsm", name="Modal Split - NSM", kpi_ids=["15"]),
            KPIGroupImpactOutput(
                id="3__sustainable_modes", name="Modal Split - Sustainable modes", kpi_ids=["15"]),
        ]

        input_snapshot, successful_results, error_results = KpiMeasuresAnalysisJob.run_kpi_impact_analysis(
            db=mock_db,
            kpi_group_filter=None,
        )

        analyzed_names = [
            call.args[0].name for call in mock_analyzer.run_analysis_group.call_args_list]

        assert len(input_snapshot["kpi_groups"]) == 2
        assert len(successful_results) == 2
        assert len(error_results) == 0
        assert mock_analyzer.run_analysis_group.call_count == 2
        assert "Modal Split - NSM" in analyzed_names
        assert "Modal Split - Sustainable modes" in analyzed_names
        assert "Modal Split - Private" not in analyzed_names
        assert "Modal Split - Public transport" not in analyzed_names

    @patch("src.sum_impact_assessment.services.kpi_measures_analysis_job.AnalysisDataService")
    @patch("src.sum_impact_assessment.models.impact_analysis.kpi_impact_analysis.KPIImpactAnalyzer.run_ridge_regression", autospec=True)
    def test_run_kpi_impact_analysis_modal_split_all_transport_modes_filters_output_and_ridge_inputs(
        self,
        mock_run_ridge_regression,
        mock_data_service_class,
    ):
        """
        Given Modal Split group and KPI data for all transport modes,
        then all configured Modal Split sub-groups are analyzed,
        each subgroup output contains only KPIs for its transport mode filter,
        and ridge regression is called with subgroup-filtered inputs.
        """
        mock_db = Mock()

        modal_group = KPIGroup(
            id="3",
            name="Modal Split",
            kpi_ids=["15"],
            kpis=[
                KPI(
                    id="15",
                    name="Modal Split KPI",
                    kpi_number="15",
                    progression_target=1,
                    value_type="percentage",
                    value_min=0,
                    value_max=1,
                )
            ],
        )

        living_lab = LivingLab(
            id="lab1",
            name="Lab 1",
            measures=[Measure(id="m1", name="Measure 1", times_implemented=1)],
            kpis=[
                KPILivingLabResult(
                    id="15",
                    name="Modal Split KPI",
                    progression_target=1,
                    value_type="percentage",
                    value_min=0,
                    value_max=1,
                    living_lab_id="lab1",
                    transport_mode_type="NSM",
                    value_before=0.3,
                    value_after=0.4,
                ),
                KPILivingLabResult(
                    id="15",
                    name="Modal Split KPI",
                    progression_target=1,
                    value_type="percentage",
                    value_min=0,
                    value_max=1,
                    living_lab_id="lab1",
                    transport_mode_type="PRIVATE",
                    value_before=0.5,
                    value_after=0.45,
                ),
                KPILivingLabResult(
                    id="15",
                    name="Modal Split KPI",
                    progression_target=1,
                    value_type="percentage",
                    value_min=0,
                    value_max=1,
                    living_lab_id="lab1",
                    transport_mode_type="PUBLIC_TRANSPORT",
                    value_before=0.2,
                    value_after=0.15,
                ),
            ],
        )

        mock_data_service = mock_data_service_class.return_value
        mock_data_service.get_analysis_input_data.return_value = (
            [
                KPI(
                    id="15",
                    name="Modal Split KPI",
                    kpi_number="15",
                    progression_target=1,
                    value_type="percentage",
                    value_min=0,
                    value_max=1,
                )
            ],
            [Measure(id="m1", name="Measure 1")],
            [modal_group],
            [living_lab],
        )

        mock_run_ridge_regression.return_value = (
            np.zeros(1),
            0.0,
            0.0,
            np.zeros(1),
        )

        _, successful_results, error_results = KpiMeasuresAnalysisJob.run_kpi_impact_analysis(
            db=mock_db,
            kpi_group_filter=None,
        )

        assert len(successful_results) == 4
        assert len(error_results) == 0

        result_by_group_name = {
            result["group_name"]: result["results"] for result in successful_results
        }
        assert "Modal Split - NSM" in result_by_group_name
        assert "Modal Split - Private" in result_by_group_name
        assert "Modal Split - Public transport" in result_by_group_name
        assert "Modal Split - Sustainable modes" in result_by_group_name

        nsm_modes = {
            kpi["transport_mode_type"]
            for kpi in result_by_group_name["Modal Split - NSM"]["living_labs_analysis"][0]["kpis"]
        }
        private_modes = {
            kpi["transport_mode_type"]
            for kpi in result_by_group_name["Modal Split - Private"]["living_labs_analysis"][0]["kpis"]
        }
        public_modes = {
            kpi["transport_mode_type"]
            for kpi in result_by_group_name["Modal Split - Public transport"]["living_labs_analysis"][0]["kpis"]
        }
        sustainable_modes = {
            kpi["transport_mode_type"]
            for kpi in result_by_group_name["Modal Split - Sustainable modes"]["living_labs_analysis"][0]["kpis"]
        }

        assert nsm_modes == {"NSM"}
        assert private_modes == {"PRIVATE"}
        assert public_modes == {"PUBLIC_TRANSPORT"}
        assert sustainable_modes == {"NSM", "PUBLIC_TRANSPORT"}

        assert mock_run_ridge_regression.call_count == 4

        # Call order follows modal split subgroup constant order:
        # NSM[0], Private[1], Public transport[2], Sustainable modes[3].
        # With autospec on an instance method, call args are: (self, X, y, ...)
        _, nsm_call_X, nsm_call_y = mock_run_ridge_regression.call_args_list[0].args[:3]

        # NSM subgroup should use only NSM KPI variations (no PRIVATE/PUBLIC_TRANSPORT contribution).
        assert tuple(np.round(nsm_call_y, 5).tolist()) == (10.0,)

        # All subgroup analyses use same living-lab measure input design matrix in this fixture.
        ridge_x_vectors = [
            tuple(np.round(call.args[1].flatten(), 5).tolist())
            for call in mock_run_ridge_regression.call_args_list
        ]
        assert ridge_x_vectors.count((1.0,)) == 4
