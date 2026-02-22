# Phase 2 Roadmap: Projectile Lifecycle

## Status: Ready to Begin

Phase 1 is complete and all core simulation infrastructure is in place. Phase 2 focuses on adding projectile physics and ballistics.

## Phase 2 Objectives

### Deliverables
- `Projectile` class with ballistic trajectory calculation
- Launch API: agents can spawn projectiles with initial velocity
- Ground impact detection (flat terrain for Phase 2)
- Projectile persistence (projectiles remain after landing)
- Optional: recovery system placeholder

### Physics Model
```
Initial velocity:
  v0 = [vx, vy, vz]

Ballistic motion (no drag):
  x(t) = x0 + vx * t
  y(t) = y0 + vy * t
  z(t) = z0 + vz * t - 0.5 * g * t²

Impact when z(t) ≤ terrain_height(x(t), y(t))
```

### Integration Points
- `World` manages projectile list (similar to agents)
- `step()` updates all projectiles
- Projectiles generate events on impact (`ProjectileLaunched`, `ProjectileImpact`)
- Renderer draws projectile arcs for visualization

## Test Strategy

### Unit Tests
- Ballistics accuracy on flat ground
  - Range tests: 45° loft, various strengths
  - Flight time validation
  - Determinism: same launch → identical trajectory
- Impact detection
  - Ground impact coordinates
  - Multiple projectiles independent
- Replay correctness

### Validation Scenarios
1. **Single throw**: One agent launches projectile
   - Verify arc visualization
   - Check impact point accuracy

2. **Range sweep**: Loft angles 10°–80° at fixed throw strength
   - Measure range variation
   - Compare with analytical predictions

3. **Multiple projectiles**: 5 agents each throw once
   - Check no collisions/overlaps between projectiles
   - Verify independent impact events

## Implementation Plan

### Step 1: Projectile Class
```python
# sim/core/projectile.py

class Projectile:
    def __init__(self, projectile_id, x0, y0, z0, vx, vy, vz, 
                 team, owner_id, params):
        self.x, self.y, self.z = x0, y0, z0
        self.vx, self.vy, self.vz = vx, vy, vz
        self.team = team
        self.owner_id = owner_id
        self.alive = True
        self.impact_time = None
        self.impact_pos = None
    
    def integrate(self, dt):
        """Update position using ballistic motion."""
        # Update position
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.z += self.vz * dt - 0.5 * g * dt²
        
        # Update velocity
        self.vz -= g * dt
    
    def check_impact(self, terrain):
        """Check if projectile hit ground."""
        height = terrain.height(self.x, self.y)
        if self.z <= height:
            return True
        return False
```

### Step 2: World Integration
Add to `World` class:
```python
self.projectiles: List[Projectile] = []
self.projectile_dict = {}

def launch_projectile(self, x, y, z, vx, vy, vz, team, owner_id):
    """Launch a new projectile."""
    pid = self.max_projectile_id + 1
    p = Projectile(pid, x, y, z, vx, vy, vz, team, owner_id, self.params)
    self.projectiles.append(p)
    self.projectile_dict[pid] = p
    self.events.append(Event('ProjectileLaunched', owner_id, None, (x, y)))
    return pid

def step(self, actions):
    # ... existing agent stepping ...
    
    # Update projectiles
    for p in self.projectiles:
        if not p.alive:
            continue
        p.integrate(self.params.dt)
        if p.check_impact(self.terrain):
            p.alive = False
            self.events.append(Event('ProjectileImpact', None, None, (p.x, p.y), p.z))
```

### Step 3: Terrain Placeholder
```python
# sim/core/terrain.py

class Terrain:
    def __init__(self, flat: bool = True):
        self.flat = flat
    
    def height(self, x, y) -> float:
        """Return height at (x, y)."""
        if self.flat:
            return 0.0
        # Phase 15: procedural terrain
        return 0.0
```

### Step 4: Renderer Update
```python
# In Renderer2D.render():
# Draw projectile trails as polylines
for p in self.world.projectiles:
    if p.alive:
        # Draw arc
        # Draw impact marker
```

## Running Phase 2 Tests

```bash
# Run ballistics tests
pytest tests/test_ballistics.py -v

# Run full validation
python validate_phase2_quick.py

# Run scenario with visualization
python validate_phase2.py
```

## Success Criteria

✓ Projectile trajectories are deterministic  
✓ Range matches analytical formula on flat ground  
✓ Impact detection accurate to cm  
✓ Multiple projectiles independent  
✓ 100+ projectiles in flight without instability  
✓ Trajectory visualization clear and accurate  

## Estimated Effort

- Projectile class: 1 hour
- World integration: 1 hour
- Tests: 2 hours
- Visualization: 1 hour
- Validation: 1 hour

**Total: ~6 hours**

---

## Notes

- Phase 2 focuses on **ballistic correctness**, not hit detection
- Hit detection (skirmishers, infantry, shields) deferred to Phase 3–4
- Terrain system is a placeholder; fully procedural terrain in Phase 15
- Noise model (precision, fatigue affecting aim) deferred to Phase 5+
- No ammo management yet; unlimited projectiles for testing

---

**When ready, start Phase 2 by running:**
```bash
python validate_phase2_quick.py
```
