from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
except Exception:  # pragma: no cover - optional runtime dependency
    gym = None
    spaces = None


@dataclass
class RailInspectionTaskConfig:
    corridor_length_m: float = 260.0
    max_altitude_m: float = 18.0
    target_speed_mps: float = 4.0
    alert_reward: float = 5.0
    corridor_penalty: float = 2.0


if gym is not None:

    class RailInspectionEnv(gym.Env):
        """Gymnasium skeleton for replacing the rule policy with trainable policies."""

        metadata = {"render_modes": ["human", "rgb_array"]}

        def __init__(self, config: Optional[RailInspectionTaskConfig] = None, render_mode: Optional[str] = None):
            super().__init__()
            self.config = config or RailInspectionTaskConfig()
            self.render_mode = render_mode
            self.observation_space = spaces.Dict(
                {
                    "pose": spaces.Box(low=-1e3, high=1e3, shape=(6,), dtype=np.float32),
                    "velocity": spaces.Box(low=-50, high=50, shape=(3,), dtype=np.float32),
                    "last_detection": spaces.Box(low=0, high=1, shape=(12,), dtype=np.float32),
                    "mission_progress": spaces.Box(low=0, high=1, shape=(1,), dtype=np.float32),
                }
            )
            self.action_space = spaces.Box(low=np.array([-1.0, -1.0, -0.5]), high=np.array([1.0, 1.0, 0.5]), dtype=np.float32)
            self.state = np.zeros(10, dtype=np.float32)
            self.step_count = 0

        def reset(self, *, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None):
            super().reset(seed=seed)
            self.step_count = 0
            self.state = np.zeros(10, dtype=np.float32)
            obs = self._obs()
            return obs, {"mode": "skeleton", "note": "Connect ROS2/Gazebo adapters before training."}

        def step(self, action):
            self.step_count += 1
            action = np.asarray(action, dtype=np.float32)
            self.state[0:3] += np.array([action[0], action[1], action[2]], dtype=np.float32)
            self.state[0] = np.clip(self.state[0], 0.0, self.config.corridor_length_m)
            self.state[2] = np.clip(self.state[2], 2.0, self.config.max_altitude_m)
            progress = self.state[0] / self.config.corridor_length_m
            lateral_penalty = abs(float(self.state[1])) / 12.0
            reward = float(progress - lateral_penalty * self.config.corridor_penalty)
            terminated = bool(progress >= 0.99)
            truncated = self.step_count > 800
            return self._obs(), reward, terminated, truncated, {"progress": progress}

        def _obs(self):
            return {
                "pose": np.array([self.state[0], self.state[1], self.state[2], 0, 0, 0], dtype=np.float32),
                "velocity": np.zeros(3, dtype=np.float32),
                "last_detection": np.zeros(12, dtype=np.float32),
                "mission_progress": np.array([self.state[0] / self.config.corridor_length_m], dtype=np.float32),
            }

        def render(self):
            if self.render_mode == "rgb_array":
                return np.zeros((240, 320, 3), dtype=np.uint8)
            return None

else:

    class RailInspectionEnv:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            raise RuntimeError("gymnasium is not installed. Install it inside the project container.")


class RulePolicyAdapter:
    """Adapter contract for swapping the current rule mission manager with an RL policy."""

    def compute_action(self, observation: Dict[str, np.ndarray]) -> np.ndarray:
        progress = float(observation.get("mission_progress", np.array([0.0]))[0])
        forward = 0.8 if progress < 0.95 else -0.2
        return np.array([forward, 0.0, 0.0], dtype=np.float32)


def main() -> None:
    env = RailInspectionEnv()
    obs, info = env.reset()
    total_reward = 0.0
    policy = RulePolicyAdapter()
    for _ in range(8):
        obs, reward, terminated, truncated, step_info = env.step(policy.compute_action(obs))
        total_reward += reward
        if terminated or truncated:
            break
    print({"env": "RailInspectionEnv", "info": info, "total_reward": round(total_reward, 3), "last": step_info})


if __name__ == "__main__":
    main()
