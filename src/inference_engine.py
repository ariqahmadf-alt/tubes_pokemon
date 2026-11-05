"""Forward-chaining inference for the battle KB's FOL Horn rules."""

from dataclasses import dataclass

from knowledge_base import Atom


@dataclass(frozen=True)
class Derivation:
    rule_id: str
    substitution: tuple[tuple[str, str], ...]
    conclusion: Atom


@dataclass
class InferenceResult:
    initial_facts: tuple[Atom, ...]
    facts: frozenset[Atom]
    evaluations: tuple[dict, ...]
    derivations: tuple[Derivation, ...]

    def ask(self, query):
        if query in self.facts:
            return "entailed"
        opposite = Atom(query.predicate, query.arguments, not query.negated)
        if opposite in self.facts:
            return "contradicted"
        return "unknown"


def _is_variable(term):
    return term.startswith("?")


def _unify(pattern, fact, substitution):
    if (
        pattern.predicate != fact.predicate
        or pattern.negated != fact.negated
        or len(pattern.arguments) != len(fact.arguments)
    ):
        return None

    result = dict(substitution)
    for expected, actual in zip(pattern.arguments, fact.arguments):
        if _is_variable(expected):
            bound = result.get(expected)
            if bound is not None and bound != actual:
                return None
            result[expected] = actual
        elif expected != actual:
            return None
    return result


def _instantiate(atom, substitution):
    arguments = tuple(
        substitution.get(argument, argument) for argument in atom.arguments
    )
    return Atom(atom.predicate, arguments, atom.negated)


class InferenceEngine:
    """Evaluates declared rules by FOL matching until no new facts are derived."""

    def infer(self, knowledge_base):
        initial_facts = tuple(sorted(knowledge_base.facts))
        known = set(initial_facts)
        evaluations = []
        derivations = []
        iteration = 0

        while True:
            iteration += 1
            derived_this_round = []

            for rule in knowledge_base.rules:
                bindings = [({}, ())]
                condition_traces = []

                for condition in rule.conditions:
                    next_bindings = []
                    condition_matches = []
                    contradictions = []
                    for substitution, matched_facts in bindings:
                        matches = []
                        for fact in sorted(known):
                            unified = _unify(condition, fact, substitution)
                            if unified is not None:
                                matches.append((unified, fact))
                        condition_matches.extend(
                            str(fact) for _, fact in matches
                        )
                        if not matches:
                            grounded_condition = _instantiate(
                                condition, substitution
                            )
                            opposite = Atom(
                                grounded_condition.predicate,
                                grounded_condition.arguments,
                                not grounded_condition.negated,
                            )
                            if opposite in known:
                                contradictions.append(str(opposite))
                        next_bindings.extend(
                            (unified, matched_facts + (fact,))
                            for unified, fact in matches
                        )

                    if next_bindings:
                        condition_status = "entailed"
                    elif contradictions and len(contradictions) == len(bindings):
                        condition_status = "contradicted"
                    elif contradictions:
                        condition_status = "partially contradicted"
                    else:
                        condition_status = "unknown"

                    condition_traces.append(
                        {
                            "condition": condition,
                            "matched": bool(next_bindings),
                            "status": condition_status,
                            "matches": tuple(dict.fromkeys(condition_matches)),
                            "contradictions": tuple(dict.fromkeys(contradictions)),
                        }
                    )
                    bindings = next_bindings
                    if not bindings:
                        break

                rule_derivations = []
                for substitution, _ in bindings:
                    conclusion = _instantiate(rule.conclusion, substitution)
                    if conclusion in known:
                        continue
                    known.add(conclusion)
                    derivation = Derivation(
                        rule_id=rule.rule_id,
                        substitution=tuple(sorted(substitution.items())),
                        conclusion=conclusion,
                    )
                    derivations.append(derivation)
                    derived_this_round.append(derivation)
                    rule_derivations.append(derivation)

                evaluations.append(
                    {
                        "iteration": iteration,
                        "rule_id": rule.rule_id,
                        "description": rule.description,
                        "matched": bool(bindings),
                        "conditions": tuple(condition_traces),
                        "substitutions": tuple(
                            tuple(sorted(substitution.items()))
                            for substitution, _ in bindings
                        ),
                        "derived": tuple(rule_derivations),
                    }
                )

            if not derived_this_round:
                break

        return InferenceResult(
            initial_facts=initial_facts,
            facts=frozenset(known),
            evaluations=tuple(evaluations),
            derivations=tuple(derivations),
        )
