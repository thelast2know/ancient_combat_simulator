"""
Phase 1 Quick Validation (without heavy video generation)
Tests core functionality needed before proceeding to Phase 2.
"""

import sys
from pathlib import Path
import numpy as np
import yaml

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sim.core import World, GlobalParams


def test_determinism() -> bool:
    """Test determinism: two runs with same seed should match."""
    print(f"\n{'='*70}")
    print("TEST 1: Determinism (Single Agent)")
    print(f"{'='*70}")
    
    try:
        params = GlobalParams()
        
        # Run 1
        world1 = World(params, seed=42)
        world1.add_infantry_block(0, *params.infantry_blue_rect)
        world1.add_infantry_block(1, *params.infantry_red_rect)
        a1 = world1.add_agent(0, 50.0, 50.0, {'cruise_speed': 5.0})
        
        hashes1 = []
        for _ in range(100):
            world1.step({a1: (5.0, 0.0)})
            hashes1.append(world1.get_state_hash())
        
        # Run 2
        world2 = World(params, seed=42)
        world2.add_infantry_block(0, *params.infantry_blue_rect)
        world2.add_infantry_block(1, *params.infantry_red_rect)
        a2 = world2.add_agent(0, 50.0, 50.0, {'cruise_speed': 5.0})
        
        hashes2 = []
        for _ in range(100):
            world2.step({a2: (5.0, 0.0)})
            hashes2.append(world2.get_state_hash())
        
        if hashes1 == hashes2:
            print("✓ PASSED: Determinism verified across 100 steps")
            print(f"  Final position (run 1): ({world1.agent_dict[a1].x:.2f}, {world1.agent_dict[a1].y:.2f})")
            print(f"  Final position (run 2): ({world2.agent_dict[a2].x:.2f}, {world2.agent_dict[a2].y:.2f})")
            return True
        else:
            print("✗ FAILED: Hashes don't match")
            return False
    
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multi_agent_determinism() -> bool:
    """Test determinism with multiple agents."""
    print(f"\n{'='*70}")
    print("TEST 2: Multi-Agent Determinism")
    print(f"{'='*70}")
    
    try:
        params = GlobalParams()
        
        # Run 1
        world1 = World(params, seed=123)
        world1.add_infantry_block(0, *params.infantry_blue_rect)
        world1.add_infantry_block(1, *params.infantry_red_rect)
        
        ids_1 = [
            world1.add_agent(0, 30.0, 40.0, {'cruise_speed': 5.0}),
            world1.add_agent(0, 35.0, 45.0, {'cruise_speed': 5.0}),
            world1.add_agent(1, 70.0, 40.0, {'cruise_speed': 5.0}),
        ]
        
        hashes1 = []
        for _ in range(50):
            actions = {ids_1[i]: (5.0 if i % 2 == 0 else -5.0, 0.0) for i in range(len(ids_1))}
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
        ]
        
        hashes2 = []
        for _ in range(50):
            actions = {ids_2[i]: (5.0 if i % 2 == 0 else -5.0, 0.0) for i in range(len(ids_2))}
            world2.step(actions)
            hashes2.append(world2.get_state_hash())
        
        if hashes1 == hashes2:
            print("✓ PASSED: Multi-agent determinism verified")
            print(f"  Agents: {len(world1.agents)}, Steps: 50")
            return True
        else:
            print("✗ FAILED: Hashes don't match")
            return False
    
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_collision_safety() -> bool:
    """Test that agents don't overlap after collisions."""
    print(f"\n{'='*70}")
    print("TEST 3: Collision Safety (No Penetration)")
    print(f"{'='*70}")
    
    try:
        params = GlobalParams()
        world = World(params, seed=42)
        world.add_infantry_block(0, *params.infantry_blue_rect)
        world.add_infantry_block(1, *params.infantry_red_rect)
        
        a1 = world.add_agent(0, 45.0, 50.0, {'cruise_speed': 5.0})
        a2 = world.add_agent(0, 55.0, 50.0, {'cruise_speed': 5.0})
        
        min_dist_observed = float('inf')
        violations = 0
        for _ in range(100):
            world.step({a1: (5.0, 0.0), a2: (-5.0, 0.0)})
            
            agent_a1 = world.agent_dict[a1]
            agent_a2 = world.agent_dict[a2]
            dist = agent_a1.distance_to(agent_a2)
            min_dist_observed = min(min_dist_observed, dist)
            min_dist = 2 * params.agent_radius
            
            if dist < min_dist - 0.01:
                violations += 1
        
        if violations == 0:
            print("✓ PASSED: No overlaps detected")
            print(f"  Min distance observed: {min_dist_observed:.4f} m")
            print(f"  Min allowed distance: {2 * params.agent_radius:.4f} m")
            print(f"  100 collision steps executed safely")
            return True
        else:
            print(f"✗ FAILED: {violations} overlap violations detected")
            return False
    
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_arena_bounds() -> bool:
    """Test that agents stay within arena bounds."""
    print(f"\n{'='*70}")
    print("TEST 4: Arena Bounds Enforcement")
    print(f"{'='*70}")
    
    try:
        params = GlobalParams()
        world = World(params, seed=42)
        world.add_infantry_block(0, *params.infantry_blue_rect)
        world.add_infantry_block(1, *params.infantry_red_rect)
        
        # Place agent at corner, push it hard outward
        agent_id = world.add_agent(0, 1.0, 1.0, {'max_speed': 20.0})
        
        for _ in range(200):
            world.step({agent_id: (-20.0, -20.0)})
        
        agent = world.agent_dict[agent_id]
        margin = params.agent_radius
        
        violations = 0
        if not (agent.x >= margin - 0.1):
            violations += 1
            print(f"  X violation: {agent.x} < {margin}")
        
        if not (agent.x <= params.arena_width - margin + 0.1):
            violations += 1
            print(f"  X violation: {agent.x} > {params.arena_width - margin}")
        
        if not (agent.y >= margin - 0.1):
            violations += 1
            print(f"  Y violation: {agent.y} < {margin}")
        
        if not (agent.y <= params.arena_height - margin + 0.1):
            violations += 1
            print(f"  Y violation: {agent.y} > {params.arena_height - margin}")
        
        if violations == 0:
            print("✓ PASSED: Bounds respected")
            print(f"  Final position: ({agent.x:.2f}, {agent.y:.2f})")
            print(f"  Arena bounds: [0, {params.arena_width}] x [0, {params.arena_height}]")
            return True
        else:
            print(f"✗ FAILED: {violations} bounds violations")
            return False
    
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_60_second_run() -> bool:
    """Test that 60-minute sim time (600 seconds at dt=0.1) runs without instability."""
    print(f"\n{'='*70}")
    print("TEST 5: Extended Run (60 seconds sim time)")
    print(f"{'='*70}")
    
    try:
        params = GlobalParams()
        world = World(params, seed=999)
        world.add_infantry_block(0, *params.infantry_blue_rect)
        world.add_infantry_block(1, *params.infantry_red_rect)
        
        # Add 10 agents per side
        agents = []
        for i in range(10):
            # Blue side
            agents.append(world.add_agent(0, 30.0 + i * 2, 40.0, {'cruise_speed': 5.0}))
            # Red side
            agents.append(world.add_agent(1, 70.0 - i * 2, 40.0, {'cruise_speed': 5.0}))
        
        duration_steps = 600  # 60 seconds at dt=0.1
        
        for step in range(duration_steps):
            # Simple: agents move toward arena center
            actions = {}
            for agent in world.agents:
                if not agent.alive:
                    continue
                cx, cy = params.arena_width / 2, params.arena_height / 2
                dx = cx - agent.x
                dy = cy - agent.y
                dist = np.sqrt(dx**2 + dy**2)
                if dist > 0:
                    vx = (dx / dist) * agent.cruise_speed
                    vy = (dy / dist) * agent.cruise_speed
                else:
                    vx, vy = 0, 0
                actions[agent.agent_id] = (vx, vy)
            
            world.step(actions)
            
            # Sanity check: no NaNs
            for agent in world.agents:
                if not np.isfinite(agent.x) or not np.isfinite(agent.y):
                    print(f"✗ FAILED: Non-finite position detected at step {step}")
                    return False
            
            if (step + 1) % 100 == 0:
                alive = len([a for a in world.agents if a.alive])
                print(f"  Step {step+1}/{duration_steps}: {alive} agents alive")
        
        print("✓ PASSED: 60-second run completed without instability")
        print(f"  Total steps: {world.step_count}")
        print(f"  Simulation time: {world.step_count * params.dt:.1f} seconds")
        return True
    
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Phase 1 quick tests."""
    print("\n" + "="*70)
    print("PHASE 1 VALIDATION: Skeleton World + Deterministic Stepping")
    print("  (Quick Test Suite - Core Functionality)")
    print("="*70)
    
    results = {}
    
    results['determinism'] = test_determinism()
    results['multi_agent_determinism'] = test_multi_agent_determinism()
    results['collision_safety'] = test_collision_safety()
    results['bounds'] = test_arena_bounds()
    results['extended_run'] = test_60_second_run()
    
    # Summary
    print(f"\n{'='*70}")
    print("PHASE 1 VALIDATION SUMMARY")
    print(f"{'='*70}")
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {test_name}")
    
    all_passed = all(results.values())
    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)
    
    print(f"{'='*70}")
    print(f"Result: {passed_count}/{total_count} tests passed")
    
    if all_passed:
        print("\n✓ ALL PHASE 1 CORE TESTS PASSED")
        print("\nPhase 1 Exit Criteria Met:")
        print("  ✓ Determinism verified (single and multi-agent)")
        print("  ✓ Collision safety confirmed (no agent penetration)")
        print("  ✓ Arena bounds enforced")
        print("  ✓ Extended 60-second run completed without instability")
        print("\nReady to proceed to Phase 2: Projectile Lifecycle")
    else:
        print("\n✗ SOME PHASE 1 TESTS FAILED")
        print("Address failures before proceeding to Phase 2")
    
    print(f"{'='*70}\n")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
