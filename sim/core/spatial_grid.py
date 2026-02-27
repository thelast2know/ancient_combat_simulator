#!/usr/bin/env python3
"""Spatial grid-based collision detection for efficient broad-phase queries.

Instead of checking every agent against every other agent (O(n²)),
we partition the arena into a grid and only check agents within
adjacent cells. This reduces average-case complexity dramatically.

Grid structure:
- Arena divided into N×N cells
- Each cell tracks agents within it
- For collision detection, check only 9 cells (3×3 neighborhood)
"""
import numpy as np
from typing import List, Tuple, Dict, Set


class SpatialGrid:
    """Spatial hash grid for efficient collision detection."""

    def __init__(self, arena_width: float, arena_height: float,
                 cell_size: float = 10.0):
        """Initialize spatial grid.

        Args:
            arena_width: Width of arena (meters)
            arena_height: Height of arena (meters)
            cell_size: Size of each grid cell (meters)
                      Recommendation: 2x agent_radius * typical_density
                      For 0.3m agents: ~1-10m works well
        """
        self.arena_width = arena_width
        self.arena_height = arena_height
        self.cell_size = cell_size

        # Grid dimensions
        self.grid_width = int(np.ceil(arena_width / cell_size))
        self.grid_height = int(np.ceil(arena_height / cell_size))

        # Grid cells: grid[row][col] = set of agent ids
        self.grid: Dict[Tuple[int, int], Set[int]] = {}

        # Statistics for performance analysis
        self.stats_pairs_checked = 0
        self.stats_pairs_colliding = 0
        self.stats_cells_occupied = 0

        print(
            f"[SpatialGrid] Initialized {self.grid_width}×{self.grid_height} grid "
            f"({self.grid_width * self.grid_height} cells)")
        print(f"[SpatialGrid] Cell size: {cell_size}m")

    def _get_cell(self, x: float, y: float) -> Tuple[int, int]:
        """Get grid cell coordinates for a position."""
        col = int(np.clip(x / self.cell_size, 0, self.grid_width - 1))
        row = int(np.clip(y / self.cell_size, 0, self.grid_height - 1))
        return (row, col)

    def insert(self, agent_id: int, x: float, y: float):
        """Insert agent into grid at position (x, y)."""
        cell = self._get_cell(x, y)
        if cell not in self.grid:
            self.grid[cell] = set()
        self.grid[cell].add(agent_id)

    def clear(self):
        """Clear grid for next timestep."""
        self.grid.clear()

    def get_neighbors(self, x: float, y: float, radius: float = 0) -> Set[int]:
        """Get all agent IDs in cells adjacent to position (x, y).

        Checks 3×3 grid of cells (center + 8 neighbors).

        Args:
            x, y: Position to query
            radius: Extra buffer radius (added to search area)

        Returns:
            Set of agent IDs in neighboring cells
        """
        row, col = self._get_cell(x, y)

        neighbors = set()

        # Check 3x3 grid (center + 8 adjacent)
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                check_row = row + dr
                check_col = col + dc

                # Bounds check
                if (0 <= check_row < self.grid_height and
                    0 <= check_col < self.grid_width):
                    cell = (check_row, check_col)
                    if cell in self.grid:
                        neighbors.update(self.grid[cell])

        return neighbors

    def get_all_neighbor_pairs(self) -> List[Tuple[int, int]]:
        """Get all unique pairs of agents that could potentially collide.

        This is the broad-phase collision detection. Returns pairs of
        agents in the same or adjacent cells.

        Assumes grid has already been built with insert() calls.

        Returns:
            List of (agent_id_a, agent_id_b) pairs where a < b
        """
        pairs = set()
        self.stats_cells_occupied = len(self.grid)
        
        # Iterate through each occupied cell
        for (row, col), agent_ids in self.grid.items():
            # Convert set to list for indexing
            agent_list = list(agent_ids)
            
            # Pairs within this cell (all combinations)
            for i in range(len(agent_list)):
                for j in range(i + 1, len(agent_list)):
                    a_id, b_id = agent_list[i], agent_list[j]
                    pair = (min(a_id, b_id), max(a_id, b_id))
                    pairs.add(pair)
            
            # Pairs with each neighboring cell (to avoid duplicate checking,
            # only check cells with higher row/col indices)
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue  # Already handled above
                    
                    neighbor_row = row + dr
                    neighbor_col = col + dc
                    
                    # Only process neighbors with row >= current row (to avoid duplicates)
                    if neighbor_row < row or (neighbor_row == row and neighbor_col <= col):
                        continue
                    
                    # Bounds check
                    if not (0 <= neighbor_row < self.grid_height and
                            0 <= neighbor_col < self.grid_width):
                        continue
                    
                    neighbor_cell = (neighbor_row, neighbor_col)
                    if neighbor_cell not in self.grid:
                        continue
                    
                    neighbor_agent_list = list(self.grid[neighbor_cell])
                    
                    # All cross-pairs between this cell and neighbor
                    for a_id in agent_list:
                        for b_id in neighbor_agent_list:
                            pair = (min(a_id, b_id), max(a_id, b_id))
                            pairs.add(pair)

        self.stats_pairs_checked = len(pairs)
        return list(pairs)
    
    def record_collision(self):
        """Called when a collision is actually processed."""
        self.stats_pairs_colliding += 1
    
    def reset_stats(self):
        """Reset collision counter for next step."""
        self.stats_pairs_colliding = 0

    def stats(self) -> dict:
        """Return grid statistics."""
        total_cells = self.grid_width * self.grid_height
        occupied_cells = len(self.grid)
        total_agents = sum(len(agents) for agents in self.grid.values())

        avg_per_cell = total_agents / max(occupied_cells, 1)
        max_per_cell = max((len(agents) for agents in self.grid.values()),
                           default=0)

        return {
            'total_cells': total_cells,
            'occupied_cells': occupied_cells,
            'total_agents': total_agents,
            'avg_agents_per_cell': avg_per_cell,
            'max_agents_in_cell': max_per_cell,
            'density': occupied_cells / total_cells if total_cells > 0 else 0,
        }


def estimate_cell_size(
        arena_width: float,
        arena_height: float,
        num_agents: int,
        agent_radius: float = 0.3) -> float:
    """Estimate optimal cell size based on arena and agent count.

    Goal: Each cell should contain ~2-5 agents on average.
    This balances memory (too many cells) vs. collision checks (too few).

    Args:
        arena_width, arena_height: Arena dimensions
        num_agents: Total number of agents
        agent_radius: Agent radius (for reference)

    Returns:
        Recommended cell size in meters
    """
    arena_area = arena_width * arena_height
    target_agents_per_cell = 3
    target_cells = max(1, num_agents / target_agents_per_cell)
    cell_area = arena_area / target_cells
    cell_size = np.sqrt(cell_area)

    # Clamp to reasonable range
    min_cell = agent_radius * 2  # At least 2 agents wide
    max_cell = max(arena_width, arena_height) / 3  # At most 1/3 of arena

    return np.clip(cell_size, min_cell, max_cell)


if __name__ == '__main__':
    # Simple test
    grid = SpatialGrid(arena_width=100, arena_height=100, cell_size=10)

    # Insert some agents
    positions = {
        0: (15, 15),
        1: (18, 18),  # Close to 0
        2: (50, 50),  # Far from others
        3: (51, 51),  # Close to 2
        4: (95, 95),  # Corner
    }

    for agent_id, (x, y) in positions.items():
        grid.insert(agent_id, x, y)

    # Get neighbors
    print("Neighbors of agent 0 (at 15, 15):", grid.get_neighbors(15, 15))
    print("Neighbors of agent 2 (at 50, 50):", grid.get_neighbors(50, 50))

    # Get all pairs
    pairs = grid.get_all_neighbor_pairs(positions)
    print(f"Potential collision pairs: {pairs}")

    # Stats
    stats = grid.stats()
    print(f"Grid stats: {stats}")
