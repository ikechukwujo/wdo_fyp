import numpy as np
import random
from deap import base, creator, tools, algorithms
from epanet_simulator import EPANETSimulator
import json
from typing import List, Dict, Tuple


# ─── DEAP Setup: Define multi-objective minimization problem ───────────────────
# weights=(-1,-1,-1) means minimize all three objectives
creator.create("FitnessMulti", base.Fitness, weights=(-1.0, -1.0, -1.0))
creator.create("Individual", list, fitness=creator.FitnessMulti)


class NSGAII_WaterOptimizer:
    """
    NSGA-II Multi-Objective Optimizer for Water Distribution Networks.
    Optimizes simultaneously for:
      - f1: Energy cost minimization
      - f2: Pressure variance minimization (equity)
      - f3: Pressure deficit minimization (NRW proxy)
    """

    def __init__(self, network_file: str, params: dict):
        self.simulator = EPANETSimulator(network_file)
        self.num_genes = (self.simulator.get_num_pumps() +
                          self.simulator.get_num_valves())
        if self.num_genes == 0:
            print("Warning: Network has no pumps or valves. Optimization may not be meaningful.")
            # Fallback to avoid complete failure or ZeroDivisionError:
            self.num_genes = 1

        self.params = params

        # Track all evaluated solutions for analysis
        self.all_solutions: List[dict] = []
        self.generation_log: List[dict] = []

        # DEAP toolbox setup
        self.toolbox = self._setup_toolbox()

    # ─── TOOLBOX CONFIGURATION ─────────────────────────────────────────────────

    def _setup_toolbox(self) -> base.Toolbox:
        toolbox = base.Toolbox()

        # Gene: random float between 0 and 1
        toolbox.register("attr_float", random.uniform, 0.0, 1.0)

        # Individual: list of genes
        toolbox.register(
            "individual",
            tools.initRepeat,
            creator.Individual,
            toolbox.attr_float,
            n=self.num_genes
        )

        # Population: list of individuals
        toolbox.register(
            "population",
            tools.initRepeat,
            list,
            toolbox.individual
        )

        # Register genetic operators
        toolbox.register("evaluate", self._evaluate_individual)
        toolbox.register(
            "mate",
            tools.cxSimulatedBinaryBounded,
            low=0.0, up=1.0, eta=20.0  # SBX crossover
        )
        toolbox.register(
            "mutate",
            tools.mutPolynomialBounded,
            low=0.0, up=1.0, eta=20.0,
            indpb=1.0 / self.num_genes if self.num_genes > 0 else 0.1  # Polynomial mutation
        )
        toolbox.register(
            "select",
            tools.selNSGA2  # Core NSGA-II selection operator
        )

        return toolbox

    # ─── FITNESS EVALUATION ────────────────────────────────────────────────────

    def _evaluate_individual(self, individual: list) -> Tuple[float, float, float]:
        """
        Evaluate one chromosome by running EPANET simulation.
        Returns tuple of (energy_cost, pressure_variance, pressure_deficit).
        DEAP requires fitness as a tuple matching the number of objectives.
        """
        try:
            result = self.simulator.run_simulation(individual)

            f1 = result['energy_cost']           # Objective 1: Energy
            f2 = result['pressure_variance']     # Objective 2: Equity
            f3 = result['pressure_deficit']      # Objective 3: NRW proxy

            # Apply constraint penalty if hydraulic constraints violated
            penalty = self._calculate_penalty(result)
            
            # DEAP fitness logic requires penalized values
            fit_f1 = f1 + penalty
            fit_f2 = f2 + penalty
            fit_f3 = f3 + penalty

            # Log this solution for analysis, storing unpenalized real-world values
            self.all_solutions.append({
                'genes': list(individual),
                'f1_energy': f1,            # Log original unpenalized metric
                'f2_pressure_variance': f2, # Log original unpenalized metric
                'f3_pressure_deficit': f3,  # Log original unpenalized metric
                'penalty': penalty,
                'pressures': result['pressures'],
                'flows': result['flows']
            })

            return (fit_f1, fit_f2, fit_f3)

        except Exception as e:
            # Return worst-case fitness on simulation failure
            print(f"Simulation failed: {e}")
            return (1e9, 1e9, 1e9)

    def _calculate_penalty(self, result: dict) -> float:
        """
        Constraint handling via penalty function.
        Adds penalty for constraint violations — kept intentionally moderate
        so NSGA-II can still distinguish between "slightly infeasible" and
        "very infeasible" chromosomes (a too-large coefficient collapses all
        fitness values to the same huge number).
        """
        penalty = 0.0
        penalty_coefficient = 100.0  # was 1000 — reduced to preserve gradient

        # Penalty for nodes below minimum pressure
        min_pressure = self.params.get('min_pressure_threshold', 5.0)
        for node_id, pressure in result['pressures'].items():
            if pressure < min_pressure:
                penalty += penalty_coefficient * (min_pressure - pressure)

        # Penalty for pipes exceeding max velocity
        max_velocity = self.params.get('max_velocity', 3.0)
        for pipe_id, velocity in result.get('velocities', {}).items():
            if velocity > max_velocity:
                penalty += penalty_coefficient * (velocity - max_velocity)

        return penalty

    # ─── MAIN NSGA-II LOOP ─────────────────────────────────────────────────────

    def run(self, progress_callback=None) -> dict:
        """
        Execute the full NSGA-II algorithm.
        Returns Pareto front solutions and convergence data.
        Optional `progress_callback(current_gen, total_gen)` reports progress.
        """
        POP_SIZE = self.params.get('population_size', 100)
        N_GEN = self.params.get('num_generations', 200)
        CXPB = self.params.get('crossover_rate', 0.9)
        MUTPB = self.params.get('mutation_rate', 0.1)

        print(f"Starting NSGA-II: Pop={POP_SIZE}, Gen={N_GEN}")

        # Initialize population
        population = self.toolbox.population(n=POP_SIZE)

        # Evaluate initial population
        fitnesses = list(map(self.toolbox.evaluate, population))
        for ind, fit in zip(population, fitnesses):
            ind.fitness.values = fit

        # Assign initial crowding distance (NSGA-II requirement)
        population = self.toolbox.select(population, len(population))

        # ── Generation Loop ──────────────────────────────────────────────────
        for generation in range(N_GEN):
            # Generate offspring via tournament selection + crossover + mutation
            offspring = tools.selTournament(population, len(population), tournsize=2)
            offspring = list(map(self.toolbox.clone, offspring))

            # Apply crossover
            for child1, child2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < CXPB:
                    self.toolbox.mate(child1, child2)
                    del child1.fitness.values
                    del child2.fitness.values

            # Apply mutation
            for mutant in offspring:
                if random.random() < MUTPB:
                    self.toolbox.mutate(mutant)
                    del mutant.fitness.values

            # Evaluate individuals with invalid fitness
            invalid_individuals = [
                ind for ind in offspring if not ind.fitness.valid
            ]
            fitnesses = map(self.toolbox.evaluate, invalid_individuals)
            for ind, fit in zip(invalid_individuals, fitnesses):
                ind.fitness.values = fit

            # NSGA-II: Combine parent + offspring, select best N
            combined = population + offspring
            population = self.toolbox.select(combined, POP_SIZE)

            # Log generation statistics
            gen_stats = self._log_generation(generation, population)
            self.generation_log.append(gen_stats)

            print(
                f"Gen {generation+1}/{N_GEN} | "
                f"Pareto Front Size: {gen_stats['pareto_front_size']} | "
                f"Avg Energy: {gen_stats['avg_f1']:.3f} | "
                f"Avg Pressure Var: {gen_stats['avg_f2']:.3f}"
            )
            
            if progress_callback:
                progress_callback(generation + 1, N_GEN)

        # ── Extract Final Pareto Front ────────────────────────────────────────
        pareto_front = tools.sortNondominated(
            population, len(population), first_front_only=True
        )[0]

        return self._package_results(pareto_front, population)

    # ─── RESULT PACKAGING ──────────────────────────────────────────────────────

    def _package_results(self, pareto_front, final_population) -> dict:
        """
        Package all results into a structured dictionary for API and DB storage.
        """
        pareto_solutions = []
        for ind in pareto_front:
            sim_result = self.simulator.run_simulation(ind)
            penalty = self._calculate_penalty(sim_result)
            pareto_solutions.append({
                'chromosome': list(ind),
                'f1_energy_cost': sim_result['energy_cost'],
                'f2_pressure_variance': sim_result['pressure_variance'],
                'f3_pressure_deficit': sim_result['pressure_deficit'],
                'penalty': penalty,
                'pressures': sim_result['pressures'],
                'pump_settings': list(ind[:self.simulator.get_num_pumps()]),
                'valve_settings': list(ind[self.simulator.get_num_pumps():])
            })

        # Identify knee point solution (best balanced compromise)
        knee_solution = self._find_knee_point(pareto_solutions)

        return {
            'pareto_front': pareto_solutions,
            'knee_solution': knee_solution,
            'generation_log': self.generation_log,
            'total_evaluations': len(self.all_solutions),
            'pareto_front_size': len(pareto_solutions),
            'hypervolume': self._calculate_hypervolume(pareto_solutions)
        }

    def _find_knee_point(self, pareto_solutions: List[dict]) -> dict:
        """
        Find the knee point: solution with best balance across all objectives.
        Uses normalized distance from ideal point method.
        """
        if not pareto_solutions:
            return None

        # Normalize each objective to [0, 1]
        f1_vals = [s['f1_energy_cost'] for s in pareto_solutions]
        f2_vals = [s['f2_pressure_variance'] for s in pareto_solutions]
        f3_vals = [s['f3_pressure_deficit'] for s in pareto_solutions]

        def normalize(vals):
            min_v, max_v = min(vals), max(vals)
            if max_v == min_v:
                return [0.0] * len(vals)
            return [(v - min_v) / (max_v - min_v) for v in vals]

        f1_norm = normalize(f1_vals)
        f2_norm = normalize(f2_vals)
        f3_norm = normalize(f3_vals)

        # Distance from ideal point (0, 0, 0)
        distances = [
            np.sqrt(f1_norm[i]**2 + f2_norm[i]**2 + f3_norm[i]**2)
            for i in range(len(pareto_solutions))
        ]

        knee_idx = np.argmin(distances)
        knee = pareto_solutions[knee_idx].copy()
        knee['is_knee_point'] = True
        return knee

    def _calculate_hypervolume(self, pareto_solutions: List[dict]) -> float:
        """
        Calculate hypervolume indicator — standard metric for
        multi-objective optimization quality.
        Higher hypervolume = better Pareto front coverage.
        """
        if len(pareto_solutions) < 2:
            return 0.0

        # Reference point (worst acceptable values)
        ref_point = np.array([1e6, 1e6, 1e6])

        points = np.array([
            [s['f1_energy_cost'],
             s['f2_pressure_variance'],
             s['f3_pressure_deficit']]
            for s in pareto_solutions
        ])

        # Simplified hypervolume for 3D (use pygmo for production)
        # This is an approximation
        dominated_volume = 0.0
        for point in points:
            vol = np.prod(ref_point - point)
            if vol > 0:
                dominated_volume += vol

        return float(dominated_volume)

    def _log_generation(self, generation: int, population) -> dict:
        """Log statistics for each generation for convergence analysis."""
        fitnesses = [ind.fitness.values for ind in population]
        f1_vals = [f[0] for f in fitnesses]
        f2_vals = [f[1] for f in fitnesses]
        f3_vals = [f[2] for f in fitnesses]

        pareto_front = tools.sortNondominated(
            population, len(population), first_front_only=True
        )[0]

        return {
            'generation': generation,
            'avg_f1': np.mean(f1_vals),
            'min_f1': np.min(f1_vals),
            'avg_f2': np.mean(f2_vals),
            'min_f2': np.min(f2_vals),
            'avg_f3': np.mean(f3_vals),
            'min_f3': np.min(f3_vals),
            'pareto_front_size': len(pareto_front)
        }