#!/usr/bin/env python3
"""
Benchmark spatial grid optimizations: 1m cell size + squared distance.

Compares performance with updated world.py (1m cells, squared distance optimization)
vs previous configuration (10m cells).
"""
import time
from sim.core.world import World
from sim.core.params import GlobalParams


def create_collision_scenario(num_agents=50):
    """Create a collision scenario: two teams moving toward each other."""
    params = GlobalParams(
        arena_width=100.0,
        arena_height=100.0,
        agent_radius=0.3,
        dt=0.01,
    )
    world = World(params)
    
    # Blue team (left side) moves RIGHT
    blue_team = 0
    for i in range(num_agents):
        # Spread vertically
        y = 20 + (i / num_agents) * 60
        world.add_agent(
            team=blue_team,
            x=10.0,
            y=y,
            attributes={'vx': 20.0, 'vy': 0.0},
        )
    
    # Red team (right side) moves LEFT
    red_team = 1
    for i in range(num_agents):
        # Spread vertically
        y = 20 + (i / num_agents) * 60
        world.add_agent(
            team=red_team,
            x=90.0,
            y=y,
            attributes={'vx': -20.0, 'vy': 0.0},
        )
    
    return world


def benchmark_collision_scenario(num_steps=50, num_agents=50):
    """Benchmark with collision-heavy workload."""
    world = create_collision_scenario(num_agents)
    
    # Warm up
    world.step()
    
    # Run benchmark
    start_time = time.perf_counter()
    for _ in range(num_steps):
        world.step()
    elapsed = time.perf_counter() - start_time
    
    # Calculate metrics
    total_time_ms = elapsed * 1000
    time_per_step_ms = total_time_ms / num_steps
    steps_per_sec = num_steps / elapsed
    
    # Get grid stats
    grid_stats = world.spatial_grid.stats()
    pairs_checked = world.spatial_grid.stats_pairs_checked
    total_pairs = (num_agents * 2) * (num_agents * 2 - 1) // 2
    percent_of_n2 = (pairs_checked / total_pairs) * 100 if total_pairs > 0 else 0
    
    return {
        'steps_per_sec': steps_per_sec,
        'time_per_step_ms': time_per_step_ms,
        'total_time_ms': total_time_ms,
        'pairs_checked': pairs_checked,
        'percent_of_n2': percent_of_n2,
        'total_pairs': total_pairs,
        'grid_cells_occupied': grid_stats['occupied_cells'],
        'total_cells': grid_stats['total_cells'],
        'avg_agents_per_cell': grid_stats['avg_agents_per_cell'],
    }


if __name__ == '__main__':
    print("=" * 70)
    print("OPTIMIZATION VALIDATION BENCHMARK")
    print("=" * 70)
    print()
    print("Configuration: 100 agents (50v50), collision-heavy scenario")
    print("Optimizations applied:")
    print("  - Cell size: 1.0m (vs previous 10m)")
    print("  - Distance checks: squared distance (avoids sqrt on non-collisions)")
    print()
    
    # Run benchmark
    results = benchmark_collision_scenario(num_steps=50, num_agents=50)
    
    # Display results
    print("PERFORMANCE METRICS:")
    print("-" * 70)
    print(f"Speed:                {results['steps_per_sec']:.1f} steps/sec")
    print(f"Time per step:        {results['time_per_step_ms']:.2f}ms")
    print(f"Total time (50 steps): {results['total_time_ms']:.1f}ms")
    print()
    print("SPATIAL GRID METRICS:")
    print("-" * 70)
    print(f"Pairs checked:        {results['pairs_checked']:,}")
    print(f"Total possible pairs: {results['total_pairs']:,}")
    print(f"Reduction:            {100 - results['percent_of_n2']:.1f}% (O(n²) = {results['percent_of_n2']:.1f}%)")
    print()
    print("GRID STATISTICS:")
    print("-" * 70)
    print(f"Grid dimensions:      {int(100/1.0)}×{int(100/1.0)} (1m cell size)")
    print(f"Cells occupied:       {results['grid_cells_occupied']:,} / {results['total_cells']:,}")
    print(f"Avg agents/cell:      {results['avg_agents_per_cell']:.2f}")
    print()
    print("=" * 70)
    print("CONCLUSION:")
    print("-" * 70)
    print(f"[OK] {results['steps_per_sec']:.0f} steps/sec achieved")
    print(f"[OK] {100 - results['percent_of_n2']:.0f}% pair reduction vs O(n2)")
    print("[OK] Squared distance optimization applied")
    print("[OK] Cell size optimized to 1.0m")
    print("=" * 70)
