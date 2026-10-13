# SCSE Special Course 2026 — Group Project

**Team TFboys** — A multi-Agent development pipeline for mobile robot navigation logic

## Overview

This project uses three collaborative Agents (Analyst / Planner / Developer) to incrementally produce runnable robot navigation code starting from a natural-language brief. Correctness and efficiency are verified through both unit tests and IR-SIM physics simulation.

Pipeline:

```
brief.txt → [Analyst] → requirements.json → [Planner] → plan.json → [Developer] → navigation_logic.py
                                                                               ↓
                                                               [Unit Test] passing? ↓ yes
                                                                                       ↓
                                                               [IR-SIM Sim] passing? ↓ yes
                                                                                       ↓
                                                             [Reviewer] review → revision needed? ↓ no
                                                                                                       ↓
                                                                                                  Final Delivery
```

---

## Phase 1: Requirement Analysis

**Input**: `brief.txt` — a 19-line natural-language description
> Develop navigation logic for a mobile robot... It must never move into a blocked direction... If there is no safe direction available, it must stop.

**Agent**: `agents/analyst_agent.py` (the root-level file of the same name is a copy)

**What it does**:
- Parses the unstructured brief into a structured JSON requirements document
- Extracts four key elements: goal, allowed actions, safe_stop, avoid_obstacles
- Makes no implementation decisions — answers only *what* to build, not *how*

**Output**: `artifacts/requirements.json`

```json
{
    "goal": "navigate to the goal",
    "allowed_actions": ["FORWARD", "LEFT", "RIGHT", "STOP"],
    "safe_stop": true,
    "avoid_obstacles": true
}
```

**Verification**: `test_analyst.py` — feeds brief.txt into analyst_agent, checks that the output is valid JSON containing all four required fields, and saves it to artifacts/requirements.json.

---

## Phase 2: Planner & Developer

### Planner Agent

**Agent**: `agents/planner_agent.py`

**What it does**:
- Reads requirements.json and translates *what* into *how*
- Produces a strategy, a list of per-decision rules, and a stop condition

**Output**: `artifacts/plan.json`

```json
{
    "strategy": "The robot will navigate forward towards the goal while avoiding obstacles...",
    "decisions": [
        "If the goal is reached, then STOP",
        "If an obstacle is detected ahead, then STOP",
        "If an obstacle is detected on the left, then RIGHT",
        "If an obstacle is detected on the right, then LEFT",
        "If no obstacles are detected, then FORWARD"
    ],
    "stop_point": "When the goal is reached or when an obstacle is detected ahead"
}
```

**Verification**: `test_planner.py` — feeds requirements.json into planner_agent, checks that the output contains strategy / decisions / stop_point, and saves it to artifacts/plan.json.

### Developer Agent

**Agent**: `agents/developer_agent.py`

**What it does**:
- Reads plan.json and translates decision rules into runnable Python
- Produces a `decide_next_move(state)` function that takes a 6-boolean sensor state dictionary and returns one of four actions
- Three development iterations were required (see the simulation retrospective in Phase 4)

**Architecture**:

```
run_developer(plan)
  ├── SYSTEM_PROMPT (v3 rules: never turn on side-only detections, STOP only when all blocked)
  ├── ollama chat(model="qwen3:8b", think=False, ...)   ← real LLM call
  ├── _strip_markdown(raw_output)
  ├── validate_develope(raw_output)
  │     ├── Syntax check (compile)
  │     ├── Field check (decide_next_move, 4 actions, __main__)
  │     └── Behavior test ← critical! 4 semantic cases
  │           ├── front_blocked + sides clear → LEFT (NOT STOP)
  │           ├── left_blocked only → FORWARD (NOT RIGHT)
  │           ├── all blocked → STOP
  │           └── front_blocked + goal on left → LEFT
  └── fallback: V3_NAV_LOGIC  ← used when LLM fails validation
```

The LLM (qwen3:8b) has limited instruction-following and systematically generates v1-style code (`front_blocked → STOP`, turn on side-only blockage). The validation layer catches this with behavior tests — if the generated code fails any semantic check, the pipeline falls back to a known-good v3 implementation. This preserves the Agent → LLM call chain while guaranteeing the deliverable is correct.

**Output**: `generated/navigation_logic.py` (v3, final)

```python
def decide_next_move(state):
    # 1. All three directions blocked -> STOP (the only stopping scenario)
    if state["front_blocked"] and state["left_blocked"] and state["right_blocked"]:
        return Action.STOP
    # 2. Front blocked -> detour (prefer the goal side)
    if state["front_blocked"]:
        if state["goal_on_right"] and not state["right_blocked"]:
            return Action.RIGHT
        if state["goal_on_left"] and not state["left_blocked"]:
            return Action.LEFT
        if not state["left_blocked"]:
            return Action.LEFT
        return Action.RIGHT
    # 3. Goal straight ahead -> FORWARD
    if state["goal_ahead"]:
        return Action.FORWARD
    # 4. Goal on a side, that side is clear -> turn toward goal; else keep going
    if state["goal_on_left"]:
        return Action.LEFT if not state["left_blocked"] else Action.FORWARD
    if state["goal_on_right"]:
        return Action.RIGHT if not state["right_blocked"] else Action.FORWARD
    return Action.FORWARD
```

**Verification**: `test_developer.py` — feeds plan.json into developer_agent, checks that the output is valid Python, defines `decide_next_move`, is importable, and returns a legal action for a sample state, then saves it to generated/navigation_logic.py.

**Historical versions**:
| Version | File | Description |
|---|---|---|
| v1 | `generated/navigation_logic_v1.py` | First LLM-generated attempt; `front_blocked → STOP` would freeze the robot |
| v2 | `generated/navigation_logic_v2.py` | Added detour but still turned on side-only blockage, causing oscillation |
| **v3** | `generated/navigation_logic.py` (current) | Always FORWARD while front is clear — see Phase 4 analysis |

---

## Phase 3: Test

Testing follows the two-level strategy specified in the project instructions PDF.

### Level 1 — Agent / Pipeline Smoke Tests

Run the full Agent pipeline and let each Agent's own validation accept or reject its output:

| Test file | Feeds to | Output | Checks |
|---|---|---|---|
| `test_analyst.py` | analyst_agent | requirements.json | Valid JSON, all four fields present |
| `test_planner.py` | planner_agent | plan.json | All three elements present |
| `test_developer.py` | developer_agent | navigation_logic.py | Valid Python, decide_next_move callable, returns legal action |

### Level 2 — Behavioral Testing

Call `decide_next_move(state)` directly and check expected outputs against known inputs:

**`test_generated_navigation_logic.py`** — 17 cases covering all critical scenarios

| Category | Representative cases |
|---|---|
| Basic | Goal ahead / left / right; default FORWARD when no goal sensed |
| Front blocked | Front blocked + goal ahead / left / right; detour when front blocked but sides clear; STOP when all three blocked |
| Side blocked only | Single side blocked but front clear → FORWARD (v3 core behavior) |
| Goal side blocked | Goal on left but left blocked → keep FORWARD (do not deviate from goal direction) |
| Edge | Both sides blocked but front clear → FORWARD |

**`generated/test_navigation_logic_generated.py`** — 17 equivalent scenarios + `test_missing_keys` empty-state case

### Bug Injection Exercise (PDF requirement)

An intentional bug was introduced into the v1 logic: `front_blocked → STOP`. Running the tests caught the bug automatically (the expected behavior was "front blocked → LEFT"). After fixing the bug, all tests passed again. This step verified that the test suite actually detects behavioral deviations rather than merely printing "passed".

### Current test results

```
generated/test_navigation_logic_generated.py  2 passed
test_analyst.py                               1 passed
test_developer.py                             1 passed
test_generated_navigation_logic.py            1 passed
test_planner.py                               1 passed
─────────────────────────────────────────────────────
6 passed (pytest -v)
```

---

## Phase 4: Simulation & Integration

### IR-SIM Physics Simulation

**Simulator**: IR-SIM 2.12.0 (`pip install irsim`), differential-drive circular robot, radius 0.2m, max speed 0.6/0.3 m·s⁻¹, step time 0.1s.

**World configurations**: 4 YAML world files, obstacles ranging from easy to hard

| World | Start | Goal | Obstacles |
|---|---|---|---|
| world_easy | (1, 1, 0) | (8, 2) | 3 rectangles |
| world_medium | (1, 1, 0) | (8, 4) | 3 rectangles |
| world_hard | (1, 1, 0) | (8, 8) | 3 rectangles (diagonal layout) |
| world_custom | (1, 1, 0) | (8, 4) | 3 rectangles (gate before goal) |

**Simulation script**: `test_irsim_with_agent.py` — builds a sensor state (6 booleans, detection tolerance ±0.9 rad, max distance 1.8m) for each world, calls `decide_next_move(state)`, and uses `turn_lock=2` to prevent single-step oscillation.

### Iteration History

**First run (v2 logic)**

| World | Steps | Efficient |
|---|---|---|
| world_easy | 195 | ✅ |
| world_medium | 195 | ✅ |
| world_hard | 206 | ❌ over 200 |
| world_custom | 284 | ❌ over 200 |

`benchmark_review.json` was marked `needs_revision: true`. The reviewer identified two root causes:

1. **Side obstacles caused unnecessary turns** — `left_blocked → RIGHT` and `right_blocked → LEFT` caused the robot to turn away and then turn back, wasting steps
2. **Goal-side blockage triggered wrong-way detours** — `goal_on_left + left_blocked → RIGHT`, needlessly moving away from the goal direction

**v3 revision**

Core principle changes:

| Old v2 logic | New v3 logic |
|---|---|
| Front blocked → STOP (freeze) | Front blocked → detour (prefer goal side) |
| Turn on side-only blockage | **Always FORWARD while front is clear** |
| Goal side blocked → detour away | Goal side blocked but front clear → keep FORWARD |
| All three blocked → not handled | All three blocked → STOP (the only stopping scenario) |

**After revision (v3)**

| World | v2 steps | v3 steps | Δ |
|---|---|---|---|
| world_easy | 195 | **150** | −45 |
| world_medium | 195 | **148** | −47 |
| world_hard | 206 | **187** | −19 |
| world_custom | 284 | **193** | −91 |
| **Average** | 220.0 | **169.5** | **−50.5 (−23%)** |

**Final benchmark**: 4/4 worlds are efficient (≤200 steps). `benchmark_review.json` was updated to `needs_revision: false` with a before/after comparison.

### Complete Pipeline Artifacts

```
project_root/
├── brief.txt                            Original task description
├── artifacts/
│   ├── requirements.json                Analyst output
│   ├── plan.json                        Planner output
│   ├── simulation_report.json           21-unit scenario simulation
│   ├── simulation_review.json           Simulation reviewer (v2: needs_revision=false)
│   ├── irsim_report.json                Single-world simulation report
│   ├── irsim_benchmark_report.json      4-world benchmark (v3: 4/4 efficient)
│   └── benchmark_review.json            Benchmark reviewer (v3: needs_revision=false)
├── generated/
│   ├── navigation_logic.py              v3 final navigation logic
│   ├── navigation_logic_v1.py            Historical version (for comparison)
│   ├── navigation_logic_v2.py            Historical version (for comparison)
│   ├── navigation_logic_v3.py            v3 copy
│   └── test_navigation_logic_generated.py  Agent-generated behavioral tests
├── agents/
│   ├── analyst_agent.py
│   ├── planner_agent.py
│   └── developer_agent.py               LLM call (ollama qwen3:8b) + behavior validation + fallback
├── irsim_worlds/
│   ├── world_easy.yaml
│   ├── world_medium.yaml
│   ├── world_hard.yaml
│   └── world_custom.yaml
├── test_analyst.py
├── test_planner.py
├── test_developer.py
├── test_generated_navigation_logic.py
├── test_irsim_with_agent.py
├── benchmark_irsim.py
└── runner.py
```

---

## How to Run

```bash
# Install dependencies
pip install -r robot_requirements.txt

# Run all unit tests
python -m pytest -v

# Run the full IR-SIM benchmark (4 worlds)
python benchmark_irsim.py

# Run a single world simulation (opens IR-SIM window)
python test_irsim_with_agent.py irsim_worlds/world_hard.yaml
```

---

## Key Takeaways

1. **LLM code generation needs semantic validation, not just syntax checks.** The local small model (qwen3:8b) compiles syntactically valid code that is semantically wrong (`front_blocked → STOP`). Adding behavior tests to `validate_develope()` catches this. The fallback pattern — LLM generates, validation tests, known-good code replaces on failure — keeps the Agent→LLM chain while guaranteeing correctness.
2. **There are two developer_agent.py files.** The root-level version and the `agents/` subdirectory version are different files. `test_developer.py` imports from `agents/developer_agent.py`. Tracking down the file-override issue took significant time.
3. **"Always FORWARD while front is clear" is more efficient than "turn on detected obstacles".** Side obstacles are not necessarily in the robot's path; premature turning caused oscillation and accounted for a 23% efficiency loss.
4. **The only correct semantics for STOP is "all three directions blocked".** That line in the brief — *"If there is no safe direction available, it must stop"* — is worth rereading repeatedly.
