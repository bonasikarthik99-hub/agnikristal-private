"""
Process alternatives for dapagliflozin synthesis.

Reference data for replacing hazardous / cryogenic reagents in the two
steps that usually drive route risk:

  1. Aryl-metal formation for C-glycosylation (baseline: n-BuLi, -78 C)
  2. Ionic reduction of the methyl glycoside / diaryl ketone
     (baseline: Et3SiH / BF3.OEt2 in MeCN/DCM)

Entries are literature-level summaries, not validated procedures. Verify
against the original papers / patents and run a process-safety review
before use.
"""

STEP_METALATION = "Aryl-metal formation (C-glycosylation)"
STEP_REDUCTION = "Reduction (glycoside / diaryl ketone)"
STEP_PURIFICATION = "Purification / final form"
STEP_SOLVENT = "Solvent swap"

MATURITY_ORDER = {"Industrial": 0, "Patent/literature": 1, "Academic": 2}

ALTERNATIVES = [
    # ---------------- Aryl-metal formation ----------------
    {
        "step": STEP_METALATION,
        "reagent": "n-BuLi (baseline)",
        "conditions": "-78 C, THF/toluene",
        "pros": "Fast, well-precedented exchange",
        "cons": "Pyrophoric, deep cryogenic, poor scalability",
        "maturity": "Industrial",
    },
    {
        "step": STEP_METALATION,
        "reagent": "iPrMgCl.LiCl (turbo Grignard)",
        "conditions": "About -20 to 0 C (some reports near rt), THF",
        "pros": "Avoids deep cryogenics, safer, common industrial swap",
        "cons": "Slower exchange; strict moisture control",
        "maturity": "Industrial",
    },
    {
        "step": STEP_METALATION,
        "reagent": "Bu3MgLi (lithium trialkylmagnesiate)",
        "conditions": "About -10 to 0 C, THF/toluene",
        "pros": "Milder than n-BuLi, sub-stoichiometric in organometallic",
        "cons": "Fewer scalable precedents",
        "maturity": "Patent/literature",
    },
    {
        "step": STEP_METALATION,
        "reagent": "Continuous-flow lithiation (n-BuLi in microreactor)",
        "conditions": "About -20 to 0 C, seconds residence time",
        "pros": "Keeps n-BuLi chemistry without deep cryogenics; better heat control",
        "cons": "Needs flow equipment; clogging risk",
        "maturity": "Patent/literature",
    },
    {
        "step": STEP_METALATION,
        "reagent": "Direct Mg insertion (Mg / LiCl, Barbier-type)",
        "conditions": "Ambient to mild heating",
        "pros": "No pyrophoric alkyllithium",
        "cons": "Initiation and exotherm control",
        "maturity": "Patent/literature",
    },
    {
        "step": STEP_METALATION,
        "reagent": "Aryl-zinc / aryl-boron cross-coupling",
        "conditions": "Pd or Ni catalysis",
        "pros": "Avoids strongly basic organometallics",
        "cons": "Needs a glycosyl partner; few precedents for this API",
        "maturity": "Academic",
    },
    {
        "step": STEP_METALATION,
        "reagent": "Ni/Pd reductive or photoredox glycosyl C-arylation",
        "conditions": "Mild, about room temperature",
        "pros": "No organometallic reagent at all",
        "cons": "Alpha/beta control and scale-up not established",
        "maturity": "Academic",
    },
    # ---------------- Reduction ----------------
    {
        "step": STEP_REDUCTION,
        "reagent": "Et3SiH / BF3.OEt2 (baseline)",
        "conditions": "MeCN/DCM, about -20 to 10 C",
        "pros": "High beta-selectivity, well precedented",
        "cons": "Costly silane, corrosive BF3, DCM use",
        "maturity": "Industrial",
    },
    {
        "step": STEP_REDUCTION,
        "reagent": "Et3SiH / AlCl3",
        "conditions": "MeCN/DCM",
        "pros": "Cheaper Lewis acid than BF3",
        "cons": "Moisture sensitive, aluminum waste",
        "maturity": "Industrial",
    },
    {
        "step": STEP_REDUCTION,
        "reagent": "Et3SiH / TMSOTf",
        "conditions": "MeCN or DCM",
        "pros": "Good beta-selectivity",
        "cons": "Costly, moisture sensitive",
        "maturity": "Patent/literature",
    },
    {
        "step": STEP_REDUCTION,
        "reagent": "TMDS (tetramethyldisiloxane) + Lewis acid",
        "conditions": "As for Et3SiH",
        "pros": "Cheaper, more atom-economical silane",
        "cons": "Selectivity must be re-optimized",
        "maturity": "Patent/literature",
    },
    {
        "step": STEP_REDUCTION,
        "reagent": "PMHS (polymethylhydrosiloxane) + Lewis acid",
        "conditions": "As for Et3SiH",
        "pros": "Cheapest silane",
        "cons": "Polymeric siloxane waste, messier workup",
        "maturity": "Patent/literature",
    },
    {
        "step": STEP_REDUCTION,
        "reagent": "B(C6F5)3-catalyzed hydrosilylation",
        "conditions": "Mild, catalytic Lewis acid",
        "pros": "Catalytic, milder",
        "cons": "Expensive catalyst, limited precedent",
        "maturity": "Academic",
    },
    {
        "step": STEP_REDUCTION,
        "reagent": "NaBH4 / BF3 or NaBH4 / AlCl3 (diaryl ketone step only)",
        "conditions": "THF or glyme",
        "pros": "Silane-free",
        "cons": "Poor selectivity for the glycoside step",
        "maturity": "Patent/literature",
    },
    {
        "step": STEP_REDUCTION,
        "reagent": "AVOID: H2, Pd/C hydrogenolysis",
        "conditions": "-",
        "pros": "-",
        "cons": "Risks dechlorination of the aryl chloride",
        "maturity": "Academic",
    },
    # ---------------- Purification / final form ----------------
    {
        "step": STEP_PURIFICATION,
        "reagent": "Acetylation / recrystallization / deacetylation (baseline)",
        "conditions": "Ac2O or AcCl, pyridine; then base",
        "pros": "Well known; removes impurities via a crystalline tetraacetate",
        "cons": "Two extra steps, extra reagents and waste, yield loss",
        "maturity": "Industrial",
    },
    {
        "step": STEP_PURIFICATION,
        "reagent": "L-proline co-crystal purification",
        "conditions": "Crystallize co-crystal from alcohol/water or ester, then release",
        "pros": "Replaces derivatization with a crystallization; proline is cheap and benign",
        "cons": "Needs a conversion step to the final form; co-crystal landscape is patented",
        "maturity": "Patent/literature",
    },
    {
        "step": STEP_PURIFICATION,
        "reagent": "DL-proline co-crystal purification",
        "conditions": "Crystallize from solvent mixture, optional seeding; then to propanediol monohydrate",
        "pros": "Cheaper racemic coformer; described as purification route in a patent",
        "cons": "Freedom-to-operate check needed (third-party patent)",
        "maturity": "Patent/literature",
    },
    {
        "step": STEP_PURIFICATION,
        "reagent": "Direct propanediol monohydrate crystallization (seeded)",
        "conditions": "Dapagliflozin + (S)-1,2-propanediol + water in EtOAc/MTBE",
        "pros": "Fewest steps; gives the marketed form directly",
        "cons": "Needs input of sufficiently pure crude; limited impurity rejection",
        "maturity": "Industrial",
    },
    # ---------------- Solvents ----------------
    {
        "step": STEP_SOLVENT,
        "reagent": "DCM -> toluene, 2-MeTHF, CPME or EtOAc",
        "conditions": "Check Lewis acid compatibility",
        "pros": "Removes chlorinated solvent",
        "cons": "May change beta-selectivity and rate",
        "maturity": "Patent/literature",
    },
    {
        "step": STEP_SOLVENT,
        "reagent": "Keep MeCN in the glycoside reduction",
        "conditions": "-",
        "pros": "Main driver of beta-selectivity",
        "cons": "-",
        "maturity": "Industrial",
    },
]

# Relative cost vs the baseline reagent, and risk of failing to deliver the
# exact product (beta-C-glycoside, (1S) configuration, aryl chloride intact).
_PROFILE = {
    "n-BuLi (baseline)": ("Baseline", "Low"),
    "iPrMgCl.LiCl (turbo Grignard)": ("Lower", "Low"),
    "Bu3MgLi (lithium trialkylmagnesiate)": ("Lower", "Medium"),
    "Continuous-flow lithiation (n-BuLi in microreactor)": ("Similar", "Low"),
    "Direct Mg insertion (Mg / LiCl, Barbier-type)": ("Lower", "Medium"),
    "Aryl-zinc / aryl-boron cross-coupling": ("Higher", "High"),
    "Ni/Pd reductive or photoredox glycosyl C-arylation": ("Higher", "High"),
    "Et3SiH / BF3.OEt2 (baseline)": ("Baseline", "Low"),
    "Et3SiH / AlCl3": ("Lower", "Low"),
    "Et3SiH / TMSOTf": ("Higher", "Low"),
    "TMDS (tetramethyldisiloxane) + Lewis acid": ("Lower", "Medium"),
    "PMHS (polymethylhydrosiloxane) + Lewis acid": ("Lower", "Medium"),
    "B(C6F5)3-catalyzed hydrosilylation": ("Higher", "High"),
    "NaBH4 / BF3 or NaBH4 / AlCl3 (diaryl ketone step only)": ("Lower", "Medium"),
    "AVOID: H2, Pd/C hydrogenolysis": ("n/a", "High"),
    "Acetylation / recrystallization / deacetylation (baseline)": ("Baseline", "Low"),
    "L-proline co-crystal purification": ("Lower", "Medium"),
    "DL-proline co-crystal purification": ("Lower", "Medium"),
    "Direct propanediol monohydrate crystallization (seeded)": ("Lower", "Medium"),
    "DCM -> toluene, 2-MeTHF, CPME or EtOAc": ("Similar", "Medium"),
    "Keep MeCN in the glycoside reduction": ("Baseline", "Low"),
}

_MATURITY_WEIGHT = {"Industrial": 0.9, "Patent/literature": 0.7, "Academic": 0.4}
_RISK_WEIGHT = {"Low": 1.0, "Medium": 0.85, "High": 0.6}

for _row in ALTERNATIVES:
    _cost, _risk = _PROFILE[_row["reagent"]]
    _row["cost"] = _cost
    _row["product_risk"] = _risk
    # Heuristic prior only: maturity x product risk. Not a measured yield
    # or probability; replace with your own lab data when available.
    _row["likelihood"] = round(
        _MATURITY_WEIGHT[_row["maturity"]] * _RISK_WEIGHT[_risk], 2
    )

DISCLAIMER = (
    "Literature-level summary, not a validated procedure. Verify against "
    "papers/patents and run a process-safety review before use."
)


def list_steps():
    """Return the distinct step names in display order."""
    seen = []
    for row in ALTERNATIVES:
        if row["step"] not in seen:
            seen.append(row["step"])
    return seen


def get_alternatives(step=None, max_maturity=None):
    """
    Return alternative rows, optionally filtered.

    step         -- one of list_steps(), or None for all
    max_maturity -- "Industrial", "Patent/literature" or "Academic";
                    keeps rows at least that mature
    """
    rows = ALTERNATIVES
    if step:
        rows = [r for r in rows if r["step"] == step]
    if max_maturity:
        limit = MATURITY_ORDER[max_maturity]
        rows = [r for r in rows if MATURITY_ORDER[r["maturity"]] <= limit]
    return [dict(r) for r in rows]


def rank_alternatives(step=None, cheaper_only=True):
    """
    Rank options for obtaining the exact dapagliflozin product at lower cost.

    cheaper_only -- keep only rows whose cost is "Lower" than the baseline
    Rows are sorted by the heuristic likelihood score, highest first.
    The score is a prior built from maturity and product risk, not an
    experimentally measured probability.
    """
    rows = get_alternatives(step=step)
    if cheaper_only:
        rows = [r for r in rows if r["cost"] == "Lower"]
    return sorted(rows, key=lambda r: r["likelihood"], reverse=True)
