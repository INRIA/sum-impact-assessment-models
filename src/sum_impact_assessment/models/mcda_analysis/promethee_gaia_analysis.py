from typing import List, Dict
import numpy as np
from pyDecision.algorithm import promethee_i, promethee_ii, promethee_gaia
from sklearn.decomposition import PCA
from ...schemas.mcda import Goal, Alternative
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

        self.criteria_short = [f"G{i+1}" for i in range(len(self.goals))]
        self.alternative_short = [
            f"A{i+1}" for i in range(len(self.alternatives))]

    def run_prometheeI(self, graph: bool = False) -> Dict:
        flows = promethee_i(self.matrix, W=self.weights,
                            Q=self.Q, S=self.S, P=self.P, F=self.F, graph=graph)
        print('promethee_i flows', flows)
        results = {'alternatives': self.alternative_short,
                   'flows': flows.tolist()}
        self.prometheeI_results = results
        return results

    def run_prometheeII(self, graph: bool = False) -> Dict:
        net_flows = promethee_ii(self.matrix, self.weights,
                                 Q=self.Q, S=self.S, P=self.P, F=self.F, sort=True, graph=graph, verbose=True)
        results = {'alternatives': self.alternative_short,
                   'net_flow': net_flows.tolist()}
        self.prometheeII_results = results
        return results

    def run_gaia(self, x: int = 10, y: int = 10) -> Dict:
        # Use pyDecision's built-in GAIA function
        promethee_gaia(
            self.matrix, self.weights,  Q=self.Q, S=self.S, P=self.P, F=self.F, size_x=x, size_y=y)

    def run_gaia_custom(self, n_components: int = 2) -> Dict:
        # Center and scale the decision matrix (standard GAIA practice)
        X = (self.matrix - np.mean(self.matrix, axis=0)) / \
            (np.std(self.matrix, axis=0) + 1e-12)
        pca = PCA(n_components=n_components)
        alt_coords = pca.fit_transform(X)  # Alternatives in new PCA/GAIA plane
        crit_coords = pca.components_.T    # Criteria as vectors in this plane

        # Save for potential display function
        self.gaia_results = {
            'alternative_names': self.alternative_short,
            # shape: [n_alt x n_comp]
            'alternative_coords': alt_coords.tolist(),
            'criteria_names': self.criteria_short,
            # shape: [n_criteria x n_comp]
            'criteria_coords': crit_coords.tolist(),
            'explained_variance_ratio': pca.explained_variance_ratio_.tolist()
        }
        return self.gaia_results

    # CUSTOM VISUALIZATION FUNCTIONS
    def display_prometheeI(self):
        flows = self.prometheeI_results['flows']
        alternatives = self.prometheeI_results['alternatives']
        n = len(alternatives)

        # Define colors for each code
        code_colors = {
            'P+': '#4caf50',   # Green: preference
            'R': '#2196f3',    # Blue: indifference
            'I': '#ffeb3b',    # Yellow: incomparability
            '-': '#e0e0e0'     # Grey: not applicable or self-comparison
        }

        flow_array = np.array(flows)
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
        idx_and_values = self.prometheeII_results['net_flow']

        # Sort by net flow descending
        idx_and_values = sorted(idx_and_values, key=lambda x: -x[1])
        indices = [int(i[0]) - 1 for i in idx_and_values]
        flows = [i[1] for i in idx_and_values]

        # Map indices to alternative names using self.alternative_short
        sorted_alts = [self.alternative_short[i] for i in indices]

        fig, ax = plt.subplots(figsize=(max(8, len(idx_and_values)*0.7), 5))
        bars = ax.bar(sorted_alts, flows, color='#1976d2', alpha=0.8)
        ax.set_ylabel('Net Flow')
        ax.set_title('PROMETHEE II Net Flow Ranking')
        ax.set_xticklabels(sorted_alts, rotation=90, fontsize=8)
        plt.tight_layout()
        plt.show()

    def display_gaia(self, figsize=(8, 6), save_path=None) -> None:
        # Requires run_gaia_custom() to have been run
        if not hasattr(self, 'gaia_results') or self.gaia_results is None:
            raise ValueError(
                'Please run run_gaia_custom() before display_gaia().')

        alt_coords = np.array(self.gaia_results['alternative_coords'])
        crit_coords = np.array(self.gaia_results['criteria_coords'])
        alt_names = self.gaia_results['alternative_names']
        crit_names = self.gaia_results['criteria_names']

        # Plot alternatives as points
        plt.figure(figsize=figsize)
        plt.scatter(alt_coords[:, 0], alt_coords[:, 1], color='blue')
        for i, txt in enumerate(alt_names):
            plt.annotate(
                txt, (alt_coords[i, 0], alt_coords[i, 1]), fontsize=8, color='blue')

        # Plot criteria as arrows from origin
        for i, name in enumerate(crit_names):
            plt.arrow(0, 0, crit_coords[i, 0], crit_coords[i, 1],
                      color='red', head_width=0.1, length_includes_head=True)
            plt.text(crit_coords[i, 0]*1.15, crit_coords[i, 1]*1.15, name,
                     color='red', fontsize=10, ha='center', va='center')

        plt.axhline(0, color='grey', lw=1, zorder=0)
        plt.axvline(0, color='grey', lw=1, zorder=0)
        plt.xlabel('GAIA axis 1 (PC1)')
        plt.ylabel('GAIA axis 2 (PC2)')
        plt.title('GAIA decision plane')
        plt.grid(True)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150)
        else:
            plt.show()
