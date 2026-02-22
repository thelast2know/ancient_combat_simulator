#!/usr/bin/env python3
"""Debug script to check if agents are actually moving."""

import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import numpy as np
from sim.core import World, GlobalParams

params = GlobalParams()
world = World(params, seed=42)

# Add a single agent
agent_id = world.add_agent(0, 25.0, 50.0, {'cruise_speed': 5.0})

print(f"Initial state:")
agent = world.agents[0]
print(f"  Position: ({agent.x:.2f}, {agent.y:.2f})")
print(f"  Velocity: ({agent.vx:.2f}, {agent.vy:.2f})")
print(f"  Desired Velocity: ({agent.desired_vx:.2f}, {agent.desired_vy:.2f})")
print(f"  Cruise Speed: {agent.cruise_speed:.2f}")
print(f"  dt: {params.dt}")

# Run a few steps with movement toward center
cx, cy = params.arena_width / 2, params.arena_height / 2

for step in range(5):
    # Calculate direction to center
    dx = cx - agent.x
    dy = cy - agent.y
    dist = np.sqrt(dx**2 + dy**2)
    
    if dist > 0:
        vx = (dx / dist) * agent.cruise_speed
        vy = (dy / dist) * agent.cruise_speed
    else:
        vx, vy = 0, 0
    
    print(f"\nStep {step + 1}:")
    print(f"  Distance to center: {dist:.2f}")
    print(f"  Setting desired velocity: ({vx:.2f}, {vy:.2f})")
    
    # Set desired velocity
    world.set_desired_velocity(agent_id, vx, vy)
    
    print(f"  Agent desired velocity after set: ({agent.desired_vx:.2f}, {agent.desired_vy:.2f})")
    
    # Step
    world.step({agent_id: (vx, vy)})
    
    print(f"  Position after step: ({agent.x:.2f}, {agent.y:.2f})")
    print(f"  Actual velocity after step: ({agent.vx:.2f}, {agent.vy:.2f})")
