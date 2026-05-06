"""
CutFlow - Window & Door Fabrication Calculator
Core engine for computing profile cuts, hardware BOQ, and bar optimisation.
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional


# ─── Database / Rules ──────────────────────────────────────────────────────────

# Profile catalogue  (name, weight_kg_per_m, cost_per_m_inr, standard_bar_len_mm)
PROFILES = {
    "FRAME_OUTER":      {"label": "Outer Frame",         "wt": 1.20, "cost": 320, "bar": 6000},
    "SASH_HORIZ":       {"label": "Sash Horizontal",     "wt": 0.95, "cost": 280, "bar": 6000},
    "SASH_VERT":        {"label": "Sash Vertical",       "wt": 0.95, "cost": 280, "bar": 6000},
    "MULLION":          {"label": "Mullion / Transom",   "wt": 1.10, "cost": 300, "bar": 6000},
    "BEAD":             {"label": "Glass Bead",           "wt": 0.40, "cost": 120, "bar": 6000},
    "MESH_FRAME":       {"label": "Mesh Frame",           "wt": 0.55, "cost": 150, "bar": 6000},
}

# Glass options  (label, cost_per_sqm)
GLASS_OPTIONS = {
    "clear_4":    {"label": "Clear 4mm",           "cost": 450},
    "clear_6":    {"label": "Clear 6mm",           "cost": 550},
    "tinted_5":   {"label": "Tinted 5mm",          "cost": 650},
    "frosted_5":  {"label": "Frosted 5mm",         "cost": 700},
    "tempered_6": {"label": "Tempered 6mm",        "cost": 950},
    "dgu_24":     {"label": "DGU 24mm",            "cost": 1800},
}

# Finish options  (label, surcharge_pct)
FINISH_OPTIONS = {
    "mill":       {"label": "Mill Finish",         "surcharge": 0.00},
    "powder":     {"label": "Powder Coated",       "surcharge": 0.18},
    "anodised":   {"label": "Anodised",            "surcharge": 0.25},
    "wood_grain": {"label": "Wood Grain Foil",     "surcharge": 0.30},
}

# Hardware BOQ per typology (qty per window unit)
HARDWARE_DB = {
    "sliding": {
        "Roller Set":          2,
        "Handle (Crescent)":   1,
        "Lock & Keep":         1,
        "Wool Pile (m)":       4,
        "Rubber Gasket (m)":   3,
        "Screws Pack":         1,
    },
    "casement": {
        "Friction Stay (pair)": 2,
        "Handle":               1,
        "Lock & Keep":          1,
        "Rubber Gasket (m)":    4,
        "Hinge (pair)":         2,
        "Screws Pack":          1,
    },
    "fixed": {
        "Rubber Gasket (m)":    4,
        "Setting Block (pair)": 2,
        "Screws Pack":          1,
    },
    "door_sliding": {
        "Heavy Roller Set":     2,
        "Pull Handle (pair)":   1,
        "Lock & Keep":          1,
        "Bottom Guide":         2,
        "Wool Pile (m)":        6,
        "Screws Pack":          2,
    },
    "door_swing": {
        "Door Hinge (pair)":    3,
        "Lever Handle (pair)":  1,
        "Mortise Lock":         1,
        "Floor Closer":         1,
        "Rubber Gasket (m)":    5,
        "Screws Pack":          2,
    },
}

HARDWARE_COST = {
    "Roller Set": 280, "Handle (Crescent)": 150, "Lock & Keep": 120,
    "Wool Pile (m)": 35, "Rubber Gasket (m)": 40, "Screws Pack": 60,
    "Friction Stay (pair)": 350, "Handle": 150, "Hinge (pair)": 280,
    "Heavy Roller Set": 650, "Pull Handle (pair)": 400, "Bottom Guide": 90,
    "Setting Block (pair)": 45, "Floor Closer": 2200, "Lever Handle (pair)": 550,
    "Mortise Lock": 850, "Door Hinge (pair)": 320,
}

TYPOLOGY_LABELS = {
    "sliding":     "Sliding Window",
    "casement":    "Casement Window",
    "fixed":       "Fixed/Picture Window",
    "door_sliding":"Sliding Door",
    "door_swing":  "Swing Door",
}

# ─── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class WindowEntry:
    """Single window/door specification."""
    code: str
    width: float         # mm
    height: float        # mm
    typology: str
    glass_type: str
    finish: str
    mesh: bool
    qty: int = 1


@dataclass
class ProfileCut:
    profile_key: str
    label: str
    length: float        # mm
    count: int = 1       # pieces per window


@dataclass
class BarUsage:
    bar_id: int
    bar_length: float    # mm
    cuts: List[Tuple[float, str]]  # (cut_length, label)
    waste: float = 0.0

    @property
    def used(self):
        return sum(c[0] for c in self.cuts)

    @property
    def utilisation(self):
        return (self.used / self.bar_length * 100) if self.bar_length else 0


@dataclass
class WindowResult:
    entry: WindowEntry
    profile_cuts: List[ProfileCut] = field(default_factory=list)
    glass_width: float = 0
    glass_height: float = 0
    glass_area: float = 0
    hardware: Dict[str, int] = field(default_factory=dict)
    profile_cost: float = 0
    glass_cost: float = 0
    hardware_cost: float = 0
    finish_surcharge: float = 0
    total_cost: float = 0


# ─── Core Calculation ─────────────────────────────────────────────────────────

def compute_window(entry: WindowEntry) -> WindowResult:
    """
    Compute all profile cuts, glass, and hardware for a single window entry.
    Cutting allowances: 5 mm kerf + 10 mm end waste per cut.
    """
    W = entry.width
    H = entry.height
    t = entry.typology
    result = WindowResult(entry=entry)
    cuts = []

    # Frame cuts (outer frame around the opening)
    frame_h_len = W                            # 2 horizontal frame pieces
    frame_v_len = H - 0                        # 2 vertical frame pieces
    cuts.append(ProfileCut("FRAME_OUTER", PROFILES["FRAME_OUTER"]["label"], frame_h_len, 2))
    cuts.append(ProfileCut("FRAME_OUTER", PROFILES["FRAME_OUTER"]["label"], frame_v_len, 2))

    if t in ("sliding", "casement"):
        # Sash: inset 15 mm each side
        sash_w = W - 30
        sash_h = H - 30
        if t == "sliding":
            # Two sashes side by side → each half width minus overlap
            sash_w = (W // 2) - 20
        cuts.append(ProfileCut("SASH_HORIZ", PROFILES["SASH_HORIZ"]["label"], sash_w, 4))
        cuts.append(ProfileCut("SASH_VERT",  PROFILES["SASH_VERT"]["label"],  sash_h, 4))
        # Glass bead around each sash
        bead_h = sash_w - 20
        bead_v = sash_h - 20
        cuts.append(ProfileCut("BEAD", PROFILES["BEAD"]["label"], bead_h, 4))
        cuts.append(ProfileCut("BEAD", PROFILES["BEAD"]["label"], bead_v, 4))
        # Glass: sash inner clear – rebate 25 mm each side
        result.glass_width  = sash_w - 50
        result.glass_height = sash_h - 50

    elif t == "fixed":
        # Bead only, no sash
        bead_h = W - 20
        bead_v = H - 20
        cuts.append(ProfileCut("BEAD", PROFILES["BEAD"]["label"], bead_h, 2))
        cuts.append(ProfileCut("BEAD", PROFILES["BEAD"]["label"], bead_v, 2))
        result.glass_width  = W - 50
        result.glass_height = H - 50

    elif t in ("door_sliding", "door_swing"):
        sash_w = (W // 2) - 20 if t == "door_sliding" else W - 30
        sash_h = H - 40
        cuts.append(ProfileCut("SASH_HORIZ", PROFILES["SASH_HORIZ"]["label"], sash_w, 4))
        cuts.append(ProfileCut("SASH_VERT",  PROFILES["SASH_VERT"]["label"],  sash_h, 4))
        bead_h = sash_w - 20
        bead_v = sash_h - 20
        cuts.append(ProfileCut("BEAD", PROFILES["BEAD"]["label"], bead_h, 4))
        cuts.append(ProfileCut("BEAD", PROFILES["BEAD"]["label"], bead_v, 4))
        result.glass_width  = sash_w - 50
        result.glass_height = sash_h - 50

    # Mullion (for wide openings > 1200mm, add a mullion)
    if W > 1200 and t != "fixed":
        cuts.append(ProfileCut("MULLION", PROFILES["MULLION"]["label"], H - 30, 1))

    # Mesh frame (if mesh requested, additional frame equal to glass area)
    if entry.mesh:
        mesh_w = result.glass_width  if result.glass_width  else W - 50
        mesh_h = result.glass_height if result.glass_height else H - 50
        cuts.append(ProfileCut("MESH_FRAME", PROFILES["MESH_FRAME"]["label"], mesh_w, 2))
        cuts.append(ProfileCut("MESH_FRAME", PROFILES["MESH_FRAME"]["label"], mesh_h, 2))

    result.profile_cuts = cuts

    # Glass area (m²)
    result.glass_area = (result.glass_width * result.glass_height) / 1e6

    # Costs
    profile_cost = 0.0
    for pc in cuts:
        p = PROFILES[pc.profile_key]
        meters = (pc.length / 1000) * pc.count * entry.qty
        profile_cost += meters * p["cost"]

    glass_data = GLASS_OPTIONS.get(entry.glass_type, {"cost": 450})
    glass_cost = result.glass_area * glass_data["cost"] * entry.qty

    hw = dict(HARDWARE_DB.get(t, {}))
    hw_cost = 0.0
    for item, qty_per in hw.items():
        total_qty = qty_per * entry.qty
        hw[item] = total_qty
        hw_cost += total_qty * HARDWARE_COST.get(item, 200)

    result.hardware = hw
    finish_pct = FINISH_OPTIONS.get(entry.finish, {}).get("surcharge", 0)
    finish_sur = (profile_cost + glass_cost) * finish_pct

    result.profile_cost    = round(profile_cost, 2)
    result.glass_cost      = round(glass_cost, 2)
    result.hardware_cost   = round(hw_cost, 2)
    result.finish_surcharge= round(finish_sur, 2)
    result.total_cost      = round(profile_cost + glass_cost + hw_cost + finish_sur, 2)

    return result


# ─── Bar Optimiser (First-Fit Decreasing) ─────────────────────────────────────

def optimise_bars(results: List[WindowResult]) -> Dict[str, List[BarUsage]]:
    """
    Run bar optimisation for each profile type across all windows.
    Uses First-Fit Decreasing (FFD) heuristic.
    Returns dict: profile_key → list of BarUsage.
    """
    KERF = 5          # saw kerf in mm
    END_WASTE = 10    # end trim in mm

    # Aggregate all required cuts per profile
    demand: Dict[str, List[Tuple[float, str]]] = {}
    for res in results:
        for pc in res.profile_cuts:
            key = pc.profile_key
            demand.setdefault(key, [])
            for _ in range(pc.count * res.entry.qty):
                label = f"{res.entry.code} – {pc.label} {pc.length}mm"
                demand[key].append((pc.length, label))

    optimised: Dict[str, List[BarUsage]] = {}

    for profile_key, pieces in demand.items():
        bar_len = PROFILES[profile_key]["bar"]
        usable  = bar_len - END_WASTE   # usable length per bar

        # Sort pieces largest first (FFD)
        pieces_sorted = sorted(pieces, key=lambda x: x[0], reverse=True)

        bars: List[BarUsage] = []

        for piece_len, piece_label in pieces_sorted:
            placed = False
            for bar in bars:
                remaining = usable - bar.used - (KERF * len(bar.cuts) if bar.cuts else 0)
                if piece_len <= remaining:
                    bar.cuts.append((piece_len, piece_label))
                    placed = True
                    break
            if not placed:
                new_bar = BarUsage(
                    bar_id=len(bars) + 1,
                    bar_length=bar_len,
                    cuts=[(piece_len, piece_label)]
                )
                bars.append(new_bar)

        for bar in bars:
            bar.waste = bar.bar_length - bar.used - (KERF * len(bar.cuts))

        optimised[profile_key] = bars

    return optimised


# ─── Summary Aggregation ──────────────────────────────────────────────────────

def aggregate_hardware(results: List[WindowResult]) -> Dict[str, int]:
    """Merge hardware quantities from all window results."""
    totals: Dict[str, int] = {}
    for res in results:
        for item, qty in res.hardware.items():
            totals[item] = totals.get(item, 0) + qty
    return totals
