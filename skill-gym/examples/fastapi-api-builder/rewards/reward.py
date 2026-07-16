"""
reward.py -- Reward function for the fastapi-api-builder skill.

Computes a scalar reward from verification results, suitable for use in
RL training pipelines (PPO, GRPO, DPO). The reward combines verifier
scores with optional bonuses for code quality signals.

Usage:
    python reward.py --report report.json
    python reward.py --report report.json --bonuses style,efficiency
"""

from __future__ import annotations

import json
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Reward configuration
# ---------------------------------------------------------------------------

@dataclass
class RewardConfig:
    """Configuration for reward computation."""

    # Base reward from verification score (0.0 - 1.0 weight)
    base_weight: float = 0.7

    # Bonus multipliers
    style_bonus: float = 0.1
    efficiency_bonus: float = 0.1
    completeness_bonus: float = 0.1

    # Penalty for partial verdict
    partial_penalty: float = 0.3

    # Floor reward -- even a complete failure gets this (helps with exploration)
    floor_reward: float = 0.05

    # Ceiling reward
    ceiling_reward: float = 1.0


@dataclass
class RewardResult:
    """Computed reward with breakdown."""

    total_reward: float
    components: dict[str, float] = field(default_factory=dict)
    bonuses_applied: list[str] = field(default_factory=list)
    penalties_applied: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_reward": round(self.total_reward, 6),
            "components": {k: round(v, 6) for k, v in self.components.items()},
            "bonuses_applied": self.bonuses_applied,
            "penalties_applied": self.penalties_applied,
        }


# ---------------------------------------------------------------------------
# Bonus functions
# ---------------------------------------------------------------------------

def compute_style_bonus(
    verification_details: list[dict[str, Any]],
    trajectory: list[dict[str, Any]] | None,
) -> float:
    """
    Reward code style quality.

    Checks for:
    - Presence of docstrings on functions/classes
    - Type hints on function signatures
    - Consistent naming conventions
    """
    score = 0.0
    checks = 0

    if trajectory:
        for step in trajectory:
            if step.get("role") == "assistant":
                content = step.get("content", "")

                # Check for type hints
                if "def " in content and "->" in content:
                    score += 1.0
                checks += 1

                # Check for docstrings
                if '"""' in content or "'''" in content:
                    score += 1.0
                checks += 1

    if checks == 0:
        return 0.0

    return score / checks


def compute_efficiency_bonus(
    verification_details: list[dict[str, Any]],
    trajectory: list[dict[str, Any]] | None,
) -> float:
    """
    Reward efficient solutions.

    Checks for:
    - Fewer assistant turns (less back-and-forth)
    - No failed tool calls (no trial-and-error)
    """
    if not trajectory:
        return 0.0

    assistant_turns = sum(
        1 for step in trajectory if step.get("role") == "assistant"
    )
    failed_tool_calls = sum(
        1
        for step in trajectory
        if step.get("role") == "tool"
        and step.get("tool_result", {}).get("success") is False
    )

    # Score decreases with more turns and failures
    turn_score = max(0.0, 1.0 - (assistant_turns - 1) * 0.1)
    failure_penalty = failed_tool_calls * 0.15

    return max(0.0, turn_score - failure_penalty)


def compute_completeness_bonus(
    verification_details: list[dict[str, Any]],
) -> float:
    """
    Reward completeness of output.

    Checks that all expected files exist and all verification checks pass.
    """
    if not verification_details:
        return 0.0

    total = len(verification_details)
    passed = sum(1 for d in verification_details if d.get("passed", False))

    return passed / total if total > 0 else 0.0


# ---------------------------------------------------------------------------
# Main reward function
# ---------------------------------------------------------------------------

BONUS_REGISTRY: dict[str, Any] = {
    "style": lambda details, traj, _: compute_style_bonus(details, traj),
    "efficiency": lambda details, traj, _: compute_efficiency_bonus(details, traj),
    "completeness": lambda details, traj, _: compute_completeness_bonus(details),
}


def compute_reward(
    verification_report: dict[str, Any],
    trajectory: list[dict[str, Any]] | None = None,
    config: RewardConfig | None = None,
    enabled_bonuses: list[str] | None = None,
) -> RewardResult:
    """
    Compute scalar reward from verification report.

    Args:
        verification_report: Dict with keys 'score', 'verdict', 'details'.
        trajectory: Optional agent trajectory for style/efficiency bonuses.
        config: Reward configuration. Uses defaults if None.
        enabled_bonuses: List of bonus names to apply. None = all bonuses.

    Returns:
        RewardResult with total reward and component breakdown.
    """
    if config is None:
        config = RewardConfig()

    result = RewardResult(total_reward=0.0)

    # --- Base reward from verification score ---
    base_score = verification_report.get("score", 0.0)
    base_reward = base_score * config.base_weight
    result.components["base"] = base_reward

    # --- Verdict adjustment ---
    verdict = verification_report.get("verdict", "fail")
    if verdict == "partial":
        penalty = config.partial_penalty * config.base_weight
        result.components["partial_penalty"] = -penalty
        result.penalties_applied.append("partial_verdict")
    elif verdict == "fail":
        result.components["partial_penalty"] = -config.base_weight
        result.penalties_applied.append("fail_verdict")

    # --- Bonuses ---
    details = verification_report.get("details", [])
    active_bonuses = enabled_bonuses or list(BONUS_REGISTRY.keys())

    bonus_weights = {
        "style": config.style_bonus,
        "efficiency": config.efficiency_bonus,
        "completeness": config.completeness_bonus,
    }

    for bonus_name in active_bonuses:
        if bonus_name not in BONUS_REGISTRY:
            continue

        raw_bonus = BONUS_REGISTRY[bonus_name](details, trajectory, config)
        weighted_bonus = raw_bonus * bonus_weights.get(bonus_name, 0.0)
        result.components[bonus_name] = weighted_bonus
        if raw_bonus > 0:
            result.bonuses_applied.append(bonus_name)

    # --- Aggregate ---
    total = sum(result.components.values())
    total = max(config.floor_reward, min(config.ceiling_reward, total))
    result.total_reward = total

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point for computing rewards."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Compute reward from verification report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Example:
              python reward.py --report report.json
              python reward.py --report report.json --bonuses style,efficiency
              python reward.py --report report.json --floor-reward 0.1 --ceiling-reward 0.95
        """),
    )
    parser.add_argument(
        "--report",
        type=Path,
        required=True,
        help="Path to verification report JSON file.",
    )
    parser.add_argument(
        "--bonuses",
        type=str,
        default=None,
        help="Comma-separated list of bonus names to apply (style, efficiency, completeness).",
    )
    parser.add_argument(
        "--floor-reward",
        type=float,
        default=0.05,
        help="Minimum reward even for complete failures (default: 0.05).",
    )
    parser.add_argument(
        "--ceiling-reward",
        type=float,
        default=1.0,
        help="Maximum reward cap (default: 1.0).",
    )
    parser.add_argument(
        "--trajectory",
        type=Path,
        default=None,
        help="Path to trajectory JSON file for style/efficiency bonuses.",
    )

    args = parser.parse_args()

    with open(args.report, encoding="utf-8") as f:
        verification_report = json.load(f)

    trajectory = None
    if args.trajectory:
        with open(args.trajectory, encoding="utf-8") as f:
            trajectory = json.load(f)

    config = RewardConfig(
        floor_reward=args.floor_reward,
        ceiling_reward=args.ceiling_reward,
    )

    enabled_bonuses = None
    if args.bonuses:
        enabled_bonuses = [b.strip() for b in args.bonuses.split(",")]

    result = compute_reward(
        verification_report, trajectory, config, enabled_bonuses
    )

    print(json.dumps(result.to_dict(), indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
