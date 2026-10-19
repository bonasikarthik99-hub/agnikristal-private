"""
Experimental-data analysis for dapagliflozin process routes.

Load step-level results from any company (internal runs, CRO reports, data
transcribed from patent examples), then:

  * compute route-level overall yield and cost per kg of final product
  * estimate the probability that a route delivers the exact product
    (in-spec material) from replicate runs, with a credible interval
  * rank routes with a transparent, adjustable composite score
  * assemble a "best of all" route by picking the strongest step from
    each company (a projection, flagged as an untested combination)

Probability model
-----------------
For each step with n_runs replicates of which n_runs_in_spec met the
specification, the success rate gets a Beta(1 + k, 1 + n - k) posterior
(uniform prior). A route's probability is the product over steps, sampled
by Monte Carlo so the credible interval is honest about thin data.
Steps without replicate counts are reported as having no probability, and
the route is marked incomplete rather than guessed.

Default "in spec" targets (see DEFAULT_SPEC) come from the impurity limits
quoted in a recent dapagliflozin process patent; edit them for your own
specification.
"""

import io

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = [
    "company",
    "route_id",
    "step_no",
    "step_name",
    "yield_pct",
]

OPTIONAL_COLUMNS = [
    "reagents",
    "solvent",
    "temp_c",
    "time_h",
    "purity_pct",
    "alpha_anomer_pct",
    "n_runs",
    "n_runs_in_spec",
    "scale_kg",
    "step_cost_usd_per_kg",
    "hazards",
    "source",
    "is_demo",
]

# Target specification for the final API (used for flags, not for scoring).
DEFAULT_SPEC = {
    "purity_pct_min": 99.5,
    "alpha_anomer_pct_max": 0.1,
}

DEFAULT_WEIGHTS = {
    "yield": 0.35,
    "probability": 0.30,
    "cost": 0.25,
    "safety": 0.10,
}

# Hazards that count against a route's safety score (comma-separated in data).
HAZARD_PENALTY = {
    "pyrophoric": 0.30,
    "cryogenic": 0.25,
    "corrosive": 0.10,
    "chlorinated_solvent": 0.10,
    "toxic": 0.20,
    "high_pressure": 0.15,
}

# A route is only comparable with others if it ends in an isolated, purified
# API form; otherwise fewer steps would unfairly inflate its overall yield.
FINAL_STEP_KEYS = {
    "purification",
    "final_crystallization",
    "final_isolation",
    "api_isolation",
    "cocrystal_purification",
}

N_SAMPLES = 20000
_RNG_SEED = 7


# ---------------------------------------------------------------------------
# Loading and validation
# ---------------------------------------------------------------------------

def load_experiments(source):
    """
    Load experimental data from a CSV/Excel path, a file-like object
    (e.g. a Streamlit upload), or a DataFrame. Returns a cleaned DataFrame.
    Raises ValueError with a readable message when the data is unusable.
    """
    if isinstance(source, pd.DataFrame):
        df = source.copy()
    else:
        name = getattr(source, "name", str(source)).lower()
        if name.endswith((".xlsx", ".xlsm", ".xls")):
            df = pd.read_excel(source)
        else:
            if hasattr(source, "read"):
                raw = source.read()
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8-sig")
                df = pd.read_csv(io.StringIO(raw))
            else:
                df = pd.read_csv(source, encoding="utf-8-sig")

    df.columns = [str(c).strip().lower() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            "Missing required column(s): " + ", ".join(missing)
            + ". Required: " + ", ".join(REQUIRED_COLUMNS)
        )

    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan

    for col in ("step_no", "yield_pct", "temp_c", "time_h", "purity_pct",
                "alpha_anomer_pct", "n_runs", "n_runs_in_spec", "scale_kg",
                "step_cost_usd_per_kg"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ("company", "route_id", "step_name"):
        df[col] = df[col].astype(str).str.strip()
    df["step_key"] = df["step_name"].str.lower().str.replace(r"\s+", "_", regex=True)

    df["hazards"] = df["hazards"].fillna("").astype(str).str.lower()
    df["is_demo"] = (
        df["is_demo"].astype(str).str.lower().isin(["1", "true", "yes", "y"])
        | df["company"].str.upper().str.startswith("DEMO")
    )

    problems = validate_experiments(df)
    errors = [p for p in problems if p.startswith("ERROR")]
    if errors:
        raise ValueError("\n".join(errors))
    df.attrs["warnings"] = [p for p in problems if p.startswith("WARN")]
    return df


def validate_experiments(df):
    """Return a list of 'ERROR: ...' / 'WARN: ...' strings."""
    out = []

    bad = df[df["yield_pct"].isna() | (df["yield_pct"] < 0) | (df["yield_pct"] > 100)]
    for idx, row in bad.iterrows():
        out.append(
            f"ERROR: row {idx + 2}: yield_pct must be 0-100 "
            f"(company={row['company']}, route={row['route_id']}, step={row['step_name']})"
        )

    if df["step_no"].isna().any():
        out.append("ERROR: step_no must be a number on every row")

    for col in ("purity_pct", "alpha_anomer_pct"):
        vals = df[col].dropna()
        if ((vals < 0) | (vals > 100)).any():
            out.append(f"ERROR: {col} must be 0-100")

    k, n = df["n_runs_in_spec"], df["n_runs"]
    if ((k > n) & k.notna() & n.notna()).any():
        out.append("ERROR: n_runs_in_spec cannot exceed n_runs")

    dup = df.duplicated(["company", "route_id", "step_no"], keep=False)
    if dup.any():
        out.append("ERROR: duplicate (company, route_id, step_no) rows")

    if df["n_runs"].isna().all():
        out.append(
            "WARN: no n_runs/n_runs_in_spec supplied - probabilities cannot be estimated"
        )
    if df["is_demo"].any():
        out.append(
            "WARN: contains DEMO rows - fictional placeholder numbers, not real data"
        )
    return out


# ---------------------------------------------------------------------------
# Per-step statistics
# ---------------------------------------------------------------------------

def _beta_samples(k, n, rng):
    return rng.beta(1 + k, 1 + n - k, N_SAMPLES)


def step_table(df):
    """Per-step posterior success rate (mean and 90% interval) where replicates exist."""
    rng = np.random.default_rng(_RNG_SEED)
    rows = []
    for _, r in df.iterrows():
        has_runs = pd.notna(r["n_runs"]) and pd.notna(r["n_runs_in_spec"]) and r["n_runs"] > 0
        if has_runs:
            s = _beta_samples(r["n_runs_in_spec"], r["n_runs"], rng)
            p_mean = float(s.mean())
            p_lo, p_hi = (float(x) for x in np.percentile(s, [5, 95]))
        else:
            p_mean = p_lo = p_hi = np.nan
        rows.append({
            **r.to_dict(),
            "p_in_spec": p_mean,
            "p_lo90": p_lo,
            "p_hi90": p_hi,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Route-level metrics
# ---------------------------------------------------------------------------

def _route_cost(steps):
    """
    Cost per kg of final product. step_cost_usd_per_kg is the cost per kg of
    that step's output; to make 1 kg of final product you need
    1 / (product of downstream yields) kg of the step output. Treats
    fractional yield as a mass yield, which is an approximation.
    """
    steps = steps.sort_values("step_no")
    if steps["step_cost_usd_per_kg"].isna().any():
        return np.nan
    y = (steps["yield_pct"] / 100.0).to_numpy()
    cost = steps["step_cost_usd_per_kg"].to_numpy()
    total = 0.0
    for i in range(len(steps)):
        downstream = float(np.prod(y[i + 1:])) if i + 1 < len(steps) else 1.0
        if downstream <= 0:
            return np.nan
        total += cost[i] / downstream
    return float(total)


def _safety_score(steps):
    flags = set()
    for h in steps["hazards"]:
        flags.update(x.strip() for x in str(h).split(",") if x.strip())
    penalty = sum(HAZARD_PENALTY.get(f, 0.10) for f in flags)
    return float(max(0.0, 1.0 - penalty)), sorted(flags)


def _route_probability(steps, rng):
    """Product of per-step Beta samples; NaN when any step lacks replicates."""
    draws = []
    for _, r in steps.iterrows():
        if pd.isna(r["n_runs"]) or pd.isna(r["n_runs_in_spec"]) or r["n_runs"] <= 0:
            return np.nan, np.nan, np.nan
        draws.append(_beta_samples(r["n_runs_in_spec"], r["n_runs"], rng))
    prod = np.prod(np.vstack(draws), axis=0)
    lo, hi = np.percentile(prod, [5, 95])
    return float(prod.mean()), float(lo), float(hi)


def route_summary(df, spec=None):
    """One row per (company, route_id) with overall yield, cost, probability, safety."""
    spec = {**DEFAULT_SPEC, **(spec or {})}
    rng = np.random.default_rng(_RNG_SEED)
    rows = []
    for (company, route_id), steps in df.groupby(["company", "route_id"], sort=False):
        steps = steps.sort_values("step_no")
        overall_yield = float(np.prod(steps["yield_pct"] / 100.0))
        p_mean, p_lo, p_hi = _route_probability(steps, rng)
        safety, flags = _safety_score(steps)

        last = steps.iloc[-1]
        meets_purity = (
            bool(last["purity_pct"] >= spec["purity_pct_min"])
            if pd.notna(last["purity_pct"]) else None
        )
        meets_alpha = (
            bool(last["alpha_anomer_pct"] <= spec["alpha_anomer_pct_max"])
            if pd.notna(last["alpha_anomer_pct"]) else None
        )

        rows.append({
            "company": company,
            "route_id": route_id,
            "n_steps": len(steps),
            "reaches_final_form": bool(last["step_key"] in FINAL_STEP_KEYS),
            "overall_yield_pct": round(overall_yield * 100, 2),
            "cost_usd_per_kg": _route_cost(steps),
            "p_exact_product": p_mean,
            "p_lo90": p_lo,
            "p_hi90": p_hi,
            "complete_probability_data": not np.isnan(p_mean),
            "final_purity_pct": last["purity_pct"],
            "final_alpha_anomer_pct": last["alpha_anomer_pct"],
            "meets_purity_spec": meets_purity,
            "meets_alpha_spec": meets_alpha,
            "safety_score": round(safety, 2),
            "hazards": ", ".join(flags),
            "is_demo": bool(steps["is_demo"].any()),
        })
    return pd.DataFrame(rows)


def rank_routes(df, weights=None, spec=None):
    """
    Rank routes by a composite score in [0, 1]:

        score = w_yield*yield + w_prob*P(exact product)
              + w_cost*cost_score + w_safety*safety

    cost_score is min-max scaled across the routes supplied (cheapest = 1).
    Missing components are left out and the remaining weights renormalized,
    so incomplete routes are not silently rewarded or punished; the
    'components_used' column says what each score rests on. Routes whose
    last step is not an isolation/purification step (reaches_final_form =
    False) are ranked below complete routes because their yield and cost
    leave out work the others include.
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    summary = route_summary(df, spec=spec)
    if summary.empty:
        return summary

    costs = summary["cost_usd_per_kg"]
    if costs.notna().sum() >= 2 and costs.max() > costs.min():
        cost_score = 1.0 - (costs - costs.min()) / (costs.max() - costs.min())
    elif costs.notna().sum() == 1:
        cost_score = pd.Series(np.where(costs.notna(), 1.0, np.nan), index=costs.index)
    else:
        cost_score = pd.Series(np.nan, index=costs.index)

    scores, used = [], []
    for i, r in summary.iterrows():
        parts = {
            "yield": r["overall_yield_pct"] / 100.0,
            "probability": r["p_exact_product"],
            "cost": cost_score.iloc[i],
            "safety": r["safety_score"],
        }
        avail = {k: v for k, v in parts.items() if pd.notna(v)}
        total_w = sum(w[k] for k in avail)
        scores.append(sum(w[k] * v for k, v in avail.items()) / total_w if total_w else np.nan)
        used.append(", ".join(avail))
    summary["score"] = np.round(scores, 3)
    summary["components_used"] = used
    # Routes that stop before an isolated API form are not comparable on
    # yield or cost, so they are listed after the complete ones.
    return summary.sort_values(
        ["reaches_final_form", "score"], ascending=[False, False], ignore_index=True
    )


# ---------------------------------------------------------------------------
# Best-of-all assembly
# ---------------------------------------------------------------------------

def best_of_all(df):
    """
    Pick the strongest result for each step type across every company.

    Per step, utility = yield * P(in spec) when replicates exist, otherwise
    yield alone (marked). The result is a PROJECTION: step conditions from
    different companies have not been run together, so intermediates,
    solvents and impurity profiles may not carry over.
    """
    table = step_table(df)
    table["utility"] = table["yield_pct"] / 100.0 * table["p_in_spec"].fillna(1.0)
    table["utility_uses_replicates"] = table["p_in_spec"].notna()

    picks = []
    for key, group in table.groupby("step_key", sort=False):
        best = group.sort_values(
            ["utility", "step_cost_usd_per_kg"], ascending=[False, True],
            na_position="last"
        ).iloc[0]
        picks.append(best)
    chosen = pd.DataFrame(picks).sort_values("step_no").reset_index(drop=True)

    y = float(np.prod(chosen["yield_pct"] / 100.0))
    p_vals = chosen["p_in_spec"]
    p_route = float(p_vals.prod()) if p_vals.notna().all() else np.nan
    companies = chosen["company"].nunique()

    notes = []
    if companies > 1:
        notes.append(
            "Steps come from different companies; this exact combination has "
            "not been run. Confirm intermediate compatibility before use."
        )
    if (~chosen["utility_uses_replicates"]).any():
        notes.append(
            "Some picks rank on yield alone (no replicate data): "
            + ", ".join(chosen.loc[~chosen["utility_uses_replicates"], "step_name"])
        )
    if chosen["is_demo"].any():
        notes.append("Includes DEMO rows (fictional numbers).")

    return {
        "steps": chosen[[
            "step_no", "step_name", "company", "route_id", "reagents", "solvent",
            "temp_c", "yield_pct", "purity_pct", "alpha_anomer_pct",
            "p_in_spec", "utility_uses_replicates",
        ]],
        "projected_overall_yield_pct": round(y * 100, 2),
        "projected_p_exact_product": p_route,
        "n_companies": int(companies),
        "notes": notes,
    }


def company_summary(df):
    """Mean step yield and replicate success rate per company."""
    t = step_table(df)
    g = t.groupby("company")
    return pd.DataFrame({
        "n_steps_reported": g.size(),
        "mean_step_yield_pct": g["yield_pct"].mean().round(1),
        "mean_p_in_spec": g["p_in_spec"].mean().round(3),
    }).reset_index()
