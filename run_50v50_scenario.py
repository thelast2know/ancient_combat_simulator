#!/usr/bin/env python3
"""Run 50v50 combat scenario end-to-end with video rendering."""
import numpy as np
from pathlib import Path
from datetime import datetime
import cv2
from sim.core.world import World
from sim.core.params import GlobalParams
from sim.render.renderer2d import Renderer2D


def run_50v50_scenario_with_video(num_steps=300, output_dir='output_videos'):
    """Run 50v50 scenario and render video with smooth interpolation.
    
    Args:
        num_steps: Number of simulation steps
        output_dir: Directory to save video
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Create world
    params = GlobalParams()
    world = World(params)
    
    print("=" * 80)
    print("50v50 COMBAT SCENARIO - VIDEO GENERATION")
    print("=" * 80)
    print()
    
    # Setup agents - Team 0 (Blue) on left, Team 1 (Red) on right
    print("Setting up agents...")
    team0_agents = []
    team1_agents = []
    
    # 50 agents per team, arranged in grid
    for i in range(50):
        x = 10 + (i % 10) * 4
        y = 20 + (i // 10) * 8
        agent_id = world.add_agent(team=0, x=x, y=y,
                                   attributes={'health': 100, 'range': 50})
        team0_agents.append(agent_id)
    
    for i in range(50):
        x = 90 - (i % 10) * 4
        y = 20 + (i // 10) * 8
        agent_id = world.add_agent(team=1, x=x, y=y,
                                   attributes={'health': 100, 'range': 50})
        team1_agents.append(agent_id)
    
    print(f"  Team 0: {len(team0_agents)} agents")
    print(f"  Team 1: {len(team1_agents)} agents")
    print(f"  Total: {len(world.agents)} agents")
    print()
    
    # Setup renderer and video writer
    renderer = Renderer2D(world, figsize=(12, 10))
    
    # Get dimensions from first render
    first_frame = renderer.render(title="50v50 Combat Scenario")
    height, width = first_frame.shape[:2]
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_path / f'50v50_scenario_{timestamp}.mp4'
    
    # Create video writer (30 FPS)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(str(output_file), fourcc, 30, (width, height))
    
    print("Running simulation and rendering...")
    print()
    
    alive_counts = []
    
    # Main simulation loop
    for step in range(num_steps):
        if (step + 1) % 50 == 0:
            alive_team0 = sum(1 for aid in team0_agents
                            if aid in world.agent_dict and world.agent_dict[aid].alive)
            alive_team1 = sum(1 for aid in team1_agents
                            if aid in world.agent_dict and world.agent_dict[aid].alive)
            print(f"  Step {step + 1}/{num_steps}: Team 0: {alive_team0}, Team 1: {alive_team1}")
        
        # Build action dictionary for agent movement
        actions = {}
        
        # Team 0 moves toward Team 1 centroid
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
                            vx = (dx / mag) * 8
                            vy = (dy / mag) * 8
                            actions[aid] = (vx, vy)
        
        # Team 1 moves toward Team 0 centroid
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
                            vx = (dx / mag) * 8
                            vy = (dy / mag) * 8
                            actions[aid] = (vx, vy)
        
        # Projectile fire (30% chance per agent per step)
        for agent in world.agents:
            if agent.alive and np.random.random() < 0.25:
                azimuth = np.random.uniform(0, 2*np.pi)
                loft_angle = np.random.uniform(np.pi/6, np.pi/3)
                speed = np.random.uniform(20, 35)
                world.launch_projectile(agent.agent_id, azimuth, loft_angle, speed)
        
        # Step simulation
        world.step(actions)
        
        # Render frame
        alive_team0 = sum(1 for aid in team0_agents
                        if aid in world.agent_dict and world.agent_dict[aid].alive)
        alive_team1 = sum(1 for aid in team1_agents
                        if aid in world.agent_dict and world.agent_dict[aid].alive)
        alive_counts.append((alive_team0, alive_team1))
        
        title = f"50v50 Combat - Step {step + 1}/{num_steps} | Team 0: {alive_team0} | Team 1: {alive_team1}"
        frame_rgb = renderer.render(title=title)
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        video_writer.write(frame_bgr)
    
    # Clean up
    video_writer.release()
    
    # Final stats
    print()
    print("=" * 80)
    print("SIMULATION COMPLETE!")
    print("=" * 80)
    print(f"Output video: {output_file}")
    print(f"  Resolution: {width}x{height}")
    print(f"  Frames: {num_steps}")
    print(f"  Duration: {num_steps/30:.1f} seconds at 30 FPS")
    print(f"  File size: {output_file.stat().st_size / (1024*1024):.1f} MB")
    print()
    
    # Final agent counts
    final_team0 = sum(1 for aid in team0_agents
                     if aid in world.agent_dict and world.agent_dict[aid].alive)
    final_team1 = sum(1 for aid in team1_agents
                     if aid in world.agent_dict and world.agent_dict[aid].alive)
    
    print("Final State:")
    print(f"  Team 0 surviving: {final_team0}/50")
    print(f"  Team 1 surviving: {final_team1}/50")
    print(f"  Total projectiles fired: {world.projectile_count}")
    print(f"  Total collisions: {world.collision_count}")
    print()


if __name__ == '__main__':
    run_50v50_scenario_with_video(num_steps=300)
