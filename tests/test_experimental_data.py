"""Run with:  python tests/test_experimental_data.py"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from core.experimental_data import (
    load_experiments, rank_routes, best_of_all, route_summary, step_table,
)

HERE = os.path.dirname(__file__)
df = load_experiments(os.path.join(HERE, "..", "data", "experimental_template.csv"))

# loading and demo flagging
assert len(df) == 11
assert df["is_demo"].all()
assert any("DEMO" in w for w in df.attrs["warnings"])

# route yield = product of step yields
summary = route_summary(df).set_index("route_id")
exp_a1 = 0.72 * 0.88 * 0.70 * 0.65
assert abs(summary.loc["A1", "overall_yield_pct"] / 100 - exp_a1) < 1e-4

# cost: sum(cost_i / product of downstream yields)
exp_cost = 900 / (0.88 * 0.70 * 0.65) + 120 / (0.70 * 0.65) + 600 / 0.65 + 300
assert abs(summary.loc["A1", "cost_usd_per_kg"] - exp_cost) < 1e-6

# probability: route C1 has 3 steps with replicates but only 3 steps total -> complete
assert summary.loc["C1", "complete_probability_data"]
# Beta(1+k,1+n-k) mean = (k+1)/(n+2): step with 5/5 -> 6/7
t = step_table(df)
row = t[(t.route_id == "A1") & (t.step_no == 2)].iloc[0]
assert abs(row["p_in_spec"] - 6 / 7) < 0.01
assert row["p_lo90"] < row["p_in_spec"] < row["p_hi90"]

# ranking: B1 (milder, high purity, proline co-crystal) should beat A1,
# and C1 (stops before purification) must not outrank complete routes
ranked = rank_routes(df)
assert ranked.iloc[0]["route_id"] == "B1"
assert ranked.iloc[-1]["route_id"] == "C1"
assert not ranked.set_index("route_id").loc["C1", "reaches_final_form"]
assert ranked["score"].between(0, 1).all()

# best-of-all picks one entry per step type and warns about mixing companies
best = best_of_all(df)
assert best["steps"]["step_name"].is_unique
assert best["n_companies"] >= 2
assert any("not been run" in n for n in best["notes"])
assert any("DEMO" in n for n in best["notes"])

# missing replicate data -> NaN probability, not a guess
df2 = df.copy()
df2.loc[df2["route_id"] == "B1", "n_runs"] = float("nan")
s2 = route_summary(df2).set_index("route_id")
assert not s2.loc["B1", "complete_probability_data"]
assert pd.isna(s2.loc["B1", "p_exact_product"])
r2 = rank_routes(df2)
assert "probability" not in r2.set_index("route_id").loc["B1", "components_used"]

# validation errors
bad = df.copy()
bad.loc[0, "yield_pct"] = 140
try:
    load_experiments(bad)
    raise SystemExit("expected ValueError for yield > 100")
except ValueError:
    pass

print(ranked[["company", "route_id", "reaches_final_form", "overall_yield_pct",
              "cost_usd_per_kg", "p_exact_product", "score"]].to_string(index=False))
print("\nbest-of-all steps:")
print(best["steps"][["step_no", "step_name", "company", "yield_pct", "p_in_spec"]].to_string(index=False))
print("projected yield %:", best["projected_overall_yield_pct"],
      "| projected P:", best["projected_p_exact_product"])
print("\nALL TESTS PASSED")
