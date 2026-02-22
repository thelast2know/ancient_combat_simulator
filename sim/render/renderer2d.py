"""
Simple 2D rendering for Phase 1 evaluation and debugging.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
from typing import List, Tuple

from sim.core import World


class Renderer2D:
    """2D matplotlib-based renderer for simulation visualization."""
    
    def __init__(self, world: World, figsize: Tuple[float, float] = (12, 10)):
        self.world = world
        self.figsize = figsize
        self.fig = None
        self.ax = None
        
        # Stored frames for video generation
        self.frames = []
    
    def _setup_figure(self):
        """Initialize matplotlib figure and axes."""
        if self.fig is None:
            self.fig, self.ax = plt.subplots(figsize=self.figsize)
            self.ax.set_xlim(0, self.world.params.arena_width)
            self.ax.set_ylim(0, self.world.params.arena_height)
            self.ax.set_aspect('equal')
            self.ax.set_xlabel('X (m)')
            self.ax.set_ylabel('Y (m)')
            self.ax.grid(True, alpha=0.3)
    
    def render(self, title: str = "", debug: bool = False) -> np.ndarray:
        """
        Render current world state and return as RGB array.
        
        Args:
            title: optional title for the plot
            debug: if True, show velocity vectors and neighbor links
        
        Returns:
            RGB array (H, W, 3) with values 0-255
        """
        self._setup_figure()
        self.ax.clear()
        
        # Set limits and grid
        self.ax.set_xlim(0, self.world.params.arena_width)
        self.ax.set_ylim(0, self.world.params.arena_height)
        self.ax.set_aspect('equal')
        self.ax.grid(True, alpha=0.3)
        
        # Draw infantry blocks
        for block in self.world.infantry_blocks:
            width = block.x_max - block.x_min
            height = block.y_max - block.y_min
            color = 'lightblue' if block.team == 0 else 'lightcoral'
            rect = patches.Rectangle(
                (block.x_min, block.y_min), width, height,
                linewidth=2, edgecolor='black', facecolor=color, alpha=0.5
            )
            self.ax.add_patch(rect)
            
            # Label
            cx, cy = block.center()
            team_label = 'BLUE' if block.team == 0 else 'RED'
            self.ax.text(cx, cy, team_label, ha='center', va='center',
                         fontsize=12, weight='bold')
        
        # Draw agents
        for agent in self.world.agents:
            if not agent.alive:
                continue
            
            color = 'blue' if agent.team == 0 else 'red'
            circle = patches.Circle(
                (agent.x, agent.y), self.world.params.agent_radius,
                color=color, alpha=0.7, zorder=10
            )
            self.ax.add_patch(circle)
            
            # Draw velocity vector
            if debug:
                scale = 2.0
                self.ax.arrow(
                    agent.x, agent.y,
                    agent.vx * scale, agent.vy * scale,
                    head_width=0.3, head_length=0.2,
                    fc='black', ec='black', alpha=0.5, zorder=9
                )
            
            # Agent ID label
            self.ax.text(agent.x, agent.y + 1.5, str(agent.agent_id),
                         ha='center', va='bottom', fontsize=8)
        
        # Title
        title_str = f"Step {self.world.step_count}: {title}"
        self.ax.set_title(title_str, fontsize=14, weight='bold')
        
        # Convert to RGB array
        self.fig.canvas.draw()
        image = np.frombuffer(self.fig.canvas.tostring_rgb(), dtype='uint8')
        image = image.reshape(self.fig.canvas.get_width_height()[::-1] + (3,))
        
        return image
    
    def save_frame(self, title: str = "", debug: bool = False):
        """Capture current frame for video generation."""
        frame = self.render(title=title, debug=debug)
        self.frames.append(frame)
    
    def render_trajectory(self, agent_id: int,
                          trajectory: List[Tuple[float, float]],
                          title: str = ""):
        """
        Render a specific agent's trajectory.
        
        Args:
            agent_id: which agent to show
            trajectory: list of (x, y) positions
            title: plot title
        """
        self._setup_figure()
        self.ax.clear()
        
        # Draw arena and blocks
        self.ax.set_xlim(0, self.world.params.arena_width)
        self.ax.set_ylim(0, self.world.params.arena_height)
        self.ax.set_aspect('equal')
        self.ax.grid(True, alpha=0.3)
        
        for block in self.world.infantry_blocks:
            width = block.x_max - block.x_min
            height = block.y_max - block.y_min
            color = 'lightblue' if block.team == 0 else 'lightcoral'
            rect = patches.Rectangle(
                (block.x_min, block.y_min), width, height,
                linewidth=2, edgecolor='black', facecolor=color, alpha=0.5
            )
            self.ax.add_patch(rect)
        
        # Draw trajectory
        if trajectory:
            xs, ys = zip(*trajectory)
            self.ax.plot(xs, ys, 'o-', linewidth=1, markersize=3, alpha=0.5)
            
            # Mark start and end
            self.ax.plot(xs[0], ys[0], 'go', markersize=8, label='Start')
            self.ax.plot(xs[-1], ys[-1], 'r*', markersize=15, label='End')
        
        self.ax.set_title(f"Agent {agent_id} Trajectory: {title}")
        self.ax.legend()
        
        return self.render(title=title)
    
    def save_mp4(self, output_path: str, fps: int = 10):
        """
        Save collected frames as MP4 video.
        
        Requires: pip install opencv-python
        """
        if not self.frames:
            print("No frames to save")
            return
        
        try:
            import cv2
        except ImportError:
            print("ERROR: opencv-python required for video export. Install: pip install opencv-python")
            return
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get frame dimensions
        h, w = self.frames[0].shape[:2]
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))
        
        # Write frames
        for frame in self.frames:
            # Convert RGB to BGR for OpenCV
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            out.write(frame_bgr)
        
        out.release()
        print(f"Saved video to {output_path}")
        print(f"Frames: {len(self.frames)}, FPS: {fps}, Duration: {len(self.frames)/fps:.1f}s")
    
    def close(self):
        """Clean up matplotlib resources."""
        if self.fig is not None:
            plt.close(self.fig)
            self.fig = None
            self.ax = None
