from typing import List, Dict
import numpy as np
from pyDecision.algorithm import promethee_i, promethee_ii, promethee_gaia
from sklearn.decomposition import PCA
from ...schemas.mcda import Goal, Alternative, MCDAAnalysisOutput, GAIAAlternativeCoordinate, GAIACriterionVector
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


class PrometheeGaiaAnalyzer:
    def __init__(self,
                 goals: List[Goal],
                 alternatives: List[Alternative]):
        self.goals = goals
        self.alternatives = alternatives
        self.criteria_names = [g.name for g in goals]
        self.weights = [g.weight for g in goals]
        self.directions = ['max' if g.direction ==
                           'max' else 'min' for g in goals]
        self.Q = [g.Q for g in goals]
        self.S = [g.S for g in goals]
        self.P = [g.P for g in goals]
        self.F = [g.F for g in goals]
        self.matrix = np.array(
            [[a.values[c] for c in self.criteria_names] for a in alternatives])
        self.alternative_names = [a.name for a in alternatives]

        # Standardized keys (c1, c2 for criteria; a1, a2 for alternatives)
        self.criteria_short = [f"c{i+1}" for i in range(len(self.goals))]
        self.alternative_short = [
            f"a{i+1}" for i in range(len(self.alternatives))]

        # Label mappings: keys to full names
        self.alternative_labels = {
            f"a{i+1}": self.alternative_names[i]
            for i in range(len(self.alternative_names))
        }
        self.criteria_labels = {
            f"c{i+1}": self.criteria_names[i]
            for i in range(len(self.criteria_names))
        }

    def _calculate_preference_function(self, diff: float, Q: float, S: float, P: float, F: str) -> float:
        """
        Calculate preference value based on PROMETHEE preference function type.

        Args:
            diff: Performance difference (alternative_i - alternative_j)
            Q: Indifference threshold
            S: Preference threshold (used for Gaussian and C-form)
            P: Veto/strict preference threshold
            F: Preference function type ('t1' to 't7')

        Returns:
            Preference value in [0, 1]
        """
        import math

        if diff <= 0:
            return 0.0

        if F == 't1':  # Usual criterion
            return 1.0
        elif F == 't2':  # U-shape criterion
            return 0.0 if diff <= Q else 1.0
        elif F == 't3':  # V-shape criterion
            if diff <= 0:
                return 0.0
            elif diff <= P:
                return diff / P
            else:
                return 1.0
        elif F == 't4':  # Level criterion
            if diff <= Q:
                return 0.0
            elif diff <= P:
                return 0.5
            else:
                return 1.0
        elif F == 't5':  # V-shape with indifference
            if diff <= Q:
                return 0.0
            elif diff <= P:
                return (diff - Q) / (P - Q)
            else:
                return 1.0
        elif F == 't6':  # Gaussian criterion
            return 1.0 - math.exp(-(diff ** 2) / (2 * S ** 2))
        elif F == 't7':  # C-form criterion
            if diff == 0:
                return 0.0
            elif diff <= S:
                return (diff / S) ** 0.5
            else:
                return 1.0
        else:
            raise ValueError(f"Unknown preference function type: {F}")

    def _calculate_preference_degree_matrix(self, matrix: np.ndarray, weights: List[float],
                                            Q: List[float], S: List[float], P: List[float],
                                            F: List[str]) -> np.ndarray:
        """
        Calculate the aggregated preference degree matrix.

        Returns:
            n x n matrix where element [i,j] represents the degree to which alternative i 
            is preferred over alternative j, aggregated across all criteria.
        """
        n_alternatives = matrix.shape[0]
        n_criteria = matrix.shape[1]
        pd_matrix = np.zeros((n_alternatives, n_alternatives))

        for k in range(n_criteria):
            criterion_pd = np.zeros((n_alternatives, n_alternatives))
            for i in range(n_alternatives):
                for j in range(n_alternatives):
                    if i != j:
                        diff = matrix[i, k] - matrix[j, k]
                        criterion_pd[i, j] = self._calculate_preference_function(
                            diff, Q[k], S[k], P[k], F[k]
                        )
            pd_matrix += weights[k] * criterion_pd

        pd_matrix = pd_matrix / sum(weights)
        return pd_matrix

    def _calculate_unicriterion_flows(self, criterion_idx: int) -> np.ndarray:
        """
        Calculate PROMETHEE net flows for a single criterion.

        This is used for proper GAIA analysis, which projects unicriterion flows.

        Args:
            criterion_idx: Index of the criterion to analyze

        Returns:
            Array of net flows (φ+ - φ-) for each alternative on this single criterion
        """
        n_alternatives = self.matrix.shape[0]

        # Create single-criterion matrix
        single_criterion_matrix = self.matrix[:, criterion_idx:criterion_idx+1]

        # Calculate preference degree for this criterion only
        pd_matrix = np.zeros((n_alternatives, n_alternatives))
        for i in range(n_alternatives):
            for j in range(n_alternatives):
                if i != j:
                    diff = single_criterion_matrix[i,
                                                   0] - single_criterion_matrix[j, 0]
                    pd_matrix[i, j] = self._calculate_preference_function(
                        diff,
                        self.Q[criterion_idx],
                        self.S[criterion_idx],
                        self.P[criterion_idx],
                        self.F[criterion_idx]
                    )

        # Calculate flows
        flow_plus = np.sum(pd_matrix, axis=1) / (n_alternatives - 1)
        flow_minus = np.sum(pd_matrix, axis=0) / (n_alternatives - 1)
        net_flow = flow_plus - flow_minus

        return net_flow

    def run_prometheeI(self, graph: bool = False) -> Dict:
        """
        Run PROMETHEE I analysis to get positive and negative flows.

        Returns:
            Dictionary with:
            - alternatives: List of alternative short names
            - positive_flows: Dict mapping alternative names to φ+ values
            - negative_flows: Dict mapping alternative names to φ- values  
            - preference_matrix: n x n matrix of preference codes (P+, R, I, -)
        """
        # Get preference matrix codes from pyDecision
        preference_codes = promethee_i(self.matrix, W=self.weights,
                                       Q=self.Q, S=self.S, P=self.P, F=self.F, graph=graph)

        # Calculate actual flow values manually
        pd_matrix = self._calculate_preference_degree_matrix(
            self.matrix, self.weights, self.Q, self.S, self.P, self.F
        )

        flow_plus = np.sum(pd_matrix, axis=1) / (pd_matrix.shape[0] - 1)
        flow_minus = np.sum(pd_matrix, axis=0) / (pd_matrix.shape[0] - 1)

        # Create dictionaries mapping alternative names to flow values
        positive_flows_dict = {
            self.alternative_short[i]: float(flow_plus[i])
            for i in range(len(self.alternative_short))
        }
        negative_flows_dict = {
            self.alternative_short[i]: float(flow_minus[i])
            for i in range(len(self.alternative_short))
        }

        results = {
            'alternatives': self.alternative_short,
            'positive_flows': positive_flows_dict,
            'negative_flows': negative_flows_dict,
            'preference_matrix': preference_codes.tolist()
        }
        self.prometheeI_results = results
        return results

    def run_prometheeII(self, graph: bool = False) -> Dict:
        """
        Run PROMETHEE II analysis to get net flows and ranking.

        Returns:
            Dictionary with:
            - alternatives: List of alternative short names
            - net_flows: Dict mapping alternative names to net flow values
            - ranking: Ordered list of alternative names (best to worst)
        """
        net_flow_array = promethee_ii(self.matrix, self.weights,
                                      Q=self.Q, S=self.S, P=self.P, F=self.F,
                                      sort=True, graph=graph, verbose=False)

        # Convert from [[index, net_flow], ...] to dict
        net_flows_dict = {}
        ranking = []

        for idx_and_flow in net_flow_array:
            # pyDecision uses 1-based indexing
            alt_index = int(idx_and_flow[0]) - 1
            net_flow_value = float(idx_and_flow[1])
            alt_name = self.alternative_short[alt_index]
            net_flows_dict[alt_name] = net_flow_value
            ranking.append(alt_name)

        results = {
            'alternatives': self.alternative_short,
            'net_flows': net_flows_dict,
            'ranking': ranking
        }
        self.prometheeII_results = results
        return results

    def run_gaia(self, x: int = 10, y: int = 10) -> Dict:
        # Use pyDecision's built-in GAIA function
        promethee_gaia(
            self.matrix, self.weights,  Q=self.Q, S=self.S, P=self.P, F=self.F, size_x=x, size_y=y)

    def run_gaia_custom(self, n_components: int = 2) -> Dict:
        """
        Run proper GAIA analysis using unicriterion net flows.

        This implements the theoretically correct GAIA method:
        1. Calculate net flows for each criterion separately (unicriterion flows)
        2. Build flow matrix: rows = alternatives, columns = unicriterion flows
        3. Center and scale the flow matrix
        4. Apply PCA to obtain the GAIA plane
        5. Calculate decision stick as weighted sum of criterion vectors

        Args:
            n_components: Number of principal components (default: 2 for visualization)

        Returns:
            Dictionary with complete GAIA visualization data
        """
        n_alternatives = self.matrix.shape[0]
        n_criteria = len(self.goals)

        # Step 1 & 2: Build unicriterion flow matrix
        flow_matrix = np.zeros((n_alternatives, n_criteria))
        for criterion_idx in range(n_criteria):
            unicriterion_flows = self._calculate_unicriterion_flows(
                criterion_idx)
            flow_matrix[:, criterion_idx] = unicriterion_flows

        # Step 3: Center and scale the flow matrix
        X = (flow_matrix - np.mean(flow_matrix, axis=0)) / \
            (np.std(flow_matrix, axis=0) + 1e-12)

        # Step 4: Apply PCA
        pca = PCA(n_components=n_components)
        alt_coords = pca.fit_transform(X)  # Alternatives in GAIA plane
        crit_coords = pca.components_.T    # Criteria vectors in GAIA plane

        # Step 5: Calculate decision stick (weighted sum of criterion vectors)
        # The decision stick points in the direction that optimizes all weighted criteria
        decision_stick = np.zeros(n_components)
        for i in range(n_criteria):
            decision_stick += self.weights[i] * crit_coords[i, :]

        # Calculate quality percentage (variance explained by first 2 components)
        quality_percentage = float(np.sum(pca.explained_variance_ratio_) * 100)

        # Save results for visualization and output
        self.gaia_results = {
            'alternative_names': self.alternative_short,
            'alternative_coords': alt_coords.tolist(),
            'criteria_names': self.criteria_short,
            'criteria_coords': crit_coords.tolist(),
            'decision_stick': decision_stick.tolist(),
            'quality_percentage': quality_percentage,
            'explained_variance_ratio': pca.explained_variance_ratio_.tolist(),
            'method': 'pca'
        }
        return self.gaia_results

    def run_analysis(self, run_visualizations: bool = False) -> MCDAAnalysisOutput:
        """
        Run complete PROMETHEE-GAIA analysis and return structured output.

        This is the recommended method for API/database usage as it returns
        a fully typed and JSON-serializable Pydantic model with standardized keys.

        Args:
            run_visualizations: If True, also displays matplotlib charts

        Returns:
            MCDAAnalysisOutput with:
            - Standardized keys (a1, a2, c1, c2, etc.)
            - Label mappings to retrieve full names
            - All flow values, ranking, and GAIA data
        """
        # Run all analyses
        pI_results = self.run_prometheeI(graph=False)
        pII_results = self.run_prometheeII(graph=False)

        # GAIA requires min(n_alternatives, n_criteria) >= 2 for PCA
        gaia_alternatives = None
        gaia_criteria = None
        gaia_decision_stick = None
        gaia_quality = None
        gaia_method = None
        try:
            gaia_results = self.run_gaia_custom(n_components=2)
            gaia_alternatives = [
                GAIAAlternativeCoordinate(
                    key=gaia_results['alternative_names'][i],
                    x=float(gaia_results['alternative_coords'][i][0]),
                    y=float(gaia_results['alternative_coords'][i][1])
                )
                for i in range(len(gaia_results['alternative_names']))
            ]
            gaia_criteria = [
                GAIACriterionVector(
                    key=gaia_results['criteria_names'][i],
                    x=float(gaia_results['criteria_coords'][i][0]),
                    y=float(gaia_results['criteria_coords'][i][1])
                )
                for i in range(len(gaia_results['criteria_names']))
            ]
            gaia_decision_stick = [float(x) for x in gaia_results['decision_stick']]
            gaia_quality = float(gaia_results['quality_percentage'])
            gaia_method = gaia_results['method']
        except Exception:
            pass

        # Create the output model
        output = MCDAAnalysisOutput(
            alternative_labels=self.alternative_labels,
            criteria_labels=self.criteria_labels,
            positive_flows=pI_results['positive_flows'],
            negative_flows=pI_results['negative_flows'],
            net_flows=pII_results['net_flows'],
            ranking=pII_results['ranking'],
            gaia_alternatives=gaia_alternatives,
            gaia_criteria=gaia_criteria,
            gaia_decision_stick=gaia_decision_stick,
            gaia_quality=gaia_quality,
            gaia_method=gaia_method
        )

        # Optionally show visualizations
        if run_visualizations:
            self.display_gaia()
            self.display_prometheeI()
            self.display_prometheeII()

        return output

    # CUSTOM VISUALIZATION FUNCTIONS
    def display_prometheeI(self):
        """Display PROMETHEE I preference matrix as a colored grid."""
        preference_matrix = self.prometheeI_results['preference_matrix']
        alternatives = self.prometheeI_results['alternatives']
        n = len(alternatives)

        # Define colors for each code
        code_colors = {
            'P+': '#4caf50',   # Green: preference
            'R': '#2196f3',    # Blue: indifference
            'I': '#ffeb3b',    # Yellow: incomparability
            '-': '#e0e0e0'     # Grey: not applicable or self-comparison
        }

        flow_array = np.array(preference_matrix)
        # Create colored grid representation
        color_grid = np.zeros((n, n, 3))
        for i in range(n):
            for j in range(n):
                color_hex = code_colors.get(flow_array[i][j], '#ffffff')
                color_grid[i, j] = mcolors.to_rgb(color_hex)

        fig, ax = plt.subplots(figsize=(1.2*n, 1.2*n))
        ax.imshow(color_grid, aspect='equal')

        # Add text labels in each cell
        for i in range(n):
            for j in range(n):
                txt = flow_array[i][j]
                ax.text(j, i, txt, ha="center", va="center", fontsize=8)

        ax.set_xticks(np.arange(n))
        ax.set_yticks(np.arange(n))
        ax.set_xticklabels(alternatives, rotation=90, fontsize=8)
        ax.set_yticklabels(alternatives, fontsize=8)
        ax.set_title("PROMETHEE I Partial Outranking Matrix")
        plt.tight_layout()
        plt.show()

    def display_prometheeII(self):
        """Display PROMETHEE II net flows as a bar chart."""
        net_flows = self.prometheeII_results['net_flows']
        ranking = self.prometheeII_results['ranking']

        # Get flows in ranking order
        flows = [net_flows[alt] for alt in ranking]

        fig, ax = plt.subplots(figsize=(max(8, len(ranking)*0.7), 5))
        bars = ax.bar(ranking, flows, color='#1976d2', alpha=0.8)
        ax.set_ylabel('Net Flow')
        ax.set_title('PROMETHEE II Net Flow Ranking')
        ax.set_xticklabels(ranking, rotation=90, fontsize=8)
        plt.tight_layout()
        plt.show()

    def display_gaia(self, figsize=(8, 6), save_path=None) -> None:
        """Display GAIA decision plane with alternatives, criteria, and decision stick."""
        # Requires run_gaia_custom() to have been run
        if not hasattr(self, 'gaia_results') or self.gaia_results is None:
            raise ValueError(
                'Please run run_gaia_custom() before display_gaia().')

        alt_coords = np.array(self.gaia_results['alternative_coords'])
        crit_coords = np.array(self.gaia_results['criteria_coords'])
        alt_names = self.gaia_results['alternative_names']
        crit_names = self.gaia_results['criteria_names']
        decision_stick = np.array(self.gaia_results['decision_stick'])
        quality = self.gaia_results['quality_percentage']

        # Plot alternatives as points
        plt.figure(figsize=figsize)
        plt.scatter(alt_coords[:, 0], alt_coords[:, 1],
                    color='blue', s=100, alpha=0.6, label='Alternatives')
        for i, txt in enumerate(alt_names):
            plt.annotate(
                txt, (alt_coords[i, 0], alt_coords[i, 1]), fontsize=8, color='blue')

        # Plot criteria as arrows from origin
        for i, name in enumerate(crit_names):
            plt.arrow(0, 0, crit_coords[i, 0], crit_coords[i, 1],
                      color='red', head_width=0.1, length_includes_head=True, alpha=0.7)
            plt.text(crit_coords[i, 0]*1.15, crit_coords[i, 1]*1.15, name,
                     color='red', fontsize=10, ha='center', va='center')

        # Plot decision stick (weighted combination of criteria)
        plt.arrow(0, 0, decision_stick[0], decision_stick[1],
                  color='green', head_width=0.15, length_includes_head=True,
                  linewidth=3, alpha=0.8, label='Decision Stick')

        plt.axhline(0, color='grey', lw=1, zorder=0)
        plt.axvline(0, color='grey', lw=1, zorder=0)
        plt.xlabel('GAIA axis 1 (PC1)')
        plt.ylabel('GAIA axis 2 (PC2)')
        plt.title(f'GAIA Decision Plane (Quality: {quality:.1f}%)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150)
        else:
            plt.show()
