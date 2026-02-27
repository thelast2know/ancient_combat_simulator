"""
Core World and Agent classes for Phase 1: deterministic stepping with kinematics and collisions.

Data contract: all state stored in aligned NumPy arrays by agent index.
"""

import numpy as np
from typing import Tuple, List, Optional
from dataclasses import dataclass
import hashlib
import json

from .params import GlobalParams
from .projectile import Projectile
from .spatial_grid import SpatialGrid


@dataclass
class Event:
    """Compact event structure for replay and reward."""
    event_type: str  # e.g., 'collision', 'boundary_hit', etc.
    agent_id: Optional[int] = None
    target_id: Optional[int] = None
    pos: Optional[Tuple[float, float]] = None
    value: Optional[float] = None
    
    def to_dict(self):
        return {
            'event_type': self.event_type,
            'agent_id': self.agent_id,
            'target_id': self.target_id,
            'pos': self.pos,
            'value': self.value
        }


class Agent:
    """
    Base agent class holding all state for Phase 1.
    """
    
    def __init__(self, agent_id: int, team: int, x: float, y: float,
                 attributes: dict, params: GlobalParams):
        """
        Initialize an agent.
        
        Args:
            agent_id: Unique ID within world
            team: 0 (blue) or 1 (red)
            x, y: Initial position (meters)
            attributes: dict of attribute values
            params: GlobalParams
        """
        self.agent_id = agent_id
        self.team = team
        self.params = params
        
        # Kinematic state
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.heading = 0.0  # radians
        
        # Attributes
        self.strength = attributes.get('strength', 1.0)
        self.cruise_speed = attributes.get('cruise_speed', 5.0)
        self.max_speed = attributes.get('max_speed', 8.0)
        self.acceleration = attributes.get('acceleration', 2.0)
        self.agility = attributes.get('agility', 3.0)  # turn rate rad/s
        
        self.precision = attributes.get('precision', 0.7)
        self.impetuousness = attributes.get('impetuousness', 0.5)
        self.timidity = attributes.get('timidity', 0.5)
        
        # Control state
        self.desired_vx = 0.0
        self.desired_vy = 0.0
        
        self.alive = True
    
    def update_heading(self, desired_vx: float, desired_vy: float, dt: float):
        """
        Update heading toward desired velocity direction.
        Limited by agility (turn rate).
        """
        if desired_vx == 0 and desired_vy == 0:
            return
        
        desired_heading = np.arctan2(desired_vy, desired_vx)
        angle_diff = desired_heading - self.heading
        
        # Normalize to [-pi, pi]
        angle_diff = np.arctan2(np.sin(angle_diff), np.cos(angle_diff))
        
        # Clamp by max turn rate
        max_turn = self.agility * dt
        angle_diff = np.clip(angle_diff, -max_turn, max_turn)
        
        self.heading += angle_diff
    
    def update_velocity(self, desired_vx: float, desired_vy: float, dt: float):
        """
        Update velocity toward desired velocity.
        Limited by acceleration and max_speed.
        """
        desired_speed = np.sqrt(desired_vx**2 + desired_vy**2)
        desired_speed = np.clip(desired_speed, 0, self.max_speed)
        
        # Current speed
        current_speed = np.sqrt(self.vx**2 + self.vy**2)
        
        # Accelerate/decelerate
        accel_limit = self.acceleration * dt
        new_speed = np.clip(desired_speed, current_speed - accel_limit, current_speed + accel_limit)
        
        # Update velocity in heading direction
        if desired_speed > 0:
            self.vx = new_speed * np.cos(self.heading)
            self.vy = new_speed * np.sin(self.heading)
        else:
            # Decelerate toward zero
            friction = 0.95
            self.vx *= friction
            self.vy *= friction
    
    def update_position(self, dt: float):
        """Integrate position."""
        self.x += self.vx * dt
        self.y += self.vy * dt
    
    def clamp_to_arena(self, arena_width: float, arena_height: float):
        """Clamp position to arena bounds, reverse velocity if hitting boundary."""
        margin = self.params.agent_radius
        
        if self.x - margin < 0:
            self.x = margin
            self.vx = 0
        elif self.x + margin > arena_width:
            self.x = arena_width - margin
            self.vx = 0
        
        if self.y - margin < 0:
            self.y = margin
            self.vy = 0
        elif self.y + margin > arena_height:
            self.y = arena_height - margin
            self.vy = 0
    
    def distance_to(self, other: "Agent") -> float:
        """Euclidean distance to another agent."""
        dx = self.x - other.x
        dy = self.y - other.y
        return np.sqrt(dx**2 + dy**2)
    
    def overlaps(self, other: "Agent") -> bool:
        """Check if this agent overlaps with another."""
        return self.distance_to(other) < 2 * self.params.agent_radius
    
    def launch_projectile(self, azimuth: float, loft_angle: float, speed: float):
        """
        Launch a projectile from this agent's position.
        
        Args:
            azimuth: Direction in XY plane (radians)
            loft_angle: Elevation angle (radians)
            speed: Initial speed (m/s)
        
        Returns:
            Projectile instance (caller must add to World)
        """
        from .projectile import Projectile
        import numpy as np
        
        # Compute velocity components from polar coords
        vx = speed * np.cos(loft_angle) * np.cos(azimuth)
        vy = speed * np.cos(loft_angle) * np.sin(azimuth)
        vz = speed * np.sin(loft_angle)
        
        proj = Projectile(
            projectile_id=-1,  # Will be assigned by World
            launcher_id=self.agent_id,
            launcher_team=self.team,
            x0=self.x,
            y0=self.y,
            z0=1.0,  # Throw from ~shoulder height
            vx=vx,
            vy=vy,
            vz=vz,
            gravity=self.params.gravity
        )
        return proj
    
    def state_tuple(self) -> tuple:
        """Return state as tuple for hashing."""
        return (
            self.x, self.y, self.vx, self.vy, self.heading,
            self.desired_vx, self.desired_vy, self.alive
        )


class InfantryBlock:
    """
    Static rectangular infantry unit.
    """
    
    def __init__(self, team: int, x_min: float, y_min: float, x_max: float, y_max: float):
        self.team = team
        self.x_min = min(x_min, x_max)
        self.x_max = max(x_min, x_max)
        self.y_min = min(y_min, y_max)
        self.y_max = max(y_min, y_max)
    
    def contains(self, x: float, y: float) -> bool:
        """Check if point is inside block."""
        return (self.x_min <= x <= self.x_max and
                self.y_min <= y <= self.y_max)
    
    def distance_to_boundary(self, x: float, y: float) -> float:
        """Compute distance from point to nearest boundary of block."""
        if self.contains(x, y):
            return 0.0
        
        # Clamp point to rectangle
        cx = np.clip(x, self.x_min, self.x_max)
        cy = np.clip(y, self.y_min, self.y_max)
        
        dx = x - cx
        dy = y - cy
        return np.sqrt(dx**2 + dy**2)
    
    def center(self) -> Tuple[float, float]:
        """Return center of block."""
        return ((self.x_min + self.x_max) / 2, (self.y_min + self.y_max) / 2)


class World:
    """
    Core simulation world. Manages agents, collisions, boundaries, and stepping.
    
    Data contract:
    - All agent state in aligned arrays by agent_id
    - One event list per step
    - Deterministic under fixed seed
    """
    
    def __init__(self, params: GlobalParams, seed: Optional[int] = None):
        self.params = params
        self.rng = np.random.RandomState(seed)
        self.seed_value = seed
        
        self.agents: List[Agent] = []
        self.agent_dict = {}  # agent_id -> Agent
        
        # Projectiles
        self.projectiles: List[Projectile] = []
        self.projectile_dict = {}  # projectile_id -> Projectile
        self.in_flight_projectiles: List[Projectile] = []  # Only active (in-flight) projectiles for faster stepping
        self.next_projectile_id = 0
        
        # Infantry blocks
        self.infantry_blocks: List[InfantryBlock] = []
        
        # Episode tracking
        self.step_count = 0
        self.events: List[Event] = []
        self.max_agent_id = -1
        
        # Spatial grid for collision detection optimization
        # Use fixed 10m cells for good balance between grid overhead and pair reduction
        self.spatial_grid = SpatialGrid(params.arena_width, params.arena_height, cell_size=1.0)
    
    def add_infantry_block(self, team: int, x_min: float, y_min: float, x_max: float, y_max: float):
        """Add an infantry block to the world."""
        block = InfantryBlock(team, x_min, y_min, x_max, y_max)
        self.infantry_blocks.append(block)
    
    def add_agent(self, team: int, x: float, y: float, attributes: dict) -> int:
        """
        Add an agent to the world.
        
        Returns: agent_id
        """
        agent_id = self.max_agent_id + 1
        self.max_agent_id = agent_id
        
        agent = Agent(agent_id, team, x, y, attributes, self.params)
        self.agents.append(agent)
        self.agent_dict[agent_id] = agent
        
        return agent_id
    
    def set_desired_velocity(self, agent_id: int, vx: float, vy: float):
        """Set desired velocity for an agent."""
        if agent_id in self.agent_dict:
            agent = self.agent_dict[agent_id]
            agent.desired_vx = vx
            agent.desired_vy = vy
    
    def launch_projectile(self, agent_id: int, azimuth: float, loft_angle: float, speed: float) -> int:
        """
        Launch a projectile from an agent.
        
        Args:
            agent_id: Agent launching the projectile
            azimuth: Direction in XY plane (radians)
            loft_angle: Elevation angle (radians)
            speed: Initial speed (m/s)
        
        Returns:
            projectile_id
        """
        if agent_id not in self.agent_dict:
            return -1
        
        agent = self.agent_dict[agent_id]
        proj = agent.launch_projectile(azimuth, loft_angle, speed)
        proj.projectile_id = self.next_projectile_id
        self.next_projectile_id += 1
        
        self.projectiles.append(proj)
        self.projectile_dict[proj.projectile_id] = proj
        self.in_flight_projectiles.append(proj)  # Track as in-flight for faster stepping
        
        return proj.projectile_id
    
    def _resolve_collisions(self):
        """Resolve circle-circle collisions between agents.
        
        Uses O(n²) approach for small scenarios, spatial grid for large ones.
        """
        # For scenarios with <= 150 agents, O(n²) is actually faster
        # than the overhead of grid building + querying
        if len(self.agents) <= 150:
            self._resolve_collisions_naive()
        else:
            self._resolve_collisions_spatial()
    
    def _resolve_collisions_naive(self):
        """O(n²) collision detection - faster for small scenarios."""
        min_dist = 2 * self.params.agent_radius
        min_dist_sq = min_dist * min_dist  # Squared distance for optimization
        
        for i, a in enumerate(self.agents):
            if not a.alive:
                continue
            for j in range(i + 1, len(self.agents)):
                b = self.agents[j]
                if not b.alive:
                    continue
                
                # Check overlap using squared distance (avoids sqrt)
                dx = b.x - a.x
                dy = b.y - a.y
                dist_sq = dx * dx + dy * dy
                
                if dist_sq < min_dist_sq:
                    # Now compute actual distance only if collision detected
                    dist = np.sqrt(dist_sq) if dist_sq > 0 else 0.0
                    
                    # Handle zero distance case
                    if dist == 0:
                        dx_norm, dy_norm = 1.0, 0.0
                    else:
                        dx_norm = dx / dist
                        dy_norm = dy / dist
                    
                    # Relative velocity
                    dvx = b.vx - a.vx
                    dvy = b.vy - a.vy
                    
                    # Relative velocity in collision normal
                    dvn = dvx * dx_norm + dvy * dy_norm
                    
                    # Do not resolve momentum if velocities are separating
                    if dvn < 0:
                        a.vx += dvn * dx_norm
                        a.vy += dvn * dy_norm
                        b.vx -= dvn * dx_norm
                        b.vy -= dvn * dy_norm
                    
                    # Separate to avoid overlap
                    overlap = min_dist - dist
                    sep = overlap / 2 + 0.001
                    a.x -= sep * dx
                    a.y -= sep * dy
                    b.x += sep * dx
                    b.y += sep * dy
                    
                    # Log event
                    self.events.append(Event(
                        event_type='collision',
                        agent_id=a.agent_id,
                        target_id=b.agent_id,
                        pos=(a.x, a.y)
                    ))
    
    def _resolve_collisions_spatial(self):
        """Spatial grid-based collision detection - faster for large scenarios."""
        # Get all potentially colliding pairs from spatial grid
        neighbor_pairs = self.spatial_grid.get_all_neighbor_pairs()
        
        min_dist = 2 * self.params.agent_radius
        min_dist_sq = min_dist * min_dist  # Squared distance for optimization
        
        # Check collisions only for nearby pairs
        for agent_id_a, agent_id_b in neighbor_pairs:
            a = self.agent_dict[agent_id_a]
            b = self.agent_dict[agent_id_b]
            
            if not a.alive or not b.alive:
                continue
            
            # Check overlap using squared distance (avoids sqrt)
            dx = b.x - a.x
            dy = b.y - a.y
            dist_sq = dx * dx + dy * dy
            
            if dist_sq < min_dist_sq:
                # Record this actual collision
                self.spatial_grid.record_collision()
                
                # Now compute actual distance only if collision detected
                dist = np.sqrt(dist_sq) if dist_sq > 0 else 0.0
                
                # Handle zero distance case
                if dist == 0:
                    dx_norm, dy_norm = 1.0, 0.0
                else:
                    dx_norm = dx / dist
                    dy_norm = dy / dist
                
                # Relative velocity
                dvx = b.vx - a.vx
                dvy = b.vy - a.vy
                
                # Relative velocity in collision normal
                dvn = dvx * dx_norm + dvy * dy_norm
                
                # Do not resolve momentum if velocities are separating
                if dvn < 0:
                    a.vx += dvn * dx_norm
                    a.vy += dvn * dy_norm
                    b.vx -= dvn * dx_norm
                    b.vy -= dvn * dy_norm
                
                # Separate to avoid overlap
                overlap = min_dist - dist
                sep = overlap / 2 + 0.001
                a.x -= sep * dx
                a.y -= sep * dy
                b.x += sep * dx
                b.y += sep * dy
                
                # Log event
                self.events.append(Event(
                    event_type='collision',
                    agent_id=a.agent_id,
                    target_id=b.agent_id,
                    pos=(a.x, a.y)
                ))
    
    def _step_projectiles(self):
        """Integrate projectiles and process impacts."""
        # Only step in-flight projectiles (much faster than checking all)
        impacted = []
        
        for proj in self.in_flight_projectiles:
            # Step projectile
            still_flying = proj.step(self.params.dt)
            
            if not still_flying:
                # Projectile impacted - log event and mark for removal from in-flight list
                self.events.append(Event(
                    event_type='projectile_impact',
                    agent_id=proj.launcher_id,
                    pos=proj.impact_pos
                ))
                impacted.append(proj)
        
        # Remove impacted projectiles from in-flight list (keep in projectiles for rendering)
        for proj in impacted:
            self.in_flight_projectiles.remove(proj)
    
    def step(self, actions: Optional[dict] = None) -> List[Event]:
        """
        Advance simulation by one timestep.
        
        Args:
            actions: dict of agent_id -> (desired_vx, desired_vy)
        
        Returns:
            list of Event objects generated this step
        """
        self.events = []
        
        if actions:
            for agent_id, (vx, vy) in actions.items():
                self.set_desired_velocity(agent_id, vx, vy)
        
        # Update heading and velocity for each agent
        for agent in self.agents:
            if not agent.alive:
                continue
            agent.update_heading(agent.desired_vx, agent.desired_vy, self.params.dt)
            agent.update_velocity(agent.desired_vx, agent.desired_vy, self.params.dt)
        
        # Build spatial grid for collision detection
        self.spatial_grid.clear()
        for agent in self.agents:
            if agent.alive:
                self.spatial_grid.insert(agent.agent_id, agent.x, agent.y)
        
        # Resolve collisions
        self._resolve_collisions()
        
        # Update position
        for agent in self.agents:
            if not agent.alive:
                continue
            agent.update_position(self.params.dt)
            agent.clamp_to_arena(self.params.arena_width, self.params.arena_height)
        
        # Step projectiles
        self._step_projectiles()
        
        self.step_count += 1
        return self.events
    
    def reset(self, seed: Optional[int] = None):
        """Reset world to initial state."""
        if seed is not None:
            self.rng = np.random.RandomState(seed)
            self.seed_value = seed
        
        self.agents = []
        self.agent_dict = {}
        self.projectiles = []
        self.projectile_dict = {}
        self.in_flight_projectiles = []
        self.next_projectile_id = 0
        self.step_count = 0
        self.events = []
        self.max_agent_id = -1
    
    def get_state_hash(self) -> str:
        """
        Compute a deterministic hash of world state.
        Used for regression testing.
        """
        state_list = []
        for agent in sorted(self.agents, key=lambda a: a.agent_id):
            state_list.append(agent.state_tuple())
        
        state_tuple = tuple(state_list)
        state_str = json.dumps(state_tuple, sort_keys=True)
        return hashlib.md5(state_str.encode()).hexdigest()
    
    def get_full_state_dict(self) -> dict:
        """Export full state as dictionary."""
        return {
            'step_count': self.step_count,
            'agents': [
                {
                    'agent_id': a.agent_id,
                    'team': a.team,
                    'x': a.x,
                    'y': a.y,
                    'vx': a.vx,
                    'vy': a.vy,
                    'heading': a.heading,
                    'alive': a.alive
                }
                for a in self.agents
            ],
            'events': [e.to_dict() for e in self.events]
        }
