from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from nsga2_engine import NSGAII_WaterOptimizer
from epanet_simulator import EPANETSimulator
from results_analyzer import MultiObjectiveResultsAnalyzer
from database import save_run, get_all_runs, init_db
import uuid, os, shutil, traceback, threading

app = FastAPI(title="Multi-Objective Water Distribution Optimizer")

app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.on_event("startup")
def startup():
    init_db()


jobs = {}

# Module-level simulator cache: keyed by network_file path.
# Avoids running _prepare_optim_inp() on every request.
_sim_cache: dict = {}
_sim_lock = threading.Lock()

def _get_sim(network_file: str) -> EPANETSimulator:
    """Return a cached EPANETSimulator for this network file (Thread-safe)."""
    with _sim_lock:
        if network_file not in _sim_cache:
            _sim_cache[network_file] = EPANETSimulator(network_file)
        return _sim_cache[network_file]


class OptimizationRequest(BaseModel):
    network_file: str = "networks/nigeria_demo.inp"
    population_size: int = 50
    num_generations: int = 50
    crossover_rate: float = 0.9
    mutation_rate: float = 0.1
    min_pressure_threshold: float = 5.0
    max_velocity: float = 3.0


class ChromosomeRequest(BaseModel):
    network_file: str = "networks/nigeria_demo.inp"
    chromosome: List[float]


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Water Distribution Optimizer API is running"}


# ── Optimization ──────────────────────────────────────────────────────────────

@app.post("/api/optimize")
async def start_optimization(
    request: OptimizationRequest,
    background_tasks: BackgroundTasks
):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "running", "progress": 0, "result": None}
    background_tasks.add_task(run_optimization_job, job_id, request)
    return {"job_id": job_id, "status": "running",
            "message": f"Optimization started. Poll /api/results/{job_id}"}


def run_optimization_job(job_id: str, request: OptimizationRequest):
    try:
        print(f"\n{'='*50}")
        print(f"Job {job_id}  |  Network: {request.network_file}")
        print(f"Pop: {request.population_size}  Gen: {request.num_generations}")
        print(f"{'='*50}\n")

        def update_progress(gen, total):
            jobs[job_id]["progress"] = int((gen / total) * 100)

        optimizer = NSGAII_WaterOptimizer(
            network_file=request.network_file,
            params=request.dict()
        )
        results = optimizer.run(progress_callback=update_progress)

        # Use cached simulator for baseline
        sim     = _get_sim(request.network_file)
        baseline = sim.get_baseline()

        analyzer = MultiObjectiveResultsAnalyzer(results, baseline)
        summary  = analyzer.generate_summary_table()

        save_run(job_id, results, baseline, summary)

        jobs[job_id] = {
            "status": "complete",
            "result": {
                "pareto_front":      results["pareto_front"],
                "knee_solution":     results["knee_solution"],
                "generation_log":    results["generation_log"],
                "pareto_front_size": results["pareto_front_size"],
                "hypervolume":       results["hypervolume"],
                "baseline":          baseline,
                "summary_table":     summary,
            }
        }
        print(f"\nJob {job_id} complete -- Pareto front size: {results['pareto_front_size']}")

    except Exception as e:
        print(f"Job {job_id} FAILED: {e}")
        traceback.print_exc()
        jobs[job_id] = {"status": "failed", "error": str(e)}


@app.get("/api/results/{job_id}")
def get_results(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── Network ───────────────────────────────────────────────────────────────────

@app.post("/api/network/upload")
async def upload_network(file: UploadFile = File(...)):
    """Upload an EPANET .inp file -- saves to networks/ and returns path."""
    if not file.filename.endswith(".inp"):
        raise HTTPException(status_code=400, detail="Only .inp files are accepted")
    dest = os.path.join("networks", file.filename)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    # Clear cache so the new file gets a fresh simulator
    with _sim_lock:
        _sim_cache.pop(dest, None)
    return {"network_file": dest, "filename": file.filename}


@app.get("/api/network/topology")
def get_network_topology(network_file: str = "networks/nigeria_demo.inp"):
    """Static topology (no simulation -- nodes have pressure=0)."""
    try:
        sim = _get_sim(network_file)
        return sim.get_network_topology()
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/network/topology/simulated")
def get_simulated_topology(
    network_file: str = "networks/nigeria_demo.inp",
    mode: str = "baseline"
):
    """
    Baseline simulation (all pumps speed=1.0) with enriched topology --
    nodes with real pressures, links with flow/velocity/type.
    """
    try:
        sim = _get_sim(network_file)
        return sim.get_simulated_topology(chromosome=None)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/network/topology/chromosome")
def get_chromosome_topology(request: ChromosomeRequest):
    """Return simulated topology for a specific GA chromosome."""
    try:
        sim = _get_sim(request.network_file)
        return sim.get_simulated_topology(chromosome=request.chromosome)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/baseline")
def get_baseline(network_file: str = "networks/nigeria_demo.inp"):
    try:
        sim = _get_sim(network_file)
        return sim.get_baseline()
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
def get_history():
    return get_all_runs()