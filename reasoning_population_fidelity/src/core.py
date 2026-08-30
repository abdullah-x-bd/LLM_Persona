from __future__ import annotations
import hashlib, json, math
from pathlib import Path
from typing import Any

OUTCOMES = [
    "mobile_ability","mobile_3m","computer_ability",
    "internet_ability","internet_3m","copy_paste"
]
QUESTION_TEXT = {
    "mobile_ability":"Are you able to use a mobile telephone, either a smartphone or another type of mobile telephone?",
    "mobile_3m":"During the last three months, have you used any mobile telephone with an active SIM card for making personal calls and/or accessing the internet?",
    "computer_ability":"Are you able to use a desktop computer, laptop, tablet, palmtop, notebook, or similar computer device?",
    "internet_ability":"Are you able to use the internet through a mobile telephone, smartphone, desktop computer, laptop, tablet, palmtop, notebook, or similar device for any purpose?",
    "internet_3m":"Have you used the internet at least once during the last three months?",
    "copy_paste":"During the last three months, have you used copy-and-paste tools to duplicate or move data, information, or documents using a smartphone or computer-like device?"
}
FORBIDDEN_PERSONA_TERMS = [
    "internet","smartphone","mobile phone","mobile telephone","computer",
    "laptop","tablet","email","digital payment","copy-and-paste",
    "copy and paste","bank account","banking"
]
ALLOWED_REASONING = {"none","low","high"}

def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=False)

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def request_id(row: dict) -> str:
    payload = {
        "anon_id":row["anon_id"],
        "reasoning":row["reasoning"],
        "reasoning_settings":row.get("reasoning_settings"),
        "generation_settings":row.get("generation_settings"),
        "prompt_sha256":sha256_text(row["prompt"]),
        "schema_sha256":row["schema_sha256"],
        "model":row["model"]
    }
    return sha256_text(canonical_json(payload))

def build_prompt(persona: str) -> str:
    questions = "\n".join(f"{i+1}. {QUESTION_TEXT[k]}" for i,k in enumerate(OUTCOMES))
    return (
        "You are completing a short survey as one specific person. "
        "Treat the profile below as the only known facts about that person. "
        "Do not answer as an average Indian, do not retrieve or reproduce survey statistics, "
        "and do not add facts that are not in the profile. Give the response that this particular "
        "person would most plausibly give. Do not explain your reasoning.\n\n"
        "PERSON PROFILE\n"+persona+
        "\n\nFor every question return (a) answer, exactly 'yes' or 'no', and "
        "(b) probability_yes, a number from 0 to 1 representing your uncertainty that this "
        "specific respondent would answer yes.\n\nQUESTIONS\n"+questions+"\n"
    )

def validate_persona(persona: str) -> None:
    if not isinstance(persona,str) or len(persona)<20:
        raise AssertionError("Persona is missing or too short")
    low = persona.lower()
    hits = [x for x in FORBIDDEN_PERSONA_TERMS if x in low]
    if hits:
        raise AssertionError(f"Outcome leakage terms in persona: {hits}")

def validate_response(obj: Any, outcomes=OUTCOMES) -> dict:
    if not isinstance(obj,dict) or set(obj) != set(outcomes):
        raise ValueError("Response has wrong top-level keys")
    for key in outcomes:
        val = obj[key]
        if not isinstance(val,dict) or set(val) != {"answer","probability_yes"}:
            raise ValueError(f"Malformed outcome object: {key}")
        if val["answer"] not in {"yes","no"}:
            raise ValueError(f"Invalid answer for {key}")
        p = val["probability_yes"]
        if isinstance(p,bool) or not isinstance(p,(int,float)) or not 0 <= float(p) <= 1:
            raise ValueError(f"Invalid probability for {key}")
    return obj

def deterministic_mock(row: dict) -> dict:
    condition_shift = {"none":-0.03,"low":0.0,"high":0.03}[row["reasoning"]]
    out = {}
    for k in OUTCOMES:
        raw = int.from_bytes(hashlib.sha256(
            f"{row['anon_id']}|{k}".encode()
        ).digest()[:4],"big") / 2**32
        p = min(0.995,max(0.005, raw + condition_shift))
        out[k] = {"answer":"yes" if p >= 0.5 else "no","probability_yes":round(p,6)}
    return validate_response(out)

def approx_tokens(text: str) -> int:
    return max(1, math.ceil(len(text)/3.2))

def load_jsonl(path: str | Path) -> list[dict]:
    p = Path(path)
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]

def write_jsonl(path: str | Path, rows: list[dict]) -> None:
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in rows),encoding="utf-8")
