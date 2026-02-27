# Configurable Scenario Runner - Architecture

## Overview

A clean, modular system for running combat simulations with full control over:
- Scenario configuration (agent placement, team setup)
- Behavior configuration (movement, firing, etc.)
- Simulation parameters (steps, random seed)
- Rendering and video generation (optional, can be disabled)

## Architecture

### Three-Part System

```
Scenario YAML Config
        ↓
Scenario Builder (loads agents)
        ↓
Simulation Runner (pure physics, no I/O)
        ↓
[Captured Frames]
        ↓
Frame Renderer (optional post-processing)
        ↓
Video Output
```

### Key Benefits

1. **Clean Separation of Concerns**
   - Pure simulation runs at full speed
   - Rendering is optional post-processing
   - No rendering overhead in physics loop

2. **Flexible Configuration**
   - YAML-based scenario and run configs
   - Easy to create new scenarios
   - Full control over behaviors and parameters

3. **Easy to Extend**
   - Add new formation types in `ScenarioBuilder`
   - Add new behavior strategies in `SimulationRunner`
   - Add new rendering options in `FrameRenderer`

## Usage

### Run with rendering and video output:
```bash
python run_scenario.py run_50v50.yaml
```

### Run pure simulation (no rendering overhead):
```bash
python run_scenario.py run_50v50_sim_only.yaml
```

## Configuration Files

### Scenario YAML (`scenarios/50v50.yaml`)

Defines agent placement and attributes:

```yaml
description: "Large-scale combat between two teams"

blue_agents:
  count: 50
  formation: "grid"
  grid_params:
    rows: 5
    cols: 10
    spacing_x: 4
    spacing_y: 8
    origin: [10, 20]
  attributes:
    health: 100
    range: 50

red_agents:
  count: 50
  formation: "grid"
  grid_params:
    rows: 5
    cols: 10
    spacing_x: 4
    spacing_y: 8
    origin: [90, 20]
    reverse_x: true  # Mirror from right
  attributes:
    health: 100
    range: 50
```

### Run YAML (`run_50v50.yaml`)

Defines how to run the scenario:

```yaml
scenario: "scenarios/50v50.yaml"

simulation:
  num_steps: 300
  random_seed: 42

behaviors:
  team_movement:
    enabled: true
    target_strategy: "centroid"
    speed: 8.0
  
  projectile_fire:
    enabled: true
    fire_probability: 0.25
    azimuth_range: [0, 6.28]
    loft_angle_range: [0.52, 1.05]
    speed_range: [20, 35]

rendering:
  enabled: true  # Set to false to skip rendering
  fps: 30
  figsize: [12, 10]
  output_dir: "output_videos"

video:
  enabled: true
  codec: "mp4v"
  quality: 18

output:
  verbose: true
  stats_interval: 50
```

## Performance

Pure simulation (no rendering):
- 300 steps, 100 agents (50v50): **completes instantly**
- 7563 projectiles, optimized spatial grid collision detection
- No I/O overhead

With rendering (post-processing):
- Renders frames at 30 FPS
- Generates 1200×1000 MP4 in ~5.9 MB
- Video rendering is parallelizable (current implementation is single-threaded)

## File Structure

```
run_scenario.py              # Main runner script
scenarios/50v50.yaml        # Scenario definition
run_50v50.yaml             # Run configuration (with rendering)
run_50v50_sim_only.yaml    # Run configuration (simulation only)
```

## Creating New Scenarios

1. Create a new scenario file:
```bash
cp scenarios/50v50.yaml scenarios/my_scenario.yaml
# Edit my_scenario.yaml with your agent setup
```

2. Create a run config:
```bash
cp run_50v50.yaml run_my_scenario.yaml
# Edit run_my_scenario.yaml to reference your scenario
```

3. Run it:
```bash
python run_scenario.py run_my_scenario.yaml
```

## Extending Formation Types

Add a new formation to `ScenarioBuilder.setup_world()`:

```python
if scenario_config.blue_agents.get('formation') == 'my_formation':
    blue_agents = ScenarioBuilder.build_my_formation(...)
```

## Extending Behaviors

Add a new movement strategy to `SimulationRunner._build_actions()`:

```python
if strategy == 'my_strategy':
    # Implement your custom movement logic
```
