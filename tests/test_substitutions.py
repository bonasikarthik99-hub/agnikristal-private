"""Run with:  python tests/test_substitutions.py"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.experimental_data import load_experiments
from core.substitutions import (
    KNOWLEDGE_BASE, auto_hazards, find_matches, lookup_table, screen_route, suggest,
)


def ids(text):
    return [e["id"] for e in find_matches(text)]


# whole-token matching: no false positives
assert ids("2-MeTHF") == []
assert ids("petroleum ether") == []
assert ids("pyridinium chloride") == []
assert ids("iPrMgCl.LiCl") == []
assert ids("DMSO") == []

# true positives
assert ids("MeCN/DCM") == ["dcm"]
assert "organolithium" in ids("n-BuLi")
assert "bf3" in ids("Et3SiH/BF3.OEt2") and "silanes" in ids("Et3SiH/BF3.OEt2")
assert "dmf_family" in ids("DMF")
assert "lah" in ids("LiAlH4 in THF")
assert "chromatography" in ids("purified by column chromatography")

# temperature trigger
assert "cryogenic_generic" in [e["id"] for e in suggest("x", "y", -78)]
assert "cryogenic_generic" not in [e["id"] for e in suggest("x", "y", -10)]
assert "pyrophoric" in auto_hazards("n-BuLi", "THF", -78)

# knowledge-base integrity
assert len({e["id"] for e in KNOWLEDGE_BASE}) == len(KNOWLEDGE_BASE)
for e in KNOWLEDGE_BASE:
    assert e["options"] and e["triggers"] and e["caution"]
    for o in e["options"]:
        assert o["cost"] in ("Lower", "Similar", "Higher")
        assert o["maturity"] in ("Industrial", "Patent/literature", "Academic")

# route screen on the demo table
df = load_experiments(os.path.join(os.path.dirname(__file__), "..", "data", "experimental_template.csv"))
scr = screen_route(df)
assert {"organolithium", "dcm", "bf3"} <= set(scr["item"])
assert not lookup_table("LiAlH4, DMF").empty
assert lookup_table("water").empty

print("ALL TESTS PASSED (%d knowledge-base entries)" % len(KNOWLEDGE_BASE))
