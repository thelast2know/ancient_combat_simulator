#!/usr/bin/env python3
"""Profiling Analysis and Optimization Report"""

analysis = """
PROFILING RESULTS - 1000 steps, 6 agents, 204 projectiles
Total time: 0.194 seconds → ~5,154 steps per second

TOP BOTTLENECKS (by cumulative time):

1. _step_projectiles() - 0.057s (29.4% of world.step)
   - Called 1000 times
   - 0.057ms per call
   - Issue: Iterates through projectile list each step
   - ~204 projectiles checked each step
   
2. update_velocity() - 0.048s (shared among agents)
   - Called 6000 times (6 agents * 1000 steps)
   - Uses numpy.clip() heavily
   - Issue: Wrapping NumPy calls has overhead
   
3. update_heading() - 0.031s
   - Called 6000 times
   - Similar clip-based operations
   
4. Enum access (_ProjectileState.value) - 0.023s
   - Called 106,400 times!
   - Each check: proj.state.value != 'in_flight' triggers __get__
   - This is VERY expensive when done in tight loops

5. Projectile.position() - 0.009s
   - Called 12,484 times
   - Repeated calculation overhead

OPTIMIZATION OPPORTUNITIES:

Priority 1 (HIGH IMPACT):
  ✗ Enum value access is called 106k times but only takes 0.023s total
  ✗ Actually, the Enum.value property is cached after first access
  ✓ Skip optimization - not a real bottleneck

Priority 2 (MEDIUM):
  ✗ _step_projectiles iterates ALL projectiles (204)
  ✗ Most are already impacted and don't need stepping
  ✓ OPTIMIZE: Only iterate active (in-flight) projectiles

Priority 3 (LOW):
  - NumPy clip calls are already optimized
  - Agent updates are minimal
  - Projectile position calc is unavoidable

RECOMMENDED OPTIMIZATIONS:

1. Track only in-flight projectiles separately (HIGH VALUE)
   - Store in-flight in a separate list
   - Only step those (not all 204)
   - Saves ~200 projectile checks per step

2. Pre-compute velocity magnitude (MEDIUM VALUE)
   - Cache v_mag in Projectile after step
   - Avoid sqrt() recalculation in renderer
   
3. Use cached state enum rather than repeated lookups (LOW VALUE)
   - Python caches enum access anyway
"""

print(analysis)
