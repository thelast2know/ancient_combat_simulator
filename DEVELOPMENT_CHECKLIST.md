# Development Checklist: Ancient Combat Simulator

## Phase 1: Skeleton World + Deterministic Stepping ✓ COMPLETE

- [x] Project structure and directories
- [x] GlobalParams configuration system
- [x] Agent class with kinematics
- [x] InfantryBlock static geometry
- [x] World simulation engine
- [x] Event logging system
- [x] Collision resolution (elastic, circle-circle)
- [x] Arena boundary enforcement
- [x] State hashing for determinism testing
- [x] Determinism tests (single and multi-agent)
- [x] Collision safety tests
- [x] Arena bounds tests
- [x] Extended 60-second stability test
- [x] Renderer2D visualization
- [x] Scenario YAML loading
- [x] Requirements.txt and setup
- [x] Quick validation suite
- [x] Full validation suite with video
- [x] Phase 1 completion report
- [x] Git commit with summary

**Status: READY FOR PHASE 2**

---

## Phase 2: Projectile Lifecycle

### Deliverables
- [ ] Create `sim/core/projectile.py` with Projectile class
- [ ] Ballistic integration (parabolic motion, gravity)
- [ ] Launch API in World class
- [ ] Ground impact detection
- [ ] Projectile persistence storage
- [ ] Terrain placeholder class
- [ ] Update renderer to draw projectile arcs

### Tests
- [ ] Ballistics accuracy test (range vs angle)
- [ ] Flight time validation
- [ ] Impact point accuracy
- [ ] Determinism of projectile trajectories
- [ ] Multiple projectile independence
- [ ] Impact event logging

### Validation
- [ ] Scenario: single thrower
- [ ] Scenario: range sweep (10°-80° loft)
- [ ] Scenario: 5 agents throw simultaneously
- [ ] Video visualization of arcs
- [ ] No performance regression

### Documentation
- [ ] Update PHASE2_COMPLETION.md
- [ ] Add Phase 3 roadmap

**Estimated: 6 hours**

---

## Phase 3: Hit Detection + Infantry Hit Scoring

### Deliverables
- [ ] InfantryBlock.contains() for point-in-region
- [ ] Projectile-infantry intersection detection
- [ ] Event types: InfantryHit, FriendlyInfantryHit
- [ ] Hit counter tracking

### Tests
- [ ] Geometric correctness (border cases)
- [ ] Event accuracy
- [ ] Friendly fire detection

### Scenarios
- [ ] Stationary throwers aiming at infantry
- [ ] Moving throwers targeting static blocks

**Estimated: 4 hours**

---

## Phase 4: Skirmisher Hits, Shields, Friendly Fire

### Deliverables
- [ ] Agent hit model (projectile distance check at impact)
- [ ] Shield spawning (p_shield parameter)
- [ ] Shield directional protection (left hemisphere)
- [ ] Shield survival chance (20% with parametrization)
- [ ] Event types: AgentHit, AgentKilled, ShieldSaved
- [ ] Friendly fire toggle

### Tests
- [ ] Monte Carlo shield survival rate
- [ ] Friendly fire on/off verification
- [ ] No double-kill bugs

### Scenarios
- [ ] Two agents crossing fire paths
- [ ] Shielded agent vs unshielded casualty rates

**Estimated: 2 hours**

---

## Phase 5: Infantry Proximity Death Zone

### Deliverables
- [ ] Distance to infantry boundary calculation
- [ ] Death probability: p = 1 - d/3 for d ≤ 3m
- [ ] Event: InfantryZoneKill

### Tests
- [ ] Boundary tests (d=0, 1.5, 3.0, 3.1 m)
- [ ] Statistical kill-rate validation

### Visualization
- [ ] 3m danger band rendering
- [ ] Agent walking into zone scenario

**Estimated: 2 hours**

---

## Phase 6: Ammo, Persistence, Recovery, Breakage

### Deliverables
- [ ] Per-agent ammo count tracking
- [ ] Landed projectile persistence
- [ ] Recovery on proximity (1m radius)
- [ ] Breakage chance on recovery
- [ ] Event types: AmmoSpent, AmmoRecovered, AmmoBroken

### Tests
- [ ] Conservation: ammo never negative
- [ ] Recovery correctness

### Scenario
- [ ] Agents sprinting through javelin field to recover

**Estimated: 2 hours**

---

## Phase 7: Fatigue Model + Movement Modifiers

### Deliverables
- [ ] Fatigue accumulation: above cruise speed
- [ ] Fatigue recovery: below fast walk threshold
- [ ] Fatigue effects:
  - [ ] Max speed reduction
  - [ ] Acceleration reduction
  - [ ] Agility reduction
  - [ ] Throw dispersion increase
  - [ ] Impetuousness non-linear decay
- [ ] Exposure in observation

### Tests
- [ ] Fatigue curve monotonicity
- [ ] Speed cap enforcement
- [ ] Bounds checking [0, 1]

### Scenario
- [ ] Sprint cycles vs cruise speed recovery

**Estimated: 3 hours**

---

## Phase 8: Morale Model + Casualty Feedback

### Deliverables
- [ ] Unit morale M ∈ [0, 1]
- [ ] Event-driven updates:
  - [ ] +kills
  - [ ] +enemy infantry hits
  - [ ] -unit casualties
  - [ ] -friendly infantry hits
  - [ ] -leader death (stacking)
- [ ] Morale effects:
  - [ ] Reaction time
  - [ ] Compliance probability
  - [ ] Survival reward weighting

### Tests
- [ ] Morale response to scripted events

### Scenario
- [ ] Force casualties, observe compliance drop

**Estimated: 3 hours**

---

## Phase 9: Command System (Leader + Propagation)

### Deliverables
- [ ] Leader role assignment
- [ ] Successor chain (3 deep)
- [ ] Discrete order types (ADVANCE, RETREAT, HOLD, etc.)
- [ ] Audible transmission:
  - [ ] Distance-based reception P_hear
  - [ ] Corruption below threshold
- [ ] Visual propagation (neighbor imitation)
- [ ] Thinking delay (reaction_time modified by timidity)
- [ ] Compliance probability (timidity-based)

### Tests
- [ ] Order reception distance curve
- [ ] Corruption frequency
- [ ] Successor takeover on leader death

### Visualization
- [ ] Leader marker and order label overlay
- [ ] Scenario: leader wheels and advances

**Estimated: 4 hours**

---

## Phase 10: Throw Control & Aim Head

### Deliverables
- [ ] Throw action split: binary trigger + continuous aim
- [ ] Loft angle commands from leader
- [ ] Aim head outputs (θ, φ)
- [ ] Throw dispersion based on:
  - [ ] Fatigue
  - [ ] Movement speed
  - [ ] Precision attribute
- [ ] Competency linkage

### Tests
- [ ] Loft band enforcement
- [ ] Dispersion scaling with fatigue/speed

### Scenario
- [ ] Deflection shots at moving target

**Estimated: 2 hours**

---

## Phase 11: Observation Encoder (Nearest-K)

### Deliverables
- [ ] Spatial neighbor indexing (k-d tree or grid)
- [ ] Fixed-size observation tensor
- [ ] Per-agent state: fatigue, morale, ammo, order
- [ ] Self state + unit state + cultural weights
- [ ] Masking for unavailable neighbors

### Tests
- [ ] Neighbor correctness vs brute force
- [ ] Observation shape stability
- [ ] Performance with N=200 agents

### Visualization
- [ ] Debug overlay showing selected K neighbors

**Estimated: 2 hours**

---

## Phase 12: Reward Engine + Credit Assignment

### Deliverables
- [ ] Event-driven reward calculation
- [ ] Parameterized culture weights (visible to agents)
- [ ] Multi-level accounting:
  - [ ] Individual pool
  - [ ] Unit pool
  - [ ] Leader pool
- [ ] Shame tax (inactivity > 3s)
- [ ] Friendly infantry hit penalties
- [ ] Optional: rolling hit-rate penalty

### Tests
- [ ] Unit tests per event type
- [ ] Reward sign regression tests

### Visualization
- [ ] Overlay per-agent reward contributions

**Estimated: 3 hours**

---

## Phase 13: RL Environment Integration (PettingZoo)

### Deliverables
- [ ] PettingZoo ParallelEnv wrapper
- [ ] reset(seed, options) method
- [ ] step(action_dict) method
- [ ] observations, rewards, terminations, truncations, infos
- [ ] Headless vectorization support
- [ ] Evaluation harness

### Tests
- [ ] PettingZoo API compliance
- [ ] Performance smoke tests

### Validation
- [ ] Deterministic policy evaluation
- [ ] Render evaluation episodes

**Estimated: 4 hours**

---

## Phase 14: Self-Play Training Loop

### Deliverables
- [ ] Two separate policies per side
- [ ] Self-play opponent pool
- [ ] Snapshot and sampling mechanism
- [ ] Curriculum toggles:
  - [ ] Flat terrain
  - [ ] No command noise
  - [ ] Enable fatigue
  - [ ] Enable morale
  - [ ] Enable command noise
  - [ ] Terrain + obstacles
- [ ] Training stability monitoring

### Tests
- [ ] Loss monitoring (no NaNs)
- [ ] Behavioral sanity metrics

### Visualization
- [ ] Highlight reel video generation

**Estimated: 5 hours**

---

## Phase 15: Terrain, Elevation, Roughness, Obstacles

### Deliverables
- [ ] Procedural height map z(x, y)
- [ ] Roughness field r(x, y)
- [ ] Discrete obstacles:
  - [ ] Ditch
  - [ ] Stream
  - [ ] Wall
  - [ ] Rock clusters
- [ ] Speed/fatigue modifiers
- [ ] Elevation effects on throw
- [ ] Toggleable in scenario config

### Tests
- [ ] Determinism with terrain seed
- [ ] No agents spawning in obstacles

### Scenarios
- [ ] Obstacle choke points
- [ ] Terrain elevation effect on throw

**Estimated: 4 hours**

---

## Post-V1 Extensions

- [ ] Wind model with sinusoidal gusts
- [ ] Directional armor
- [ ] Formation encoding experiments
- [ ] Emergent wedge detection metrics
- [ ] Doctrine clustering analysis
- [ ] Large-scale 100+ agent battles
- [ ] Curriculum learning progression analysis

---

## Project Metrics (Track Throughout)

### Simulation Performance
- [ ] Steps per second
- [ ] Agent count scaling
- [ ] Memory usage per agent
- [ ] Collision resolution efficiency

### Combat Metrics
- [ ] Throws per minute per agent
- [ ] Hit rate vs distance
- [ ] Friendly fire percentage
- [ ] Infantry hit rate

### Behavioral Metrics
- [ ] Unit cohesion (distance to leader)
- [ ] Formation dispersion
- [ ] Heading alignment
- [ ] Wedge indicators

### Command Metrics
- [ ] Order reception rate
- [ ] Corruption frequency
- [ ] Compliance latency
- [ ] Defection rate by order

### Learning Metrics (Phase 14+)
- [ ] Policy loss convergence
- [ ] Win rate vs random
- [ ] Formation emergence time
- [ ] Skill progression rate

---

## Documentation Checklist

- [x] specification.md (completed, detailed)
- [x] build_plan.md (completed, detailed)
- [x] PHASE1_COMPLETION.md (detailed report)
- [x] PHASE2_ROADMAP.md (Phase 2 detailed plan)
- [x] PROJECT_SUMMARY.md (comprehensive overview)
- [ ] PHASE2_COMPLETION.md (after Phase 2)
- [ ] PHASE3_ROADMAP.md (after Phase 2)
- [ ] ... (one per phase)
- [ ] FINAL_REPORT.md (after all phases complete)
- [ ] API_REFERENCE.md (after Phase 13)
- [ ] TRAINING_GUIDE.md (after Phase 14)
- [ ] EXPERIMENT_LOG.md (during Phase 15)

---

## Git Workflow

After each phase:
1. [ ] Commit with clear message and phase completion
2. [ ] Tag release: `git tag phase-X`
3. [ ] Update main README.md with current status
4. [ ] Push to origin

---

## Success Criteria Summary

**V1 Production Ready When:**
- ✓ Phase 1: Deterministic core (✓ DONE)
- ⏳ Phase 2-6: Combat mechanics stable
- ⏳ Phase 7-8: Fatigue and morale working
- ⏳ Phase 9-10: Command system functioning
- ⏳ Phase 11-12: RL interface ready
- ⏳ Phase 13-14: Self-play training operational
- ⏳ Phase 15: Terrain system integrated

**When all complete:**
- Can train for extended runs (100k+ steps) without crashes
- Deterministic replay matches live episodes exactly
- At least 3 distinct behavioral modes across different reward cultures
- Doctrine weights predictably affect behavior

---

## Contact / Questions

Development checklist maintained here. Update this file as you progress through phases.

**Current Phase:** Phase 1 ✓ COMPLETE → Ready for Phase 2
