from ...schemas.impact_analysis import MeasureImpactCoefficient, LivingLabImpactError, KPIGroupImpactOutput
from ...schemas.core import LivingLab, Measure, KPILivingLab, KPIGroup
import numpy as np
from sklearn.linear_model import ridge_regression
from enum import Enum

class KPIAnalysisParam(Enum):
    MIN_PERC_MEASURED_KPI_IN_GROUP = 0.8
    MIN_PERC_FEASIBLE_LIVING_LABS = 0.8
    REGULARIZATION_PENALTY = 1.0

class KPIImpactAnalyzer:
    def __init__(self, living_labs: list[LivingLab], measures: list[Measure], kpis: list[KPILivingLab], kpi_groups: list[KPIGroup]):
        """
        Initialize with a list of LivingLabs information.
        """
        self.living_labs = living_labs
        self.measures = measures
        self.kpis = kpis
        self.kpi_groups = kpi_groups

    def normalize_variation(self, y:np.array, max_variation:float, target_range=1.0):
        '''
        Normalize a variation y to [-target_range, target_range] symmetrically,
        preserving zero and sign. Uses M = max(upper, -lower) for scaling.

        Parameters:
        - y (numpy array): absolute variation(s)
        - max_variation (float): expected maximum variation (in absolute value, for positive or negative variations)
        - target_range (float): upper bound of normalized range (default 1.0 for [-1, 1])

        Returns:
        - numpy array of normalized variation(s)
        ''' 

        if (max_variation <= 0):
            raise ValueError("Expected 'max_variation' > 0 for normalization.")

        if (target_range <= 0):
            raise ValueError("Expected normalization range 'target_range' > 0.")

        return (y / max_variation) * target_range

    def run_analysis_group(self, kpi_group:KPIGroup) -> KPIGroupImpactOutput:
        """
        Run KPI impact analysis on the LivingLabs data.
        Uses Ridge regression to estimate the impact of the implementation of each measure 
        in the group of KPIs selected.
        
        Parameters:
        - kpi_group (KPIGroup): group of KPIs that we are running this analysis for

        Returns:
        - list of KPIGroup with updated fields with the analysis results namely:
            > the list of living labs with estimation squared error `LivingLabImpactError` obtained from the analysis,
            > the mean square error of the estimation,
            > the espected variation if no measures were implemented (aka intercept term),
            > the list of measures with updated impact coeffients `MeasureImpactCoefficient` obtained from the analysis.
        """

        # Initialise data matrix X and target vector y
        n_living_labs = len(self.living_labs)
        X_rows = [] # Rows of data matrix X
        y_rows = [] # Rows of target vector y
        feasible_ll = []

        # Compute data matrix X and target vector y
        for l in range(n_living_labs):
            lab = self.living_labs[l]
            # Check if living lab is feasible (has enough KPI information)
            measured_kpis_in_lab = [kpi for kpi in lab.kpis if kpi.id in kpi_group.kpi_ids]
            if len(measured_kpis_in_lab)/len(kpi_group.kpi_ids) >= KPIAnalysisParam.MIN_PERC_MEASURED_KPI_IN_GROUP.value:
                # Add living lab to list of feasible leaving labs
                feasible_ll.append(lab)

                # Create data rows with 1s for implemented measures
                new_row = [1 if m.id in {lm.id for lm in lab.measures} else 0 for m in self.measures]
                X_rows.append(new_row)

                for kpi in measured_kpis_in_lab:
                    kpi.update_absolute_variation()
                variation = sum(kpi.abs_variation for kpi in measured_kpis_in_lab)
                y_rows.append(variation)

        # Check that there are enough livings labs for the analysis
        if len(feasible_ll)/n_living_labs < KPIAnalysisParam.MIN_PERC_FEASIBLE_LIVING_LABS.value:
                raise ValueError("Not enough living labs have measured these KPIs to ensure analysis relevance.")
        
        # Convert to X and y to numpy arrays
        X = np.array(X_rows, dtype=int)
        y = np.array(y_rows, dtype=float)

        # Remove any measures that are not implemented in any living lab
        # TODO (also keep track of list of implemented measures)

        # Compute theoretical maximum variation (from difference between max and min values of KPIs in group)
        seen_ids = set()
        max_variation = 0.0
        for kpi in self.kpis:
            if ((kpi.id in kpi_group.kpi_ids) and (kpi.id not in seen_ids)):
                seen_ids.add(kpi.id)
                max_variation += kpi.value_max - kpi.value_min

        # Normalise target vector y
        y = self.normalize_variation(y=y, max_variation=max_variation)

        # Run Ridge Regression
        coef, intercept = ridge_regression(X, y, 
                                           alpha=KPIAnalysisParam.REGULARIZATION_PENALTY.value, 
                                           return_intercept=True)

        # Compute Mean Squared Error (MSE)
        y_pred = X @ coef + intercept # Compute predicted y using the estimated coefficients
        sqe_per_sample = (y - y_pred)**2 # Squared error per living lab
        msqe = np.mean((y - y_pred)**2)  # Standard definition of Mean Squared Error

        # Update KPIGroup object with analysis results
        output_group = KPIGroupImpactOutput(id=kpi_group.id, 
                                            name=kpi_group.name, 
                                            kpi_ids=kpi_group.kpi_ids)
        labs_analysis = []
        for lab in feasible_ll:
            index = feasible_ll.index(lab)
            temp_lab = LivingLabImpactError(id=lab.id,
                                            name=lab.name,
                                            kpis = lab.kpis,
                                            measures=lab.measures,
                                            kpi_group_id=kpi_group.id,
                                            sqe=sqe_per_sample[index])
            labs_analysis.append(temp_lab)

        output_group.living_labs_analysis = feasible_ll
        output_group.msqe = msqe
        output_group.variation_under_no_measures = intercept        
        results = []
        for measure in self.measures:
            # TODO If measure is never implemented the coefficient should be None.
            index = self.measures.index(measure) # TODO Adjust when not all measures considered
            result = MeasureImpactCoefficient(id=measure.id,
                                              name=measure.name,
                                              kpi_group_id=kpi_group.id,
                                              coefficient=coef[index])
            results.append(result)
        output_group.measure_coefficients = results

        return output_group

    def run_analysis(self, list_groups:list[KPIGroup]=None) -> list[KPIGroupImpactOutput]:
        '''
        Runs the impact analysis for the KPI groups in 'list_groups'

        Parameters:
        - list_groups (list[KPIGroup]): KPI groups to perform the analysis for. 
                                        If not provided, analysis is run for all groups.

        Returns:
        - list of the same KPIGroupImpactOutput objects with updated fields with the analysis results.
        '''
        # If list of groups not provided, select all KPI groups
        if list_groups is None: 
            list_groups = self.kpi_groups 

        # Run impact analysis for KPI groups selected
        for i in range(len(self.kpi_groups)):
            self.kpi_groups[i] = self.run_analysis_group(self.kpi_groups[i]) # analysis results stored in each KPIGroup object directly



