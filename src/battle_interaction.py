"""Validates action intents inferred for the two opposing NPCs."""

from dataclasses import dataclass

@dataclass(frozen=True)
class ActionHint:
    actor: str
    target: str
    action: str
    rule_id: str


class BattleInteractionHandler:
    def hints_from(self, inference_result):
        hints = []
        seen = set()
        for derivation in inference_result.derivations:
            conclusion = derivation.conclusion
            if conclusion.predicate != "ActionIntent" or conclusion.negated:
                continue
            if len(conclusion.arguments) != 3:
                continue
            hint = ActionHint(
                actor=conclusion.arguments[0],
                target=conclusion.arguments[1],
                action=conclusion.arguments[2].upper(),
                rule_id=derivation.rule_id,
            )
            if hint not in seen:
                seen.add(hint)
                hints.append(hint)
        return tuple(hints)

    def validate(self, hint, actor, target, move_name, available_move_names):
        if hint.actor != actor or hint.target != target:
            return False, "The inferred actor or target no longer matches the battle state."
        if move_name.upper() != hint.action:
            return False, "The selected action does not match the inferred action intent."
        if move_name.upper() not in {name.upper() for name in available_move_names}:
            return False, "The inferred action is no longer available."
        return True, "The inferred interaction is valid for this battle state."

    @staticmethod
    def matching_hints(hints, actor, target, move_name):
        return tuple(
            hint
            for hint in hints
            if hint.actor == actor
            and hint.target == target
            and hint.action == move_name.upper()
        )
