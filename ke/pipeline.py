"""The three phases: understand -> check for conflicts -> commit."""

from . import config, db, embed, llm

VERDICTS_NEEDING_A_DECISION = {"conflict", "duplicate", "refines"}

DECISIONS = {
    "keep_new",   # the new claim wins; the existing one is superseded
    "keep_old",   # discard the new claim
    "keep_both",  # both stay live (they are compatible after all)
    "merge",      # commit an edited statement and supersede the existing one
}


def understand(raw_text: str, author: str | None, source: str | None) -> str:
    """Phase 1. Turn a brain-dump into claims and open a review session."""
    atoms = llm.extract_atoms(raw_text)
    for index, atom in enumerate(atoms):
        atom["id"] = f"a{index}"
    return db.create_session(
        {
            "raw_text": raw_text,
            "author": author,
            "source": source,
            "atoms": atoms,
            "conflicts": [],
            "committed": [],
        }
    )


def find_conflicts(atoms: list[dict]) -> list[dict]:
    """Phase 2. For each claim, retrieve neighbours and ask the model how they relate."""
    conflicts = []
    vectors = embed.embed([a["statement"] for a in atoms])
    for atom, vector in zip(atoms, vectors):
        candidates = db.neighbours(
            vector, config.CONFLICT_TOP_K, config.CONFLICT_MAX_DISTANCE
        )
        if not candidates:
            continue
        verdicts = llm.compare(atom, candidates)
        for candidate in candidates:
            verdict = verdicts.get(candidate["id"])
            if verdict and verdict["verdict"] in VERDICTS_NEEDING_A_DECISION:
                conflicts.append(
                    {
                        "key": f"{atom['id']}::{candidate['id']}",
                        "atom_id": atom["id"],
                        "existing_id": candidate["id"],
                        "existing_title": candidate["title"],
                        "existing_statement": candidate["statement"],
                        "distance": round(float(candidate["distance"]), 4),
                        "verdict": verdict["verdict"],
                        "reason": verdict["reason"],
                    }
                )
    return conflicts


def plan(atoms: list[dict], conflicts: list[dict], decisions: dict[str, dict]) -> list[dict]:
    """Pure. Work out what to write, given the user's decisions.

    Returns one action per atom: {"atom", "statement", "supersedes": [ids]} for
    atoms to insert, or {"atom", "skipped": reason} for atoms to drop.
    """
    by_atom: dict[str, list[dict]] = {}
    for conflict in conflicts:
        by_atom.setdefault(conflict["atom_id"], []).append(conflict)

    actions = []
    for atom in atoms:
        pairs = by_atom.get(atom["id"], [])
        if not pairs:
            actions.append({"atom": atom, "statement": atom["statement"], "supersedes": []})
            continue

        chosen = [(p, decisions.get(p["key"], {})) for p in pairs]
        for _, decision in chosen:
            if decision.get("action") not in DECISIONS:
                raise ValueError(f"missing or invalid decision for atom {atom['id']}")

        if all(d["action"] == "keep_old" for _, d in chosen):
            actions.append({"atom": atom, "skipped": "keep_old"})
            continue

        statement = next(
            (
                d["statement"].strip()
                for _, d in chosen
                if d["action"] == "merge" and d.get("statement", "").strip()
            ),
            atom["statement"],
        )
        supersedes = [
            pair["existing_id"]
            for pair, decision in chosen
            if decision["action"] in ("keep_new", "merge")
        ]
        actions.append({"atom": atom, "statement": statement, "supersedes": supersedes})
    return actions


def commit(actions: list[dict], author: str | None, source: str | None) -> list[dict]:
    """Phase 3. Write the accepted claims and supersede what they replace."""
    to_insert = [a for a in actions if "statement" in a]
    vectors = embed.embed([a["statement"] for a in to_insert])

    committed = []
    for action, vector in zip(to_insert, vectors):
        atom = dict(action["atom"], statement=action["statement"])
        new_id = db.insert(atom, vector, author, source)
        for old_id in action["supersedes"]:
            db.supersede(old_id, new_id)
        committed.append(
            {
                "id": new_id,
                "title": atom["title"],
                "statement": atom["statement"],
                "superseded": action["supersedes"],
            }
        )
    return committed
