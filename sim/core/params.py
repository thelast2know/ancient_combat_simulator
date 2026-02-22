"""
Global simulation parameters and configuration loading.

All parameters are exposed in a single config dict for:
- deterministic replay
- YAML/JSON loading
- cultural experimentation
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any
import json
import yaml


@dataclass
class GlobalParams:
    """Global simulation parameters (non-negotiable constants)."""
    
    # Physics
    dt: float = 0.1  # timestep in seconds
    gravity: float = 9.81  # m/s^2
    agent_radius: float = 0.3  # m
    
    # Arena
    arena_width: float = 100.0  # m
    arena_height: float = 100.0  # m
    
    # Infantry blocks (static)
    infantry_blue_rect: tuple = (20.0, 25.0, 60.0, 50.0)  # (x_min, y_min, x_max, y_max)
    infantry_red_rect: tuple = (80.0, 25.0, 40.0, 50.0)  # (x_min, y_min, x_max, y_max)
    
    # Episode
    max_episode_steps: int = 36000  # 60 minutes at dt=0.1s
    episode_timeout_minutes: float = 60.0
    
    # Infantry danger zone
    infantry_danger_radius: float = 3.0  # meters
    
    # Terrain (Phase 1: flat)
    terrain_flat: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Export as dict for serialization."""
        return asdict(self)
    
    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "GlobalParams":
        """Construct from dict."""
        return GlobalParams(**d)
    
    def to_json(self, path: str):
        """Save to JSON file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @staticmethod
    def from_json(path: str) -> "GlobalParams":
        """Load from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        return GlobalParams.from_dict(data)


@dataclass
class CultureParams:
    """
    Cultural reward weights and tactical preferences.
    Exposed in observation so agents can adapt.
    """
    survival_bonus: float = 0.01  # per-step survival reward
    kill_reward: float = 1.0  # enemy skirmisher kill
    enemy_infantry_hit: float = 1.0  # hit on enemy infantry
    friendly_infantry_hit_penalty: float = -1.0  # hit on friendly infantry
    casualty_penalty: float = -0.5  # unit casualty
    shame_tax_rate: float = 0.01  # per step of inactivity
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "CultureParams":
        return CultureParams(**d)


@dataclass
class AgentAttributeDistribution:
    """
    Distributions for random agent attribute initialization.
    (Will expand to correlated normal in later phases.)
    """
    # Physical
    strength_mean: float = 1.0
    strength_std: float = 0.15
    cruise_speed_mean: float = 5.0  # m/s
    cruise_speed_std: float = 0.5
    max_speed_mean: float = 8.0
    max_speed_std: float = 1.0
    acceleration_mean: float = 2.0  # m/s^2
    acceleration_std: float = 0.3
    agility_mean: float = 3.0  # rad/s (turn rate)
    agility_std: float = 0.5
    
    # Cognitive
    precision_mean: float = 0.7
    precision_std: float = 0.2
    impetuousness_mean: float = 0.5
    impetuousness_std: float = 0.2
    timidity_mean: float = 0.5
    timidity_std: float = 0.2
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_scenario(yaml_path: str) -> Dict[str, Any]:
    """Load scenario from YAML file."""
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)


def save_scenario(scenario: Dict[str, Any], yaml_path: str):
    """Save scenario to YAML file."""
    with open(yaml_path, 'w') as f:
        yaml.dump(scenario, f, default_flow_style=False)
