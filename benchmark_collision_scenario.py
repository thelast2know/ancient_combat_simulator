#!/usr/bin/env python3
"""
Benchmark with actual agent collisions - agents moving toward each other.
"""

import time
import numpy as np
from sim.core.world import World
from sim.core.params import GlobalParams


def benchmark_with_collisions(num_steps: int = 100, cell_size: float = 10.0):
    """Benchmark with agents colliding."""
    params = GlobalParams()
    world = World(params, seed=42)
    
    # Add agents in two teams facing each other
    for team in range(2):
        for i in range(50):
            if team == 0:
                # Blue team on left, moving right
                x = 20 + (i % 10) * 2
                y = 30 + (i // 10) * 2
            else:
                # Red team on right, moving left
                x = 80 - (i % 10) * 2
                y = 30 + (i // 10) * 2
            world.add_agent(team, x, y, {})
    
    # Override cell size and force spatial grid
    world.spatial_grid.cell_size = cell_size
    world.spatial_grid.grid_width = int(np.ceil(params.arena_width / cell_size))
    world.spatial_grid.grid_height = int(np.ceil(params.arena_height / cell_size))
    world._resolve_collisions = world._resolve_collisions_spatial
    
    print(f"\n[COLLISION TEST] Cell size: {cell_size}m -> {world.spatial_grid.grid_width}×{world.spatial_grid.grid_height} grid")
    
    num_agents = len(world.agents)
    n_squared = num_agents * (num_agents - 1) // 2
    
    print(f"Configuration: {num_agents} agents, {num_steps} steps")
    print(f"O(n²) would check: {n_squared} pairs per step")
    print("\n{'Step':>4} | {'Pairs':>5} | {'% of N²':>7} | {'Collisions':>10} | {'Time':>7}")
    print("-" * 65)
    
    step_times = []
    pair_counts = []
    collision_counts = []
    
    for step in range(num_steps):
        world.spatial_grid.reset_stats()
        
        # Blue team moves right, red team moves left
        actions = {}
        for i, agent in enumerate(world.agents):
            if agent.team == 0:
                actions[agent.agent_id] = (3.0, 0.0)  # Move right
            else:
                actions[agent.agent_id] = (-3.0, 0.0)  # Move left
        
        t0 = time.perf_counter()
        world.step(actions)
        t1 = time.perf_counter()
        
        step_time = (t1 - t0) * 1000
        pairs = world.spatial_grid.stats_pairs_checked
        collisions = world.spatial_grid.stats_pairs_colliding
        
        step_times.append(step_time)
        pair_counts.append(pairs)
        collision_counts.append(collisions)
        
        pct = 100 * pairs / n_squared if n_squared > 0 else 0
        
        if step % 10 == 0 or step == num_steps - 1:
            print(f"{step:4d} | {pairs:5d} | {pct:6.1f}% | {collisions:10d} | {step_time:7.2f}ms")
    
    print("-" * 65)
    print("\nSummary:")
    print(f"  Average pairs checked:      {np.mean(pair_counts):.0f} ({100*np.mean(pair_counts)/n_squared:.1f}% of N²)")
    print(f"  Average collisions/step:    {np.mean(collision_counts):.1f}")
    print(f"  Average step time:          {np.mean(step_times):.2f}ms")
    print(f"  Steps per second:           {1000/np.mean(step_times):.1f}")
    print(f"  Pair reduction vs O(n²):    {100*(1 - np.mean(pair_counts)/n_squared):.1f}%")


if __name__ == '__main__':
    print("=" * 70)
    print("COLLISION SCENARIO: TWO TEAMS MOVING TOWARD EACH OTHER")
    print("=" * 70)
    
    for cell_size in [1.0, 5.0, 10.0, 20.0]:
        benchmark_with_collisions(num_steps=50, cell_size=cell_size)
    
    print("\n" + "=" * 70)
