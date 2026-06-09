import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from rail_inspection_rl.env import RailInspectionEnv, RailInspectionTaskConfig, RulePolicyAdapter


def run_episode(seed: int, max_steps: int, config: Optional[RailInspectionTaskConfig] = None) -> Dict[str, Any]:
    env = RailInspectionEnv(config=config)
    obs, reset_info = env.reset(seed=seed)
    policy = RulePolicyAdapter()
    total_reward = 0.0
    last_info: Dict[str, Any] = {}
    terminated = False
    truncated = False
    steps = 0
    for steps in range(1, max_steps + 1):
        action = policy.compute_action(obs)
        obs, reward, terminated, truncated, last_info = env.step(action)
        total_reward += float(reward)
        if terminated or truncated:
            break
    progress = float(obs["mission_progress"][0])
    pose = np.asarray(obs["pose"], dtype=np.float32)
    return {
        "seed": seed,
        "steps": steps,
        "terminated": bool(terminated),
        "truncated": bool(truncated),
        "total_reward": round(total_reward, 6),
        "final_progress": round(progress, 6),
        "final_position": {
            "x": round(float(pose[0]), 4),
            "y": round(float(pose[1]), 4),
            "z": round(float(pose[2]), 4),
        },
        "reset_info": reset_info,
        "last_info": last_info,
    }


def summarize(episodes: List[Dict[str, Any]], config: RailInspectionTaskConfig) -> Dict[str, Any]:
    rewards = [float(item["total_reward"]) for item in episodes]
    progress = [float(item["final_progress"]) for item in episodes]
    success_count = sum(1 for item in episodes if item["terminated"])
    return {
        "env": "RailInspectionEnv",
        "policy": "RulePolicyAdapter",
        "config": asdict(config),
        "episodes": len(episodes),
        "success_count": success_count,
        "success_rate": round(success_count / max(1, len(episodes)), 6),
        "mean_total_reward": round(float(np.mean(rewards)) if rewards else 0.0, 6),
        "mean_final_progress": round(float(np.mean(progress)) if progress else 0.0, 6),
        "episode_results": episodes,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the baseline rule policy in the RL skeleton environment.")
    parser.add_argument("--episodes", type=int, default=3, help="Number of smoke episodes to run.")
    parser.add_argument("--max-steps", type=int, default=360, help="Maximum steps per episode.")
    parser.add_argument("--seed", type=int, default=7, help="Base random seed.")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = RailInspectionTaskConfig()
    episodes = [run_episode(seed=args.seed + index, max_steps=args.max_steps, config=config) for index in range(args.episodes)]
    payload = summarize(episodes, config)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    if payload["success_rate"] <= 0:
        print("[FAIL] Baseline policy did not complete any episode.")
        return 1
    print("[PASS] RL baseline evaluation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
