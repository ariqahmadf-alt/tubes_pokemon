"""Declarative FOL facts and rules for the two-NPC battle."""

import json
from dataclasses import dataclass
from pathlib import Path


KNOWLEDGE_DIRECTORY = Path(__file__).parent / "assets" / "knowledge_base"


@dataclass(frozen=True, order=True)
class Atom:
    predicate: str
    arguments: tuple[str, ...]
    negated: bool = False

    def __str__(self):
        prefix = "NOT " if self.negated else ""
        return f"{prefix}{self.predicate}({', '.join(self.arguments)})"


@dataclass(frozen=True)
class Rule:
    rule_id: str
    description: str
    conditions: tuple[Atom, ...]
    conclusion: Atom


def _read_atom(data):
    predicate = data["predicate"]
    arguments = data.get("args", [])
    if not isinstance(predicate, str) or not predicate:
        raise ValueError("An atom must have a non-empty predicate.")
    if not all(isinstance(argument, str) and argument for argument in arguments):
        raise ValueError(f"Invalid arguments for predicate {predicate!r}.")
    return Atom(predicate, tuple(arguments), bool(data.get("negated", False)))


class KnowledgeBase:
    """Stores declarative facts separately from the inference procedure."""

    def __init__(self, facts=(), rules=()):
        self._base_facts = set(facts)
        self._facts = set(self._base_facts)
        self.rules = tuple(rules)

    @classmethod
    def from_json(cls, facts_path=None, rules_path=None):
        facts_path = Path(facts_path or KNOWLEDGE_DIRECTORY / "battle_facts.json")
        rules_path = Path(rules_path or KNOWLEDGE_DIRECTORY / "battle_rules.json")

        with facts_path.open(encoding="utf-8") as facts_file:
            facts_data = json.load(facts_file)
        with rules_path.open(encoding="utf-8") as rules_file:
            rules_data = json.load(rules_file)

        facts = tuple(_read_atom(fact) for fact in facts_data["facts"])
        rules = tuple(
            Rule(
                rule_id=rule["id"],
                description=rule["description"],
                conditions=tuple(_read_atom(atom) for atom in rule["conditions"]),
                conclusion=_read_atom(rule["conclusion"]),
            )
            for rule in rules_data["rules"]
        )
        return cls(facts, rules)

    @property
    def facts(self):
        return frozenset(self._facts)

    def tell(self, fact):
        if not isinstance(fact, Atom):
            raise TypeError("KnowledgeBase.tell expects an Atom.")
        self._facts.add(fact)

    def update_observations(self, facts):
        """Replace environment observations while preserving declarative facts."""
        self._facts = set(self._base_facts)
        for fact in facts:
            self.tell(fact)

    def ask(self, query, inferred_facts=()):
        """Return entailed, contradicted, or unknown without a closed-world guess."""
        known = self._facts.union(inferred_facts)
        if query in known:
            return "entailed"
        opposite = Atom(query.predicate, query.arguments, not query.negated)
        if opposite in known:
            return "contradicted"
        return "unknown"
