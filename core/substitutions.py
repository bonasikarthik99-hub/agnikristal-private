"""
Drug-agnostic reagent / solvent / process-step substitution engine.

Works for any API route: give it the reagents, solvents and temperatures of
a step (typed in, or read from the experimental-data table) and it returns
hazard flags and cheaper / safer / greener alternatives.

The knowledge base follows well-known green-chemistry and process-safety
practice (CHEM21 and GSK solvent guides, ACS GCI Pharmaceutical Roundtable
reagent guides, ICH Q3C / Q3D). Entries are literature-level guidance, not
validated procedures: a substitution changes selectivity, impurity profile
and sometimes the regulatory filing, so every swap needs experimental
confirmation for the specific drug.

Fields per entry
----------------
category   solvent | reagent | process
triggers   lowercase names matched as whole tokens in the step text
hazards    flags compatible with core.experimental_data.HAZARD_PENALTY
problem    why the item is worth replacing
options    list of alternatives (name, note, cost vs the original, maturity)
caution    what to re-check after swapping
"""

import re

import pandas as pd

MATURITY = ("Industrial", "Patent/literature", "Academic")


def _opt(name, note, cost="Similar", maturity="Industrial"):
    return {"name": name, "note": note, "cost": cost, "maturity": maturity}


KNOWLEDGE_BASE = [
    # ------------------------------------------------------------------ solvents
    {
        "id": "dcm", "category": "solvent",
        "triggers": ["dcm", "dichloromethane", "methylene chloride", "ch2cl2"],
        "hazards": ["chlorinated_solvent", "toxic"],
        "problem": "Chlorinated, regulated (ICH Q3C class 2), poor environmental profile",
        "options": [
            _opt("2-MeTHF", "Good for extractions, Grignards, many reactions", "Similar"),
            _opt("Ethyl acetate", "Extractions, crystallizations, workups", "Lower"),
            _opt("Toluene", "Non-polar reactions, azeotropic drying", "Lower"),
            _opt("CPME", "Stable to peroxides, hydrophobic", "Higher", "Industrial"),
        ],
        "caution": "Lewis-acid or cation chemistry may change selectivity; polarity differs",
    },
    {
        "id": "chlorinated_other", "category": "solvent",
        "triggers": ["chloroform", "chcl3", "dce", "1,2-dichloroethane", "carbon tetrachloride", "ccl4"],
        "hazards": ["chlorinated_solvent", "toxic"],
        "problem": "Toxic or carcinogenic chlorinated solvent",
        "options": [
            _opt("2-MeTHF", "General replacement for ethers and DCM-type uses"),
            _opt("Ethyl acetate", "Workups and crystallizations", "Lower"),
            _opt("Toluene", "Higher-temperature reactions replacing DCE", "Lower"),
        ],
        "caution": "Check boiling point and reaction rate",
    },
    {
        "id": "dmf_family", "category": "solvent",
        "triggers": ["dmf", "dimethylformamide", "n,n-dimethylformamide", "nmp",
                     "n-methylpyrrolidone", "dmac", "dimethylacetamide"],
        "hazards": ["toxic"],
        "problem": "Reproductive toxicity (REACH SVHC), hard to remove",
        "options": [
            _opt("DMSO", "Similar polarity; thermal stability limits apply", "Similar"),
            _opt("N-butylpyrrolidinone (NBP)", "Non-reprotoxic dipolar aprotic", "Higher", "Patent/literature"),
            _opt("Cyrene", "Bio-based dipolar aprotic; reacts with some bases/amines", "Higher", "Patent/literature"),
            _opt("Acetonitrile or 2-MeTHF/water", "For couplings and SNAr where applicable", "Similar"),
        ],
        "caution": "Rates and solubility change; Cyrene is not compatible with strong bases",
    },
    {
        "id": "ether_solvents", "category": "solvent",
        "triggers": ["diethyl ether", "et2o", "1,4-dioxane", "dioxane", "dme",
                     "dimethoxyethane", "diglyme"],
        "hazards": ["toxic"],
        "problem": "Peroxide formation, flammability, dioxane/DME toxicity",
        "options": [
            _opt("2-MeTHF", "Replaces THF, ether, dioxane in most organometallic uses"),
            _opt("CPME", "Low peroxide formation, easy recovery", "Higher"),
            _opt("MTBE", "Extractions and workups", "Lower"),
        ],
        "caution": "Organometallic solubility and aggregation can differ",
    },
    {
        "id": "thf", "category": "solvent",
        "triggers": ["thf", "tetrahydrofuran"],
        "hazards": [],
        "problem": "Peroxides, fully water-miscible (hard to recycle)",
        "options": [
            _opt("2-MeTHF", "Bio-derived, separates from water, recyclable", "Similar"),
            _opt("CPME", "More stable, lower water miscibility", "Higher"),
        ],
        "caution": "Lithium and Grignard chemistry usually transfers; confirm",
    },
    {
        "id": "benzene_hexane", "category": "solvent",
        "triggers": ["benzene", "hexane", "n-hexane"],
        "hazards": ["toxic"],
        "problem": "Carcinogen (benzene) / neurotoxic (n-hexane)",
        "options": [
            _opt("Toluene", "Replaces benzene", "Similar"),
            _opt("Heptane", "Replaces hexane", "Similar"),
        ],
        "caution": "Boiling points differ slightly",
    },
    {
        "id": "hmpa", "category": "solvent",
        "triggers": ["hmpa"],
        "hazards": ["toxic"],
        "problem": "Carcinogenic additive",
        "options": [_opt("DMPU", "Common substitute as a co-solvent", "Higher", "Industrial")],
        "caution": "Confirm reactivity enhancement is retained",
    },
    {
        "id": "pyridine", "category": "solvent",
        "triggers": ["pyridine"],
        "hazards": ["toxic"],
        "problem": "Toxic, odorous, hard to remove",
        "options": [
            _opt("Triethylamine or DIPEA in EtOAc or 2-MeTHF", "Acid-scavenger uses", "Lower"),
            _opt("N-methylmorpholine", "Milder base", "Similar"),
        ],
        "caution": "Acylation catalysis by pyridine may need DMAP",
    },
    # ------------------------------------------------------------------ reagents
    {
        "id": "organolithium", "category": "reagent",
        "triggers": ["n-buli", "buli", "butyllithium", "n-butyllithium", "s-buli",
                     "t-buli", "tert-butyllithium", "phenyllithium"],
        "hazards": ["pyrophoric", "cryogenic"],
        "problem": "Pyrophoric, usually needs -78 C, difficult to scale",
        "options": [
            _opt("iPrMgCl.LiCl (turbo Grignard)", "Halogen-metal exchange at -20 to 0 C", "Lower"),
            _opt("Continuous-flow lithiation", "Keeps lithium chemistry, avoids deep cryogenics", "Similar", "Patent/literature"),
            _opt("Mg / LiCl direct insertion", "No alkyllithium", "Lower", "Patent/literature"),
            _opt("Directed metalation with LDA or LiTMP", "Where deprotonation, not exchange, is needed", "Similar"),
        ],
        "caution": "Functional-group tolerance and regioselectivity must be rechecked",
    },
    {
        "id": "lah", "category": "reagent",
        "triggers": ["lialh4", "lah", "lithium aluminum hydride", "lithium aluminium hydride"],
        "hazards": ["pyrophoric"],
        "problem": "Violent with water, hydrogen evolution, aluminum waste",
        "options": [
            _opt("Red-Al / Vitride", "Soluble, less pyrophoric, toluene-compatible", "Similar"),
            _opt("NaBH4 with activators (CaCl2, LiCl, I2)", "Esters and some amides", "Lower"),
            _opt("Catalytic hydrogenation or hydrosilylation", "Avoids stoichiometric hydride", "Similar", "Patent/literature"),
        ],
        "caution": "Reducing power differs; amides and acids may not reduce",
    },
    {
        "id": "nah", "category": "reagent",
        "triggers": ["nah", "sodium hydride"],
        "hazards": ["pyrophoric"],
        "problem": "Hydrogen evolution, dust and mineral-oil handling",
        "options": [
            _opt("KOtBu or NaOtBu", "Strong soluble base", "Similar"),
            _opt("K2CO3 / Cs2CO3 (with PTC where needed)", "For alkylations of acidic NH/OH", "Lower"),
            _opt("NaHMDS / KHMDS solutions", "Controlled dosing", "Higher"),
        ],
        "caution": "Base strength and counter-ion affect selectivity",
    },
    {
        "id": "azide", "category": "reagent",
        "triggers": ["nan3", "sodium azide", "azide", "tmsn3", "dppa"],
        "hazards": ["toxic", "explosive"],
        "problem": "Explosive and toxic; HN3 risk with acid",
        "options": [
            _opt("Continuous-flow azide chemistry", "Small hold-up, safer", "Similar", "Patent/literature"),
            _opt("Amine installation without azides (Gabriel, Mitsunobu with phthalimide, reductive amination)", "Route redesign", "Similar"),
        ],
        "caution": "May add steps; check waste and quench protocols",
    },
    {
        "id": "diazomethane", "category": "reagent",
        "triggers": ["diazomethane", "ch2n2", "tmsdiazomethane", "tms-diazomethane"],
        "hazards": ["explosive", "toxic"],
        "problem": "Explosive, toxic gas",
        "options": [
            _opt("Dimethyl carbonate or MeOH/acid", "Methyl esters without diazo reagents", "Lower"),
            _opt("In-situ flow generation (tube-in-tube)", "Never isolates diazomethane", "Higher", "Patent/literature"),
        ],
        "caution": "Different chemoselectivity for acids vs phenols",
    },
    {
        "id": "phosgene", "category": "reagent",
        "triggers": ["phosgene", "cocl2", "diphosgene"],
        "hazards": ["toxic"],
        "problem": "Highly toxic gas",
        "options": [
            _opt("CDI", "Carbonyl transfer for carbamates, ureas, acylations", "Higher"),
            _opt("Dimethyl carbonate", "Methylation and carbonylation under forcing conditions", "Lower", "Industrial"),
            _opt("Triphosgene (solid)", "Easier to handle but still toxic", "Similar", "Industrial"),
        ],
        "caution": "Triphosgene still releases phosgene; needs scrubbers",
    },
    {
        "id": "acid_chloride_reagents", "category": "reagent",
        "triggers": ["thionyl chloride", "socl2", "oxalyl chloride", "(cocl)2", "pcl5", "pocl3"],
        "hazards": ["corrosive", "toxic"],
        "problem": "Corrosive, releases HCl/SO2/CO, strict off-gas handling",
        "options": [
            _opt("T3P (propylphosphonic anhydride)", "Direct amide/ester coupling, low epimerization", "Higher"),
            _opt("CDI or EDC/Oxyma", "Mild activation without acid chloride", "Higher"),
            _opt("Mixed anhydride (isobutyl chloroformate)", "Cheaper at scale", "Lower"),
        ],
        "caution": "Acid chlorides are often cheapest; compare total cost including waste",
    },
    {
        "id": "benzotriazole_couplers", "category": "reagent",
        "triggers": ["hobt", "hoat", "hbtu", "hatu", "pybop"],
        "hazards": ["explosive"],
        "problem": "Benzotriazole additives are explosive and sensitizing; uronium salts are costly",
        "options": [
            _opt("T3P", "Safer, easy aqueous workup", "Similar"),
            _opt("EDC / Oxyma Pure", "Non-explosive additive", "Similar"),
            _opt("COMU", "Oxyma-based uronium", "Similar", "Industrial"),
            _opt("Boronic-acid catalysed amidation", "Direct amidation", "Lower", "Academic"),
        ],
        "caution": "Epimerization-sensitive couplings need testing",
    },
    {
        "id": "dcc", "category": "reagent",
        "triggers": ["dcc", "dicyclohexylcarbodiimide"],
        "hazards": ["toxic"],
        "problem": "Potent sensitizer; DCU urea removal is difficult",
        "options": [
            _opt("EDC (water-soluble urea)", "Easy aqueous removal", "Similar"),
            _opt("DIC", "Soluble urea in organic solvents", "Similar"),
        ],
        "caution": "Different urea solubility changes isolation",
    },
    {
        "id": "alkylating_agents", "category": "reagent",
        "triggers": ["dimethyl sulfate", "me2so4", "methyl iodide", "mei", "iodomethane"],
        "hazards": ["toxic"],
        "problem": "Genotoxic alkylating agents; impurity-control burden (ICH M7)",
        "options": [
            _opt("Dimethyl carbonate", "Green methylating agent (higher temperature)", "Lower"),
            _opt("Alternative disconnection avoiding late-stage alkylation", "Reduces genotoxic-impurity control", "Similar"),
        ],
        "caution": "Residual alkylating agents need controlled limits",
    },
    {
        "id": "mitsunobu", "category": "reagent",
        "triggers": ["mitsunobu", "diad", "dead"],
        "hazards": ["explosive"],
        "problem": "Azodicarboxylates are shock-sensitive; large PPh3O / hydrazide waste",
        "options": [
            _opt("Mesylate or tosylate activation then SN2", "Two steps, simpler workup", "Lower"),
            _opt("Catalytic Mitsunobu variants", "Lower waste", "Higher", "Academic"),
        ],
        "caution": "Stereochemical inversion must be retained by the alternative",
    },
    {
        "id": "chromium_oxidants", "category": "reagent",
        "triggers": ["pcc", "pdc", "jones", "cro3", "chromium", "k2cr2o7", "chromic acid"],
        "hazards": ["toxic"],
        "problem": "Cr(VI) is carcinogenic; heavy-metal waste",
        "options": [
            _opt("TEMPO / NaOCl (Anelli)", "Alcohol oxidation, aqueous, cheap", "Lower"),
            _opt("Parikh-Doering (SO3.py / DMSO)", "Near room temperature", "Similar"),
            _opt("Catalytic Ru or Cu / O2 or air", "Aerobic oxidation", "Lower", "Patent/literature"),
        ],
        "caution": "Over-oxidation and chlorination side products with NaOCl",
    },
    {
        "id": "swern_dmp", "category": "reagent",
        "triggers": ["swern", "dess-martin"],
        "hazards": ["cryogenic", "explosive"],
        "problem": "Swern is cryogenic with CO/dimethyl sulfide off-gas; Dess-Martin periodinane is shock-sensitive",
        "options": [
            _opt("TEMPO / NaOCl", "Mild, scalable", "Lower"),
            _opt("Parikh-Doering", "No cryogenic step", "Similar"),
        ],
        "caution": "Substrate sensitivity to chlorinating conditions",
    },
    {
        "id": "cyanides", "category": "reagent",
        "triggers": ["nacn", "kcn", "cyanide", "tmscn", "cucn", "zn(cn)2"],
        "hazards": ["toxic"],
        "problem": "Acutely toxic; HCN risk",
        "options": [
            _opt("K4[Fe(CN)6] in Pd-catalysed cyanation", "Non-toxic cyanide source", "Similar", "Industrial"),
            _opt("Alternative routes to nitrile (amide dehydration, aldoxime)", "Avoids free cyanide", "Similar"),
        ],
        "caution": "Metal catalysis conditions needed",
    },
    {
        "id": "tin", "category": "reagent",
        "triggers": ["bu3snh", "tributyltin", "tin hydride", "bu3sn", "stannane"],
        "hazards": ["toxic"],
        "problem": "Organotin toxicity and very low residual limits",
        "options": [
            _opt("(TMS)3SiH or photoredox radical conditions", "Tin-free radical chemistry", "Higher", "Patent/literature"),
            _opt("Suzuki or Negishi instead of Stille", "Cross-coupling without tin", "Similar", "Industrial"),
        ],
        "caution": "Radical selectivity may differ",
    },
    {
        "id": "bromine", "category": "reagent",
        "triggers": ["br2", "bromine"],
        "hazards": ["corrosive", "toxic"],
        "problem": "Volatile, corrosive, toxic",
        "options": [
            _opt("NBS or DBDMH", "Solid brominating agents", "Similar"),
            _opt("HBr / H2O2 or NaBr / oxidant", "In-situ bromine, cheaper", "Lower", "Patent/literature"),
            _opt("Continuous-flow bromination", "Small hold-up", "Similar", "Patent/literature"),
        ],
        "caution": "Regioselectivity and over-bromination",
    },
    {
        "id": "peracids", "category": "reagent",
        "triggers": ["mcpba", "m-cpba", "peracetic acid"],
        "hazards": ["explosive"],
        "problem": "Shock-sensitive peracids, costly waste (benzoic acid)",
        "options": [
            _opt("H2O2 with tungstate / catalyst", "Cheap oxidant, water byproduct", "Lower", "Industrial"),
            _opt("Oxone or urea-hydrogen peroxide", "Solid, easier handling", "Similar"),
        ],
        "caution": "Epoxidation / N-oxidation selectivity differs",
    },
    {
        "id": "alcl3", "category": "reagent",
        "triggers": ["alcl3", "aluminum chloride", "aluminium chloride"],
        "hazards": ["corrosive"],
        "problem": "Stoichiometric Lewis acid, aluminum waste, HCl release",
        "options": [
            _opt("Solid acids (zeolites, sulfonated resins)", "Recyclable catalysts", "Similar", "Patent/literature"),
            _opt("Metal triflates (Bi, Sc, Fe) catalytic", "Sub-stoichiometric", "Higher", "Patent/literature"),
            _opt("Methanesulfonic acid / P2O5 (Eaton)", "Brønsted-acid acylation", "Lower", "Industrial"),
        ],
        "caution": "Regioselectivity changes with acid type",
    },
    {
        "id": "bf3", "category": "reagent",
        "triggers": ["bf3", "boron trifluoride", "bf3.oet2"],
        "hazards": ["corrosive"],
        "problem": "Corrosive, fluoride waste",
        "options": [
            _opt("AlCl3 or TMSOTf", "Other Lewis acids (ionic reductions, glycosylations)", "Lower"),
            _opt("Brønsted acid (MsOH, TFA) where compatible", "Simpler waste", "Lower"),
        ],
        "caution": "Stereoselectivity can depend strongly on the Lewis acid",
    },
    {
        "id": "silanes", "category": "reagent",
        "triggers": ["et3sih", "triethylsilane"],
        "hazards": [],
        "problem": "Costly at scale; siloxane waste",
        "options": [
            _opt("TMDS or PMHS", "Cheaper hydride sources", "Lower", "Patent/literature"),
            _opt("NaBH4 / Lewis acid", "Silane-free reductions for ketones", "Lower", "Patent/literature"),
        ],
        "caution": "Selectivity must be re-optimized",
    },
    {
        "id": "palladium", "category": "reagent",
        "triggers": ["palladium", "pd(oac)2", "pd2(dba)3", "pd(pph3)4", "pd/c", "pdcl2", "pd(dppf)cl2"],
        "hazards": [],
        "problem": "Expensive metal; residual-metal limits (ICH Q3D)",
        "options": [
            _opt("Lower Pd loading via ligand/precatalyst screening", "Often 10x less Pd", "Lower"),
            _opt("Ni, Cu or Fe catalysis", "Base-metal coupling where precedent exists", "Lower", "Patent/literature"),
            _opt("Metal scavengers (thiol silica, activated carbon)", "Meet ppm limits", "Similar"),
        ],
        "caution": "Residual-metal testing required for the final API",
    },
    {
        "id": "high_pressure_h2", "category": "reagent",
        "triggers": ["high-pressure h2", "h2 (50 bar)", "autoclave"],
        "hazards": ["high_pressure"],
        "problem": "High-pressure hydrogen needs specialized equipment",
        "options": [
            _opt("Transfer hydrogenation (formate, iPrOH, HCOOH/Et3N)", "Ambient pressure", "Similar"),
            _opt("Continuous-flow hydrogenation", "Small inventory", "Higher", "Patent/literature"),
        ],
        "caution": "Chemoselectivity can differ",
    },
    # ------------------------------------------------------------------ process
    {
        "id": "chromatography", "category": "process",
        "triggers": ["chromatography", "column chromatography", "silica gel column",
                     "prep-hplc", "flash column"],
        "hazards": [],
        "problem": "Solvent-heavy and hard to scale for a manufacturing route",
        "options": [
            _opt("Crystallization of the compound or a salt", "Standard purification at scale", "Lower"),
            _opt("Co-crystal screening (use AgniKristal)", "Co-crystal formation can purify and give a stable solid form", "Lower", "Patent/literature"),
            _opt("Anti-solvent / reactive crystallization", "Isolation without a column", "Lower"),
        ],
        "caution": "Impurity rejection must be shown by purge studies",
    },
    {
        "id": "cryogenic_generic", "category": "process",
        "triggers": ["cryogenic", "dry ice", "-78 c", "-78c"],
        "hazards": ["cryogenic"],
        "problem": "Deep cooling is energy-intensive and limits batch size",
        "options": [
            _opt("Continuous-flow microreactor", "Fast mixing and heat removal allow warmer operation", "Similar", "Patent/literature"),
            _opt("Less reactive organometallics (turbo Grignard, zincates)", "-20 to 0 C operation", "Lower"),
        ],
        "caution": "Flow needs solids-free streams",
    },
]


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def _compile(trigger):
    return re.compile(r"(?<![a-z0-9])" + re.escape(trigger.lower()) + r"(?![a-z0-9])")


_PATTERNS = [
    (entry, [_compile(t) for t in entry["triggers"]]) for entry in KNOWLEDGE_BASE
]


def find_matches(text):
    """Return the knowledge-base entries whose triggers appear in the text."""
    if text is None or (isinstance(text, float) and text != text):
        return []
    s = str(text).lower()
    return [entry for entry, pats in _PATTERNS if any(p.search(s) for p in pats)]


def suggest(reagents="", solvent="", temp_c=None, extra=""):
    """
    Substitution suggestions for one step.

    Returns a list of entries (copies) with a 'matched_in' field. A
    temperature at or below -40 C also triggers the generic cryogenic entry.
    """
    seen, out = set(), []
    for field, value in (("reagents", reagents), ("solvent", solvent), ("notes", extra)):
        for entry in find_matches(value):
            if entry["id"] not in seen:
                seen.add(entry["id"])
                out.append({**entry, "matched_in": field})
    try:
        if temp_c is not None and float(temp_c) <= -40 and "cryogenic_generic" not in seen:
            entry = next(e for e in KNOWLEDGE_BASE if e["id"] == "cryogenic_generic")
            out.append({**entry, "matched_in": "temperature"})
    except (TypeError, ValueError):
        pass
    return out


def auto_hazards(reagents="", solvent="", temp_c=None):
    """Hazard flags implied by the step text, for filling a blank hazards column."""
    flags = set()
    for entry in suggest(reagents, solvent, temp_c):
        flags.update(entry["hazards"])
    return sorted(flags)


def lookup_table(text):
    """Flat table of alternatives for free text (reagents, solvents, notes)."""
    rows = []
    for entry in suggest(extra=text):
        for opt in entry["options"]:
            rows.append({
                "Found": entry["id"],
                "Category": entry["category"],
                "Problem": entry["problem"],
                "Alternative": opt["name"],
                "How it helps": opt["note"],
                "Cost vs original": opt["cost"],
                "Maturity": opt["maturity"],
                "Re-check": entry["caution"],
            })
    return pd.DataFrame(rows)


def screen_route(df):
    """
    Screen an experimental-data table (see core.experimental_data) and list,
    for every step, the hazardous or costly items found and what could
    replace them. Works for any drug.
    """
    rows = []
    for _, r in df.iterrows():
        for entry in suggest(r.get("reagents", ""), r.get("solvent", ""), r.get("temp_c")):
            rows.append({
                "company": r.get("company", ""),
                "route_id": r.get("route_id", ""),
                "step_no": r.get("step_no", ""),
                "step_name": r.get("step_name", ""),
                "item": entry["id"],
                "category": entry["category"],
                "flags": ", ".join(entry["hazards"]),
                "problem": entry["problem"],
                "alternatives": "; ".join(o["name"] for o in entry["options"]),
                "re_check": entry["caution"],
            })
    return pd.DataFrame(rows)
