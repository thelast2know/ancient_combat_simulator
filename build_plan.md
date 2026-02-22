# Build Plan: Emergent Skirmisher Tactics RL Environment

This build plan is ordered to maximize **validation per unit effort**: every phase produces (1) a runnable sim, (2) a test suite expansion, (3) a visualization/replay artifact you can inspect, and (4) instrumentation for diagnosing failures and reward hacks.

The intent is to avoid the common MARL failure mode: training on a half-specified world where bugs look like “interesting emergent behaviour.”

---

# 0. Core Principles

## 0.1 Determinism and Reproducibility
- Every episode is reproducible from:
  - environment params
  - RNG seed
  - action log (optional)
- All stochastic events are drawn from a single seeded RNG stream (or named substreams: physics/combat/command).
- Replay correctness is a first-class requirement from Day 1.

## 0.2 Separation of Concerns
Split the project into:
- **Simulation** (pure state transition)
- **Observation** (what agents see)
- **Reward** (event accounting)
- **Policy interface** (PettingZoo / RLlib glue)
- **Rendering** (read-only, never changes state)
- **Logging/replay** (read-only snapshots + event stream)

## 0.3 Event-Driven Combat and Rewards
Do *not* compute reward as arbitrary dense heuristics early.
- Use explicit events: `ProjectileLaunched`, `ProjectileImpact`, `AgentHit`, `AgentKilled`, `InfantryHit`, `OrderIssued`, `OrderReceived`, `OrderCorrupted`, `ShameTick`, etc.
- Rewards are derived **only** from the event stream + optional per-step survival term.

## 0.4 Tight Feedback Loops
Each phase ends with:
- a deterministic regression test
- a short scripted scenario ("micro-sim") you can watch
- a replay video (mp4) from that scenario

---

# 1. Recommended Repo Layout

```
project/
  sim/
    core/
      world.py
      physics.py
      terrain.py
      infantry.py
      projectile.py
      agents.py
      command.py
      events.py
      rng.py
      params.py
    obs/
      encoder.py
      sensors.py
      neighbor_index.py
    reward/
      reward_engine.py
      culture.py
      credit_assignment.py
    env/
      pettingzoo_env.py
      wrappers.py
    render/
      renderer2d.py
      overlays.py
      video.py
    replay/
      recorder.py
      playback.py
      schema.py
  tests/
    test_determinism.py
    test_ballistics.py
    test_collisions.py
    test_neighbors.py
    test_rewards.py
    test_command_noise.py
  scenarios/
    duel.yaml
    5v5_flat.yaml
    20v20_flat.yaml
    command_noise.yaml
    infantry_screen.yaml
  train/
    rllib_selfplay.py
    evaluation.py
  tools/
    profile_step.py
    validate_params.py
    inspect_replay.py
```

---

# 2. Data Contracts (Non-negotiable)

## 2.1 State Objects
- All core state is in plain arrays/structs (NumPy), not scattered across Python objects.
- Keep entity “components” aligned by index:
  - `pos[N,2]`, `vel[N,2]`, `alive[N]`, `team[N]`, `fatigue[N]`, `morale[N]`, etc.

Why: faster, easier to serialize, easier to test.

## 2.2 Event Stream
Events are append-only per step:
- `events[t] = [Event, Event, ...]`
- Each event is a compact struct:
  - `type: int`
  - `a: int` (actor id)
  - `b: int` (target id / block id)
  - `pos: (x,y)` (optional)
  - `value: float` (optional)

This makes reward debugging and replay overlays trivial.

## 2.3 Parameters and Scenarios
- All parameters loadable from YAML/JSON.
- Every run stores a single `run_config.json` alongside logs.

---

# 3. Build Order (Phases)

Each phase has:
- Deliverables
- Tests
- Visualization / inspection
- Exit criteria

## Phase 1 — Skeleton World + Deterministic Stepping

### Deliverables
- `World.step(dt)` that advances:
  - agent kinematics (velocity/heading control)
  - collision resolution (circle-circle)
  - boundary conditions
- Flat terrain only
- Two static infantry rectangles
- Episode init from scenario files

### Tests
- **Determinism**: same seed + same actions → identical state hash after T steps
- **Collision sanity**:
  - agents never overlap after resolution
  - symmetric response in pairwise collision
- **Bounds**: agents remain within arena

### Visualization
- Minimal 2D render:
  - circles for agents
  - rectangles for infantry
  - velocity vectors overlay
- Save a 10-second mp4 from a scripted scenario

### Exit Criteria
- 60 seconds sim time runs without numerical instability
- Determinism test passes on multiple machines

---

## Phase 2 — Projectile Lifecycle (No Hit Logic Yet)

### Deliverables
- `Projectile` objects with ballistic integration (no drag)
- Launch API: spawn projectile with initial velocity vector
- Impact with ground/terrain (flat for now)
- Persist projectiles after landing

### Tests
- **Ballistics**:
  - analytic range/flight-time checks on level ground
  - loft angle extremes behave
- **Replay**: projectile trajectories identical under replay

### Visualization
- Draw projectile arcs (polyline) + impact points
- Scenario: single thrower fires at fixed loft angles

### Exit Criteria
- Projectile motion stable across dt choices (0.05–0.2s)

---

## Phase 3 — Hit Detection + Infantry Hit Scoring

### Deliverables
- `InfantryBlock.contains(point)` returns boolean
- On projectile impact:
  - if inside enemy infantry region → `InfantryHit` event
  - if inside friendly infantry region → `FriendlyInfantryHit` event
- No skirmisher hits yet

### Tests
- **Geometric correctness**: impacts inside/outside border cases
- **Event logging**: correct event counts

### Visualization
- Overlay infantry hit markers and cumulative counters
- Scenario: stationary throwers aiming at infantry

### Exit Criteria
- Event counts match hand-checked expected values

---

## Phase 4 — Skirmisher Hits, Shields, and Friendly Fire

### Deliverables
- Agent hit model on projectile impact:
  - direct hit if projectile passes within (agent radius) at impact time (simplify: impact point distance check)
  - friendly fire enabled
- Shield survival chance:
  - spawn shield with `p_shield`
  - compute incoming direction vs agent left-facing direction
  - if in shield hemisphere → 20% survival chance (parameterized)
- Events:
  - `AgentHit`, `AgentKilled`, `ShieldSaved`

### Tests
- Monte Carlo test for shield survivability rate
- Friendly fire toggles on/off via params

### Visualization
- Hit markers; shield indicator; kill feed
- Scenario: two throwers crossing fire, demonstrate friendly fire

### Exit Criteria
- Statistical tests pass within tolerance
- No “double kill” / repeated death events

---

## Phase 5 — Infantry Proximity Death Zone

### Deliverables
- Compute distance from agent to infantry block boundary
- Death probability per timestep for d <= 3m:
  - `p = 1 - d/3` (capped 0..1)
- Event: `InfantryZoneKill`

### Tests
- Boundary tests at d=0,1.5,3.0,3.1
- Statistical kill-rate checks over many runs

### Visualization
- Draw a 3m danger band around infantry
- Scenario: agent walks into danger zone at various speeds

### Exit Criteria
- Observed death rate matches intended curve

---

## Phase 6 — Ammo, Persistence, Recovery, Breakage

### Deliverables
- Per-agent ammo count
- Landed projectiles persist with owner/team id
- Recovery when agent passes within 1m:
  - `p_recover`
  - `p_break`
- Events: `AmmoSpent`, `AmmoRecovered`, `AmmoBroken`

### Tests
- Conservation tests: ammo never negative; recovered increments correctly

### Visualization
- Show ammo above heads
- Scenario: agents sprint through javelin field to recover

### Exit Criteria
- Recovery mechanics stable and deterministic

---

## Phase 7 — Fatigue Model + Movement Modifiers (Flat Terrain)

### Deliverables
- Fatigue accumulation/recovery:
  - above cruise speed: fatigue increases
  - below fast-walk: fatigue decreases
- Fatigue affects:
  - max speed
  - acceleration
  - agility
  - throw dispersion
  - impetuousness (decreases non-linearly beyond threshold)
- Expose fatigue in observation

### Tests
- Fatigue curve tests (expected monotonicity)
- Speed cap enforcement

### Visualization
- Fatigue heatbar per agent
- Scenario: sprint cycles vs cruise to show recovery

### Exit Criteria
- Fatigue can’t explode; remains within [0,1]

---

## Phase 8 — Morale Model + Casualty/Hits Feedback

### Deliverables
- Unit morale M in [0,1]
- Update rules triggered by event stream:
  - +kills, +enemy infantry hits
  - -unit casualties, -friendly infantry hits
  - -leader death stacking
- Morale affects:
  - reaction time
  - compliance probability
  - survival reward weighting

### Tests
- Morale response tests on scripted events

### Visualization
- Unit morale gauge
- Scenario: force casualties and observe compliance drop

### Exit Criteria
- Morale updates only via events; no hidden drift

---

## Phase 9 — Command System (Leader + Propagation)

### Deliverables
- Roles:
  - leader index per unit
  - successor chain (3 deep)
- Order state machine:
  - leader issues discrete order events
  - followers update “current_order” when received
- Audible channel:
  - `P_hear = min(1, voice_volume / d^2)`
  - if 0 < P_hear < 0.1: corruption chance → random other order OR no change
- Visual channel:
  - neighbor imitation (no occlusion for now)
- Thinking delay and defection probability:
  - increases with timidity
  - higher for high-risk orders (advance/throw)

### Tests
- Order reception probability vs distance
- Corruption frequency under threshold
- Successor leader takeover correctness

### Visualization
- Draw leader marker + current order text per agent
- Scenario: leader wheels and advances; observe propagation and corruption

### Exit Criteria
- Command propagation produces believable lags/errors in video

---

## Phase 10 — Throw Control: Aim Head + Loft Angle as Leader Command

### Deliverables
- Throw action split:
  - follower has binary “throw now” (or “comply with throw order”)
  - leader issues `THROW_LOW/HIGH` which sets desired loft band
- Aim head outputs continuous aim:
  - either (θ, φ) directly, OR aim point in world coords + derived (θ, φ)
- Competency linkage:
  - follower skill modifies how well loft band is executed

### Tests
- Loft band enforcement
- Dispersion increases with fatigue and speed

### Visualization
- Draw aim ray + predicted impact point distribution ellipse (optional debug)
- Scenario: moving target deflection shots as skill rises

### Exit Criteria
- Deflection shots are at least physically possible

---

## Phase 11 — Observation Encoder (Nearest-K)

### Deliverables
- Neighbor index (grid hash / k-d tree) for nearest-K
- Fixed-size observation tensor with masking
- Include self state + unit state + command state + cultural weights

### Tests
- Neighbor correctness vs brute force
- Masking correctness
- Performance profiling (N up to ~200)

### Visualization
- Debug overlay showing selected K neighbors per agent

### Exit Criteria
- Obs stable shape; fast enough for training

---

## Phase 12 — Reward Engine + Credit Assignment

### Deliverables
- Reward derived from event stream
- Parameterized “culture” weights visible to agents
- Multi-level accounting:
  - individual pool
  - unit pool
  - leader pool
- Shame tax:
  - per individual after 3s inactivity
  - per unit if no one acts
  - extra shame if leader commands throw and follower doesn’t
- Friendly infantry penalty:
  - per hit + rolling hit-rate penalty

### Tests
- Unit tests for each event type reward
- Regression tests to prevent reward sign mistakes

### Visualization
- Overlay per-agent reward contributions (stacked text) in debug mode

### Exit Criteria
- No reward computed outside events

---

## Phase 13 — RL Environment Integration (PettingZoo Parallel)

### Deliverables
- PettingZoo ParallelEnv wrapper:
  - `reset(seed, options)`
  - `step(action_dict)`
  - `observations, rewards, terminations, truncations, infos`
- Headless vectorization support:
  - multiple env instances batched in Python multiprocessing
- Evaluation harness:
  - deterministic fixed policy vs scripted opponents

### Tests
- API compliance tests (PettingZoo test suite)
- Performance smoke tests (steps/sec)

### Visualization
- Run evaluation episodes and render replays

### Exit Criteria
- Can train a baseline random policy without crashes

---

## Phase 14 — Self-Play Training Loop

### Deliverables
- Two separate policies per side (as requested)
- Self-play regime:
  - periodically snapshot opponents
  - sample opponents from a pool
- Curriculum toggles:
  - start flat/no command noise
  - gradually enable fatigue/morale/noise/terrain

### Tests
- Training stability checks (loss finite, no NaNs)
- Behavioural sanity metrics (below)

### Visualization
- Every N training iters: export a highlight reel of 5 replays

### Exit Criteria
- Non-trivial behaviour emerges (hits/kills not near zero)

---

## Phase 15 — Terrain, Elevation, Roughness, Obstacles

### Deliverables
- Procedural terrain fields:
  - height map z(x,y)
  - roughness r(x,y)
  - heat modifier h(x,y) (optional)
- Discrete obstacles placed procedurally:
  - ditch/stream/wall/rocks
- Effects:
  - speed and acceleration modifiers
  - fatigue modifiers
  - elevation effects on throw (optional)
- Toggleable in scenario config

### Tests
- Determinism with terrain seed
- No agents spawned inside obstacles

### Visualization
- Terrain shading + obstacle outlines
- Scenario: obstacle choke points

### Exit Criteria
- Training remains stable when terrain enabled

---

# 4. Validation Metrics (Track from Early Phases)

These are cheap to compute and will tell you if learning is sane.

## 4.1 Combat
- throws per minute per agent
- hit rate vs distance
- friendly fire rate
- infantry hit rate

## 4.2 Tactics / Formation
- unit cohesion: mean distance to leader
- dispersion: covariance eigenvalues of unit positions
- alignment: mean heading alignment within unit
- wedge/chevron indicators: leader-forward axis density gradient

## 4.3 Command and Compliance
- order reception rate (audible/visual)
- corruption rate
- compliance latency distribution
- defection rate by order type

## 4.4 Survival and Risk
- deaths by cause (projectile vs infantry zone)
- time spent in danger band (<3m)
- fatigue distribution over episode

## 4.5 Anti-degeneracy
- inactivity time share
- shame tax accumulated
- average inter-team distance (to detect runaway kiting)

---

# 5. Visualization & Debugging Toolkit

## 5.1 Renderer Modes
- **Evaluation mode**: clean visuals for video
- **Debug mode**: overlays
  - neighbor links (K graph)
  - danger band
  - current order labels
  - projectile arcs
  - reward contributions

## 5.2 Replay Format
Store per episode:
- `metadata.json` (params + seed)
- `frames.npz` OR `deltas.npz` (state snapshots or compressed deltas)
- `events.jsonl` (event stream)

Recommended approach:
- Save state every N steps + store action/event deltas between

## 5.3 Video
- Render from replay, not live sim, so training stays headless
- Use ffmpeg to encode mp4

---

# 6. Performance Roadmap

## 6.1 Before Optimization
- Write correctness-first code
- Profile steps/sec after Phase 11

## 6.2 Likely Hotspots
- nearest-K neighbor search
- collision resolution
- projectile integration if many projectiles

## 6.3 Planned Accelerations
- uniform grid spatial hashing for neighbors + collisions
- vectorized NumPy kernels
- optional Numba for hotspots (GPU-independent)

---

# 7. Minimal First Training Curriculum (Practical)

1) 1v1 duel, infinite ammo, no fatigue, no command noise
2) 5v5 flat, finite ammo, infantry hit scoring only
3) Enable skirmisher hits + friendly fire
4) Enable fatigue
5) Enable morale
6) Enable command noise + visual propagation
7) Increase to 20v20
8) Enable closing infantry blocks
9) Enable procedural terrain & obstacles

Exit each stage only when metrics are stable and videos look sane.

---

# 8. Done Criteria for “Version 1”

V1 is complete when you can:
- Train self-play for long runs without crashes
- Export deterministic replays that match live episodes exactly
- Show at least 3 distinct, repeatable behavioural modes across seeds/cultures (e.g., tight cohesion screen, loose harassment swarm, high-arc infantry suppression)
- Demonstrate that changing culture weights changes behaviour in predictable ways

---

End of Build Plan

