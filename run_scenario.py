#!/usr/bin/env python3
"""
Configurable scenario runner with clean separation of concerns.

Usage:
    python run_scenario.py run_50v50.yaml
"""
import sys
import yaml
import numpy as np
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

from sim.core.world import World
from sim.core.params import GlobalParams


@dataclass
class ScenarioConfig:
    """Parsed scenario configuration."""
    description: str
    blue_agents: dict
    red_agents: dict


@dataclass
class RunConfig:
    """Parsed run configuration."""
    scenario: str
    simulation: dict
    behaviors: dict
    rendering: dict
    video: dict
    output: dict


class ScenarioBuilder:
    """Builds agents from scenario YAML configuration."""
    
    @staticmethod
    def load_scenario(scenario_path: str) -> ScenarioConfig:
        """Load scenario from YAML file."""
        with open(scenario_path, 'r') as f:
            data = yaml.safe_load(f)
        return ScenarioConfig(**data)
    
    @staticmethod
    def build_grid_formation(formation_config: dict, team: int, world: World) -> List[str]:
        """Build agents in grid formation."""
        agents = []
        config = formation_config['grid_params']
        origin_x, origin_y = config['origin']
        rows = config['rows']
        cols = config['cols']
        spacing_x = config['spacing_x']
        spacing_y = config['spacing_y']
        reverse_x = config.get('reverse_x', False)
        
        for row in range(rows):
            for col in range(cols):
                x = origin_x + col * spacing_x
                y = origin_y + row * spacing_y
                
                if reverse_x:
                    x = origin_x - col * spacing_x
                
                agent_id = world.add_agent(
                    team=team,
                    x=x,
                    y=y,
                    attributes=formation_config.get('attributes', {})
                )
                agents.append(agent_id)
        
        return agents
    
    @staticmethod
    def setup_world(scenario_config: ScenarioConfig) -> Tuple[World, List[str], List[str]]:
        """Create world and populate with agents from scenario config."""
        params = GlobalParams()
        world = World(params)
        
        blue_agents = []
        red_agents = []
        
        if scenario_config.blue_agents.get('formation') == 'grid':
            blue_agents = ScenarioBuilder.build_grid_formation(
                scenario_config.blue_agents, team=0, world=world
            )
        
        if scenario_config.red_agents.get('formation') == 'grid':
            red_agents = ScenarioBuilder.build_grid_formation(
                scenario_config.red_agents, team=1, world=world
            )
        
        return world, blue_agents, red_agents


class SimulationRunner:
    """Runs pure physics simulation without rendering overhead."""
    
    def __init__(self, world: World, run_config: RunConfig):
        self.world = world
        self.run_config = run_config
        self.sim_config = run_config.simulation
        self.behavior_config = run_config.behaviors
        self.output_config = run_config.output
        
        # Store seed for potential replay
        self.seed = self.sim_config.get('random_seed', None)
        if self.seed:
            np.random.seed(self.seed)
    
    def run(self, blue_agents: List[str], red_agents: List[str], capture_full_state: bool = False) -> List[dict]:
        """Run simulation and return frame data for rendering.
        
        Returns:
            List of frame dictionaries containing agent states
        """
        num_steps = self.sim_config['num_steps']
        record_interval = self.sim_config.get('record_interval', 1)  # Record every N steps
        frames = []
        stats_interval = self.output_config.get('stats_interval', 50)
        
        print("=" * 80)
        print("RUNNING SIMULATION")
        print("=" * 80)
        print(f"  Steps: {num_steps}")
        print(f"  Blue agents: {len(blue_agents)}")
        print(f"  Red agents: {len(red_agents)}")
        print()
        
        for step in range(num_steps):
            # Capture frame state before step (for rendering) - record at specified interval
            if step % record_interval == 0:
                frame_data = self._capture_frame(step)
                frames.append(frame_data)
            
            # Print stats
            if self.output_config['verbose'] and (step + 1) % stats_interval == 0:
                alive_blue = frame_data['alive_blue']
                alive_red = frame_data['alive_red']
                print(f"  Step {step + 1}/{num_steps}: Blue {alive_blue}, Red {alive_red}")
            
            # Build actions
            actions = self._build_actions(blue_agents, red_agents)
            
            # Fire projectiles
            if self.behavior_config['projectile_fire']['enabled']:
                self._fire_projectiles()
            
            # Step simulation
            self.world.step(actions)
        
        # Capture final frame
        final_frame = self._capture_frame(num_steps)
        frames.append(final_frame)
        
        print()
        print("Simulation complete!")
        print(f"  Total projectiles fired: {len(self.world.projectiles)}")
        print(f"  Frames captured: {len(frames)} (record_interval={record_interval})")
        print(f"  Final Blue: {final_frame['alive_blue']}")
        print(f"  Final Red: {final_frame['alive_red']}")
        print()
        
        return frames
    
    def _capture_frame(self, step: int) -> dict:
        """Capture current world state - complete snapshot for rendering."""
        alive_blue = sum(1 for a in self.world.agents if a.team == 0 and a.alive)
        alive_red = sum(1 for a in self.world.agents if a.team == 1 and a.alive)
        
        # Capture full agent state for each agent
        agents_snapshot = []
        for a in self.world.agents:
            agents_snapshot.append({
                'agent_id': a.agent_id,
                'team': a.team,
                'x': a.x,
                'y': a.y,
                'heading': a.heading,
                'alive': a.alive,
            })
        
        # Capture projectile positions AND velocities for arrow rendering
        projectiles_snapshot = []
        for p in self.world.projectiles:
            x, y, z = p.position()
            vx, vy, vz = p.velocity()
            projectiles_snapshot.append({
                'x': x,
                'y': y,
                'z': z,
                'vx': vx,
                'vy': vy,
                'vz': vz,
                'state': p.state.value,
            })
        
        return {
            'step': step,
            'agents': agents_snapshot,
            'projectiles': projectiles_snapshot,
            'alive_blue': alive_blue,
            'alive_red': alive_red,
        }
    
    def _build_actions(self, blue_agents: List[str], red_agents: List[str]) -> Dict:
        """Build movement actions for agents."""
        actions = {}
        
        if not self.behavior_config['team_movement']['enabled']:
            return actions
        
        strategy = self.behavior_config['team_movement']['target_strategy']
        speed = self.behavior_config['team_movement']['speed']
        
        if strategy == 'centroid':
            # Team 0 moves toward Team 1 centroid
            team1_pos = [self.world.agent_dict[aid] for aid in red_agents
                        if aid in self.world.agent_dict and self.world.agent_dict[aid].alive]
            if team1_pos:
                cx = np.mean([a.x for a in team1_pos])
                cy = np.mean([a.y for a in team1_pos])
                
                for aid in blue_agents:
                    if aid in self.world.agent_dict and self.world.agent_dict[aid].alive:
                        agent = self.world.agent_dict[aid]
                        dx, dy = cx - agent.x, cy - agent.y
                        mag = np.sqrt(dx*dx + dy*dy)
                        if mag > 0.1:
                            actions[aid] = (dx/mag * speed, dy/mag * speed)
            
            # Team 1 moves toward Team 0 centroid
            team0_pos = [self.world.agent_dict[aid] for aid in blue_agents
                        if aid in self.world.agent_dict and self.world.agent_dict[aid].alive]
            if team0_pos:
                cx = np.mean([a.x for a in team0_pos])
                cy = np.mean([a.y for a in team0_pos])
                
                for aid in red_agents:
                    if aid in self.world.agent_dict and self.world.agent_dict[aid].alive:
                        agent = self.world.agent_dict[aid]
                        dx, dy = cx - agent.x, cy - agent.y
                        mag = np.sqrt(dx*dx + dy*dy)
                        if mag > 0.1:
                            actions[aid] = (dx/mag * speed, dy/mag * speed)
        
        return actions
    
    def _fire_projectiles(self):
        """Fire projectiles from agents."""
        fire_prob = self.behavior_config['projectile_fire']['fire_probability']
        az_range = self.behavior_config['projectile_fire']['azimuth_range']
        loft_range = self.behavior_config['projectile_fire']['loft_angle_range']
        speed_range = self.behavior_config['projectile_fire']['speed_range']
        
        for agent in self.world.agents:
            if agent.alive and np.random.random() < fire_prob:
                azimuth = np.random.uniform(*az_range)
                loft = np.random.uniform(*loft_range)
                speed = np.random.uniform(*speed_range)
                self.world.launch_projectile(agent.agent_id, azimuth, loft, speed)


class FrameRenderer:
    """Render frames to video (optional, can be disabled)."""
    
    @staticmethod
    def render_frames_to_video(frames: List[dict], world: World, run_config: RunConfig) -> Optional[Path]:
        """Render captured frames to video file."""
        if not run_config.rendering['enabled']:
            return None
        
        import cv2
        from sim.render.renderer2d import Renderer2D
        
        print("=" * 80)
        print("RENDERING VIDEO")
        print("=" * 80)
        
        render_interval = run_config.rendering.get('render_interval', 1)  # Render every Nth captured frame
        frames_to_render = frames[::render_interval]  # Sample frames
        
        renderer = Renderer2D(world, figsize=tuple(run_config.rendering['figsize']))
        
        output_dir = Path(run_config.rendering['output_dir'])
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"scenario_{timestamp}.mp4"
        
        fps = run_config.rendering['fps']
        first_frame = renderer.render(title="Rendering...")
        height, width = first_frame.shape[:2]
        
        fourcc = cv2.VideoWriter_fourcc(*run_config.video['codec'])
        video_writer = cv2.VideoWriter(str(output_file), fourcc, fps, (width, height))
        
        for i, frame_data in enumerate(frames_to_render):
            if (i + 1) % 50 == 0:
                print(f"  Rendering frame {i + 1}/{len(frames_to_render)}...")
            
            title = f"Step {frame_data['step']:04d} | Blue: {frame_data['alive_blue']:2d} | Red: {frame_data['alive_red']:2d}"
            frame_rgb = renderer.render(title=title, frame_data=frame_data)
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            video_writer.write(frame_bgr)
        
        video_writer.release()
        
        print()
        print(f"Video saved: {output_file}")
        print(f"  Total captured frames: {len(frames)}")
        print(f"  Rendered frames: {len(frames_to_render)} (render_interval={render_interval})")
        print(f"  Resolution: {width}x{height}")
        print(f"  FPS: {fps}")
        print(f"  Duration: {len(frames_to_render)/fps:.1f}s")
        print(f"  Size: {output_file.stat().st_size / (1024*1024):.1f} MB")
        print()
        
        return output_file


def load_run_config(config_path: str) -> RunConfig:
    """Load run configuration from YAML file."""
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)
    return RunConfig(**data)


def main(run_config_path: str):
    """Main execution pipeline."""
    print()
    print("=" * 80)
    print("ANCIENT COMBAT SIMULATOR - SCENARIO RUNNER")
    print("=" * 80)
    print()
    
    # Load configurations
    run_config = load_run_config(run_config_path)
    scenario_config = ScenarioBuilder.load_scenario(run_config.scenario)
    
    print(f"Scenario: {run_config.scenario}")
    print(f"Description: {scenario_config.description}")
    print()
    
    # Setup world
    world, blue_agents, red_agents = ScenarioBuilder.setup_world(scenario_config)
    
    # Run simulation
    runner = SimulationRunner(world, run_config)
    frames = runner.run(blue_agents, red_agents)
    
    # Render video (optional)
    if run_config.rendering['enabled']:
        FrameRenderer.render_frames_to_video(frames, world, run_config)
    else:
        print("[RENDERING DISABLED]")
        print()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python run_scenario.py <run_config.yaml>")
        print()
        print("Example:")
        print("  python run_scenario.py run_50v50.yaml")
        sys.exit(1)
    
    main(sys.argv[1])
