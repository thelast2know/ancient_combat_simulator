#!/usr/bin/env python3
"""Profile the simulation to identify performance bottlenecks"""
import cProfile
import pstats
from io import StringIO
from sim.core.world import World
from sim.core.params import GlobalParams
from sim.core.projectile import ProjectileFactory
import numpy as np


def run_simulation(num_steps=1000, num_agents=6, projectile_spawn_rate=0.2):
    """Run a simulation scenario for profiling"""
    params = GlobalParams()
    world = World(params)
    
    # Add agents (3v3 teams)
    for i in range(num_agents // 2):
        world.add_agent(team=0, x=10 + i*5, y=50 + (i-1)*10,
                        attributes={'health': 100, 'range': 30})
    for i in range(num_agents // 2):
        world.add_agent(team=1, x=90 - i*5, y=50 + (i-1)*10,
                        attributes={'health': 100, 'range': 30})
    
    factory = ProjectileFactory()
    step_count = 0
    
    # Run simulation
    for step in range(num_steps):
        # Randomly spawn projectiles
        if np.random.random() < projectile_spawn_rate and len(world.agents) > 0:
            agent = world.agents[np.random.randint(0, len(world.agents))]
            if agent.alive:
                proj = factory.launch(
                    launcher_id=agent.agent_id,
                    launcher_team=agent.team,
                    x0=agent.x, y0=agent.y, z0=1.8,
                    azimuth=np.random.uniform(0, 2*np.pi),
                    loft_angle=np.random.uniform(np.pi/6, np.pi/2.5),
                    speed=25
                )
                world.projectiles.append(proj)
        
        # Random agent movements
        actions = {}
        for agent in world.agents:
            if agent.alive:
                actions[agent.agent_id] = (
                    np.random.uniform(-5, 5),
                    np.random.uniform(-5, 5)
                )
        
        world.step(actions)
        step_count += 1
    
    return world, step_count


if __name__ == '__main__':
    print("Profiling simulation with 1000 steps, 6 agents, 20% projectile spawn rate...")
    print("=" * 80)
    
    # Profile the simulation
    profiler = cProfile.Profile()
    profiler.enable()
    
    world, steps = run_simulation(num_steps=1000, num_agents=6, projectile_spawn_rate=0.2)
    
    profiler.disable()
    
    # Print stats
    print(f"\nCompleted {steps} simulation steps")
    print(f"Final projectile count: {len(world.projectiles)}")
    print(f"Final agent count: {len(world.agents)}")
    print("\n" + "=" * 80)
    print("TOP 20 TIME-CONSUMING FUNCTIONS:")
    print("=" * 80)
    
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(20)
    print(s.getvalue())
    
    # Also sort by total time in function
    print("\n" + "=" * 80)
    print("TOP 20 BY INTERNAL TIME (excluding sub-calls):")
    print("=" * 80)
    
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('time')
    ps.print_stats(20)
    print(s.getvalue())
