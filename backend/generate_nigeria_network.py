# run_once: generate_nigeria_network.py
# Place this file in your backend/ folder and run it once

from epyt import epanet
import os

def create_nigeria_demo_network():
    """
    Creates a small hypothetical Nigerian town water distribution network.
    Deliberately configured with inefficient pump settings and unequal
    pressure zones to demonstrate optimization potential.
    
    Network represents a simplified district-metered area with:
    - 1 reservoir (elevated storage tank)
    - 2 pumping stations (running inefficiently at full speed)
    - 12 demand nodes (3 zones: high-elevation, mid, low)
    - Unequal pipe diameters causing pressure imbalance
    """
    
    inp_content = """[TITLE]
Nigeria Demo WDN - Hypothetical District Metered Area
Covenant University FYP - Nwuba Ikechukwu Joshua

[JUNCTIONS]
;ID    Elev   Demand   Pattern
 J1    20     50       1
 J2    25     80       1
 J3    30     60       1
 J4    15     90       1
 J5    10     70       1
 J6    35     40       1
 J7    40     30       1
 J8    20     85       1
 J9    25     65       1
 J10   30     55       1
 J11   15     75       1
 J12   10     95       1

[RESERVOIRS]
;ID    Head   Pattern
 R1    80     

[TANKS]
;ID    Elev   InitLvl  MinLvl  MaxLvl  Diam   MinVol
 T1    45     3.0      1.0     6.0     10     0

[PIPES]
;ID    Node1  Node2   Length  Diam   Rough  Minor  Status
 P1    R1     J1      500     200    100    0      Open
 P2    J1     J2      400     150    100    0      Open
 P3    J2     J3      350     100    100    0      Open
 P4    J3     J6      300     80     100    0      Open
 P5    J6     J7      250     80     100    0      Open
 P6    J1     J4      450     150    100    0      Open
 P7    J4     J5      400     150    100    0      Open
 P8    J5     J8      350     100    100    0      Open
 P9    J8     J9      300     100    100    0      Open
 P10   J9     J10     250     80     100    0      Open
 P11   J4     J11     400     100    100    0      Open
 P12   J11    J12     350     80     100    0      Open
 P13   J2     J8      500     100    100    0      Open
 P14   J3     J9      450     80     100    0      Open
 P15   J6     J10     400     80     100    0      Open
 P16   T1     J7      300     80     100    0      Open

[PUMPS]
;ID    Node1  Node2   Parameters
 PMP1  R1     J1      HEAD 1
 PMP2  J4     T1      HEAD 2

[VALVES]
;ID    Node1  Node2   Diam   Type   Setting  Minor
 V1    J2     J3      100    PRV    35       0
 V2    J8     J9      100    PRV    30       0

[TAGS]

[DEMANDS]

[STATUS]

[PATTERNS]
;ID    Multipliers
 1     0.5  0.6  0.7  0.8  1.0  1.2
 1     1.3  1.2  1.1  1.0  0.9  0.8
 1     0.7  0.6  0.5  0.6  0.8  1.0
 1     1.1  1.2  1.0  0.9  0.7  0.5

[CURVES]
;ID    X-Value   Y-Value
 1     0         80
 1     500       65
 1     1000      45
 1     1500      20
 2     0         60
 2     300       50
 2     600       35
 2     900       15

[CONTROLS]

[RULES]

[ENERGY]
 Global Efficiency  75
 Global Price       0.068
 Demand Charge      0

[EMITTERS]

[QUALITY]

[SOURCES]

[REACTIONS]

[MIXING]

[TIMES]
 Duration           24:00
 Hydraulic Timestep 1:00
 Quality Timestep   0:05
 Pattern Timestep   2:00
 Pattern Start      0:00
 Report Timestep    1:00
 Report Start       0:00
 Start ClockTime    12 am
 Statistic          None

[REPORT]
 Status    No
 Summary   No
 Page      0

[OPTIONS]
 Units           LPS
 Headloss        H-W
 Specific Gravity 1.0
 Viscosity       1.0
 Trials          40
 Accuracy        0.001
 CHECKFREQ       2
 MAXCHECK        10
 DAMPLIMIT       0
 Unbalanced      Continue 10
 Pattern         1
 Demand Multiplier 1.0
 Emitter Exponent 0.5
 Quality         None mg/L
 Diffusivity     1.0
 Tolerance       0.01

[COORDINATES]
;Node   X-Coord   Y-Coord
 R1     100       300
 J1     200       300
 J2     300       350
 J3     400       400
 J4     200       200
 J5     200       100
 J6     500       400
 J7     600       400
 J8     300       150
 J9     400       150
 J10    500       150
 J11    300       50
 J12    400       50
 T1     600       300

[VERTICES]

[LABELS]

[BACKDROP]

[END]
"""
    
    os.makedirs("networks", exist_ok=True)
    path = "networks/nigeria_demo.inp"
    
    with open(path, "w") as f:
        f.write(inp_content)
    
    print(f"Nigeria demo network created: {path}")
    
    # Verify it loads
    try:
        en = epanet(path, verbose=False)
        print(f"  Nodes:  {en.getNodeCount()}")
        print(f"  Links:  {en.getLinkCount()}")
        print(f"  Pumps:  {len(en.getLinkPumpIndex())}")
        print(f"  Valves: {len(en.getLinkValveIndex())}")
        en.unload()
        print("Network verified OK")
    except Exception as e:
        print(f"Verification error: {e}")

if __name__ == "__main__":
    create_nigeria_demo_network()