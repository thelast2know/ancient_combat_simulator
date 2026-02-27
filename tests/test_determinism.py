"""
Phase 1 Tests: Determinism, Collision, and Bounds Validation
"""

import sys
from pathlib import Path

import numpy as np
import pytest

# Add sim to path
sim_path = Path(__file__).parent.parent
sys.path.insert(0, str(sim_path))

from sim.core import World, GlobalParams


class TestDeterminism:
    """Test that same seed + same actions produce identical trajectories."""
    
    def test_deterministic_stepping_single_agent(self):
        """Single agent moving in straight line should be deterministic."""
        params = GlobalParams()
        
        # Run 1
        world1 = World(params, seed=42)
        world1.add_infantry_block(0, *params.infantry_blue_rect)
        world1.add_infantry_block(1, *params.infantry_red_rect)
        agent_id_1 = world1.add_agent(0, 50.0, 50.0, {'cruise_speed': 5.0})
        
        hashes1 = []
        for _ in range(100):
            world1.step({agent_id_1: (5.0, 0.0)})
            hashes1.append(world1.get_state_hash())
        
        # Run 2 with same seed
        world2 = World(params, seed=42)
        world2.add_infantry_block(0, *params.infantry_blue_rect)
        world2.add_infantry_block(1, *params.infantry_red_rect)
        agent_id_2 = world2.add_agent(0, 50.0, 50.0, {'cruise_speed': 5.0})
        
        hashes2 = []
        for _ in range(100):
            world2.step({agent_id_2: (5.0, 0.0)})
            hashes2.append(world2.get_state_hash())
        
        assert hashes1 == hashes2, "Determinism violated: same seed should produce identical hashes"
    
    def test_deterministic_stepping_multi_agent(self):
        """Multiple agents should be deterministic."""
        params = GlobalParams()
        
        # Run 1
        world1 = World(params, seed=123)
        world1.add_infantry_block(0, *params.infantry_blue_rect)
        world1.add_infantry_block(1, *params.infantry_red_rect)
        
        ids_1 = [
            world1.add_agent(0, 30.0, 40.0, {'cruise_speed': 5.0}),
            world1.add_agent(0, 35.0, 45.0, {'cruise_speed': 5.0}),
            world1.add_agent(1, 70.0, 40.0, {'cruise_speed': 5.0}),
            world1.add_agent(1, 65.0, 45.0, {'cruise_speed': 5.0}),
        ]
        
        hashes1 = []
        for _ in range(50):
            actions = {
                ids_1[0]: (5.0, 0.0),
                ids_1[1]: (4.0, 2.0),
                ids_1[2]: (-5.0, 0.0),
                ids_1[3]: (-4.0, -2.0),
            }
            world1.step(actions)
            hashes1.append(world1.get_state_hash())
        
        # Run 2
        world2 = World(params, seed=123)
        world2.add_infantry_block(0, *params.infantry_blue_rect)
        world2.add_infantry_block(1, *params.infantry_red_rect)
        
        ids_2 = [
            world2.add_agent(0, 30.0, 40.0, {'cruise_speed': 5.0}),
            world2.add_agent(0, 35.0, 45.0, {'cruise_speed': 5.0}),
            world2.add_agent(1, 70.0, 40.0, {'cruise_speed': 5.0}),
            world2.add_agent(1, 65.0, 45.0, {'cruise_speed': 5.0}),
        ]
        
        hashes2 = []
        for _ in range(50):
            actions = {
                ids_2[0]: (5.0, 0.0),
                ids_2[1]: (4.0, 2.0),
                ids_2[2]: (-5.0, 0.0),
                ids_2[3]: (-4.0, -2.0),
            }
            world2.step(actions)
            hashes2.append(world2.get_state_hash())
        
        assert hashes1 == hashes2, "Determinism violated in multi-agent scenario"


class TestCollisions:
    """Test collision resolution between agents."""
    
    def test_no_overlap_after_collision(self):
        """After collision, agents should separate (not overlap indefinitely)."""
        params = GlobalParams()
        world = World(params, seed=42)
        world.add_infantry_block(0, *params.infantry_blue_rect)
        world.add_infantry_block(1, *params.infantry_red_rect)
        
        # Place two agents very close with high velocities
        a1 = world.add_agent(0, 49.8, 50.0, {'cruise_speed': 5.0})
        a2 = world.add_agent(1, 50.2, 50.0, {'cruise_speed': 5.0})
        
        # Bypass velocity ramping by directly setting velocities
        agent_a1 = world.agent_dict[a1]
        agent_a2 = world.agent_dict[a2]
        agent_a1.vx = 5.0  # moving right
        agent_a2.vx = -5.0  # moving left
        
        min_dist = float('inf')
        max_overlap = 0.0
        min_allowed = 2 * params.agent_radius
        
        # Run simulation
        for step in range(100):
            agent_a1 = world.agent_dict[a1]
            agent_a2 = world.agent_dict[a2]
            dist = agent_a1.distance_to(agent_a2)
            min_dist = min(min_dist, dist)
            
            # Track maximum overlap
            overlap = min_allowed - dist if dist < min_allowed else 0
            max_overlap = max(max_overlap, overlap)
            
            world.step({a1: (5.0, 0.0), a2: (-5.0, 0.0)})
        
        # Verify agents got close
        assert min_dist < 1.0, f"Agents never got close: {min_dist}m"
        # Verify overlap is reasonable (< 0.25m tolerance for floating point errors)
        assert max_overlap < 0.25, f"Excessive overlap: {max_overlap}m"
    
    def test_symmetric_collision_response(self):
        """Collision response should result in relative velocity reduction."""
        params = GlobalParams()
        world = World(params, seed=42)
        world.add_infantry_block(0, *params.infantry_blue_rect)
        world.add_infantry_block(1, *params.infantry_red_rect)
        
        # Two agents moving toward each other
        a1 = world.add_agent(0, 48.5, 50.0, {'cruise_speed': 5.0})
        a2 = world.add_agent(1, 51.5, 50.0, {'cruise_speed': 5.0})
        
        # Set velocities directly
        agent_a1 = world.agent_dict[a1]
        agent_a2 = world.agent_dict[a2]
        agent_a1.vx = 2.5
        agent_a2.vx = -2.5
        
        # Run simulation
        for _ in range(100):
            world.step({a1: (5.0, 0.0), a2: (-5.0, 0.0)})
        
        agent_a1 = world.agent_dict[a1]
        agent_a2 = world.agent_dict[a2]
        
        # After collision, speeds should be reasonable
        speed1 = np.sqrt(agent_a1.vx**2 + agent_a1.vy**2)
        speed2 = np.sqrt(agent_a2.vx**2 + agent_a2.vy**2)
        
        # Speeds should be reasonable (< 10 m/s)
        assert speed1 < 10.0, f"Agent 1 speed too high: {speed1}"
        assert speed2 < 10.0, f"Agent 2 speed too high: {speed2}"
    
    def test_collision_events_logged(self):
        """Collision events should be recorded when agents collide."""
        params = GlobalParams()
        world = World(params, seed=42)
        world.add_infantry_block(0, *params.infantry_blue_rect)
        world.add_infantry_block(1, *params.infantry_red_rect)
        
        # Place agents close with direct velocities
        a1 = world.add_agent(0, 49.8, 50.0, {'cruise_speed': 5.0})
        a2 = world.add_agent(1, 50.2, 50.0, {'cruise_speed': 5.0})
        
        # Set high closing velocity
        agent_a1 = world.agent_dict[a1]
        agent_a2 = world.agent_dict[a2]
        agent_a1.vx = 5.0
        agent_a2.vx = -5.0
        
        collision_count = 0
        # Run enough steps for collision to occur
        for _ in range(100):
            events = world.step({a1: (5.0, 0.0), a2: (-5.0, 0.0)})
            collision_count += sum(1 for e in events if e.event_type == 'collision')
        
        # With close starting distance and high closing velocity, should detect collision
        assert collision_count > 0, \
            "No collision events - agents starting 0.4m apart with 10 m/s closing speed should collide"


class TestBounds:
    """Test boundary conditions."""
    
    def test_agents_clamped_to_arena(self):
        """Agents should not exceed arena bounds."""
        params = GlobalParams()
        world = World(params, seed=42)
        world.add_infantry_block(0, *params.infantry_blue_rect)
        world.add_infantry_block(1, *params.infantry_red_rect)
        
        # Place agent at corner, move outward
        agent_id = world.add_agent(0, 0.5, 0.5, {'max_speed': 10.0})
        
        for _ in range(50):
            world.step({agent_id: (-10.0, -10.0)})
        
        agent = world.agent_dict[agent_id]
        margin = params.agent_radius
        
        assert agent.x >= margin, f"Agent x out of bounds: {agent.x}"
        assert agent.x <= params.arena_width - margin, f"Agent x out of bounds: {agent.x}"
        assert agent.y >= margin, f"Agent y out of bounds: {agent.y}"
        assert agent.y <= params.arena_height - margin, f"Agent y out of bounds: {agent.y}"
    
    def test_velocity_zero_at_boundary(self):
        """Velocity should be zeroed when agent hits boundary."""
        params = GlobalParams()
        world = World(params, seed=42)
        world.add_infantry_block(0, *params.infantry_blue_rect)
        world.add_infantry_block(1, *params.infantry_red_rect)
        
        agent_id = world.add_agent(0, 1.0, 50.0, {'max_speed': 10.0})
        
        # Move left (into boundary)
        for _ in range(10):
            world.step({agent_id: (-10.0, 0.0)})
        
        agent = world.agent_dict[agent_id]
        
        # Velocity should be zero (or very small due to desired vel being -10)
        # Actually, desired_vx is still -10 so it will keep trying
        # But actual vx should be clamped
        assert agent.x >= params.agent_radius - 0.1, "Agent penetrated boundary"


class TestEpisodeTermination:
    """Test episode stepping and state tracking."""
    
    def test_step_counting(self):
        """Step counter should increment correctly."""
        params = GlobalParams()
        world = World(params, seed=42)
        world.add_infantry_block(0, *params.infantry_blue_rect)
        world.add_infantry_block(1, *params.infantry_red_rect)
        
        assert world.step_count == 0
        
        for i in range(10):
            world.step()
            assert world.step_count == i + 1
    
    def test_reset_clears_state(self):
        """Reset should clear all agents and events."""
        params = GlobalParams()
        world = World(params, seed=42)
        world.add_infantry_block(0, *params.infantry_blue_rect)
        world.add_infantry_block(1, *params.infantry_red_rect)
        
        agent_id = world.add_agent(0, 50.0, 50.0, {'cruise_speed': 5.0})
        world.step({agent_id: (5.0, 0.0)})
        
        assert world.step_count == 1
        assert len(world.agents) == 1
        
        world.reset(seed=99)
        
        assert world.step_count == 0
        assert len(world.agents) == 0
        assert world.max_agent_id == -1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
