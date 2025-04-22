import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout, 
                            QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
                            QMessageBox, QComboBox, QSlider)
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QFont, QRadialGradient
from PyQt5.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal, QTimer, QPointF

class BoardWidget(QWidget):
    piece_clicked = pyqtSignal(int, int)  # Ring, spoke
    move_made = pyqtSignal(int, int, int, int)  # From ring, from spoke, to ring, to spoke
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500, 500)
        self.board = np.zeros((4, 8), dtype=int)
        self.piece_values = np.zeros((4, 8), dtype=int)  # Store piece energy values
        self.selected_piece = None
        self.valid_moves = []
        self.hover_position = None
        self.animation_positions = []  # For capture animation
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        
        # Colors
        self.board_color = QColor(30, 30, 50)  # Dark blue-gray
        self.grid_color = QColor(100, 100, 160)  # Lighter blue for grid
        self.player1_color = QColor(220, 50, 50)  # Red
        self.player2_color = QColor(50, 120, 220)  # Blue
        self.selected_color = QColor(250, 230, 50)  # Bright yellow
        self.valid_move_color = QColor(80, 220, 80, 140)  # Semi-transparent green
        self.hover_color = QColor(140, 240, 240, 170)  # Semi-transparent cyan
        self.inner_circle_color = QColor(255, 215, 0, 70)  # Semi-transparent gold
        self.energy_zone_colors = [
            QColor(80, 220, 80, 60),  # Green zone
            QColor(200, 180, 20, 60),  # Yellow zone
            QColor(220, 100, 30, 60),  # Orange zone
            QColor(220, 40, 40, 60)   # Red zone
        ]
        
        # Special point indicators
        self.special_points = []  # Will be filled with (ring, spoke, color) tuples
        self.flux_angle = 0
        self.flux_timer = QTimer()
        self.flux_timer.timeout.connect(self.update_flux)
        self.flux_timer.start(50)

        # Initialize the board
        self.reset_board()

    def update_flux(self):
        """Update the flux animation angle"""
        self.flux_angle = (self.flux_angle + 1) % 360
        self.update()

    def reset_board(self):
        """Reset the board to initial state"""
        self.board = np.zeros((4, 8), dtype=int)
        self.piece_values = np.zeros((4, 8), dtype=int)
        
        # Set up initial positions
        # Player 1 on positions 0, 2, 4, 6 of outermost ring
        for i in [0, 2, 4, 6]:
            self.board[3][i] = 1
            
        # Player 2 on positions 1, 3, 5, 7 of outermost ring
        for i in [1, 3, 5, 7]:
            self.board[3][i] = 2
            
        self.selected_piece = None
        self.valid_moves = []
        self.animation_positions = []
        self.update()

    def set_special_points(self, points):
        """Set the special points on the board"""
        self.special_points = points
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Set up the drawing area
        width = self.width()
        height = self.height()
        size = min(width, height) - 40  # Margin of 20px on each side
        center_x = width // 2
        center_y = height // 2
        
        # Draw the board background
        painter.fillRect(event.rect(), self.board_color)
        
        # Draw energy zones as colored rings
        for ring_idx, color in enumerate(self.energy_zone_colors):
            outer_radius = size // 2 - (ring_idx * size // 8)
            inner_radius = outer_radius - size // 8
            
            # Create a radial gradient for each zone
            gradient = QRadialGradient(center_x, center_y, outer_radius)
            gradient.setColorAt(inner_radius/outer_radius, color)
            color_transparent = QColor(color)
            color_transparent.setAlpha(10)
            gradient.setColorAt(1, color_transparent)
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(gradient))
            painter.drawEllipse(center_x - outer_radius, center_y - outer_radius,
                              outer_radius * 2, outer_radius * 2)
        
        # Highlight the innermost circle with a special color
        painter.setBrush(QBrush(self.inner_circle_color))
        painter.setPen(Qt.NoPen)
        innermost_radius = size // 8
        painter.drawEllipse(center_x - innermost_radius, center_y - innermost_radius, 
                           innermost_radius * 2, innermost_radius * 2)
        
        # Set up the pen for grid lines
        grid_pen = QPen(self.grid_color, 1.5)
        painter.setPen(grid_pen)
        
        # Draw 4 concentric circles
        radii = [size // 8, size // 4, 3 * size // 8, size // 2]
        for radius in radii:
            painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
        
        # Draw 8 radial lines
        for angle in range(0, 360, 45):
            rad_angle = angle * np.pi / 180
            x = center_x + size // 2 * np.cos(rad_angle)
            y = center_y + size // 2 * np.sin(rad_angle)
            painter.drawLine(center_x, center_y, int(x), int(y))
        
        # Draw special points
        for ring, spoke, color_name in self.special_points:
            x, y = self.get_position_coordinates(ring, spoke, center_x, center_y, radii)
            
            # Get color based on name
            if color_name == "power":
                color = QColor(255, 215, 0)  # Gold
                size_mult = 1.0 + 0.2 * np.sin(self.flux_angle * np.pi / 180)
            elif color_name == "jump":
                color = QColor(50, 180, 255)  # Light blue
                size_mult = 1.0 + 0.2 * np.cos(self.flux_angle * np.pi / 180)
            elif color_name == "shield":
                color = QColor(140, 80, 255)  # Purple
                size_mult = 1.0 + 0.1 * np.sin(2 * self.flux_angle * np.pi / 180)
            else:
                color = QColor(255, 255, 255)  # White
                size_mult = 1.0
                
            # Draw pulsing circle for special point
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color.lighter(120)))
            point_size = int(10 * size_mult)
            painter.drawEllipse(QPoint(x, y), point_size, point_size)
            
            # Draw outer glow
            for i in range(5, 0, -1):
                glow_color = QColor(color)
                glow_color.setAlpha(50 - i * 8)
                painter.setBrush(QBrush(glow_color))
                glow_size = point_size + i * 2
                painter.drawEllipse(QPoint(x, y), glow_size, glow_size)
        
        # Draw valid moves (if a piece is selected)
        if self.valid_moves:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self.valid_move_color))
            for ring, spoke in self.valid_moves:
                x, y = self.get_position_coordinates(ring, spoke, center_x, center_y, radii)
                painter.drawEllipse(QPoint(x, y), 15, 15)
        
        # Draw hover highlight
        if self.hover_position is not None:
            ring, spoke = self.hover_position
            if (ring, spoke) in self.valid_moves:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(self.hover_color))
                x, y = self.get_position_coordinates(ring, spoke, center_x, center_y, radii)
                painter.drawEllipse(QPoint(x, y), 17, 17)
        
        # Draw pieces
        for ring in range(4):
            for spoke in range(8):
                if self.board[ring, spoke] != 0:
                    x, y = self.get_position_coordinates(ring, spoke, center_x, center_y, radii)
                    
                    # Set color based on player
                    if self.board[ring, spoke] == 1:
                        base_color = self.player1_color
                    else:
                        base_color = self.player2_color
                    
                    # Energy level affects piece appearance
                    energy = self.piece_values[ring, spoke]
                    
                    # Create gradient based on energy
                    gradient = QRadialGradient(x, y, 15)
                    
                    # Center color based on energy
                    center_color = base_color.lighter(100 + energy * 8)
                    gradient.setColorAt(0, center_color)
                    
                    # Outer color
                    outer_color = base_color
                    gradient.setColorAt(1, outer_color)
                    
                    # Draw an outline for the selected piece
                    if self.selected_piece == (ring, spoke):
                        painter.setPen(QPen(self.selected_color, 3))
                    else:
                        painter.setPen(QPen(Qt.black, 1))
                    
                    # Set brush with gradient
                    painter.setBrush(QBrush(gradient))
                    
                    # Draw the piece with size based on energy
                    piece_size = 12 + min(energy, 8)
                    painter.drawEllipse(QPoint(x, y), piece_size, piece_size)
                    
                    # Draw the energy value
                    if energy > 0:
                        painter.setPen(QPen(Qt.white))
                        painter.setFont(QFont("Arial", 9, QFont.Bold))
                        energy_text = str(energy)
                        text_rect = QRect(x - 6, y - 8, 12, 16)
                        painter.drawText(text_rect, Qt.AlignCenter, energy_text)
        
        # Draw animation effects for captures
        for pos in self.animation_positions:
            x, y, frame, player = pos
            if player == 1:
                color = self.player1_color
            else:
                color = self.player2_color
                
            # Fade out as frame increases
            alpha = 255 - min(255, frame * 25)
            size = 20 - frame
            explosion_color = QColor(color)
            explosion_color.setAlpha(alpha)
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(explosion_color))
            painter.drawEllipse(QPoint(x, y), size, size)
            
            # Draw particle effects
            for i in range(8):
                angle = i * 45 + frame * 5
                rad_angle = angle * np.pi / 180
                dist = 5 + frame * 3
                px = x + int(dist * np.cos(rad_angle))
                py = y + int(dist * np.sin(rad_angle))
                particle_color = QColor(color.lighter(150))
                particle_color.setAlpha(alpha)
                painter.setBrush(QBrush(particle_color))
                particle_size = max(1, 5 - frame // 2)
                painter.drawEllipse(QPoint(px, py), particle_size, particle_size)
    
    def update_animation(self):
        """Update the animation frames"""
        new_positions = []
        for x, y, frame, player in self.animation_positions:
            if frame < 10:  # Animation lasts 10 frames
                new_positions.append((x, y, frame + 1, player))
        
        self.animation_positions = new_positions
        if not self.animation_positions:
            self.animation_timer.stop()
        self.update()
    
    def add_capture_animation(self, ring, spoke, player):
        """Add a capture animation at the specified position"""
        x, y = self.get_position_coordinates(
            ring, spoke, 
            self.width() // 2, 
            self.height() // 2, 
            [self.height() // 8, self.height() // 4, 3 * self.height() // 8, self.height() // 2]
        )
        
        self.animation_positions.append((x, y, 0, player))
        if not self.animation_timer.isActive():
            self.animation_timer.start(50)  # 20 fps
    
    def get_position_coordinates(self, ring, spoke, center_x, center_y, radii):
        """Convert board position to screen coordinates"""
        angle = spoke * 45
        rad_angle = angle * np.pi / 180
        radius = radii[ring]
        x = center_x + radius * np.cos(rad_angle)
        y = center_y + radius * np.sin(rad_angle)
        return int(x), int(y)
    
    def get_board_position(self, x, y):
        """Convert screen coordinates to board position"""
        width = self.width()
        height = self.height()
        size = min(width, height) - 40
        center_x = width // 2
        center_y = height // 2
        radii = [size // 8, size // 4, 3 * size // 8, size // 2]
        
        # Calculate distance from center
        dx = x - center_x
        dy = y - center_y
        distance = np.sqrt(dx**2 + dy**2)
        
        # Determine ring
        ring = None
        for i, radius in enumerate(radii):
            if distance < radius + 15:
                ring = i
                break
        
        if ring is None:
            return None  # Click outside the board
            
        # Determine spoke
        angle = np.arctan2(dy, dx)
        if angle < 0:
            angle += 2 * np.pi
        spoke = int(np.round(angle / (np.pi / 4))) % 8
        
        return ring, spoke
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            position = self.get_board_position(event.x(), event.y())
            if position:
                ring, spoke = position
                
                # If there's already a selected piece and this is a valid move
                if self.selected_piece and position in self.valid_moves:
                    self.move_made.emit(self.selected_piece[0], self.selected_piece[1], ring, spoke)
                    self.selected_piece = None
                    self.valid_moves = []
                
                # Otherwise, select this piece if it belongs to the current player
                elif self.board[ring, spoke] != 0:
                    self.piece_clicked.emit(ring, spoke)
                
                self.update()
    
    def mouseMoveEvent(self, event):
        position = self.get_board_position(event.x(), event.y())
        if position != self.hover_position:
            self.hover_position = position
            self.update()
    
    def leaveEvent(self, event):
        self.hover_position = None
        self.update()
    
    def set_selected_piece(self, ring, spoke, valid_moves):
        """Set the selected piece and its valid moves"""
        self.selected_piece = (ring, spoke)
        self.valid_moves = valid_moves
        self.update()
    
    def clear_selection(self):
        """Clear the selected piece and valid moves"""
        self.selected_piece = None
        self.valid_moves = []
        self.update()
    
    def update_board(self, board, piece_values):
        """Update the board state and redraw"""
        self.board = board.copy()
        self.piece_values = piece_values.copy()
        self.update()


class EnhancedOrbitalCaptureGame:
    def __init__(self):
        # Initialize the board: 4 rings × 8 spokes
        # 0 = empty, 1 = player 1, 2 = player 2
        self.board = np.zeros((4, 8), dtype=int)
        self.piece_values = np.zeros((4, 8), dtype=int)  # Energy values for pieces
        self.current_player = 1
        self.player1_pieces = 4
        self.player2_pieces = 4
        self.player1_energy = 0
        self.player2_energy = 0
        
        # Special points on the board (ring, spoke, type)
        self.special_points = []
        
        # Game modes and settings
        self.inner_circle_threshold = 3  # Pieces needed in inner circle to win
        self.energy_threshold = 12  # Energy needed to win
        self.allow_jumps = True
        self.allow_nimber = True
        self.energy_collection = True
        
        # Track pieces in the innermost ring
        self.player1_inner_pieces = 0
        self.player2_inner_pieces = 0
        
        # Initialize the board with starting positions
        self.reset_board()
    
    def reset_board(self):
        """Reset the board to initial state"""
        self.board = np.zeros((4, 8), dtype=int)
        self.piece_values = np.zeros((4, 8), dtype=int)
        
        # Reset counters
        self.player1_pieces = 4
        self.player2_pieces = 4
        self.player1_energy = 0
        self.player2_energy = 0
        self.player1_inner_pieces = 0
        self.player2_inner_pieces = 0
        
        # Set up initial positions - alternating pattern on outer ring
        for i in [0, 2, 4, 6]:
            self.board[3][i] = 1  # Player 1
            
        for i in [1, 3, 5, 7]:
            self.board[3][i] = 2  # Player 2
            
        # Generate random special points (power, jump, shield)
        # Create a mix of special point types
        self.special_points = [
            (0, 0, "power"),   # Center top - power point
            (0, 4, "power"),   # Center bottom - power point
            (1, 2, "jump"),    # Middle ring - jump point
            (1, 6, "jump"),    # Middle ring - jump point
            (2, 1, "shield"),  # Outer middle ring - shield point
            (2, 5, "shield"),  # Outer middle ring - shield point
        ]
        
        # Reset current player
        self.current_player = 1
    
    def get_valid_moves(self, ring, spoke):
        """Get all valid moves for a piece at the given position"""
        valid_moves = []
        
        # Check if the position has a piece of the current player
        if self.board[ring][spoke] != self.current_player:
            return []
        
        # Get piece energy
        piece_energy = self.piece_values[ring][spoke]
        
        # Standard moves
        
        # 1. Move along the ring (clockwise and counterclockwise)
        for offset in [-1, 1]:
            next_spoke = (spoke + offset) % 8
            if self.board[ring][next_spoke] == 0:
                valid_moves.append((ring, next_spoke))
        
        # 2. Move inward (if not already at the innermost ring)
        if ring > 0 and self.board[ring-1][spoke] == 0:
            valid_moves.append((ring-1, spoke))
        
        # 3. Move outward if they have energy (new rule)
        if ring < 3 and piece_energy >= 2 and self.board[ring+1][spoke] == 0:
            valid_moves.append((ring+1, spoke))
        
        # 4. Advanced moves based on energy
        if piece_energy >= 3:
            # Diagonal moves along adjacent spokes and rings
            for r_offset in [-1, 0, 1]:
                new_ring = ring + r_offset
                if 0 <= new_ring <= 3:  # Valid ring
                    for s_offset in [-1, 1]:
                        new_spoke = (spoke + s_offset) % 8
                        # Make sure it's not a standard move and space is empty
                        if (new_ring, new_spoke) not in valid_moves and self.board[new_ring][new_spoke] == 0:
                            valid_moves.append((new_ring, new_spoke))
        
        # 5. Jump moves with higher energy
        if self.allow_jumps and piece_energy >= 4:
            # Jump over one intersection
            for offset in [-2, 2]:
                new_spoke = (spoke + offset) % 8
                if self.board[ring][new_spoke] == 0:
                    valid_moves.append((ring, new_spoke))
            
            # Jump two rings inward
            if ring >= 2 and self.board[ring-2][spoke] == 0:
                valid_moves.append((ring-2, spoke))
        
        # 6. Special "nimber" moves (combinatorial game theory concept)
        # These moves create interacting subgames
        if self.allow_nimber and piece_energy >= 5:
            # Jump to any empty spot in the same ring
            for new_spoke in range(8):
                if new_spoke != spoke and self.board[ring][new_spoke] == 0:
                    valid_moves.append((ring, new_spoke))
            
            # Jump to the opposite spoke in any ring
            opposite_spoke = (spoke + 4) % 8
            for new_ring in range(4):
                if new_ring != ring and self.board[new_ring][opposite_spoke] == 0:
                    valid_moves.append((new_ring, opposite_spoke))
        
        return valid_moves
    
    def check_captures(self, ring, spoke):
        """Check and process captures after a move to (ring, spoke)"""
        opponent = 2 if self.current_player == 1 else 1
        captured = []
        
        # Basic capture: surround opponent pieces
        # Check all opponent pieces
        for check_ring in range(4):
            for check_spoke in range(8):
                # Skip if not opponent's piece
                if self.board[check_ring][check_spoke] != opponent:
                    continue
                
                # Check different capture patterns
                
                # 1. Classic three-point surround (two adjacent on same ring + one inner)
                left_spoke = (check_spoke - 1) % 8
                right_spoke = (check_spoke + 1) % 8
                
                # Adjacent same ring capture
                adjacent_same_ring = (
                    self.board[check_ring][left_spoke] == self.current_player and
                    self.board[check_ring][right_spoke] == self.current_player
                )
                
                # Inner position
                inner_position = False
                if check_ring > 0:
                    inner_position = self.board[check_ring-1][check_spoke] == self.current_player
                
                # Basic three-point capture
                if adjacent_same_ring and inner_position:
                    captured.append((check_ring, check_spoke))
                    continue
                
                # 2. Energy-based captures (higher energy can capture without surrounding)
                # Calculate total energy surrounding the opponent piece
                surrounding_energy = 0
                
                # Check all adjacent positions
                for r_offset in [-1, 0, 1]:
                    new_ring = check_ring + r_offset
                    if 0 <= new_ring <= 3:  # Valid ring
                        # Check adjacent spokes
                        for s_offset in [-1, 0, 1]:
                            if r_offset == 0 and s_offset == 0:
                                continue  # Skip the piece itself
                            
                            new_spoke = (check_spoke + s_offset) % 8
                            if self.board[new_ring][new_spoke] == self.current_player:
                                surrounding_energy += self.piece_values[new_ring][new_spoke]
                
                # Energy-based capture: if surrounding energy > 2× opponent piece energy
                opponent_energy = self.piece_values[check_ring][check_spoke]
                if surrounding_energy >= opponent_energy * 2 and surrounding_energy >= 4:
                    if (check_ring, check_spoke) not in captured:
                        captured.append((check_ring, check_spoke))
        
        # Process captures
        for r, s in captured:
            # If capturing a piece from the innermost ring, update the count
            if r == 0:
                if opponent == 1:
                    self.player1_inner_pieces -= 1
                else:
                    self.player2_inner_pieces -= 1
            
            # Transfer some energy from captured piece
            captured_energy = self.piece_values[r][s]
            transfer_energy = max(1, captured_energy // 2)
            
            # Add to current player's total energy
            if self.current_player == 1:
                self.player1_energy += transfer_energy
            else:
                self.player2_energy += transfer_energy
            
            # Remove the piece
            self.board[r][s] = 0
            self.piece_values[r][s] = 0
            
            if opponent == 1:
                self.player1_pieces -= 1
            else:
                self.player2_pieces -= 1
                
        return captured
    
    def handle_special_point(self, ring, spoke):
        """Handle landing on a special point"""
        special_point = None
        for r, s, point_type in self.special_points:
            if r == ring and s == spoke:
                special_point = point_type
                break
                
        if not special_point:
            return None
        
        # Apply effects based on special point type
        if special_point == "power":
            # Increase piece energy
            self.piece_values[ring][spoke] += 2
            return {"type": "power", "message": "Power point! +2 Energy"}
            
        elif special_point == "jump":
            # Grant extra energy to the player's reserve
            if self.current_player == 1:
                self.player1_energy += 2
            else:
                self.player2_energy += 2
            return {"type": "jump", "message": "Jump point! +2 to reserve energy"}
            
        elif special_point == "shield":
            # Make piece more resistant to capture
            self.piece_values[ring][spoke] += 1
            if self.current_player == 1:
                self.player1_energy += 1
            else:
                self.player2_energy += 1
            return {"type": "shield", "message": "Shield point! +1 Energy and +1 reserve"}
            
        return None
    
    def apply_energy_from_position(self, ring, spoke):
        """Apply energy from board position - inner rings give more energy"""
        if not self.energy_collection:
            return 0
            
        # Energy values by ring: inner rings worth more
        ring_energy = [3, 2, 1, 0]
        energy_gained = ring_energy[ring]
        
        # Add energy to the piece
        if energy_gained > 0:
            self.piece_values[ring][spoke] += energy_gained
            
        return energy_gained
    
    def move(self, from_ring, from_spoke, to_ring, to_spoke):
        """Move a piece from one position to another"""
        # Calculate energy cost of the move
        energy_cost = 0
        piece_energy = self.piece_values[from_ring][from_spoke]
        
        # Calculate basic distance
        ring_distance = abs(to_ring - from_ring)
        spoke_distance = min(abs(to_spoke - from_spoke), 8 - abs(to_spoke - from_spoke))
        total_distance = ring_distance + spoke_distance
        
        # Special moves cost energy
        if total_distance > 1:
            energy_cost = total_distance
            
        # Moving outward costs extra energy
        if to_ring > from_ring:
            energy_cost += 2
            
        # Check if piece has enough energy
        if piece_energy < energy_cost:
            # Check reserve energy
            reserve_energy = self.player1_energy if self.current_player == 1 else self.player2_energy
            
            if reserve_energy + piece_energy < energy_cost:
                # Not enough energy for move
                return {"error": "Not enough energy for this move"}
            else:
                # Use reserve energy
                reserve_needed = energy_cost - piece_energy
                if self.current_player == 1:
                    self.player1_energy -= reserve_needed
                else:
                    self.player2_energy -= reserve_needed
                
                # Set piece energy to 0 after the move
                energy_after_move = 0
        else:
            # Enough energy in the piece itself
            energy_after_move = piece_energy - energy_cost
        
        # Check if moving to innermost ring and update counts
        if to_ring == 0:
            if self.current_player == 1:
                self.player1_inner_pieces += 1
            else:
                self.player2_inner_pieces += 1
        
        # If moving from the innermost ring, decrement count
        if from_ring == 0:
            if self.current_player == 1:
                self.player1_inner_pieces -= 1
            else:
                self.player2_inner_pieces -= 1
        
        # Move the piece
        self.board[from_ring][from_spoke] = 0
        self.board[to_ring][to_spoke] = self.current_player
        
        # Update piece energy
        # Update piece energy
        self.piece_values[to_ring][to_spoke] = energy_after_move
        
        # Apply energy from new position
        gained_energy = self.apply_energy_from_position(to_ring, to_spoke)
        
        # Check for special point effect
        special_point_effect = self.handle_special_point(to_ring, to_spoke)
        
        # Check for captures
        captured = self.check_captures(to_ring, to_spoke)
        
        # Check for victory conditions
        victory = self.check_victory()
        
        # Switch to the other player
        self.current_player = 2 if self.current_player == 1 else 1
        
        return {
            "success": True,
            "energy_cost": energy_cost,
            "energy_gained": gained_energy,
            "special_point": special_point_effect,
            "captured": captured,
            "victory": victory
        }
    
    def check_victory(self):
        """Check for victory conditions"""
        # Check if a player has zero pieces left
        if self.player1_pieces == 0:
            return {"winner": 2, "reason": "Player 2 captured all Player 1's pieces"}
        elif self.player2_pieces == 0:
            return {"winner": 1, "reason": "Player 1 captured all Player 2's pieces"}
        
        # Check inner circle control
        if self.player1_inner_pieces >= self.inner_circle_threshold:
            return {"winner": 1, "reason": f"Player 1 has {self.player1_inner_pieces} pieces in the inner circle"}
        elif self.player2_inner_pieces >= self.inner_circle_threshold:
            return {"winner": 2, "reason": f"Player 2 has {self.player2_inner_pieces} pieces in the inner circle"}
        
        # Check energy threshold
        if self.player1_energy >= self.energy_threshold:
            return {"winner": 1, "reason": f"Player 1 has reached {self.player1_energy} energy"}
        elif self.player2_energy >= self.energy_threshold:
            return {"winner": 2, "reason": f"Player 2 has reached {self.player2_energy} energy"}
        
        return None


class GameWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.game = EnhancedOrbitalCaptureGame()
        self.initialize_ui()
        
    def initialize_ui(self):
        """Initialize the game UI"""
        self.setWindowTitle("Orbital Capture - Enhanced with CGT")
        self.setMinimumSize(800, 700)
        
        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Create game board
        self.board_widget = BoardWidget()
        self.board_widget.piece_clicked.connect(self.on_piece_clicked)
        self.board_widget.move_made.connect(self.on_move_made)
        main_layout.addWidget(self.board_widget)
        
        # Create info panel
        info_panel = QWidget()
        info_layout = QHBoxLayout(info_panel)
        
        # Player 1 info
        player1_widget = QWidget()
        player1_layout = QVBoxLayout(player1_widget)
        player1_layout.addWidget(QLabel("Player 1 (Red)"))
        self.player1_pieces_label = QLabel("Pieces: 4")
        player1_layout.addWidget(self.player1_pieces_label)
        self.player1_energy_label = QLabel("Energy: 0")
        player1_layout.addWidget(self.player1_energy_label)
        self.player1_inner_label = QLabel("Inner Circle: 0")
        player1_layout.addWidget(self.player1_inner_label)
        info_layout.addWidget(player1_widget)
        
        # Game info
        game_info_widget = QWidget()
        game_info_layout = QVBoxLayout(game_info_widget)
        self.turn_label = QLabel("Current Turn: Player 1")
        self.turn_label.setAlignment(Qt.AlignCenter)
        self.turn_label.setFont(QFont("Arial", 12, QFont.Bold))
        game_info_layout.addWidget(self.turn_label)
        
        # Status message display
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 10))
        game_info_layout.addWidget(self.status_label)
        
        # Reset button
        reset_button = QPushButton("New Game")
        reset_button.clicked.connect(self.reset_game)
        game_info_layout.addWidget(reset_button)
        
        # Game mode selection
        mode_widget = QWidget()
        mode_layout = QHBoxLayout(mode_widget)
        
        # Difficulty level
        mode_layout.addWidget(QLabel("Difficulty:"))
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["Easy", "Medium", "Hard", "Expert"])
        self.difficulty_combo.setCurrentIndex(1)  # Default to Medium
        self.difficulty_combo.currentIndexChanged.connect(self.update_game_settings)
        mode_layout.addWidget(self.difficulty_combo)
        
        game_info_layout.addWidget(mode_widget)
        info_layout.addWidget(game_info_widget)
        
        # Player 2 info
        player2_widget = QWidget()
        player2_layout = QVBoxLayout(player2_widget)
        player2_layout.addWidget(QLabel("Player 2 (Blue)"))
        self.player2_pieces_label = QLabel("Pieces: 4")
        player2_layout.addWidget(self.player2_pieces_label)
        self.player2_energy_label = QLabel("Energy: 0")
        player2_layout.addWidget(self.player2_energy_label)
        self.player2_inner_label = QLabel("Inner Circle: 0")
        player2_layout.addWidget(self.player2_inner_label)
        info_layout.addWidget(player2_widget)
        
        main_layout.addWidget(info_panel)
        
        # Game settings
        settings_panel = QWidget()
        settings_layout = QHBoxLayout(settings_panel)
        
        # Win conditions
        win_widget = QWidget()
        win_layout = QVBoxLayout(win_widget)
        win_layout.addWidget(QLabel("Win Conditions"))
        
        inner_control_widget = QWidget()
        inner_control_layout = QHBoxLayout(inner_control_widget)
        inner_control_layout.addWidget(QLabel("Inner Circle Control:"))
        self.inner_slider = QSlider(Qt.Horizontal)
        self.inner_slider.setMinimum(2)
        self.inner_slider.setMaximum(4)
        self.inner_slider.setValue(3)
        self.inner_slider.setTickPosition(QSlider.TicksBelow)
        self.inner_slider.setTickInterval(1)
        self.inner_slider.valueChanged.connect(self.update_game_settings)
        inner_control_layout.addWidget(self.inner_slider)
        self.inner_value_label = QLabel("3")
        inner_control_layout.addWidget(self.inner_value_label)
        win_layout.addWidget(inner_control_widget)
        
        energy_widget = QWidget()
        energy_layout = QHBoxLayout(energy_widget)
        energy_layout.addWidget(QLabel("Energy Threshold:"))
        self.energy_slider = QSlider(Qt.Horizontal)
        self.energy_slider.setMinimum(10)
        self.energy_slider.setMaximum(20)
        self.energy_slider.setValue(12)
        self.energy_slider.setTickPosition(QSlider.TicksBelow)
        self.energy_slider.setTickInterval(2)
        self.energy_slider.valueChanged.connect(self.update_game_settings)
        energy_layout.addWidget(self.energy_slider)
        self.energy_value_label = QLabel("12")
        energy_layout.addWidget(self.energy_value_label)
        win_layout.addWidget(energy_widget)
        
        settings_layout.addWidget(win_widget)
        
        main_layout.addWidget(settings_panel)
        
        # Set central widget
        self.setCentralWidget(central_widget)
        
        # Initialize the board display
        self.update_display()
    
    def update_game_settings(self):
        """Update game settings based on UI controls"""
        # Update win conditions
        inner_value = self.inner_slider.value()
        self.inner_value_label.setText(str(inner_value))
        self.game.inner_circle_threshold = inner_value
        
        energy_value = self.energy_slider.value()
        self.energy_value_label.setText(str(energy_value))
        self.game.energy_threshold = energy_value
        
        # Update difficulty-based settings
        difficulty = self.difficulty_combo.currentIndex()
        
        if difficulty == 0:  # Easy
            self.game.allow_jumps = False
            self.game.allow_nimber = False
        elif difficulty == 1:  # Medium
            self.game.allow_jumps = True
            self.game.allow_nimber = False
        elif difficulty == 2:  # Hard
            self.game.allow_jumps = True
            self.game.allow_nimber = True
        elif difficulty == 3:  # Expert
            self.game.allow_jumps = True
            self.game.allow_nimber = True
            # Additional complexity for expert mode could be added here
    
    def on_piece_clicked(self, ring, spoke):
        """Handle piece selection"""
        # Check if it's the current player's piece
        if self.game.board[ring][spoke] == self.game.current_player:
            valid_moves = self.game.get_valid_moves(ring, spoke)
            self.board_widget.set_selected_piece(ring, spoke, valid_moves)
            
            # Show piece information
            piece_energy = self.game.piece_values[ring][spoke]
            self.status_label.setText(f"Piece selected: Energy = {piece_energy}")
        else:
            self.board_widget.clear_selection()
            self.status_label.setText("")
    
    def on_move_made(self, from_ring, from_spoke, to_ring, to_spoke):
        """Handle moves on the board"""
        result = self.game.move(from_ring, from_spoke, to_ring, to_spoke)
        
        if "error" in result:
            QMessageBox.warning(self, "Invalid Move", result["error"])
            return
        
        # Update the board display
        self.update_display()
        
        # Show status message
        message = f"Move completed. Energy cost: {result['energy_cost']}"
        
        if result["energy_gained"] > 0:
            message += f", Gained: {result['energy_gained']} energy"
            
        if result["special_point"]:
            message += f" | {result['special_point']['message']}"
            
        if result["captured"]:
            message += f" | Captured {len(result['captured'])} pieces!"
            # Add capture animations
            for ring, spoke in result["captured"]:
                opponent = 2 if self.game.current_player == 1 else 1
                self.board_widget.add_capture_animation(ring, spoke, opponent)
                
        self.status_label.setText(message)
        
        # Check for victory
        if result["victory"]:
            winner = result["victory"]["winner"]
            reason = result["victory"]["reason"]
            QMessageBox.information(self, "Game Over", 
                                   f"Player {winner} wins!\n{reason}")
            self.reset_game()
    
    def update_display(self):
        """Update the game display based on current state"""
        # Update board
        self.board_widget.update_board(self.game.board, self.game.piece_values)
        self.board_widget.set_special_points(self.game.special_points)
        
        # Update player info
        self.player1_pieces_label.setText(f"Pieces: {self.game.player1_pieces}")
        self.player2_pieces_label.setText(f"Pieces: {self.game.player2_pieces}")
        
        self.player1_energy_label.setText(f"Energy: {self.game.player1_energy}")
        self.player2_energy_label.setText(f"Energy: {self.game.player2_energy}")
        
        self.player1_inner_label.setText(f"Inner Circle: {self.game.player1_inner_pieces}")
        self.player2_inner_label.setText(f"Inner Circle: {self.game.player2_inner_pieces}")
        
        # Update turn indicator
        self.turn_label.setText(f"Current Turn: Player {self.game.current_player}")
    
    def reset_game(self):
        """Reset the game to initial state"""
        self.game.reset_board()
        self.board_widget.reset_board()
        self.update_display()
        self.status_label.setText("Game reset. Player 1 starts.")


class RulesDialog(QMessageBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Game Rules")
        self.setIcon(QMessageBox.Information)
        
        rules_text = """
        <h3>Orbital Capture - Enhanced with Combinatorial Game Theory</h3>
        
        <p><b>Goal:</b> Win by achieving one of these conditions:</p>
        <ul>
            <li>Capture all opponent pieces</li>
            <li>Control the inner circle with 3 pieces</li>
            <li>Reach 12 energy points</li>
        </ul>
        
        <p><b>Movement:</b></p>
        <ul>
            <li>Basic moves: one step inward or along a ring</li>
            <li>Energy-based moves: outward (costs 2 energy)</li>
            <li>Advanced moves (3+ energy): diagonal movements</li>
            <li>Jump moves (4+ energy): jump over spaces</li>
            <li>Nimber moves (5+ energy): special jumps to create subgames</li>
        </ul>
        
        <p><b>Special Points:</b></p>
        <ul>
            <li>Power points: +2 piece energy</li>
            <li>Jump points: +2 reserve energy</li>
            <li>Shield points: +1 piece energy, +1 reserve</li>
        </ul>
        
        <p><b>Energy:</b></p>
        <ul>
            <li>Inner rings give more energy per turn</li>
            <li>Capturing pieces grants energy</li>
            <li>Energy can be used for special moves</li>
        </ul>
        
        <p><b>Captures:</b></p>
        <ul>
            <li>Surround opponent piece on same ring + inner position</li>
            <li>Energy-based: surrounding energy > 2× opponent energy</li>
        </ul>
        """
        
        self.setText(rules_text)
        self.setStandardButtons(QMessageBox.Ok)


def main():
    app = QApplication(sys.argv)
    window = GameWindow()
    
    # Show rules dialog on first launch
    rules = RulesDialog(window)
    rules.exec_()
    
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()