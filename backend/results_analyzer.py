import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict
import json


class MultiObjectiveResultsAnalyzer:
    """
    Generates all analysis charts and metrics from NSGA-II results.
    Produces figures needed for Chapter 4 and Chapter 5 of the FYP.
    """

    def __init__(self, results: dict, baseline: dict):
        self.results = results
        self.baseline = baseline
        self.pareto_front = results['pareto_front']
        self.generation_log = results['generation_log']
        self.knee = results['knee_solution']

    # ─── FIGURE 1: 3D PARETO FRONT ─────────────────────────────────────────────

    def plot_3d_pareto_front(self, save_path: str = None):
        """
        3D scatter plot of the Pareto front.
        Each point is a non-dominated solution.
        Axes: Energy Cost, Pressure Variance, Pressure Deficit.
        """
        f1 = [s['f1_energy_cost'] for s in self.pareto_front]
        f2 = [s['f2_pressure_variance'] for s in self.pareto_front]
        f3 = [s['f3_pressure_deficit'] for s in self.pareto_front]

        fig = go.Figure(data=[go.Scatter3d(
            x=f1, y=f2, z=f3,
            mode='markers',
            marker=dict(
                size=8,
                color=f1,
                colorscale='Viridis',
                colorbar=dict(title='Energy Cost (₦)'),
                opacity=0.8
            ),
            text=[f"Solution {i}" for i in range(len(f1))],
            name='Pareto Front'
        )])

        # Mark the knee point
        if self.knee:
            fig.add_trace(go.Scatter3d(
                x=[self.knee['f1_energy_cost']],
                y=[self.knee['f2_pressure_variance']],
                z=[self.knee['f3_pressure_deficit']],
                mode='markers',
                marker=dict(size=14, color='red', symbol='diamond'),
                name='Knee Point (Recommended)'
            ))

        fig.update_layout(
            title='Pareto Front: 3 Objective Trade-off Space',
            scene=dict(
                xaxis_title='f1: Energy Cost (₦/day)',
                yaxis_title='f2: Pressure Variance (m²)',
                zaxis_title='f3: Pressure Deficit (m)'
            ),
            width=900, height=700
        )

        if save_path:
            fig.write_html(save_path)
        return fig

    # ─── FIGURE 2: 2D PARETO TRADE-OFF (Energy vs Pressure Variance) ──────────

    def plot_2d_tradeoff(self, obj1='f1', obj2='f2', save_path=None):
        """
        2D Pareto front showing trade-off between any two objectives.
        """
        obj_map = {
            'f1': ('f1_energy_cost', 'Energy Cost (₦/day)'),
            'f2': ('f2_pressure_variance', 'Pressure Variance (m²)'),
            'f3': ('f3_pressure_deficit', 'Pressure Deficit (m)')
        }

        x_key, x_label = obj_map[obj1]
        y_key, y_label = obj_map[obj2]

        x_vals = [s[x_key] for s in self.pareto_front]
        y_vals = [s[y_key] for s in self.pareto_front]

        fig, ax = plt.subplots(figsize=(10, 7))

        # Sort by x for connected line
        sorted_pairs = sorted(zip(x_vals, y_vals))
        x_sorted, y_sorted = zip(*sorted_pairs)

        ax.plot(x_sorted, y_sorted, 'b-', alpha=0.4, linewidth=1.5,
                label='Pareto Front')
        ax.scatter(x_vals, y_vals, c='blue', s=80, zorder=5,
                   label='Pareto Solutions')

        # Mark baseline
        baseline_x = self.baseline.get(x_key.replace('f1_', '').replace(
            'f2_', '').replace('f3_', ''), 0)
        baseline_y = self.baseline.get(y_key.replace('f1_', '').replace(
            'f2_', '').replace('f3_', ''), 0)

        ax.scatter([self.baseline['energy_cost']],
                   [self.baseline['pressure_variance']],
                   c='red', s=200, marker='*', zorder=6,
                   label='Baseline (No Optimization)')

        # Mark knee point
        if self.knee:
            ax.scatter([self.knee[x_key]], [self.knee[y_key]],
                       c='green', s=200, marker='D', zorder=7,
                       label='Knee Point (Recommended Solution)')

        ax.set_xlabel(x_label, fontsize=13)
        ax.set_ylabel(y_label, fontsize=13)
        ax.set_title(f'Pareto Trade-off: {x_label} vs {y_label}', fontsize=15)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        return fig

    # ─── FIGURE 3: CONVERGENCE CURVES ─────────────────────────────────────────

    def plot_convergence(self, save_path=None):
        """
        Plot how each objective improves over generations.
        Proves the GA is learning and converging.
        """
        generations = [g['generation'] for g in self.generation_log]
        min_f1 = [g['min_f1'] for g in self.generation_log]
        min_f2 = [g['min_f2'] for g in self.generation_log]
        min_f3 = [g['min_f3'] for g in self.generation_log]
        pareto_sizes = [g['pareto_front_size'] for g in self.generation_log]

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        axes[0, 0].plot(generations, min_f1, 'b-', linewidth=2)
        axes[0, 0].set_title('Objective 1: Min Energy Cost per Generation')
        axes[0, 0].set_xlabel('Generation')
        axes[0, 0].set_ylabel('Energy Cost (₦/day)')
        axes[0, 0].grid(True, alpha=0.3)

        axes[0, 1].plot(generations, min_f2, 'g-', linewidth=2)
        axes[0, 1].set_title('Objective 2: Min Pressure Variance per Generation')
        axes[0, 1].set_xlabel('Generation')
        axes[0, 1].set_ylabel('Pressure Variance (m²)')
        axes[0, 1].grid(True, alpha=0.3)

        axes[1, 0].plot(generations, min_f3, 'r-', linewidth=2)
        axes[1, 0].set_title('Objective 3: Min Pressure Deficit per Generation')
        axes[1, 0].set_xlabel('Generation')
        axes[1, 0].set_ylabel('Pressure Deficit (m)')
        axes[1, 0].grid(True, alpha=0.3)

        axes[1, 1].plot(generations, pareto_sizes, 'purple', linewidth=2)
        axes[1, 1].set_title('Pareto Front Size Growth per Generation')
        axes[1, 1].set_xlabel('Generation')
        axes[1, 1].set_ylabel('Number of Non-Dominated Solutions')
        axes[1, 1].grid(True, alpha=0.3)

        plt.suptitle('NSGA-II Convergence Analysis', fontsize=16, y=1.02)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        return fig

    # ─── FIGURE 4: BASELINE vs OPTIMIZED COMPARISON ────────────────────────────

    def plot_baseline_comparison(self, save_path=None):
        """
        Bar chart comparing baseline vs knee-point solution across all metrics.
        This is the key results figure for Chapter 5.
        """
        metrics = {
            'Energy Cost (₦/day)': (
                self.baseline['energy_cost'],
                self.knee['f1_energy_cost']
            ),
            'Pressure Variance (m²)': (
                self.baseline['pressure_variance'],
                self.knee['f2_pressure_variance']
            ),
            'Pressure Deficit (m)': (
                self.baseline['pressure_deficit'],
                self.knee['f3_pressure_deficit']
            )
        }

        labels = list(metrics.keys())
        baseline_vals = [v[0] for v in metrics.values()]
        optimized_vals = [v[1] for v in metrics.values()]
        improvements = [
            ((b - o) / b * 100) if b > 0 else 0
            for b, o in zip(baseline_vals, optimized_vals)
        ]

        x = np.arange(len(labels))
        width = 0.35

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        bars1 = ax1.bar(x - width/2, baseline_vals, width,
                        label='Baseline', color='#e74c3c', alpha=0.8)
        bars2 = ax1.bar(x + width/2, optimized_vals, width,
                        label='GA Optimized (Knee Point)',
                        color='#2ecc71', alpha=0.8)

        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, fontsize=10)
        ax1.set_title('Baseline vs GA-Optimized Performance', fontsize=13)
        ax1.legend()
        ax1.grid(True, alpha=0.3, axis='y')

        # Improvement percentages
        colors = ['#27ae60' if imp > 0 else '#e74c3c' for imp in improvements]
        ax2.bar(labels, improvements, color=colors, alpha=0.8)
        ax2.axhline(y=0, color='black', linewidth=0.8)
        ax2.set_title('Percentage Improvement Over Baseline (%)', fontsize=13)
        ax2.set_ylabel('Improvement (%)')
        for i, (label, imp) in enumerate(zip(labels, improvements)):
            ax2.text(i, imp + 0.5, f'{imp:.1f}%',
                     ha='center', va='bottom', fontsize=11, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        return fig

    # ─── FIGURE 5: PRESSURE DISTRIBUTION HEATMAP ──────────────────────────────

    def plot_pressure_distribution(self, save_path=None):
        """
        Compare pressure distribution across nodes: baseline vs optimized.
        """
        baseline_pressures = list(self.baseline['pressures'].values())
        optimized_pressures = list(
            self.knee['pressures'].values()
        )

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        axes[0].hist(baseline_pressures, bins=20, color='#e74c3c',
                     alpha=0.7, edgecolor='black')
        axes[0].axvline(x=10, color='black', linestyle='--',
                        linewidth=2, label='Min Threshold (10m)')
        axes[0].set_title('Baseline: Pressure Distribution Across Nodes')
        axes[0].set_xlabel('Pressure (m)')
        axes[0].set_ylabel('Number of Nodes')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        axes[1].hist(optimized_pressures, bins=20, color='#2ecc71',
                     alpha=0.7, edgecolor='black')
        axes[1].axvline(x=10, color='black', linestyle='--',
                        linewidth=2, label='Min Threshold (10m)')
        axes[1].set_title('GA Optimized: Pressure Distribution Across Nodes')
        axes[1].set_xlabel('Pressure (m)')
        axes[1].set_ylabel('Number of Nodes')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

        plt.suptitle('Pressure Equity Improvement', fontsize=15)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        return fig

    # ─── SUMMARY STATISTICS TABLE ──────────────────────────────────────────────

    def generate_summary_table(self) -> dict:
        """
        Generate the results table for Chapter 5 of the FYP.
        """
        knee = self.knee
        baseline = self.baseline

        def pct_change(baseline_val, optimized_val):
            if baseline_val == 0:
                return 0
            return ((baseline_val - optimized_val) / baseline_val) * 100

        return {
            'metrics': [
                {
                    'metric': 'Daily Energy Cost',
                    'unit': '₦/day',
                    'baseline': round(baseline['energy_cost'], 2),
                    'optimized': round(knee['f1_energy_cost'], 2),
                    'improvement_pct': round(
                        pct_change(baseline['energy_cost'],
                                   knee['f1_energy_cost']), 1)
                },
                {
                    'metric': 'Pressure Variance',
                    'unit': 'm²',
                    'baseline': round(baseline['pressure_variance'], 4),
                    'optimized': round(knee['f2_pressure_variance'], 4),
                    'improvement_pct': round(
                        pct_change(baseline['pressure_variance'],
                                   knee['f2_pressure_variance']), 1)
                },
                {
                    'metric': 'Pressure Deficit',
                    'unit': 'm',
                    'baseline': round(baseline['pressure_deficit'], 2),
                    'optimized': round(knee['f3_pressure_deficit'], 2),
                    'improvement_pct': round(
                        pct_change(baseline['pressure_deficit'],
                                   knee['f3_pressure_deficit']), 1)
                },
                {
                    'metric': 'Pareto Front Size',
                    'unit': 'solutions',
                    'baseline': 1,
                    'optimized': self.results['pareto_front_size'],
                    'improvement_pct': 'N/A'
                },
                {
                    'metric': 'Hypervolume Indicator',
                    'unit': 'dimensionless',
                    'baseline': 0,
                    'optimized': round(self.results['hypervolume'], 4),
                    'improvement_pct': 'N/A'
                }
            ]
        }