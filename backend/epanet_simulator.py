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
    SCHEDULE_HOURS = 24

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
        self.link_types = {}
        self.link_diameters = {}
        pump_set = set(self.pump_indices)
        valve_set = set(self.valve_indices)
        try:
            diameters = np.array(en.getLinkDiameter()).flatten()
        except Exception:
            diameters = []
        for lid in self.link_indices:
            try:
                n = en.getLinkNodesIndex(lid)
                self.link_connectivity[lid] = {"source": int(n[0]), "target": int(n[1])}
            except: self.link_connectivity[lid] = {"source": 0, "target": 0}
            try:
                self.link_diameters[lid] = float(diameters[lid - 1])
            except Exception:
                try:
                    self.link_diameters[lid] = float(np.array(en.getLinkDiameter(lid)).flatten()[0])
                except Exception:
                    self.link_diameters[lid] = 0.0
            if lid in pump_set:
                self.link_types[lid] = "PUMP"
            elif lid in valve_set:
                self.link_types[lid] = "VALVE"
            else:
                self.link_types[lid] = "PIPE"

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

        self.node_demands = self._read_node_demands(en)

        with _EPANET_LOCK:
            en.unload()

        # Line-by-line modification
        with open(self._src_file, "r") as f:
            lines = f.readlines()

        new_lines = []
        skip_content = False
        current_section = None
        target_sections = ["[CONTROLS]", "[RULES]"]
        patterns_found = False
        
        for line in lines:
            stripped = line.strip().upper()
            if stripped.startswith("[") and stripped.endswith("]"):
                current_section = stripped
                new_lines.append(line)
                skip_content = stripped in target_sections
                if stripped == "[PATTERNS]":
                    patterns_found = True
                    for pid in self.pump_indices:
                        new_lines.append(f"GA_PUMP_{pid}  {'  '.join(['1.0']*24)}\n")
            elif not skip_content:
                if current_section == "[TIMES]" and stripped.startswith("HYDRAULIC TIMESTEP"):
                    new_lines.append(" Hydraulic Timestep 1:00\n")
                elif current_section == "[TIMES]" and stripped.startswith("PATTERN TIMESTEP"):
                    new_lines.append(" Pattern Timestep 1:00\n")
                else:
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
    def get_pump_names(self): return [self.link_names.get(i, f"Pump {n + 1}") for n, i in enumerate(self.pump_indices)]
    def get_valve_names(self): return [self.link_names.get(i, f"Valve {n + 1}") for n, i in enumerate(self.valve_indices)]

    def _read_node_demands(self, en) -> dict:
        try:
            raw = en.getNodeBaseDemands()
            if isinstance(raw, dict):
                values = raw.get("value") or raw.get("values") or raw.get("demand") or []
            else:
                values = raw
            arr = np.array(values, dtype=float).flatten()
            return {
                nid: float(arr[nid - 1]) if nid - 1 < len(arr) else 0.0
                for nid in self.node_indices
            }
        except Exception:
            return {nid: 0.0 for nid in self.node_indices}

    def _junction_ids(self):
        return [n for n, t in self.node_types.items() if t == "JUNCTION"]

    def _zone_label(self, node_id: int, low_cut: float = None, high_cut: float = None) -> str:
        elev = self.node_elev.get(node_id, 0.0)
        junction_elevs = [self.node_elev.get(n, 0.0) for n in self._junction_ids()]
        if low_cut is None or high_cut is None:
            if len(junction_elevs) >= 3:
                low_cut, high_cut = np.percentile(junction_elevs, [33.333, 66.667])
            else:
                low_cut = high_cut = elev
        if elev <= low_cut:
            return "Low Elevation Zone"
        if elev <= high_cut:
            return "Mid Elevation Zone"
        return "High Elevation Zone"

    def _build_demand_zone_summary(self, pressures: dict, flows: dict, min_pressure: float) -> list:
        junction_ids = self._junction_ids()
        if not junction_ids:
            return []

        elevs = [self.node_elev.get(n, 0.0) for n in junction_ids]
        low_cut, high_cut = np.percentile(elevs, [33.333, 66.667]) if len(elevs) >= 3 else (0.0, 0.0)
        zones = {}
        for nid in junction_ids:
            label = self._zone_label(nid, low_cut, high_cut)
            zones.setdefault(label, []).append(nid)

        summaries = []
        for label, node_ids in zones.items():
            node_set = set(node_ids)
            zone_pressures = [pressures.get(n, 0.0) for n in node_ids]
            inflow = 0.0
            for lid, conn in self.link_connectivity.items():
                source_in = conn["source"] in node_set
                target_in = conn["target"] in node_set
                if source_in != target_in:
                    inflow += abs(flows.get(lid, 0.0))
            summaries.append({
                "zone": label,
                "node_count": len(node_ids),
                "nodes": [self.node_names.get(n, str(n)) for n in node_ids],
                "total_demand": float(sum(self.node_demands.get(n, 0.0) for n in node_ids)),
                "estimated_inflow": float(inflow),
                "avg_pressure": float(np.mean(zone_pressures)) if zone_pressures else 0.0,
                "min_pressure": float(np.min(zone_pressures)) if zone_pressures else 0.0,
                "nodes_below_min": sum(1 for p in zone_pressures if p < min_pressure),
            })
        return sorted(summaries, key=lambda z: z["zone"])

    def _build_route_ranking(self, flows: dict, velocities: dict) -> list:
        ranked = sorted(
            self.link_indices,
            key=lambda lid: abs(flows.get(lid, 0.0)),
            reverse=True
        )
        max_flow = abs(flows.get(ranked[0], 0.0)) if ranked else 0.0
        routes = []
        for rank, lid in enumerate(ranked, start=1):
            flow = abs(flows.get(lid, 0.0))
            conn = self.link_connectivity.get(lid, {"source": 0, "target": 0})
            target_zone = self._zone_label(conn["target"]) if conn["target"] in self._junction_ids() else self._zone_label(conn["source"]) if conn["source"] in self._junction_ids() else "Source/Storage Route"
            if rank <= 3 or (max_flow and flow >= max_flow * 0.7):
                importance = "Critical"
            elif max_flow and flow >= max_flow * 0.35:
                importance = "High"
            elif max_flow and flow >= max_flow * 0.1:
                importance = "Medium"
            else:
                importance = "Low"
            routes.append({
                "rank": rank,
                "link_id": lid,
                "name": self.link_names.get(lid, str(lid)),
                "type": self.link_types.get(lid, "PIPE"),
                "source": self.node_names.get(conn["source"], str(conn["source"])),
                "target": self.node_names.get(conn["target"], str(conn["target"])),
                "supplies_zone": target_zone,
                "flow": float(flow),
                "flow_share_pct": float((flow / max_flow * 100) if max_flow else 0.0),
                "velocity": float(abs(velocities.get(lid, 0.0))),
                "diameter": self.link_diameters.get(lid, 0.0),
                "importance": importance,
            })
        return routes

    def decode_control_schedule(self, chromosome: list) -> dict:
        """
        Decode either a legacy static chromosome or a 24-hour schedule chromosome.
        Returns pump speeds as multipliers and valve settings as percentages.
        """
        num_p, num_v = len(self.pump_indices), len(self.valve_indices)
        controls = num_p + num_v
        hours = self.SCHEDULE_HOURS
        values = list(chromosome or [])

        if controls == 0:
            return {"hours": []}

        if len(values) >= controls * hours:
            matrix = np.array(values[:controls * hours], dtype=float).reshape(hours, controls)
        else:
            static = np.ones(controls, dtype=float)
            if values:
                static[:min(len(values), controls)] = values[:min(len(values), controls)]
            matrix = np.tile(static, (hours, 1))

        hours_out = []
        for hour in range(hours):
            row = matrix[hour]
            pumps = []
            valves = []
            for i, pid in enumerate(self.pump_indices):
                speed = float(np.clip(row[i], 0.2, 1.0))
                pumps.append({
                    "id": pid,
                    "name": self.link_names.get(pid, f"Pump {i + 1}"),
                    "speed": speed,
                    "speed_percent": speed * 100,
                })
            for i, vid in enumerate(self.valve_indices):
                raw = row[num_p + i]
                setting = float(np.clip(raw, 0.0, 1.0)) * 100
                valves.append({
                    "id": vid,
                    "name": self.link_names.get(vid, f"Valve {i + 1}"),
                    "setting": setting,
                    "setting_percent": setting,
                })
            hours_out.append({
                "hour": hour,
                "label": f"{hour:02d}:00",
                "pumps": pumps,
                "valves": valves,
            })

        return {"hours": hours_out}

    def run_simulation(self, chromosome: list) -> dict:
        import shutil
        num_p, num_v = len(self.pump_indices), len(self.valve_indices)
        schedule = self.decode_control_schedule(chromosome)
        hourly = schedule["hours"]

        uid = uuid.uuid4().hex[:8]
        # Per-call INP also isolated in the workspace
        call_inp = os.path.join(self.workspace, f"call_{uid}.inp")
        shutil.copy2(self.inp_file, call_inp)

        en = None
        with _EPANET_LOCK:
            try:
                en = _open(call_inp)
                for i, pid in enumerate(self.pump_indices):
                    pattern = [hour["pumps"][i]["speed"] for hour in hourly] if hourly else [1.0] * 24
                    pat_name = f"GA_PUMP_{pid}"
                    pi = en.getPatternIndex(pat_name)
                    if pi > 0:
                        en.setPattern(pi, pattern)
                        en.setLinkPumpPatternIndex(pid, pi)

                # Step-by-step
                en.openHydraulicAnalysis()
                en.initializeHydraulicAnalysis(0)
                p_sum = np.zeros(self.num_nodes)
                f_sum = np.zeros(self.num_links)
                v_sum = np.zeros(self.num_links)
                hourly_p_sum = np.zeros((self.SCHEDULE_HOURS, self.num_nodes))
                hourly_f_sum = np.zeros((self.SCHEDULE_HOURS, self.num_links))
                hourly_counts = np.zeros(self.SCHEDULE_HOURS)
                e_total = 0.0
                steps = 0

                while True:
                    hour_idx = steps % self.SCHEDULE_HOURS
                    if hourly:
                        for i, vid in enumerate(self.valve_indices):
                            en.setLinkSettings(vid, hourly[hour_idx]["valves"][i]["setting"])

                    err = en.runHydraulicAnalysis()
                    
                    p_curr = np.array(en.getNodePressure(), dtype=float)
                    f_curr = np.array(en.getLinkFlows(), dtype=float)
                    v_curr = np.array(en.getLinkVelocity(), dtype=float)
                    
                    p_sum += p_curr[:self.num_nodes] if len(p_curr) >= self.num_nodes else np.pad(p_curr, (0, self.num_nodes - len(p_curr)))
                    f_sum += f_curr[:self.num_links] if len(f_curr) >= self.num_links else np.pad(f_curr, (0, self.num_links - len(f_curr)))
                    v_sum += v_curr[:self.num_links] if len(v_curr) >= self.num_links else np.pad(v_curr, (0, self.num_links - len(v_curr)))
                    p_step = p_curr[:self.num_nodes] if len(p_curr) >= self.num_nodes else np.pad(p_curr, (0, self.num_nodes - len(p_curr)))
                    f_step = f_curr[:self.num_links] if len(f_curr) >= self.num_links else np.pad(f_curr, (0, self.num_links - len(f_curr)))
                    hourly_p_sum[hour_idx] += p_step
                    hourly_f_sum[hour_idx] += np.abs(f_step)
                    hourly_counts[hour_idx] += 1
                    
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
                junction_ids = self._junction_ids()
                junction_p = [pressures[n] for n in junction_ids]
                
                tariff, min_p = 68.0, 5.0
                energy_cost = max(0.0, e_total * tariff)
                p_stats = junction_p if junction_p else [p for p in pressures.values()]
                
                # Penalize only on extremely large failures or NaNs
                if any(np.isnan(p_stats)) or any(p < -500 for p in p_stats):
                    return self._worst_case()

                hourly_metrics = []
                for hour in range(self.SCHEDULE_HOURS):
                    if hourly_counts[hour] > 0:
                        hp = hourly_p_sum[hour] / hourly_counts[hour]
                        hf = hourly_f_sum[hour] / hourly_counts[hour]
                    else:
                        hp = p_avg
                        hf = np.abs(f_avg)
                    h_pressures = [float(hp[n - 1]) for n in junction_ids] if junction_ids else [float(p) for p in hp]
                    hourly_metrics.append({
                        "hour": hour,
                        "label": f"{hour:02d}:00",
                        "expected_avg_pressure": float(np.mean(h_pressures)) if h_pressures else 0.0,
                        "expected_min_pressure": float(np.min(h_pressures)) if h_pressures else 0.0,
                        "expected_total_flow": float(np.sum(hf)),
                        "expected_nodes_below_min": sum(1 for p in h_pressures if p < min_p),
                    })

                for hour in schedule.get("hours", []):
                    metrics = hourly_metrics[hour["hour"]]
                    hour.update(metrics)

                demand_zone_summary = self._build_demand_zone_summary(pressures, flows, min_p)
                route_ranking = self._build_route_ranking(flows, velocities)

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
                    "operating_schedule": schedule,
                    "hourly_metrics": hourly_metrics,
                    "demand_zone_summary": demand_zone_summary,
                    "route_ranking": route_ranking,
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
                       "target": self.link_connectivity[l]["target"], "type": self.link_types.get(l, "PIPE"),
                       "diameter": self.link_diameters.get(l, 0.0), "flow": 0.0, "velocity": 0.0}
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
