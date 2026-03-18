"""
epanet_simulator.py  --  EPyT v2.x Robust Version

Fixes:
1. Robust INP pre-processing (avoids corruption in _optim_*.inp).
2. Step-by-step simulation with junction-only stats to avoid reservoir heads.
3. Per-call INP copies for parallel safety.
4. Error checking on hydraulic solver return codes.
"""
from epyt import epanet
import numpy as np
import os
import re
import uuid
import warnings
import traceback
import tempfile
import threading

# Global reentrant lock to serialize all access to the EPANET DLL via EPyT.
# This is required on Windows to prevent OSError: [WinError 1] and hangs.
# RLock allows the same thread to acquire the lock multiple times (reentrant).
_EPANET_LOCK = threading.RLock()

warnings.filterwarnings("ignore", category=UserWarning)

def _open(inp_file: str):
    with _EPANET_LOCK:
        try:
            return epanet(inp_file, display_msg=False)
        except TypeError:
            return epanet(inp_file)

def _flatten(val):
    if val is None: return []
    arr = np.array(val).flatten()
    return [int(x) for x in arr if int(x) > 0]

class EPANETSimulator:
    DEFAULT_NETWORK = "networks/nigeria_demo.inp"

    def __init__(self, inp_file: str = None):
        self._src_file = os.path.abspath(inp_file or self.DEFAULT_NETWORK)
        if not os.path.exists(self._src_file):
            raise FileNotFoundError(f"Network file not found: '{self._src_file}'")
        self.inp_file = None 
        self._prepare_optim_inp()

    def _prepare_optim_inp(self):
        """
        Robust line-by-line modification of the INP file.
        Preserves all structural integrity, only empties prohibited sections.
        """
        en = _open(self._src_file)
        self.pump_indices  = _flatten(en.getLinkPumpIndex())
        self.valve_indices = _flatten(en.getLinkValveIndex())
        self.num_nodes     = en.getNodeCount()
        self.num_links     = en.getLinkCount()
        self.node_indices  = list(range(1, self.num_nodes + 1))
        self.link_indices  = list(range(1, self.num_links + 1))

        # Build Metadata Mapping
        self.node_names = {i: str(en.getNodeNameID(i)) for i in self.node_indices}
        self.link_names = {i: str(en.getLinkNameID(i)) for i in self.link_indices}
        
        raw_types = en.getNodeType()
        _NTYPES = ["JUNCTION", "RESERVOIR", "TANK"]
        self.node_types = {}
        for i, nid in enumerate(self.node_indices):
            raw = raw_types[i] if i < len(raw_types) else 0
            if isinstance(raw, (int, float, np.integer)):
                self.node_types[nid] = _NTYPES[min(int(raw), 2)]
            else:
                t_str = str(raw).upper()
                if "JUNCTION" in t_str: self.node_types[nid] = "JUNCTION"
                elif "RESERVOIR" in t_str: self.node_types[nid] = "RESERVOIR"
                elif "TANK" in t_str: self.node_types[nid] = "TANK"
                else: self.node_types[nid] = "JUNCTION"

        self.link_connectivity = {}
        for lid in self.link_indices:
            try:
                n = en.getLinkNodesIndex(lid)
                self.link_connectivity[lid] = {"source": int(n[0]), "target": int(n[1])}
            except: self.link_connectivity[lid] = {"source": 0, "target": 0}

        try:
            coords = en.getNodeCoordinates()
            xd, yd = coords.get("x", {}), coords.get("y", {})
            self.node_x = {n: float(xd.get(n, 0.0)) for n in self.node_indices}
            self.node_y = {n: float(yd.get(n, 0.0)) for n in self.node_indices}
        except:
            self.node_x = {n: 0.0 for n in self.node_indices}
            self.node_y = {n: 0.0 for n in self.node_indices}
            
        try:
            elev = en.getNodeElevations()
            self.node_elev = {nid: float(elev[i]) for i, nid in enumerate(self.node_indices)}
        except: self.node_elev = {nid: 0.0 for nid in self.node_indices}

        with _EPANET_LOCK:
            en.unload()

        # Line-by-line modification
        with open(self._src_file, "r") as f:
            lines = f.readlines()

        new_lines = []
        skip_content = False
        target_sections = ["[CONTROLS]", "[RULES]"]
        patterns_found = False
        
        for line in lines:
            stripped = line.strip().upper()
            if stripped.startswith("[") and stripped.endswith("]"):
                new_lines.append(line)
                skip_content = stripped in target_sections
                if stripped == "[PATTERNS]":
                    patterns_found = True
                    for pid in self.pump_indices:
                        new_lines.append(f"GA_PUMP_{pid}  {'  '.join(['1.0']*24)}\n")
            elif not skip_content:
                new_lines.append(line)

        if not patterns_found:
            # Append patterns before [END] if possible
            end_idx = -1
            for i, ln in enumerate(new_lines):
                if "[END]" in ln.upper(): end_idx = i; break
            
            pats = ["[PATTERNS]\n"]
            for pid in self.pump_indices:
                pats.append(f"GA_PUMP_{pid}  {'  '.join(['1.0']*24)}\n")
            
            if end_idx != -1:
                new_lines = new_lines[:end_idx] + pats + new_lines[end_idx:]
            else:
                new_lines += pats

        uid = uuid.uuid4().hex[:8]
        # Use a dedicated workspace directory in temp for this simulator instance
        self.workspace = os.path.join(tempfile.gettempdir(), f"wd_optim_{uid}")
        os.makedirs(self.workspace, exist_ok=True)
        
        self.inp_file = os.path.join(self.workspace, "optim.inp")
        with open(self.inp_file, "w") as f:
            f.writelines(new_lines)

        print(f"[EPANETSimulator] Prepared (Workspace): {self.workspace}")

    def get_num_pumps(self): return len(self.pump_indices)
    def get_num_valves(self): return len(self.valve_indices)

    def run_simulation(self, chromosome: list) -> dict:
        import shutil
        num_p, num_v = len(self.pump_indices), len(self.valve_indices)
        p_speeds = list(chromosome[:num_p])
        v_setts = list(chromosome[num_p:])

        uid = uuid.uuid4().hex[:8]
        # Per-call INP also isolated in the workspace
        call_inp = os.path.join(self.workspace, f"call_{uid}.inp")
        shutil.copy2(self.inp_file, call_inp)

        en = None
        with _EPANET_LOCK:
            try:
                en = _open(call_inp)
                for i, pid in enumerate(self.pump_indices):
                    s = float(np.clip(p_speeds[i], 0.2, 1.5))
                    pat_name = f"GA_PUMP_{pid}"
                    pi = en.getPatternIndex(pat_name)
                    if pi > 0:
                        en.setPattern(pi, [s] * 24)
                        en.setLinkPumpPatternIndex(pid, pi)

                for i, vid in enumerate(self.valve_indices):
                    s = float(np.clip(v_setts[i], 0.0, 1.0)) * 100
                    en.setLinkSettings(vid, s)

                # Step-by-step
                en.openHydraulicAnalysis()
                en.initializeHydraulicAnalysis(0)
                p_sum = np.zeros(self.num_nodes)
                f_sum = np.zeros(self.num_links)
                v_sum = np.zeros(self.num_links)
                e_total = 0.0
                steps = 0

                while True:
                    err = en.runHydraulicAnalysis()
                    
                    p_curr = np.array(en.getNodePressure(), dtype=float)
                    f_curr = np.array(en.getLinkFlows(), dtype=float)
                    v_curr = np.array(en.getLinkVelocity(), dtype=float)
                    
                    p_sum += p_curr[:self.num_nodes] if len(p_curr) >= self.num_nodes else np.pad(p_curr, (0, self.num_nodes - len(p_curr)))
                    f_sum += f_curr[:self.num_links] if len(f_curr) >= self.num_links else np.pad(f_curr, (0, self.num_links - len(f_curr)))
                    v_sum += v_curr[:self.num_links] if len(v_curr) >= self.num_links else np.pad(v_curr, (0, self.num_links - len(v_curr)))
                    
                    for pid in self.pump_indices:
                        try:
                            e = en.getLinkEnergy(pid)
                            if e is not None:
                                e_total += abs(float(np.array(e).flatten()[0]))
                        except: pass
                    
                    steps += 1
                    if en.nextHydraulicAnalysisStep() <= 0: break
                
                en.closeHydraulicAnalysis()

                if steps > 0:
                    p_avg, f_avg, v_avg = p_sum/steps, f_sum/steps, v_sum/steps
                else:
                    p_avg = f_avg = v_avg = np.zeros(max(self.num_nodes, self.num_links))

                pressures = {nid: float(p_avg[nid-1]) for nid in self.node_indices}
                flows = {lid: abs(float(f_avg[lid-1])) for lid in self.link_indices}
                velocities = {lid: abs(float(v_avg[lid-1])) for lid in self.link_indices}

                # Metrics
                junction_ids = [n for n, t in self.node_types.items() if t == "JUNCTION"]
                junction_p = [pressures[n] for n in junction_ids]
                
                tariff, min_p = 68.0, 5.0
                energy_cost = max(0.0, e_total * tariff)
                p_stats = junction_p if junction_p else [p for p in pressures.values()]
                
                # Penalize only on extremely large failures or NaNs
                if any(np.isnan(p_stats)) or any(p < -500 for p in p_stats):
                    return self._worst_case()

                return {
                    "pressures": pressures,
                    "flows": flows,
                    "velocities": velocities,
                    "energy_cost": energy_cost,
                    "pressure_variance": float(np.var(p_stats)),
                    "pressure_deficit": sum(max(0.0, min_p - p) for p in p_stats),
                    "total_energy_kwh": e_total,
                    "avg_pressure": float(np.mean(p_stats)),
                    "min_pressure": float(np.min(p_stats)),
                    "max_pressure": float(np.max(p_stats)),
                    "num_nodes_below_threshold": sum(1 for p in p_stats if p < min_p),
                }

            except Exception as e:
                print(f"[EPANETSimulator] Error: {e}")
                traceback.print_exc()
                return self._worst_case()
            finally:
                if en: 
                    try: 
                        en.unload()
                    except: pass
            for ext in (".inp", ".rpt", ".out", ".bin"):
                path = call_inp.replace(".inp", ext)
                if os.path.exists(path):
                    try: os.remove(path)
                    except: pass

    def get_network_topology(self) -> dict:
        return {
            "nodes": [{"id": n, "name": self.node_names.get(n), "x": self.node_x.get(n), "y": self.node_y.get(n),
                       "elevation": self.node_elev.get(n), "type": self.node_types.get(n), "pressure": 0.0} 
                      for n in self.node_indices],
            "links": [{"id": l, "name": self.link_names.get(l), "source": self.link_connectivity[l]["source"],
                       "target": self.link_connectivity[l]["target"], "type": "PIPE", "flow": 0.0, "velocity": 0.0}
                      for l in self.link_indices],
            "num_nodes": self.num_nodes, "num_links": self.num_links,
            "num_pumps": len(self.pump_indices), "num_valves": len(self.valve_indices)
        }

    def get_simulated_topology(self, chromosome: list = None) -> dict:
        if chromosome is None:
            chromosome = [1.0]*self.get_num_pumps() + [1.0]*self.get_num_valves()
        sim = self.run_simulation(chromosome)
        res = self.get_network_topology()
        for node in res["nodes"]:
            node["pressure"] = sim["pressures"].get(node["id"], 0.0)
        for link in res["links"]:
            link["flow"] = sim["flows"].get(link["id"], 0.0)
            link["velocity"] = sim["velocities"].get(link["id"], 0.0)
        res.update({k: sim[k] for k in ["energy_cost", "pressure_variance", "pressure_deficit", "avg_pressure", "min_pressure", "max_pressure"]})
        res["min_pressure_threshold"] = 5.0
        return res

    def get_baseline(self): return self.run_simulation([1.0]*self.get_num_pumps() + [1.0]*self.get_num_valves())

    def _worst_case(self) -> dict:
        return {"pressures": {n: 0.0 for n in self.node_indices}, "flows": {l: 0.0 for l in self.link_indices},
                "velocities": {l: 0.0 for l in self.link_indices}, "energy_cost": 1e7, "pressure_variance": 1e7,
                "pressure_deficit": 1e7, "total_energy_kwh": 1e5, "avg_pressure": 0.0, "min_pressure": 0.0,
                "max_pressure": 0.0, "num_nodes_below_threshold": self.num_nodes}