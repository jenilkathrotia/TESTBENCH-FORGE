"""Tasks for TestBench-Forge — run with: hud eval tasks.py claude

`hud eval` collects the `tasks` list. Each is the forge_testbench template bound to one
module under test; the agent must author a test suite, scored by hidden-mutant kill rate.
"""
from env import forge_testbench
from testbench import MODULES

tasks = [forge_testbench(module_id=m) for m in MODULES]

# The earlier verifier-writing (forge_verifier / FHIR) and SIA harness (forge_harness)
# templates still live in env.py / families.py if you want them as alternates.
