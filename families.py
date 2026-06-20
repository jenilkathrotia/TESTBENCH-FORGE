"""Task families + datasets for RewardForge.

Each *family* is a class of underlying tasks (count a letter, sum a list, ...).
The agent writes ONE `reward(prompt, completion)` verifier for a family and is scored
on a HIDDEN bank of held-out instances it never saw. Because the hidden prompts differ
from the public ones, the agent cannot hardcode answers — its verifier must actually
parse the prompt, recompute the correct answer, and compare.

GRADING SPEC (told to the agent): a completion is CORRECT iff `completion.strip()`
exactly equals the task's correct answer. Whitespace is fine; any extra text, wrong
value, or empty string is INCORRECT.

Adversarial negatives are the whole ballgame — weak negatives = saturated accuracy =
unimpressive RFT lift. Each instance ships:
  positives: exact gold, gold+newline, gold+surrounding-spaces
  negatives: "", an off-by-one / char-swapped near-miss, another instance's gold,
             and a "The answer is <gold>." decoy (contains the right value + extra text).

Determinism matters: seeds are derived with hashlib (NOT builtin hash(), which is
salted per process), so the baseline run and the post-RFT run are scored against the
EXACT same bank.
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
import re
from dataclasses import dataclass
from typing import Callable

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _stable_seed(s: str) -> int:
    return int(hashlib.sha256(s.encode()).hexdigest(), 16) % (2**31)


def extract_code(text: str) -> str:
    """Pull Python out of the agent's final answer (fenced block, else raw text)."""
    blocks = re.findall(r"```(?:python)?\s*(.*?)```", text, re.S)
    if blocks:
        return max(blocks, key=len).strip()
    return text.strip()


def _alter_num(gold: str, rng: random.Random) -> str:
    try:
        return str(int(gold) + rng.choice([-1, 1, 2]))
    except Exception:
        return gold + "x"


def _alter_str(gold: str, rng: random.Random) -> str:
    if len(gold) >= 2:
        i = rng.randrange(len(gold) - 1)
        lst = list(gold)
        lst[i], lst[i + 1] = lst[i + 1], lst[i]
        out = "".join(lst)
        return out if out != gold else gold + "x"
    return gold + "x"


# ---------------------------------------------------------------------------
# family definition + generators
# ---------------------------------------------------------------------------

@dataclass
class Family:
    id: str
    title: str
    description: str
    fmt: str
    gen: Callable[[random.Random], tuple[str, str]]      # rng -> (prompt, gold)
    alter: Callable[[str, random.Random], str]           # gold -> near-miss wrong string


_WORDS = [
    "strawberry", "banana", "mississippi", "programming", "helloworld",
    "avocado", "tennessee", "balloon", "committee", "jealousy", "raspberry", "pineapple",
]
_LETTERS = "abcdefghijklmnopqrstuvwxyz"


def _g_count_letter(rng):
    w, ltr = rng.choice(_WORDS), rng.choice(_LETTERS)
    return (f"How many times does the letter '{ltr}' appear in the string '{w}'? "
            f"Answer with just the number.", str(w.count(ltr)))


def _g_sum(rng):
    nums = [rng.randint(1, 25) for _ in range(rng.randint(3, 5))]
    return (f"What is the sum of these numbers: {', '.join(map(str, nums))}? "
            f"Answer with just the number.", str(sum(nums)))


def _g_reverse(rng):
    w = rng.choice(_WORDS)
    return (f"Reverse the string '{w}'. Answer with just the reversed string.", w[::-1])


def _g_wordcount(rng):
    n = rng.randint(2, 6)
    sent = " ".join(rng.choice(_WORDS) for _ in range(n))
    return (f"How many words are in this sentence: '{sent}'? Answer with just the number.", str(n))


def _g_vowels(rng):
    w = rng.choice(_WORDS)
    return (f"How many vowels (a, e, i, o, u) are in the string '{w}'? "
            f"Answer with just the number.", str(sum(w.count(v) for v in "aeiou")))


def _g_max(rng):
    nums = [rng.randint(1, 99) for _ in range(rng.randint(3, 6))]
    return (f"What is the largest of these numbers: {', '.join(map(str, nums))}? "
            f"Answer with just the number.", str(max(nums)))


def _g_arith(rng):
    a, b = rng.randint(10, 99), rng.randint(10, 99)
    return (f"What is {a} + {b}? Answer with just the number.", str(a + b))


def _g_upper(rng):
    w = rng.choice(_WORDS)
    return (f"Convert the string '{w}' to uppercase. Answer with just the uppercase string.", w.upper())


FAMILIES: dict[str, Family] = {}


def _reg(f: Family):
    FAMILIES[f.id] = f


_reg(Family("count_letter", "Letter counting",
            "Count how many times a given letter appears in a string.",
            "How many times does the letter 'X' appear in the string 'WORD'? Answer with just the number.",
            _g_count_letter, _alter_num))
_reg(Family("sum_list", "Sum of integers",
            "Add up a list of integers.",
            "What is the sum of these numbers: a, b, c? Answer with just the number.",
            _g_sum, _alter_num))
_reg(Family("reverse_string", "String reversal",
            "Reverse a string character by character.",
            "Reverse the string 'WORD'. Answer with just the reversed string.",
            _g_reverse, _alter_str))
_reg(Family("word_count", "Word counting",
            "Count the words in a sentence.",
            "How many words are in this sentence: '...'? Answer with just the number.",
            _g_wordcount, _alter_num))
_reg(Family("count_vowels", "Vowel counting",
            "Count the vowels (a, e, i, o, u) in a string.",
            "How many vowels (a, e, i, o, u) are in the string 'WORD'? Answer with just the number.",
            _g_vowels, _alter_num))
_reg(Family("max_list", "Maximum of integers",
            "Find the largest integer in a list.",
            "What is the largest of these numbers: a, b, c? Answer with just the number.",
            _g_max, _alter_num))
_reg(Family("arithmetic", "Two-number addition",
            "Add two integers.",
            "What is A + B? Answer with just the number.",
            _g_arith, _alter_num))
_reg(Family("uppercase", "Uppercasing",
            "Convert a string to uppercase.",
            "Convert the string 'WORD' to uppercase. Answer with just the uppercase string.",
            _g_upper, _alter_str))


# ---------------------------------------------------------------------------
# dataset construction
# ---------------------------------------------------------------------------

def _instances(fam: Family, n: int, seed: int):
    rng = random.Random(seed)
    insts, seen, tries = [], set(), 0
    while len(insts) < n and tries < n * 40:
        tries += 1
        p, g = fam.gen(rng)
        if p in seen:
            continue
        seen.add(p)
        insts.append((p, g))
    return insts


def _bank_for_instances(fam: Family, insts):
    rng = random.Random(_stable_seed(fam.id + ":bank"))
    golds = [g for _, g in insts]
    bank = []
    for i, (p, g) in enumerate(insts):
        # "another instance's gold" — but guaranteed != this gold (numeric families
        # collide often, which would mislabel a correct answer as a negative).
        other = None
        for k in range(1, len(golds)):
            cand = golds[(i + k) % len(golds)]
            if cand.strip() != g.strip():
                other = cand
                break
        if other is None:
            other = g + "9"
        near = fam.alter(g, rng)
        if near == g:
            near = g + "_"
        # positives (strip-exact correct)
        bank.append((p, g, 1))
        bank.append((p, g + "\n", 1))
        bank.append((p, "  " + g + "  ", 1))
        # adversarial negatives
        bank.append((p, "", 0))
        bank.append((p, near, 0))            # off-by-one / char-swap near-miss
        bank.append((p, other, 0))           # plausible wrong (another instance's gold)
        bank.append((p, f"The answer is {g}.", 0))   # reward-hack: right value + extra text
    return bank


def get_examples(fam: Family, n_hidden: int = 12, n_public: int = 3):
    """Return (public_rows, hidden_bank). public_rows are shown in the prompt;
    hidden_bank is scored. The two share NO prompts."""
    hidden_insts = _instances(fam, n_hidden, _stable_seed(fam.id + ":hidden"))
    hidden_prompts = {p for p, _ in hidden_insts}

    rng = random.Random(_stable_seed(fam.id + ":public"))
    pub, seen, tries = [], set(), 0
    while len(pub) < n_public and tries < 400:
        tries += 1
        p, g = fam.gen(rng)
        if p in hidden_prompts or p in seen:
            continue
        seen.add(p)
        pub.append((p, g))

    pub_rows = []
    for p, g in pub:
        pub_rows.append((p, g, 1))
        pub_rows.append((p, f"The answer is {g}.", 0))

    return pub_rows, _bank_for_instances(fam, hidden_insts)


def get_hidden_bank(family_id: str):
    if family_id in FHIR_FAMILIES:
        return fhir_hidden_bank(family_id)
    _pub, bank = get_examples(FAMILIES[family_id])
    return bank


_VERIFIER_TEMPLATE = """You are RewardForge. Your job is to WRITE A VERIFIER: a Python function

    def reward(prompt: str, completion: str) -> float

that grades answers to the task family below. Return a float in [0, 1].

FAMILY: {title} — {description}
PROMPT FORMAT (every prompt in this family looks like this):
    {fmt}

GRADING SPEC: a completion is CORRECT (1.0) if and only if, after `.strip()`, it
EXACTLY equals the task's correct answer. Surrounding whitespace is allowed; ANY
extra text, a wrong value, or an empty string is INCORRECT (0.0).

You do NOT get the answer key. Your verifier will be scored on HELD-OUT prompts you
have not seen, by BALANCED ACCURACY over a hidden bank of correct + adversarial-wrong
completions (empty strings, off-by-one / altered near-misses, other prompts' answers,
and "The answer is <X>." decoys that contain the right value but extra text). So your
verifier must parse the prompt, recompute the correct answer itself, and compare exactly.

Public examples ([label] 1=correct, 0=incorrect):
{rows}

You may call the `test_verifier` tool to dry-run a draft on cases you invent before
answering. When ready, reply with ONLY the Python code for `reward` (a ```python block
is fine). Do not include explanation outside the code.
"""


def build_verifier_prompt(family_id: str) -> str:
    if family_id in FHIR_FAMILIES:
        return fhir_build_prompt(family_id)
    fam = FAMILIES[family_id]
    pub_rows, _bank = get_examples(fam)
    rows = "\n".join(f"  [{lbl}] prompt={p!r}  completion={c!r}" for (p, c, lbl) in pub_rows)
    return _VERIFIER_TEMPLATE.format(
        title=fam.title, description=fam.description, fmt=fam.fmt, rows=rows
    )


# ---------------------------------------------------------------------------
# OPTIONAL second task: SIA's "harness lever" as a verifiable RL task
# ---------------------------------------------------------------------------
# The agent rewrites a brittle base tool; reward = the base agent's held-out accuracy
# with the improvement applied. Fully deterministic — no LLM needed at score time.

_BASE_SOLVER = '''def solve(text):
    # brittle baseline: grab the token right after the literal "Total: "
    return text.split("Total: ")[1].split()[0]'''

_TOTAL_FORMATS = [
    "Subtotal: 5\nTax: 2\nTotal: {amt}\nThank you!",
    "items ...\nTotal:{amt}\n",
    "TOTAL:  {amt}  USD",
    "receipt\ntotal: ${amt}\n",
    "Grand Total: {amt}.00",
    "total : {amt}",
    "Order summary -- Total = {amt}",
]


def harness_bank(seed_label: str, n: int = 12):
    rng = random.Random(_stable_seed("extract_total:" + seed_label))
    rows = []
    for _ in range(n):
        amt = rng.randint(1, 9999)
        fmt = rng.choice(_TOTAL_FORMATS)
        rows.append((fmt.format(amt=amt), str(amt)))
    return rows


_HARNESS_TEMPLATE = """You are improving a TOOL used by a base agent — this is SIA's "harness lever"
expressed as a verifiable RL task (you change the scaffold, not the model weights).

TASK: write `solve(text: str) -> str` that extracts the integer TOTAL amount from a
receipt-like text and returns it as a string (digits only).

The current BASE tool is brittle and fails on most real formats:
{base}

You will be scored on HELD-OUT receipts with varied formatting (case differences,
missing spaces, '$', '.00' cents, '=' separators, etc.) by EXACT-MATCH accuracy after
`.strip()`. Maximize accuracy. Robust parsing (e.g. a case-insensitive regex for the
first integer following "total") beats string slicing.

Public examples:
{rows}

You may call the `test_solver` tool to dry-run drafts. Reply with ONLY the Python code
for `solve`.
"""


def build_harness_prompt(task_id: str = "extract_total") -> str:
    pub = harness_bank("public", n=4)
    rows = "\n".join(f"  text={t!r}  ->  correct={g!r}" for (t, g) in pub)
    return _HARNESS_TEMPLATE.format(base=_BASE_SOLVER, rows=rows)


# ===========================================================================
# FHIRForge — cross-field clinical-conformance verifiers  (the novel winner)
# ===========================================================================
# The agent authors reward(prompt, completion) that decides whether a candidate FHIR
# Observation resource is SEMANTICALLY valid — not merely well-formed JSON. The
# load-bearing rule is CROSS-FIELD: the LOINC code dictates the legal UCUM unit. A
# naive structural verifier (does the field exist?) waves through a body weight stored
# in mm[Hg]; only a verifier that checks the code<->unit relationship catches it.
#
# Validity is DECIDABLE over frozen finite tables, so a correct verifier provably hits
# balanced accuracy ~1.0 — there is NO open-ended synonym normalization in the grading
# path (that is what caps med-text graders at ~0.75 and breaks the clean demo ceiling).

SYSTEM_LOINC = "http://loinc.org"
SYSTEM_SNOMED = "http://snomed.info/sct"
SYSTEM_UCUM = "http://unitsofmeasure.org"

# Frozen LOINC code -> expected UCUM unit (the closed world the cross-field rule uses).
LOINC_UNIT = {
    "29463-7": "kg",       # Body weight
    "8302-2": "cm",        # Body height
    "39156-5": "kg/m2",    # Body mass index
    "8310-5": "Cel",       # Body temperature
    "8867-4": "/min",      # Heart rate
    "9279-1": "/min",      # Respiratory rate
    "8480-6": "mm[Hg]",    # Systolic blood pressure
    "8462-4": "mm[Hg]",    # Diastolic blood pressure
    "2339-0": "mg/dL",     # Glucose
    "2160-0": "mg/dL",     # Creatinine
    "2085-9": "mg/dL",     # HDL cholesterol
    "2089-1": "mg/dL",     # LDL cholesterol
    "718-7": "g/dL",       # Hemoglobin
    "777-3": "10*3/uL",    # Platelets
    "4548-4": "%",         # Hemoglobin A1c
}

# Frozen Observation.status value set (a closed subset).
FHIR_STATUS = {"final", "preliminary", "amended", "corrected", "registered"}

_REF_RE = re.compile(r"^Patient/\S+$")

_VITALS_CODES = ["29463-7", "8302-2", "39156-5", "8310-5", "8867-4", "9279-1", "8480-6", "8462-4"]
_LAB_CODES = ["2339-0", "2160-0", "2085-9", "2089-1", "718-7", "777-3", "4548-4"]

FHIR_FAMILIES: dict[str, dict] = {
    "fhir_observation_all": {"title": "FHIR Observation conformance (all codes)", "codes": list(LOINC_UNIT)},
    "fhir_observation_vitals": {"title": "FHIR Observation conformance (vital signs)", "codes": _VITALS_CODES},
    "fhir_observation_labs": {"title": "FHIR Observation conformance (lab results)", "codes": _LAB_CODES},
}


def fhir_canon(obj) -> str:
    """Canonical JSON so key order / whitespace carry no signal."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def fhir_is_valid(obj) -> bool:
    """Canonical conformance predicate — decidable over the frozen tables."""
    try:
        if obj.get("resourceType") != "Observation":
            return False
        if obj.get("status") not in FHIR_STATUS:
            return False
        coding = obj["code"]["coding"][0]
        if coding.get("system") != SYSTEM_LOINC:
            return False
        code = coding.get("code")
        if code not in LOINC_UNIT:
            return False
        vq = obj["valueQuantity"]
        val = vq.get("value")
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            return False
        if vq.get("unit") != LOINC_UNIT[code]:        # <-- the cross-field rule
            return False
        if not _REF_RE.match(obj.get("subject", {}).get("reference", "")):
            return False
        return True
    except Exception:
        return False


def _fhir_valid_resource(rng, codes):
    code = rng.choice(codes)
    return {
        "resourceType": "Observation",
        "status": rng.choice(sorted(FHIR_STATUS)),
        "code": {"coding": [{"system": SYSTEM_LOINC, "code": code, "display": "measurement"}]},
        "valueQuantity": {"value": round(rng.uniform(1.0, 200.0), 1),
                          "unit": LOINC_UNIT[code], "system": SYSTEM_UCUM},
        "subject": {"reference": f"Patient/{rng.randint(1000, 9999)}"},
    }


# Each mutator applies ONE surgical, invalidating edit -> a guaranteed true-FAIL.
def _fm_unit_mismatch(o, rng):
    good = LOINC_UNIT[o["code"]["coding"][0]["code"]]
    o["valueQuantity"]["unit"] = rng.choice([u for u in set(LOINC_UNIT.values()) if u != good])
    return o

def _fm_bad_code(o, rng):
    o["code"]["coding"][0]["code"] = "99999-9"
    return o

def _fm_bad_status(o, rng):
    o["status"] = "complete"
    return o

def _fm_drop_status(o, rng):
    o.pop("status", None)
    return o

def _fm_str_value(o, rng):
    o["valueQuantity"]["value"] = str(o["valueQuantity"]["value"])
    return o

def _fm_dangling_ref(o, rng):
    o["subject"]["reference"] = "Patient/"
    return o

def _fm_wrong_system(o, rng):
    o["code"]["coding"][0]["system"] = SYSTEM_SNOMED
    return o

_FHIR_MUTATORS = [_fm_unit_mismatch, _fm_bad_code, _fm_bad_status, _fm_drop_status,
                  _fm_str_value, _fm_dangling_ref, _fm_wrong_system]


def _fhir_instances_bank(codes, seed_label, n_instances):
    rng = random.Random(_stable_seed("fhir:" + seed_label))
    bank = []
    for _ in range(n_instances):
        base = _fhir_valid_resource(rng, codes)
        # positives: valid resource + valid resource with an extra optional field
        bank.append((FHIR_SPEC, fhir_canon(base), 1))
        pos2 = copy.deepcopy(base)
        pos2["id"] = f"obs-{rng.randint(1, 999)}"
        bank.append((FHIR_SPEC, fhir_canon(pos2), 1))
        # negatives: one surgical invalidating mutation each
        for mut in _FHIR_MUTATORS:
            neg = mut(copy.deepcopy(base), rng)
            bank.append((FHIR_SPEC, fhir_canon(neg), 0))
    return bank


def fhir_hidden_bank(family_id: str):
    fam = FHIR_FAMILIES[family_id]
    return _fhir_instances_bank(fam["codes"], family_id + ":hidden", n_instances=10)


_FHIR_SPEC_TABLE = "\n".join(f"      {code} -> {unit}" for code, unit in LOINC_UNIT.items())

FHIR_SPEC = f"""A FHIR R4 'Observation' resource is CONFORMANT if and only if ALL of these hold:
  - resourceType == "Observation"
  - status is one of {sorted(FHIR_STATUS)}
  - code.coding[0].system == "{SYSTEM_LOINC}"
  - code.coding[0].code is one of the frozen LOINC codes in the table below
  - valueQuantity.value is a JSON number (NOT a string)
  - valueQuantity.unit EXACTLY equals the LOINC code's expected UCUM unit  (cross-field rule)
  - subject.reference matches the pattern  Patient/<id>
Frozen LOINC code -> expected UCUM unit:
{_FHIR_SPEC_TABLE}
Extra optional fields (e.g. 'id', 'display') are allowed and do NOT make a resource invalid."""


_FHIR_VERIFIER_TEMPLATE = """You are RewardForge. Write a Python function

    def reward(prompt: str, completion: str) -> float

that grades whether `completion` (a JSON string for a FHIR Observation resource) is
CONFORMANT. Return 1.0 if conformant, else 0.0.

{spec}

Your verifier is scored on HELD-OUT resources you have not seen, by BALANCED ACCURACY
over a hidden bank of conformant resources vs adversarially-mutated ones (wrong unit for
the code, code not in the set, status out of set / missing, value given as a string,
dangling Patient reference, wrong coding system). The single most important and
most-missed check is the CROSS-FIELD one: the unit must match the code's expected unit —
a body weight (29463-7) reported in mm[Hg] is structurally perfect but INVALID.

You must `json.loads(completion)` (return 0.0 if it does not parse) and implement the
predicate above. You may hardcode the frozen table from the spec.

Public examples ([label] 1=conformant, 0=not conformant):
{rows}

You may call the `test_verifier` tool to dry-run a draft on cases you invent. When ready,
reply with ONLY the Python code for `reward` (a ```python block is fine)."""


def fhir_build_prompt(family_id: str) -> str:
    fam = FHIR_FAMILIES[family_id]
    pub = _fhir_instances_bank(fam["codes"], family_id + ":public", n_instances=2)
    shown = pub[:2] + pub[2:5]   # 2 positives + 3 varied negatives
    rows = "\n".join(f"  [{lbl}] {comp}" for (_p, comp, lbl) in shown)
    return _FHIR_VERIFIER_TEMPLATE.format(spec=FHIR_SPEC, rows=rows)
