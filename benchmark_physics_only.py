#!/usr/bin/env python3
"""Pure physics simulation benchmark - no rendering, detailed timing analysis."""
import time
import numpy as np
from sim.core.world import World
from sim.core.params import GlobalParams


def benchmark_physics_only(num_steps=300, num_agents_per_team=50):
    """Run pure physics simulation with detailed performance benchmarking.

    Args:
        num_steps: Total simulation steps
        num_agents_per_team: Agents per team (100 total)

    Returns:
        Benchmark statistics
    """
    params = GlobalParams()
    world = World(params)

    # Add agents in two teams
    team0_agents = []
    team1_agents = []

    for i in range(num_agents_per_team):
        x = 10 + (i % 10) * 5
        y = 20 + (i // 10) * 10
        agent_id = world.add_agent(team=0, x=x, y=y,
                                   attributes={'health': 100, 'range': 50})
        team0_agents.append(agent_id)

    for i in range(num_agents_per_team):
        x = 90 - (i % 10) * 5
        y = 20 + (i // 10) * 10
        agent_id = world.add_agent(team=1, x=x, y=y,
                                   attributes={'health': 100, 'range': 50})
        team1_agents.append(agent_id)

    print("=" * 80)
    print("PHYSICS BENCHMARK: 50v50 COMBAT SIMULATION")
    print("=" * 80)
    print(f"Configuration: {len(world.agents)} agents, {num_steps} steps")
    print()

    # Detailed timing buckets
    step_times = []
    action_times = []
    projectile_times = []
    world_step_times = []

    print("[BENCHMARK] Starting physics simulation...")
    print()

    total_start = time.perf_counter()

    for step in range(num_steps):
        step_start = time.perf_counter()

        # ===== ACTION PLANNING =====
        action_start = time.perf_counter()
        actions = {}

        # Team 0 moves toward team 1
        if team1_agents:
            team1_positions = [world.agent_dict[aid] for aid in team1_agents
                               if aid in world.agent_dict and
                               world.agent_dict[aid].alive]
            if team1_positions:
                centroid_x = np.mean([a.x for a in team1_positions])
                centroid_y = np.mean([a.y for a in team1_positions])

                for aid in team0_agents:
                    if aid in world.agent_dict and world.agent_dict[aid].alive:
                        agent = world.agent_dict[aid]
                        dx = centroid_x - agent.x
                        dy = centroid_y - agent.y
                        mag = np.sqrt(dx*dx + dy*dy)
                        if mag > 0.1:
                            vx = (dx / mag) * 10
                            vy = (dy / mag) * 10
                            actions[aid] = (vx, vy)

        # Team 1 moves toward team 0
        if team0_agents:
            team0_positions = [world.agent_dict[aid] for aid in team0_agents
                               if aid in world.agent_dict and
                               world.agent_dict[aid].alive]
            if team0_positions:
                centroid_x = np.mean([a.x for a in team0_positions])
                centroid_y = np.mean([a.y for a in team0_positions])

                for aid in team1_agents:
                    if aid in world.agent_dict and world.agent_dict[aid].alive:
                        agent = world.agent_dict[aid]
                        dx = centroid_x - agent.x
                        dy = centroid_y - agent.y
                        mag = np.sqrt(dx*dx + dy*dy)
                        if mag > 0.1:
                            vx = (dx / mag) * 10
                            vy = (dy / mag) * 10
                            actions[aid] = (vx, vy)

        action_time = time.perf_counter() - action_start
        action_times.append(action_time)

        # ===== PROJECTILE FIRING =====
        projectile_start = time.perf_counter()

        for agent in world.agents:
            if agent.alive and np.random.random() < 0.30:
                azimuth = np.random.uniform(0, 2*np.pi)
                loft_angle = np.random.uniform(np.pi/6, np.pi/3)
                speed = np.random.uniform(20, 35)
                world.launch_projectile(agent.agent_id, azimuth, loft_angle,
                                        speed)

        projectile_time = time.perf_counter() - projectile_start
        projectile_times.append(projectile_time)

        # ===== WORLD STEP =====
        world_step_start = time.perf_counter()
        world.step(actions)
        world_step_time = time.perf_counter() - world_step_start
        world_step_times.append(world_step_time)

        step_time = time.perf_counter() - step_start
        step_times.append(step_time)

        # Progress output every 50 steps
        if (step + 1) % 50 == 0:
            avg_step = np.mean(step_times[-50:])
            steps_per_sec = 1.0 / avg_step if avg_step > 0 else 0
            print(f"Step {step+1:3d}/{num_steps}: "
                  f"avg={avg_step*1000:.2f}ms ({steps_per_sec:,.0f} steps/sec) | "
                  f"agents={len(world.agents)} | "
                  f"projectiles={len(world.projectiles)}")

    total_time = time.perf_counter() - total_start

    print()
    print("=" * 80)
    print("BENCHMARK RESULTS")
    print("=" * 80)
    print()

    # Overall statistics
    total_steps = num_steps
    avg_step_time = np.mean(step_times)
    min_step_time = np.min(step_times)
    max_step_time = np.max(step_times)
    std_step_time = np.std(step_times)
    steps_per_sec = total_steps / total_time

    print(f"Total Execution Time: {total_time:.3f} seconds")
    print(f"Total Steps: {total_steps}")
    print(f"Overall Performance: {steps_per_sec:,.1f} steps/sec")
    print()

    print("Step Timing Statistics:")
    print(f"  Average: {avg_step_time*1000:.3f} ms/step")
    print(f"  Min:     {min_step_time*1000:.3f} ms/step (step {np.argmin(step_times)+1})")
    print(f"  Max:     {max_step_time*1000:.3f} ms/step (step {np.argmax(step_times)+1})")
    print(f"  Std Dev: {std_step_time*1000:.3f} ms")
    print()

    # Component breakdown
    avg_action_time = np.mean(action_times)
    avg_projectile_time = np.mean(projectile_times)
    avg_world_step_time = np.mean(world_step_times)

    total_component_time = (avg_action_time + avg_projectile_time +
                            avg_world_step_time)

    action_pct = (avg_action_time / total_component_time) * 100
    projectile_pct = (avg_projectile_time / total_component_time) * 100
    world_pct = (avg_world_step_time / total_component_time) * 100

    print("Component Breakdown (average per step):")
    print(f"  Action Planning:   {avg_action_time*1000:.3f} ms ({action_pct:.1f}%)")
    print(f"  Projectile Fire:   {avg_projectile_time*1000:.3f} ms ({projectile_pct:.1f}%)")
    print(f"  World Step:        {avg_world_step_time*1000:.3f} ms ({world_pct:.1f}%)")
    print("  ────────────────────────────────")
    print(f"  Total:             {total_component_time*1000:.3f} ms (100.0%)")
    print()

    # Final state
    print("Final Simulation State:")
    blue_alive = sum(1 for a in world.agents if a.team == 0 and a.alive)
    red_alive = sum(1 for a in world.agents if a.team == 1 and a.alive)
    print(f"  Blue agents alive: {blue_alive}/{num_agents_per_team}")
    print(f"  Red agents alive:  {red_alive}/{num_agents_per_team}")
    print(f"  Total projectiles: {len(world.projectiles)}")
    print(f"  In-flight missiles: {len(world.in_flight_projectiles)}")
    print()

    return {
        'total_time': total_time,
        'total_steps': total_steps,
        'steps_per_sec': steps_per_sec,
        'avg_step_ms': avg_step_time * 1000,
        'step_times': step_times,
        'action_times': action_times,
        'projectile_times': projectile_times,
        'world_step_times': world_step_times,
    }


if __name__ == '__main__':
    benchmark_physics_only(num_steps=300, num_agents_per_team=50)
