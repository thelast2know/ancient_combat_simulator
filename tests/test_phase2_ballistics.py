"""
Unit tests for Phase 2 projectile ballistics.

Tests:
1. Flight time calculation (analytic vs numeric)
2. Range on level ground
3. Trajectory stability across dt choices
4. Impact detection
5. Replay determinism
"""

import pytest
import numpy as np
from sim.core.projectile import Projectile, ProjectileState
from sim.core import World, GlobalParams


class TestProjectilePhysics:
    """Test basic projectile physics."""
    
    def test_flight_time_45_degrees(self):
        """Test flight time for 45° loft angle."""
        # Launch at 45° with 10 m/s from z=0
        proj = Projectile(
            projectile_id=1,
            launcher_id=0,
            launcher_team=0,
            x0=0.0, y0=0.0, z0=0.0,
            vx=10.0 / np.sqrt(2),
            vy=0.0,
            vz=10.0 / np.sqrt(2),
            gravity=9.81
        )
        
        # Analytic flight time: t = 2*vz/g
        t_expected = 2 * (10.0 / np.sqrt(2)) / 9.81
        t_actual = proj.flight_time_to_impact()
        
        assert abs(t_actual - t_expected) < 0.01, f"Expected {t_expected:.3f}s, got {t_actual:.3f}s"
    
    def test_range_45_degrees(self):
        """Test range for 45° loft (maximum range on level ground)."""
        speed = 20.0  # m/s
        loft = 45 * np.pi / 180
        
        proj = Projectile(
            projectile_id=1,
            launcher_id=0,
            launcher_team=0,
            x0=0.0, y0=0.0, z0=0.0,
            vx=speed * np.cos(loft),
            vy=0.0,
            vz=speed * np.sin(loft),
            gravity=9.81
        )
        
        # Analytic range: R = v0^2 * sin(2*theta) / g
        # At 45°: R = v0^2 / g
        range_expected = speed * speed / 9.81
        range_actual = proj.range_on_level_ground()
        
        assert abs(range_actual - range_expected) < 0.1, \
            f"Expected {range_expected:.2f}m, got {range_actual:.2f}m"
    
    def test_vertical_throw(self):
        """Test straight vertical throw."""
        proj = Projectile(
            projectile_id=1,
            launcher_id=0,
            launcher_team=0,
            x0=0.0, y0=0.0, z0=0.0,
            vx=0.0,
            vy=0.0,
            vz=10.0,
            gravity=9.81
        )
        
        t_flight = proj.flight_time_to_impact()
        # For vertical throw: t = 2*v0/g
        t_expected = 2 * 10.0 / 9.81
        
        assert abs(t_flight - t_expected) < 0.01


class TestTrajectoryIntegration:
    """Test numerical integration of trajectories."""
    
    def test_dt_consistency_45_deg(self):
        """Test that different dt values give consistent final positions."""
        speed = 15.0
        loft = 45 * np.pi / 180
        
        # Reference: small dt
        proj_ref = Projectile(
            projectile_id=1,
            launcher_id=0,
            launcher_team=0,
            x0=0.0, y0=0.0, z0=0.0,
            vx=speed * np.cos(loft),
            vy=0.0,
            vz=speed * np.sin(loft)
        )
        
        dt_small = 0.01
        while proj_ref.state == ProjectileState.IN_FLIGHT:
            proj_ref.step(dt_small)
        
        x_ref, y_ref, z_ref = proj_ref.impact_pos
        
        # Compare with larger dt
        dt_values = [0.05, 0.1, 0.2]
        for dt in dt_values:
            proj = Projectile(
                projectile_id=1,
                launcher_id=0,
                launcher_team=0,
                x0=0.0, y0=0.0, z0=0.0,
                vx=speed * np.cos(loft),
                vy=0.0,
                vz=speed * np.sin(loft)
            )
            
            while proj.state == ProjectileState.IN_FLIGHT:
                proj.step(dt)
            
            x_actual, y_actual, z_actual = proj.impact_pos
            
            # Allow small tolerance (larger dt = more error)
            error_margin = 0.5 + dt * 5  # Heuristic margin
            assert abs(x_actual - x_ref) < error_margin, \
                f"dt={dt}: X position diverged (ref={x_ref:.2f}, got={x_actual:.2f})"
    
    def test_trajectory_recorded(self):
        """Test that trajectory is properly recorded."""
        proj = Projectile(
            projectile_id=1,
            launcher_id=0,
            launcher_team=0,
            x0=10.0, y0=20.0, z0=1.0,
            vx=5.0,
            vy=0.0,
            vz=8.0
        )
        
        dt = 0.1
        steps = 0
        while proj.state == ProjectileState.IN_FLIGHT and steps < 50:
            proj.step(dt)
            steps += 1
        
        # Trajectory should have multiple points
        assert len(proj.trajectory) > 10, f"Trajectory too short: {len(proj.trajectory)} points"
        
        # First point should be start position
        assert proj.trajectory[0] == (10.0, 20.0, 1.0)
        
        # Last point should be impact position
        assert proj.trajectory[-1] == proj.impact_pos


class TestImpactDetection:
    """Test impact detection logic."""
    
    def test_impact_below_ground(self):
        """Test that projectile detects impact with ground (z=0)."""
        proj = Projectile(
            projectile_id=1,
            launcher_id=0,
            launcher_team=0,
            x0=0.0, y0=0.0, z0=2.0,
            vx=10.0,
            vy=0.0,
            vz=-5.0,  # Falling
        )
        
        # Step until impact
        dt = 0.1
        for _ in range(100):
            if not proj.step(dt):
                break
        
        # Should have impacted
        assert proj.state == ProjectileState.GROUND_IMPACT, f"State is {proj.state}"
        assert proj.impact_pos is not None
        x, y, z = proj.impact_pos
        assert z <= 0.01, f"Impact Z should be ~0, got {z}"
    
    def test_no_impact_rising(self):
        """Test that rising projectile doesn't impact."""
        proj = Projectile(
            projectile_id=1,
            launcher_id=0,
            launcher_team=0,
            x0=0.0, y0=0.0, z0=0.0,
            vx=10.0,
            vy=0.0,
            vz=15.0,  # Rising
        )
        
        # Step a few times
        dt = 0.1
        for _ in range(5):
            still_flying = proj.step(dt)
            assert still_flying, "Projectile should still be in flight"
        
        # Should not have impacted yet
        assert proj.state == ProjectileState.IN_FLIGHT


class TestWorldIntegration:
    """Test projectile integration with World."""
    
    def test_launch_and_integrate(self):
        """Test launching projectile from agent in world."""
        params = GlobalParams()
        world = World(params, seed=42)
        
        # Add thrower
        agent_id = world.add_agent(
            team=0,
            x=50.0,
            y=50.0,
            attributes={'strength': 1.0, 'cruise_speed': 5.0,
                        'max_speed': 8.0, 'acceleration': 2.0,
                        'agility': 3.0, 'precision': 0.7,
                        'impetuousness': 0.5, 'timidity': 0.5}
        )
        
        # Launch projectile
        azimuth = 0  # +X direction
        loft = 45 * np.pi / 180
        speed = 20.0
        
        proj_id = world.launch_projectile(agent_id, azimuth, loft, speed)
        
        assert proj_id >= 0
        assert len(world.projectiles) == 1
        
        # Step world until impact
        impacted = False
        for _ in range(1000):
            events = world.step()
            
            # Check for impact event
            for event in events:
                if event.event_type == 'projectile_impact':
                    impacted = True
                    break
            
            if impacted:
                break
        
        # Should have impacted and projectile should persist (not be removed)
        assert impacted, "Projectile should have impacted"
        assert len(world.projectiles) == 1, "Projectile should persist after impact"
        assert world.projectiles[0].state.value == 'ground_impact', "Projectile state should be ground_impact"
    
    def test_deterministic_replay(self):
        """Test that same world state produces same trajectories."""
        params = GlobalParams()
        seed = 123
        
        # Run 1
        world1 = World(params, seed=seed)
        agent_id = world1.add_agent(
            team=0, x=50.0, y=50.0,
            attributes={'strength': 1.0, 'cruise_speed': 5.0,
                        'max_speed': 8.0, 'acceleration': 2.0,
                        'agility': 3.0, 'precision': 0.7,
                        'impetuousness': 0.5, 'timidity': 0.5}
        )
        world1.launch_projectile(agent_id, 0, 45*np.pi/180, 20.0)
        impacts1 = []
        for _ in range(1000):
            events = world1.step()
            for event in events:
                if event.event_type == 'projectile_impact':
                    impacts1.append(event.pos)
        
        # Run 2
        world2 = World(params, seed=seed)
        agent_id = world2.add_agent(
            team=0, x=50.0, y=50.0,
            attributes={'strength': 1.0, 'cruise_speed': 5.0,
                        'max_speed': 8.0, 'acceleration': 2.0,
                        'agility': 3.0, 'precision': 0.7,
                        'impetuousness': 0.5, 'timidity': 0.5}
        )
        world2.launch_projectile(agent_id, 0, 45*np.pi/180, 20.0)
        impacts2 = []
        for _ in range(1000):
            events = world2.step()
            for event in events:
                if event.event_type == 'projectile_impact':
                    impacts2.append(event.pos)
        
        # Should match exactly
        assert len(impacts1) == len(impacts2), "Impact count mismatch"
        for (x1, y1, z1), (x2, y2, z2) in zip(impacts1, impacts2):
            assert abs(x1 - x2) < 1e-6
            assert abs(y1 - y2) < 1e-6
            assert abs(z1 - z2) < 1e-6


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
