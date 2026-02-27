#!/usr/bin/env python3
"""
Benchmark physics performance with detailed spatial grid metrics.

Shows:
- Candidate pair count per step
- True collision count per step
- Average agents per cell
- Comparison to O(n²) baseline
"""

import time
import numpy as np
from sim.core.world import World
from sim.core.params import GlobalParams


def benchmark_with_metrics(num_steps: int = 100, num_agents_per_team: int = 50,
                           cell_size: float = 10.0):
    """Benchmark physics with detailed grid metrics."""
    params = GlobalParams()
    world = World(params, seed=42)
    
    # Add agents in two teams
    for team in range(2):
        for i in range(num_agents_per_team):
            team_x = 25 if team == 0 else 75
            team_y = 25 + (i % 10) * 5
            team_x += (i // 10) * 5
            world.add_agent(team, team_x, team_y, {})
    
    # Override cell size
    world.spatial_grid.cell_size = cell_size
    world.spatial_grid.grid_width = int(np.ceil(params.arena_width / cell_size))
    world.spatial_grid.grid_height = int(np.ceil(params.arena_height / cell_size))
    print(f"\n[BENCHMARK] Cell size: {cell_size}m -> {world.spatial_grid.grid_width}×{world.spatial_grid.grid_height} grid")
    
    # FORCE spatial grid version for testing
    world._resolve_collisions = world._resolve_collisions_spatial
    
    num_agents = len(world.agents)
    n_squared = num_agents * (num_agents - 1) // 2
    
    print(f"\nConfiguration: {num_agents} agents, {num_steps} steps")
    print(f"O(n²) would check: {n_squared} pairs per step")
    print("\n{'Step':>4} | {'Pairs':>5} | {'% of N²':>7} | {'Collisions':>10} | {'Cells':>5} | {'Agents/Cell':>10} | {'Time':>7}")
    print("-" * 80)
    
    step_times = []
    pair_counts = []
    collision_counts = []
    cell_counts = []
    avg_agents_per_cell = []
    
    for step in range(num_steps):
        # Reset stats
        world.spatial_grid.reset_stats()
        
        # Create simple actions (all agents move forward)
        actions = {agent.agent_id: (2.0, 0.0) for agent in world.agents}
        
        t0 = time.perf_counter()
        world.step(actions)
        t1 = time.perf_counter()
        
        step_time = (t1 - t0) * 1000  # ms
        pairs = world.spatial_grid.stats_pairs_checked
        collisions = world.spatial_grid.stats_pairs_colliding
        cells = world.spatial_grid.stats_cells_occupied
        
        step_times.append(step_time)
        pair_counts.append(pairs)
        collision_counts.append(collisions)
        cell_counts.append(cells)
        
        avg_k = pairs / cells if cells > 0 else 0
        avg_agents_per_cell.append(avg_k)
        
        pct_of_n2 = 100 * pairs / n_squared if n_squared > 0 else 0
        
        if step % 10 == 0 or step == num_steps - 1:
            print(f"{step:4d} | {pairs:5d} | {pct_of_n2:6.1f}% | {collisions:10d} | {cells:5d} | {avg_k:10.2f} | {step_time:7.2f}ms")
    
    print("-" * 80)
    print("\nSummary:")
    print(f"  Average pairs checked:      {np.mean(pair_counts):.0f} ({100*np.mean(pair_counts)/n_squared:.1f}% of N²)")
    print(f"  Average collisions/step:    {np.mean(collision_counts):.2f}")
    print(f"  Average cells occupied:     {np.mean(cell_counts):.1f}")
    print(f"  Average agents per cell:    {np.mean(avg_agents_per_cell):.2f}")
    print(f"  Average step time:          {np.mean(step_times):.2f}ms")
    print(f"  Steps per second:           {1000/np.mean(step_times):.1f}")
    print(f"\nReduction vs O(n²): {100*(1 - np.mean(pair_counts)/n_squared):.1f}%")


if __name__ == '__main__':
    print("=" * 80)
    print("SPATIAL GRID COLLISION DETECTION METRICS")
    print("=" * 80)
    
    # Test different cell sizes
    for cell_size in [1.0, 5.0, 10.0, 20.0]:
        benchmark_with_metrics(num_steps=50, num_agents_per_team=50, cell_size=cell_size)
    
    print("\n" + "=" * 80)
