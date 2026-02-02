from ...schemas.impact_analysis import MeasureImpactCoefficient, LivingLabImpactError, KPIGroupImpactOutput
from ...schemas.core import LivingLab, Measure, KPILivingLabResult, KPIGroup
import numpy as np
from sklearn.linear_model import ridge_regression
from enum import Enum


class KPIAnalysisParam(Enum):
    MIN_PERC_MEASURED_KPI_IN_GROUP = 0.5
    MIN_PERC_FEASIBLE_LIVING_LABS = 0.5
    REGULARIZATION_PENALTY = 1.0


class KPIImpactAnalyzer:
    def __init__(self, living_labs: list[LivingLab], measures: list[Measure], kpis: list[KPILivingLabResult], kpi_groups: list[KPIGroup]):
        """
        Initialize with a list of LivingLabs information.
        """
        self.living_labs = living_labs
        self.measures = measures
        self.kpis = kpis
        self.kpi_groups = kpi_groups
    
    # Auxiliary functions to run the impact analysis
    def delete_measures_never_implemented(self):
        """
        Remove measures that are never implemented in any living lab.
        """
        ids_measures_not_implemented = {m.id for m in self.measures}
        for l in range(len(self.living_labs)):
            lab = self.living_labs[l]
            ids_measures_not_implemented = ids_measures_not_implemented.difference({m.id for m in lab.measures})

        self.measures = [m for m in self.measures if m.id not in ids_measures_not_implemented]
   
    def compute_X_y_input(self, kpi_group: KPIGroup) -> tuple[np.array, np.array, list[LivingLab], KPIGroup]:
        '''
        Compute the data matrix X and target vector y for the KPI impact analysis.

        Parameters:
        - kpi_group (KPIGroup): group of KPIs that we are using for analysis

        Returns:
        - X (numpy array): data matrix with shape (n_living_labs, n_measures)
        - y (numpy array): target vector with shape (n_living_labs,)
        - feasible_ll (list[LivingLab]): list of living labs used in the analysis
        - kpi_group (KPIGroup): the same KPI group passed as input
        '''
        # Initialise data matrix X and target vector y
        n_living_labs = len(self.living_labs)
        X_rows = []  # Rows of data matrix X
        y_rows = []  # Rows of target vector y
        feasible_ll = []

        # Compute data matrix X and target vector y
        for l in range(n_living_labs):
            lab = self.living_labs[l]
            
            # Check if living lab is feasible (has enough KPI information)
            measured_kpis_in_lab = [
                kpi for kpi in lab.kpis if kpi.id in kpi_group.kpi_ids
                ]
            
            if len(measured_kpis_in_lab)/len(kpi_group.kpi_ids) >= KPIAnalysisParam.MIN_PERC_MEASURED_KPI_IN_GROUP.value:
                # Add living lab to list of feasible leaving labs
                feasible_ll.append(lab)

                # Create data rows with 1s for implemented measures
                new_row = [1 if m.id in {
                    lm.id for lm in lab.measures} else 0 for m in self.measures]
                X_rows.append(new_row)

                for kpi in measured_kpis_in_lab:
                    kpi.update_absolute_variation()
                variation = sum(
                    kpi.abs_variation for kpi in measured_kpis_in_lab
                    )
                y_rows.append(variation)
        
        # Convert to X and y to numpy arrays
        X = np.array(X_rows, dtype=int)
        y = np.array(y_rows, dtype=float)
        
        return X, y, feasible_ll, kpi_group
    
    def compute_max_variation(self, kpi_group: KPIGroup) -> float:
        '''
        Compute the theoretical maximum variation for the given KPI group.

        Parameters:
        - kpi_group (KPIGroup): group of KPIs that we are using for analysis

        Returns:
        - max_variation (float): theoretical maximum variation
        '''
        # Compute theoretical maximum variation (from difference between max and min values of KPIs in group)
        seen_ids = set()
        max_variation = 0.0
        for kpi in self.kpis:
            if ((kpi.id in kpi_group.kpi_ids) and (kpi.id not in seen_ids) and kpi.value_min is not None and kpi.value_max is not None):
                seen_ids.add(kpi.id)
                max_variation += kpi.value_max - kpi.value_min

        return max_variation

    def normalize_variation(self, y: np.array, max_variation: float, target_range=10.0):
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
    
    def run_ridge_regression(self, X: np.array, y: np.array, 
                             alpha:float=KPIAnalysisParam.REGULARIZATION_PENALTY.value, 
                             return_intercept:bool = True):
        # Run Ridge Regression
        coef, intercept = ridge_regression(X, y, alpha=alpha, return_intercept=return_intercept)

        # Compute Mean Squared Error (MSE)
        y_pred = X @ coef + intercept  # Compute predicted y using the estimated coefficients
        sqe_per_sample = (y - y_pred)**2  # Squared error per living lab
        # Standard definition of Mean Squared Error
        msqe = np.mean((y - y_pred)**2)

        return coef, intercept, msqe, sqe_per_sample

    def add_living_lab_results(self, output_group:KPIGroupImpactOutput, kpi_group:KPIGroup, 
                               feasible_ll:list[LivingLab], sqe_per_sample:np.array
                            ) -> KPIGroupImpactOutput:
        """
        Add the LivingLabImpactError result to the KPIGroupImpactOutput object.
        """
        labs_analysis = []
        for lab in feasible_ll:
            index = feasible_ll.index(lab)
            temp_lab = LivingLabImpactError(id=lab.id,
                                            name=lab.name,
                                            kpis=lab.kpis,
                                            measures=lab.measures,
                                            kpi_group_id=kpi_group.id,
                                            sqe=sqe_per_sample[index])
            labs_analysis.append(temp_lab)

        output_group.living_labs_analysis = labs_analysis

        return output_group

    def add_measure_results(self, output_group:KPIGroupImpactOutput, 
                               kpi_group:KPIGroup,
                               coef:np.array
                            ) -> KPIGroupImpactOutput:
        """
        Add the MeasureImpactCoefficient results to the KPIGroupImpactOutput object.
        """
        results = []
        for measure in self.measures:
            index = self.measures.index(measure)
            result = MeasureImpactCoefficient(id=measure.id,
                                              name=measure.name,
                                              kpi_group_id=kpi_group.id,
                                              coefficient=round(coef[index], 5))
            results.append(result)

        # sort results by coefficient descending
        results.sort(key=lambda x: x.coefficient,  reverse=True)
        output_group.measure_coefficients = results

        return output_group

    # Main function to run the impact analysis
    def run_analysis_group(self, kpi_group: KPIGroup) -> KPIGroupImpactOutput:
        """
        Run KPI impact analysis on the LivingLabs data.
        Uses Ridge regression to estimate the impact of the implementation of each measure 
        in the group of KPIs selected.
        ASSUMPTION: There are enough living labs who have measured these KPIs to ensure analysis relevance (i.e. KPIAnalysisParam.MIN_PERC_FEASIBLE_LIVING_LABS)

        Parameters:
        - kpi_group (KPIGroup): group of KPIs that we are running this analysis for

        Returns:
        - list of KPIGroup with updated fields with the analysis results namely:
            > the list of living labs with estimation squared error `LivingLabImpactError` obtained from the analysis,
            > the mean square error of the estimation,
            > the espected variation if no measures were implemented (aka intercept term),
            > the list of measures with updated impact coeffients `MeasureImpactCoefficient` obtained from the analysis.

        """

        # Remove any measures that are not implemented in any living lab
        self.delete_measures_never_implemented() # The list of implemented measures is updated in self.measures

        # Initialise data matrix X and target vector y
        X, y, feasible_ll, kpi_group = self.compute_X_y_input(kpi_group)

        # Normalise target vector y
        max_variation = self.compute_max_variation(kpi_group)
        y = self.normalize_variation(y=y, max_variation=max_variation, target_range=100.0)

        # Run Ridge Regression & compute Mean Squared Error (MSE)
        coef, intercept, msqe, sqe_per_sample = self.run_ridge_regression(X, y)


        # Update KPIGroup object with analysis results
        output_group = KPIGroupImpactOutput(id=kpi_group.id,
                                            name=kpi_group.name,
                                            kpi_ids=kpi_group.kpi_ids)
        
        output_group = self.add_living_lab_results(output_group, kpi_group, feasible_ll, sqe_per_sample)
        output_group.msqe = msqe
        output_group.variation_under_no_measures = intercept
        output_group = self.add_measure_results(output_group, kpi_group, coef)

        return output_group

    def run_analysis(self, list_groups: list[KPIGroup] = None) -> list[KPIGroupImpactOutput]:
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
        for group in list_groups:
            try:
                # match list_groups entry with index in kpi_groups
                idx = self.kpi_groups.index(group)
                # analysis results stored in each KPIGroup object directly
                self.kpi_groups[idx] = self.run_analysis_group(group)
            except ValueError:
                self.kpi_groups.append(self.run_analysis_group(group))

        #for i in range(len(self.kpi_groups)):
            # analysis results stored in each KPIGroup object directly
        #    self.kpi_groups[i] = self.run_analysis_group(self.kpi_groups[i])
