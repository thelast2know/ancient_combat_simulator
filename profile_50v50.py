#!/usr/bin/env python3
"""Profile 50v50 combat scenario to identify performance at scale.

Optimized profile script that separates simulation from I/O:
- Pure physics simulation without any rendering or console output in the loop
- Deferred statistics reporting at end
"""
import cProfile
import pstats
from io import StringIO
import numpy as np
from sim.core.world import World
from sim.core.params import GlobalParams


def run_large_scenario(num_steps=500, num_agents_per_team=50):
    """Run 50v50 scenario without visualization for profiling.

    Pure physics simulation - no I/O, no rendering, minimal output.
    """
    params = GlobalParams()
    world = World(params)

    # Add 100 agents total
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

    # Run simulation
    for step in range(num_steps):
        # Agent movement toward enemies
        actions = {}

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

        # Projectile fire
        for agent in world.agents:
            if agent.alive and np.random.random() < 0.30:
                azimuth = np.random.uniform(0, 2*np.pi)
                loft_angle = np.random.uniform(np.pi/6, np.pi/3)
                speed = np.random.uniform(20, 35)
                world.launch_projectile(agent.agent_id, azimuth, loft_angle, speed)

        world.step(actions)

    return world


if __name__ == '__main__':
    print("=" * 80)
    print("PROFILING 50v50 COMBAT SCENARIO (500 steps)")
    print("=" * 80)
    print()

    profiler = cProfile.Profile()
    profiler.enable()

    world = run_large_scenario(num_steps=500, num_agents_per_team=50)

    profiler.disable()

    print("Simulation complete!")
    print(f"  Final state: {len(world.agents)} agents, {len(world.projectiles)} projectiles")
    print()
    print("=" * 80)
    print("TOP 25 TIME-CONSUMING FUNCTIONS (by cumulative time)")
    print("=" * 80)

    s = StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(25)
    print(s.getvalue())

    print()
    print("=" * 80)
    print("TOP 25 BY INTERNAL TIME (excluding sub-calls)")
    print("=" * 80)

    s = StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('time')
    ps.print_stats(25)
    print(s.getvalue())
