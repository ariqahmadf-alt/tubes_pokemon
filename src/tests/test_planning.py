import unittest

from planning import (
    Action,
    ActionSchema,
    applicable,
    forward_search,
    ground_actions,
    ignore_delete_lists_heuristic,
    planning_graph,
    regression_search,
    result,
    validate_plan,
)


def ojek_problem():
    initial = frozenset(
        {
            ("motor-at", "rumah"),
            ("passenger-at", "rumah"),
            ("gate-closed",),
        }
    )
    schemas = (
        ActionSchema(
            "open-gate",
            (),
            (("gate-closed",),),
            (("gate-open",),),
            (("gate-closed",),),
        ),
        ActionSchema(
            "pickup",
            (),
            (("motor-at", "warung"), ("passenger-at", "warung")),
            (("carrying",),),
            (("passenger-at", "warung"),),
        ),
        ActionSchema(
            "drive",
            (("?from", "place"), ("?to", "place")),
            (
                ("motor-at", "?from"),
            ),
            (
                ("motor-at", "?to"),
                ("passenger-at", "?to"),
                ("passenger-at", "?from"),
            ),
            (
                ("motor-at", "?from"),
                ("passenger-at", "?from"),
            ),
        ),
        ActionSchema(
            "drop",
            (),
            (("motor-at", "warung"), ("carrying",), ("gate-open",)),
            (("delivered",),),
            (("carrying",),),
        ),
    )
    actions = ground_actions(
        schemas,
        {"place": ("rumah", "warung")},
        initial,
    )
    return initial, frozenset({("delivered",)}), actions


class PlanningCoreTests(unittest.TestCase):
    def test_applicable_and_result_match_strips_transition(self):
        state = frozenset({("motor-at", "rumah"), ("gate-open",)})
        drive = Action(
            "drive",
            ("rumah", "warung"),
            (("motor-at", "rumah"), ("gate-open",)),
            (("motor-at", "warung"),),
            (("motor-at", "rumah"),),
        )
        self.assertTrue(applicable(state, drive))
        self.assertEqual(
            result(state, drive),
            frozenset({("gate-open",), ("motor-at", "warung")}),
        )

    def test_validate_plan_reports_missing_precondition(self):
        initial, goal, actions = ojek_problem()
        invalid = (
            next(action for action in actions if action.name == "pickup"),
        )
        states, report = validate_plan(initial, invalid)
        self.assertEqual(len(states), 1)
        self.assertFalse(report["valid"])
        self.assertIn(("motor-at", "warung"), report["missing"])

    def test_forward_and_backward_search_find_four_step_plan(self):
        initial, goal, actions = ojek_problem()
        forward = forward_search(
            initial, goal, actions, method="bfs", time_budget_ms=500
        )
        backward = regression_search(
            initial, goal, actions, time_budget_ms=500
        )
        self.assertEqual(forward.status, "plan", forward.reason)
        self.assertEqual(backward.status, "plan", backward.reason)
        self.assertEqual(len(forward.steps), 4)
        self.assertEqual(len(backward.steps), 4)
        self.assertTrue(backward.regression_goal.issubset(initial))
        self.assertTrue(
            any(
                step.action.name == "drive"
                and step.action.arguments == ("rumah", "warung")
                for step in forward.steps
            )
        )
        self.assertTrue(goal.issubset(forward.steps[-1].state))

    def test_admissible_relaxed_heuristic_does_not_exceed_bfs_length(self):
        initial, goal, actions = ojek_problem()
        plan = forward_search(
            initial, goal, actions, method="bfs", time_budget_ms=500
        )
        heuristic = ignore_delete_lists_heuristic(initial, goal, actions)
        self.assertLessEqual(heuristic, len(plan.steps))

    def test_astar_graph_bound_respects_fractional_action_costs(self):
        initial = frozenset({("start",)})
        goal = frozenset({("done",)})
        action = Action(
            "finish",
            (),
            (("start",),),
            (("done",),),
            (),
            cost=0.25,
        )

        result = forward_search(
            initial,
            goal,
            (action,),
            time_budget_ms=500,
        )

        self.assertEqual(result.status, "plan")
        self.assertEqual(result.total_cost, 0.25)
        self.assertLessEqual(result.initial_heuristic, result.total_cost)

    def test_search_rejects_negative_action_costs(self):
        initial = frozenset({("start",)})
        action = Action(
            "invalid",
            (),
            (("start",),),
            (("done",),),
            (),
            cost=-1,
        )

        with self.assertRaisesRegex(ValueError, "finite and non-negative"):
            forward_search(
                initial,
                frozenset({("done",)}),
                (action,),
                time_budget_ms=500,
            )

    def test_planning_graph_marks_drive_mutex_with_noop_at_origin(self):
        initial, goal, actions = ojek_problem()
        graph = planning_graph(initial, goal, actions)
        self.assertFalse(graph.unreachable)
        drive = next(
            action
            for action in actions
            if action.name == "drive"
            and action.arguments == ("rumah", "warung")
        )
        origin_noop = next(
            action
            for mutex_pair in graph.action_mutexes[0]
            for action in mutex_pair
            if action.name == "no-op"
            and action.arguments == ("motor-at", "rumah")
        )
        self.assertIn(frozenset({drive, origin_noop}), graph.action_mutexes[0])
        passenger_noop = next(
            action
            for mutex_pair in graph.action_mutexes[0]
            for action in mutex_pair
            if action.name == "no-op"
            and action.arguments == ("passenger-at", "rumah")
        )
        self.assertNotIn(
            frozenset({origin_noop, passenger_noop}),
            graph.action_mutexes[0],
        )

    def test_static_preconditions_prune_ground_actions(self):
        schema = ActionSchema(
            "attack",
            (("?actor", "pokemon"), ("?target", "pokemon")),
            (("advantage", "?actor", "?target"),),
            (("hit", "?target"),),
            (),
        )
        actions = ground_actions(
            (schema,),
            {"pokemon": ("a", "b")},
            frozenset({("advantage", "a", "b")}),
            static_predicates=("advantage",),
        )
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].arguments, ("a", "b"))

    def test_static_predicates_cannot_be_modified_by_action_schemas(self):
        schema = ActionSchema(
            "change-owner",
            (),
            (),
            (("owner", "a", "b"),),
            (),
        )

        with self.assertRaisesRegex(ValueError, "cannot modify static"):
            ground_actions(
                (schema,),
                {},
                frozenset(),
                static_predicates=("owner",),
            )

    def test_expansion_cap_returns_limit_status(self):
        initial, goal, actions = ojek_problem()
        result = forward_search(
            initial,
            goal,
            actions,
            max_expansions=0,
            time_budget_ms=500,
        )
        self.assertEqual(result.status, "limit")
        self.assertIn("expansions", result.reason)

    def test_plan_is_deterministic(self):
        initial, goal, actions = ojek_problem()
        first = forward_search(initial, goal, actions, time_budget_ms=500)
        second = forward_search(initial, goal, actions, time_budget_ms=500)
        self.assertEqual(
            [str(step.action) for step in first.steps],
            [str(step.action) for step in second.steps],
        )


if __name__ == "__main__":
    unittest.main()
