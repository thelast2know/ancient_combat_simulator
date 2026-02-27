"""
Projectile physics for Phase 2: ballistic trajectories (no drag).

Features:
- Simple ballistic integration: x(t) = x0 + vx*t, y(t) = y0 + vy*t, z(t) = z0 + vz*t - 0.5*g*t²
- Ground impact detection (flat terrain only for Phase 2)
- Replay-safe: trajectory determined entirely by initial state and RNG seed
- Event logging on impact
"""

import numpy as np
from typing import Tuple, Optional, List
from dataclasses import dataclass
from enum import Enum


class ProjectileState(Enum):
    """Lifecycle state of a projectile."""
    IN_FLIGHT = "in_flight"
    GROUND_IMPACT = "ground_impact"
    TERRAIN_IMPACT = "terrain_impact"
    EXPIRED = "expired"  # Out of bounds or too old


@dataclass
class Projectile:
    """
    Single projectile instance with full ballistic state.
    
    All units in SI (meters, seconds, m/s).
    """
    
    projectile_id: int
    launcher_id: int  # Agent ID who launched
    launcher_team: int  # Team of launcher (for friendly fire tracking)
    
    # Initial conditions (at spawn)
    x0: float
    y0: float
    z0: float
    vx: float  # Initial velocity x-component
    vy: float  # Initial velocity y-component
    vz: float  # Initial velocity z-component
    
    # Gravity and environment
    gravity: float = 9.81  # m/s^2
    
    # State tracking
    time_alive: float = 0.0  # Cumulative integration time
    state: ProjectileState = ProjectileState.IN_FLIGHT
    
    # Trajectory history (for visualization)
    trajectory: List[Tuple[float, float, float]] = None  # [(x, y, z), ...]
    impact_pos: Optional[Tuple[float, float, float]] = None  # Where it hit
    impact_velocity: Optional[Tuple[float, float, float]] = None  # Velocity at impact
    
    def __post_init__(self):
        """Initialize trajectory history."""
        if self.trajectory is None:
            self.trajectory = [(self.x0, self.y0, self.z0)]
    
    def position(self) -> Tuple[float, float, float]:
        """Get current position (x, y, z)."""
        # If projectile has impacted, return impact position (frozen)
        if self.state != ProjectileState.IN_FLIGHT and self.impact_pos is not None:
            return self.impact_pos
        
        # Otherwise compute based on trajectory
        t = self.time_alive
        x = self.x0 + self.vx * t
        y = self.y0 + self.vy * t
        z = self.z0 + self.vz * t - 0.5 * self.gravity * t * t
        return (x, y, z)
    
    def velocity(self) -> Tuple[float, float, float]:
        """Get current velocity (vx, vy, vz)."""
        # If projectile has impacted, return velocity at impact (frozen)
        if self.state != ProjectileState.IN_FLIGHT and self.impact_velocity is not None:
            return self.impact_velocity
        
        # Otherwise compute based on time
        t = self.time_alive
        vx = self.vx
        vy = self.vy
        vz = self.vz - self.gravity * t  # Update z-velocity with gravity
        return (vx, vy, vz)
    
    def step(self, dt: float, terrain_height_func=None) -> bool:
        """
        Integrate projectile motion by dt seconds.
        
        Args:
            dt: timestep (seconds)
            terrain_height_func: callable (x, y) -> z for terrain elevation
                                If None, assume flat ground (z=0)
        
        Returns:
            True if projectile is still in flight, False if impacted/expired
        """
        if self.state != ProjectileState.IN_FLIGHT:
            return False
        
        # Record old position
        old_x, old_y, old_z = self.position()
        
        # Integrate time
        self.time_alive += dt
        
        # Get new position
        new_x, new_y, new_z = self.position()
        
        # Determine ground level at impact location
        if terrain_height_func is not None:
            ground_z = terrain_height_func(new_x, new_y)
        else:
            ground_z = 0.0  # Flat ground
        
        # Check for impact with ground
        # Projectile impacts if:
        # 1. Current z <= ground_z (passed through ground plane)
        # 2. Was above ground previously (old_z > ground_z)
        if new_z <= ground_z and old_z > ground_z:
            # Compute exact impact time within this step via linear interpolation
            # z(t) = z0 + vz*t - 0.5*g*t^2
            # Solve: z(t_impact) = ground_z
            # This gives: t_impact such that position = (x, y, ground_z)
            
            impact_time = self._compute_impact_time(old_z, ground_z, dt)
            
            # Set impact position
            t_impact = self.time_alive - dt + impact_time
            x_impact = self.x0 + self.vx * t_impact
            y_impact = self.y0 + self.vy * t_impact
            self.impact_pos = (x_impact, y_impact, ground_z)
            
            # Set impact velocity (frozen at moment of impact)
            vx_impact = self.vx
            vy_impact = self.vy
            vz_impact = self.vz - self.gravity * t_impact
            self.impact_velocity = (vx_impact, vy_impact, vz_impact)
            
            # Add impact point to trajectory
            self.trajectory.append(self.impact_pos)
            
            # Mark as impacted
            self.state = ProjectileState.GROUND_IMPACT
            return False
        
        # Add current position to trajectory
        self.trajectory.append((new_x, new_y, new_z))
        
        # Check bounds (out of map)
        # Assume 0-100m in x and y (parameterize later)
        if (new_x < -10 or new_x > 110 or new_y < -10 or new_y > 110 or
                new_z < -50):  # Projectile went way underground
            self.state = ProjectileState.EXPIRED
            return False
        
        return True
    
    def _compute_impact_time(self, old_z: float, ground_z: float, dt: float) -> float:
        """
        Compute exact impact time within step [0, dt].
        
        Solves: z(t) = z0 + vz*t - 0.5*g*t^2 = ground_z
        Rearrange: -0.5*g*t^2 + vz*t + (z0 - ground_z) = 0
        
        Uses quadratic formula, returns t in [0, dt].
        """
        # At start of step: z = old_z, vz from previous step
        # We need to be careful: time_alive already advanced
        # So we solve relative to step start
        
        # vz at step start
        t_step_start = self.time_alive - dt
        vz_start = self.vz - self.gravity * t_step_start
        
        # Quadratic: -0.5*g*t^2 + vz_start*t + (old_z - ground_z) = 0
        a = -0.5 * self.gravity
        b = vz_start
        c = old_z - ground_z
        
        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            # No real solution (shouldn't happen if we detected impact)
            return dt
        
        t1 = (-b + np.sqrt(discriminant)) / (2 * a)
        t2 = (-b - np.sqrt(discriminant)) / (2 * a)
        
        # Choose positive root closest to 0
        valid_times = [t for t in [t1, t2] if 0 <= t <= dt]
        if valid_times:
            return min(valid_times)
        else:
            # Fallback: return dt (shouldn't happen)
            return dt
    
    def flight_time_to_impact(self) -> float:
        """Compute time to ground impact (ignoring terrain)."""
        # Solve: z(t) = z0 + vz*t - 0.5*g*t^2 = 0
        # -0.5*g*t^2 + vz*t + z0 = 0
        a = -0.5 * self.gravity
        b = self.vz
        c = self.z0
        
        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            return float('inf')  # Never hits
        
        t1 = (-b + np.sqrt(discriminant)) / (2 * a)
        t2 = (-b - np.sqrt(discriminant)) / (2 * a)
        
        # Return positive root (launched upward: t1 is later impact)
        valid = [t for t in [t1, t2] if t > 0]
        return min(valid) if valid else float('inf')
    
    def range_on_level_ground(self) -> float:
        """
        Compute horizontal range on level ground (z0=0).
        
        Range = (v_horizontal * flight_time)
        """
        t_flight = self.flight_time_to_impact()
        if t_flight == float('inf'):
            return 0.0
        
        v_horiz = np.sqrt(self.vx * self.vx + self.vy * self.vy)
        return v_horiz * t_flight


class ProjectileFactory:
    """Factory for creating projectiles with canonical parameters."""
    
    def __init__(self, gravity: float = 9.81):
        self.gravity = gravity
        self._next_id = 0
    
    def launch(self, launcher_id: int, launcher_team: int,
               x0: float, y0: float, z0: float,
               azimuth: float, loft_angle: float, speed: float) -> Projectile:
        """
        Create and return a projectile launched with polar coords.
        
        Args:
            launcher_id: Agent who threw
            launcher_team: Team of launcher
            x0, y0, z0: Launch position
            azimuth: Direction in XY plane (radians, 0 = +X direction)
            loft_angle: Elevation angle (radians, 0 = horizontal, pi/2 = straight up)
            speed: Initial speed (m/s)
        
        Returns:
            Projectile instance
        """
        # Convert polar to cartesian
        vx = speed * np.cos(loft_angle) * np.cos(azimuth)
        vy = speed * np.cos(loft_angle) * np.sin(azimuth)
        vz = speed * np.sin(loft_angle)
        
        proj = Projectile(
            projectile_id=self._next_id,
            launcher_id=launcher_id,
            launcher_team=launcher_team,
            x0=x0, y0=y0, z0=z0,
            vx=vx, vy=vy, vz=vz,
            gravity=self.gravity
        )
        self._next_id += 1
        return proj
    
    def launch_cartesian(self, launcher_id: int, launcher_team: int,
                         x0: float, y0: float, z0: float,
                         vx: float, vy: float, vz: float) -> Projectile:
        """
        Create projectile with direct cartesian velocity.
        
        Args:
            launcher_id, launcher_team: Origin info
            x0, y0, z0: Launch position
            vx, vy, vz: Velocity components
        
        Returns:
            Projectile instance
        """
        proj = Projectile(
            projectile_id=self._next_id,
            launcher_id=launcher_id,
            launcher_team=launcher_team,
            x0=x0, y0=y0, z0=z0,
            vx=vx, vy=vy, vz=vz,
            gravity=self.gravity
        )
        self._next_id += 1
        return proj
