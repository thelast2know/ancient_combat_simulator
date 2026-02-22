# Multi-Agent RL Environment Specification
## Emergent Skirmisher Tactics (Northern Greek / Macedonian Context, 380–300 BC)

---

# 1. Design Goals

Develop a 2.5D multi-agent reinforcement learning environment to explore emergent skirmisher tactics under historically plausible mechanical constraints.

Core aims:
- Emergent cohesion and formation (wedge, chevron, flying wing, etc.)
- Leader–follower hierarchy with imperfect command transmission
- Tension between individual survival/fame and unit objectives
- Fatigue, morale, and terrain influencing tactical behaviour
- Self-play driven doctrinal evolution

System must be:
- Deterministic under fixed seed
- Parallelizable for headless training
- Visually replayable from logged episodes
- Parameterized for cultural and tactical experimentation

All units use SI units.

---

# 2. Global Simulation Model

## 2.1 Coordinate System

- 2D plane (x, y), meters
- Elevation field z = height(x, y)
- Gravity: g = 9.81 m/s²
- Time step: Δt (parameterized, default 0.1 s)

## 2.2 Agent Collider

- Circular rigid body
- Radius r = 0.3 m
- Elastic collision resolution between skirmishers
- No penetration allowed

## 2.3 Infantry Blocks

Each side has one infantry block:

- Rectangular region (width × depth)
- Static in space
- Optional closing speed parameter (blocks converge over time)

Skirmisher proximity death model:

Let d = distance from skirmisher center to infantry block boundary.

If d ≤ 3 m:

P(death per timestep) = 1 − (d / 3)

If d > 3 m:

P(death) = 0

Hit scoring:
- Any projectile landing inside infantry region counts as a hit event.

---

# 3. Projectile & Ballistics Model

## 3.1 Ballistics

- No drag
- Deterministic ballistic motion after launch

Initial velocity vector:

v0 = R(θ, φ) * S

Where:
- θ = azimuth
- φ = loft angle
- S = throw strength

Projectile position:

x(t) = x0 + vx t

y(t) = y0 + vy t

z(t) = z0 + vz t − 0.5 g t²

Impact when z(t) ≤ terrain height.

## 3.2 Noise Model

Noise applied to initial velocity vector before integration.

Velocity perturbation:

v0' = v0 + N(0, Σ)

Σ depends on:
- Precision
- Fatigue
- Movement speed
- Impetuousness

Higher movement speed increases angular dispersion.

## 3.3 Shield Model (Skirmishers Only)

Each skirmisher has probability p_shield of spawning with shield.

If shielded:
- 20% survival chance on impact if incoming projectile vector lies within ±90° of left-facing hemisphere.

---

# 4. Agent Attributes

Each soldier initialized from correlated normal distributions.

Attributes:

Physical
- strength
- cruise_speed
- max_speed
- acceleration
- agility (turn rate)
- endurance

Cognitive
- precision
- impetuousness
- timidity
- reaction_time

Command
- hearing_quality
- vision_cone_angle
- voice_volume

Age evolution curves:

- Strength, acceleration: peak mid-20s (Gaussian age curve)
- Precision: linear increase with age
- Impetuousness: linear increase with age
- Agility: linear decrease

---

# 5. Fatigue & Recovery Model

Fatigue F ∈ [0, 1]

If speed > cruise_speed:

ΔF = k1 * (speed − cruise_speed)

If speed < fast_walk_threshold:

ΔF = −k2 * (fast_walk_threshold − speed)

Modifiers:
- Rough terrain increases ΔF
- Uphill increases ΔF
- Heat increases ΔF linearly until threshold, then exponentially

Effects of fatigue (non-linear beyond threshold):
- Reduced strength
- Reduced acceleration
- Reduced agility
- Reduced impetuousness
- Increased dispersion

---

# 6. Morale Model

Morale M ∈ [0, 1]

Increases with:
- Enemy skirmisher kills
- Hits on enemy infantry

Decreases with:
- Unit casualties
- Hits on friendly infantry
- Leader death (stacking penalty)

Effects:
- Alters reaction time
- Alters compliance probability
- Alters survival weighting

---

# 7. Command System

## 7.1 Hierarchy

- 1 leader per unit
- 3 successor leaders
- If all dead → automatic retreat/game over

## 7.2 Order Types

High-level discrete orders:

- ADVANCE
- RETREAT
- HOLD
- SCATTER
- WHEEL_LEFT
- WHEEL_RIGHT
- THROW_LOW
- THROW_HIGH

Leader acts event-driven.

## 7.3 Audible Transmission

Probability of reception:

P_hear = min(1, voice_volume / d²)

If 0 < P_hear < 0.1:
- Chance of corruption
- Corruption = random valid order OR no change

## 7.4 Visual Transmission

If leader or neighbor visible inside cone:
- Copy observed state change
- Errors propagate equally

Thinking delay = reaction_time modified by timidity and morale.

Compliance probability:

Reduced for high-risk orders (advance, throw) as function of timidity.

---

# 8. Action Spaces

## 8.1 Soldier Policy

Continuous:
- Desired velocity vector (vx, vy)

Discrete:
- Throw trigger (binary)

Throw uses learned aim head:
- Outputs continuous aim direction (θ, φ)

## 8.2 Leader Policy

Continuous:
- Desired velocity vector

Discrete (event-driven):
- Order selection

Separate leader network head.

---

# 9. Observation Model

Nearest-K neighbors (parameterized K).

Each entry includes:
- Relative position
- Relative velocity
- Team ID
- Alive state
- Distance to infantry

Plus self state:
- Fatigue
- Morale
- Ammo count
- Current order
- Terrain modifier

Partial observability enforced by distance limit.

---

# 10. Ammo System

Default 3 javelins.

Projectile persists after landing.

Recovery:
- If skirmisher passes within 1m
- Probability of recovery
- Breakage chance parameterized

---

# 11. Reward System

Parameterized cultural weights exposed in observation.

Event rewards:

Individual:
- Survival (positive each timestep)
- Kill enemy skirmisher
- Avoid injury

Unit:
- Enemy infantry hit
- Prevent friendly infantry hit

Leader:
- Unit infantry hits bonus
- Casualty penalty

Penalties:
- Death (individual heavy, unit moderate, leader small anti-bonus)
- Friendly infantry hit
- Shame tax (inaction > 3s, cumulative)
- Individual non-throw when ordered

Optional hit-rate penalty:
- Additional penalty proportional to rolling friendly hit rate

Sparse event-based rewards.

---

# 12. Episode Termination

Episode ends if:

- Both sides ammo exhausted
- Infantry blocks distance < 25 m
- One side eliminated
- 60-minute simulated time limit

---

# 13. Terrain System

Procedural height map (noise-based).

Discrete obstacles:
- Ditch
- Stream
- Rock clusters
- Low wall

Effects:
- Speed modifier
- Fatigue modifier
- Elevation effect on throw strength

Toggleable.

---

# 14. RL Framework Recommendation

Recommended stack:

- PyTorch
- PettingZoo (Parallel API)
- RLlib (custom policy mapping per side)
- Headless vectorized environments

Reasons:
- Strong MARL support
- Self-play utilities
- Works without NVIDIA CUDA
- CPU parallel friendly

Simulation should support:
- Batch stepping
- Deterministic replay logs

---

# 15. Architecture Design

## 15.1 Core Classes

Environment
- reset()
- step(actions)
- render()
- seed()

World
- physics_step()
- resolve_collisions()
- update_projectiles()

Agent (base)
- update_state()
- apply_fatigue()

Soldier(Agent)
- compute_throw()
- receive_order()

Leader(Soldier)
- issue_order()

Projectile
- integrate()
- check_collision()

InfantryBlock
- check_hit()
- compute_death_probability()

Terrain
- height(x,y)
- roughness(x,y)

RewardEngine
- process_events()

Logger
- record_step()
- export_replay()

---

# 16. Development Plan

## Phase 1: Deterministic Core
- Flat terrain
- No fatigue
- No morale
- No command noise
- Simple throw and hit detection
- Static infantry blocks
- Headless stepping

Validation:
- Ballistic correctness tests
- Collision tests
- Deterministic replay test

## Phase 2: Combat Mechanics
- Add fatigue
- Add morale
- Add ammo persistence + recovery
- Add shield survival chance

Validate:
- Distribution tests
- Stability under 100 agents

## Phase 3: Command System
- Leader policy
- Audible transmission
- Visual propagation
- Successor leadership

Test:
- Induced miscommunication scenarios

## Phase 4: RL Integration
- PettingZoo Parallel API
- Self-play per side
- Reward accounting
- Logging

## Phase 5: Terrain + Obstacles
- Height map
- Procedural obstacles
- Speed modifiers

## Phase 6: Cultural Experiments
- Modify reward weights
- Modify age distributions
- Observe formation emergence

---

# 17. Performance Considerations

- Vectorize physics using NumPy
- Avoid Python loops for collision resolution
- Batch environments for training
- Render only during evaluation

Target scale:
- 20–100 agents per side
- Stable at Δt = 0.1 s

---

# 18. Research Extension Points

- Wind model with sinusoidal gusts
- Directional armor
- Formation encoding experiments
- Emergent wedge detection metrics
- Doctrine clustering across training runs

---

End of Specification

