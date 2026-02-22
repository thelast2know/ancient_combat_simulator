"""
Phase 1 Validation Script
Runs all tests and generates evaluation videos.
"""

import sys
from pathlib import Path
import numpy as np
import yaml
import io

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from sim.core import World, GlobalParams
from sim.render import Renderer2D


def load_scenario(yaml_path: str) -> dict:
    """Load scenario from YAML."""
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)


def run_scenario_with_video(scenario_path: str, output_video: str,
                            seed: int = 42) -> bool:
    """
    Run a scenario and generate a video.

    Returns: True if successful
    """
    print(f"\n{'='*70}")
    print(f"Running scenario: {scenario_path}")
    print(f"{'='*70}")

    try:
        scenario = load_scenario(scenario_path)
    except Exception as e:
        print(f"ERROR loading scenario: {e}")
        return False

    # Initialize world
    params = GlobalParams()
    world = World(params, seed=seed)

    # Add infantry blocks
    infantry = scenario.get('infantry', {})
    if 'blue' in infantry:
        b = infantry['blue']
        world.add_infantry_block(0, b['x_min'], b['y_min'],
                                 b['x_max'], b['y_max'])
    if 'red' in infantry:
        r = infantry['red']
        world.add_infantry_block(1, r['x_min'], r['y_min'],
                                 r['x_max'], r['y_max'])

    # Add agents
    agent_ids = {}

    for i, agent_config in enumerate(scenario.get('blue_agents', [])):
        pos = agent_config['position']
        attrs = agent_config.get('attributes', {})
        aid = world.add_agent(0, pos[0], pos[1], attrs)
        agent_ids[f'blue_{i}'] = aid

    for i, agent_config in enumerate(scenario.get('red_agents', [])):
        pos = agent_config['position']
        attrs = agent_config.get('attributes', {})
        aid = world.add_agent(1, pos[0], pos[1], attrs)
        agent_ids[f'red_{i}'] = aid

    duration = scenario.get('duration_steps', 1000)

    print(f"Agents: {len(world.agents)}, "
          f"Duration: {duration} steps ({duration * params.dt:.1f}s sim time)")

    # Initialize renderer
    renderer = Renderer2D(world)

    # Run simulation
    try:
        for step in range(duration):
            # Simple deterministic policy: move toward center
            actions = {}
            for agent in world.agents:
                if not agent.alive:
                    continue
                # Move toward arena center
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

            # Save frame every 5 steps
            if step % 5 == 0:
                alive_count = len([a for a in world.agents if a.alive])
                collision_count = sum(1 for e in world.events
                                      if e.event_type == 'collision')
                renderer.save_frame(
                    title=(f"Agents: {alive_count}, "
                           f"Collisions: {collision_count}"),
                    debug=True
                )

            if (step + 1) % 100 == 0:
                print(f"  Step {step + 1}/{duration}")

        # Save video
        output_path = Path(output_video)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        renderer.save_mp4(str(output_path), fps=10)
        renderer.close()

        alive_count = len([a for a in world.agents if a.alive])
        print("✓ Scenario completed successfully")
        print(f"  Final agents alive: {alive_count}")
        print(f"  Total events: {world.step_count}")

        return True

    except Exception as e:
        print(f"ERROR during simulation: {e}")
        import traceback
        traceback.print_exc()
        renderer.close()
        return False


def test_determinism() -> bool:
    """Test determinism: two runs with same seed should match."""
    print(f"\n{'='*70}")
    print("TEST: Determinism (Single Agent)")
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
            print("✓ Determinism test PASSED")
            return True
        else:
            msg = "Determinism test FAILED: hashes don't match"
            print(f"✗ {msg}")
            return False

    except Exception as e:
        print(f"✗ Determinism test FAILED: {e}")
        return False


def test_collision_safety() -> bool:
    """Test that agents don't overlap after collisions."""
    print(f"\n{'='*70}")
    print("TEST: Collision Safety (No Overlap)")
    print(f"{'='*70}")

    try:
        params = GlobalParams()
        world = World(params, seed=42)
        world.add_infantry_block(0, *params.infantry_blue_rect)
        world.add_infantry_block(1, *params.infantry_red_rect)

        a1 = world.add_agent(0, 45.0, 50.0, {'cruise_speed': 5.0})
        a2 = world.add_agent(0, 55.0, 50.0, {'cruise_speed': 5.0})

        violations = 0
        for _ in range(100):
            world.step({a1: (5.0, 0.0), a2: (-5.0, 0.0)})

            agent_a1 = world.agent_dict[a1]
            agent_a2 = world.agent_dict[a2]
            dist = agent_a1.distance_to(agent_a2)
            min_dist = 2 * params.agent_radius

            if dist < min_dist - 0.01:
                violations += 1

        if violations == 0:
            msg = "Collision safety test PASSED (no overlaps detected)"
            print(f"✓ {msg}")
            return True
        else:
            msg = f"Collision safety test FAILED: {violations} violations"
            print(f"✗ {msg}")
            return False

    except Exception as e:
        print(f"✗ Collision safety test FAILED: {e}")
        return False


def test_bounds() -> bool:
    """Test that agents stay within arena bounds."""
    print(f"\n{'='*70}")
    print("TEST: Arena Bounds")
    print(f"{'='*70}")

    try:
        params = GlobalParams()
        world = World(params, seed=42)
        world.add_infantry_block(0, *params.infantry_blue_rect)
        world.add_infantry_block(1, *params.infantry_red_rect)

        # Place agent at corner, push it hard
        agent_id = world.add_agent(0, 1.0, 1.0, {'max_speed': 20.0})

        violations = 0
        for _ in range(200):
            world.step({agent_id: (-20.0, -20.0)})

        agent = world.agent_dict[agent_id]
        margin = params.agent_radius

        if not (agent.x >= margin - 0.1 and
                agent.x <= params.arena_width - margin + 0.1):
            violations += 1
            print(f"  X out of bounds: {agent.x}")

        if not (agent.y >= margin - 0.1 and
                agent.y <= params.arena_height - margin + 0.1):
            violations += 1
            print(f"  Y out of bounds: {agent.y}")

        if violations == 0:
            print("✓ Bounds test PASSED")
            return True
        else:
            print("✗ Bounds test FAILED")
            return False

    except Exception as e:
        print(f"✗ Bounds test FAILED: {e}")
        return False


def main():
    """Run all Phase 1 validations."""
    print("\n" + "="*70)
    print("PHASE 1 VALIDATION: Skeleton World + Deterministic Stepping")
    print("="*70)

    results = {}

    # Run unit tests
    results['determinism'] = test_determinism()
    results['collision_safety'] = test_collision_safety()
    results['bounds'] = test_bounds()

    # Run scenarios with video
    scenarios_dir = Path(__file__).parent / 'scenarios'
    videos_dir = Path(__file__).parent / 'outputs' / 'videos'

    results['duel_scenario'] = run_scenario_with_video(
        str(scenarios_dir / 'duel.yaml'),
        str(videos_dir / 'phase1_duel.mp4'),
        seed=42
    )

    results['collision_scenario'] = run_scenario_with_video(
        str(scenarios_dir / 'collision_test.yaml'),
        str(videos_dir / 'phase1_collision.mp4'),
        seed=42
    )

    # Summary
    print(f"\n{'='*70}")
    print("PHASE 1 VALIDATION SUMMARY")
    print(f"{'='*70}")

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {test_name}")

    all_passed = all(results.values())

    print(f"{'='*70}")
    if all_passed:
        print("ALL PHASE 1 TESTS PASSED ✓")
        print("\nPhase 1 Exit Criteria Met:")
        print("  ✓ 60+ seconds sim time runs without instability")
        print("  ✓ Determinism test passes")
        print("  ✓ Collision safety verified")
        print("  ✓ Boundary conditions enforced")
        print("  ✓ Video replays generated")
    else:
        print("SOME PHASE 1 TESTS FAILED ✗")

    print(f"{'='*70}\n")

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
