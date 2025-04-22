import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout, 
                            QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
                            QMessageBox)
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QFont
from PyQt5.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal, QTimer

class BoardWidget(QWidget):
    piece_clicked = pyqtSignal(int, int)  # Ring, spoke
    move_made = pyqtSignal(int, int, int, int)  # From ring, from spoke, to ring, to spoke
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500, 500)
        self.board = np.zeros((4, 8), dtype=int)
        self.selected_piece = None
        self.valid_moves = []
        self.hover_position = None
        
        # Colors
        self.board_color = QColor(240, 240, 240)
        self.grid_color = QColor(0, 0, 0)
        self.player1_color = QColor(255, 50, 50)  # Red
        self.player2_color = QColor(50, 50, 255)  # Blue
        self.selected_color = QColor(255, 255, 0)  # Yellow
        self.valid_move_color = QColor(0, 200, 0, 100)  # Semi-transparent green
        self.hover_color = QColor(0, 200, 200, 150)  # Semi-transparent cyan
        self.inner_circle_color = QColor(255, 215, 0, 50)  # Semi-transparent gold for inner circle

        # Initialize the board
        self.reset_board()

    def reset_board(self):
        """Reset the board to initial state"""
        self.board = np.zeros((4, 8), dtype=int)
        
        # Set up initial positions
        # Player 1 on positions 1, 3, 5, 7 of outermost ring
        for i in [0, 2, 4, 6]:
            self.board[3][i] = 1
            
        # Player 2 on positions 2, 4, 6, 8 of outermost ring
        for i in [1, 3, 5, 7]:
            self.board[3][i] = 2
            
        self.selected_piece = None
        self.valid_moves = []
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
        
        # Highlight the innermost circle with a special color
        painter.setBrush(QBrush(self.inner_circle_color))
        painter.setPen(Qt.NoPen)
        innermost_radius = size // 8
        painter.drawEllipse(center_x - innermost_radius, center_y - innermost_radius, 
                           innermost_radius * 2, innermost_radius * 2)
        
        # Set up the pen for grid lines
        grid_pen = QPen(self.grid_color, 2)
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
                        painter.setBrush(QBrush(self.player1_color))
                    else:
                        painter.setBrush(QBrush(self.player2_color))
                    
                    # Draw an outline for the selected piece
                    if self.selected_piece == (ring, spoke):
                        painter.setPen(QPen(self.selected_color, 3))
                    else:
                        painter.setPen(QPen(Qt.black, 1))
                    
                    # Draw the piece
                    painter.drawEllipse(QPoint(x, y), 12, 12)
                    
                    # Draw the player number
                    painter.setPen(QPen(Qt.white))
                    painter.setFont(QFont("Arial", 9, QFont.Bold))
                    player_num = str(self.board[ring, spoke])
                    text_rect = QRect(x - 6, y - 8, 12, 16)
                    painter.drawText(text_rect, Qt.AlignCenter, player_num)
    
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
    
    def update_board(self, board):
        """Update the board state and redraw"""
        self.board = board.copy()
        self.update()


class OrbitalCaptureGame:
    def __init__(self):
        # Initialize the board: 4 rings × 8 spokes
        # 0 = empty, 1 = player 1, 2 = player 2
        self.board = np.zeros((4, 8), dtype=int)
        self.current_player = 1
        self.player1_pieces = 8
        self.player2_pieces = 8
        # Track pieces in the innermost ring
        self.player1_inner_pieces = 0
        self.player2_inner_pieces = 0
        # Set threshold for inner circle win condition (can be adjusted)
        self.inner_circle_threshold = 3
        
        # Set up initial positions
        # Player 1 on positions 1, 3, 5, 7 of outermost ring
        for i in [0, 2, 4, 6]:
            self.board[3][i] = 1
            
        # Player 2 on positions 2, 4, 6, 8 of outermost ring
        for i in [1, 3, 5, 7]:
            self.board[3][i] = 2
    
    def get_valid_moves(self, ring, spoke):
        """Get all valid moves for a piece at the given position"""
        valid_moves = []
        
        # Check if the position has a piece of the current player
        if self.board[ring][spoke] != self.current_player:
            return []
        
        # Move along the ring (clockwise and counterclockwise)
        for offset in [-1, 1]:
            next_spoke = (spoke + offset) % 8
            if self.board[ring][next_spoke] == 0:
                valid_moves.append((ring, next_spoke))
        
        # Move inward (if not already at the innermost ring)
        if ring > 0 and self.board[ring-1][spoke] == 0:
            valid_moves.append((ring-1, spoke))
        
        return valid_moves
    
    def check_captures(self, ring, spoke):
        """Check and process captures after a move to (ring, spoke)"""
        opponent = 2 if self.current_player == 1 else 1
        captured = []
        
        # Check all neighboring positions for potential captures
        for check_spoke in range(8):
            for check_ring in range(4):
                # Skip if not opponent's piece
                if self.board[check_ring][check_spoke] != opponent:
                    continue
                
                # Check if the piece is surrounded
                # 1. Check adjacent positions on the same ring
                left_spoke = (check_spoke - 1) % 8
                right_spoke = (check_spoke + 1) % 8
                adjacent_same_ring = (
                    self.board[check_ring][left_spoke] == self.current_player and
                    self.board[check_ring][right_spoke] == self.current_player
                )
                
                # 2. Check inner position on the same spoke (if not on innermost ring)
                inner_position = False
                if check_ring > 0:
                    inner_position = self.board[check_ring-1][check_spoke] == self.current_player
                
                # If surrounded, add to captured list
                if adjacent_same_ring and inner_position:
                    captured.append((check_ring, check_spoke))
        
        # Remove captured pieces and update inner piece counts if necessary
        for r, s in captured:
            # If capturing a piece from the innermost ring, update the count
            if r == 0:
                if opponent == 1:
                    self.player1_inner_pieces -= 1
                else:
                    self.player2_inner_pieces -= 1
            
            # Remove the piece
            self.board[r][s] = 0
            if opponent == 1:
                self.player1_pieces -= 1
            else:
                self.player2_pieces -= 1
                
        return captured
    
    def move(self, from_ring, from_spoke, to_ring, to_spoke):
        """Move a piece from one position to another"""
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
        
        # Make the move
        self.board[from_ring][from_spoke] = 0
        self.board[to_ring][to_spoke] = self.current_player
        
        # Check for captures
        captured = self.check_captures(to_ring, to_spoke)
        
        # Check for inner circle win condition before switching players
        inner_circle_win, winner = self.check_inner_circle_win()
        
        # Switch players
        self.current_player = 2 if self.current_player == 1 else 1
        
        # Check if the game is over
        game_over, winner_standard, reason_standard = self.check_game_over()
        
        # Combine win conditions
        if inner_circle_win:
            return {
                "captured": captured, 
                "game_over": True, 
                "winner": winner, 
                "reason": f"Player {winner} reached {self.inner_circle_threshold} pieces in the innermost circle first"
            }
        
        return {
            "captured": captured, 
            "game_over": game_over, 
            "winner": winner_standard, 
            "reason": reason_standard
        }
    
    def check_inner_circle_win(self):
        """Check if either player has reached the threshold for pieces in the innermost ring"""
        if self.player1_inner_pieces >= self.inner_circle_threshold:
            return True, 1
        elif self.player2_inner_pieces >= self.inner_circle_threshold:
            return True, 2
        return False, None
    
    def check_game_over(self):
        """Check if the game is over and determine the winner"""
        # Check if any player has fewer than 3 pieces
        if self.player1_pieces < 3:
            return True, 2, "Player 1 has fewer than 3 pieces remaining"
        if self.player2_pieces < 3:
            return True, 1, "Player 2 has fewer than 3 pieces remaining"
        
        # Check if current player has any legal moves
        player1_has_moves = False
        player2_has_moves = False
        
        # Check for player 1's moves
        for ring in range(4):
            for spoke in range(8):
                if self.board[ring][spoke] == 1:
                    # Temporarily set current player to check moves
                    original_player = self.current_player
                    self.current_player = 1
                    moves = self.get_valid_moves(ring, spoke)
                    self.current_player = original_player
                    if moves:
                        player1_has_moves = True
                        break
            if player1_has_moves:
                break
        
        # Check for player 2's moves
        for ring in range(4):
            for spoke in range(8):
                if self.board[ring][spoke] == 2:
                    # Temporarily set current player to check moves
                    original_player = self.current_player
                    self.current_player = 2
                    moves = self.get_valid_moves(ring, spoke)
                    self.current_player = original_player
                    if moves:
                        player2_has_moves = True
                        break
            if player2_has_moves:
                break
        
        # Check for stalemate (neither player can move)
        if not player1_has_moves and not player2_has_moves:
            # Player with more pieces wins
            if self.player1_pieces > self.player2_pieces:
                return True, 1, "Stalemate - Player 1 wins with more pieces"
            elif self.player2_pieces > self.player1_pieces:
                return True, 2, "Stalemate - Player 2 wins with more pieces"
            else:
                # If equal pieces, compare inner ring positions
                p1_score = self.calculate_inner_ring_score(1)
                p2_score = self.calculate_inner_ring_score(2)
                if p1_score > p2_score:
                    return True, 1, "Stalemate - Player 1 wins with better positions"
                else:
                    return True, 2, "Stalemate - Player 2 wins with better positions"
        
        # Check if current player has no legal moves
        if self.current_player == 1 and not player1_has_moves:
            return True, 2, "Player 1 has no legal moves"
        if self.current_player == 2 and not player2_has_moves:
            return True, 1, "Player 2 has no legal moves"
        
        return False, None, None
    
    def calculate_inner_ring_score(self, player):
        """Calculate score based on inner ring positions for specified player"""
        score = 0
        for ring in range(4):
            ring_value = 4 - ring  # Inner rings are worth more
            for spoke in range(8):
                if self.board[ring][spoke] == player:
                    score += ring_value
        return score
    
    def calculate_score(self):
        """Calculate scores for both players"""
        scores = {1: 0, 2: 0}
        
        # Count pieces with inner rings worth more
        for ring in range(4):
            ring_value = 4 - ring  # Inner rings are worth more
            for spoke in range(8):
                player = self.board[ring][spoke]
                if player in [1, 2]:
                    scores[player] += ring_value
        
        return scores
    
    def set_test_board(self):
        """Set up a test board for the stalemate condition shown in the image"""
        # Clear the board first
        self.board = np.zeros((4, 8), dtype=int)
        
        # Add the pieces as shown in the image
        # Player 1 (red) pieces in the inner rings
        self.board[1][0] = 1  # Left
        self.board[1][4] = 1  # Right
        self.board[1][6] = 1  # Bottom
        
        # Player 2 (blue) pieces in the inner rings
        self.board[1][1] = 2  # Top-left
        self.board[1][2] = 2  # Top
        self.board[1][3] = 2  # Top-right
        self.board[1][5] = 2  # Bottom-right
        
        # Update piece counts
        self.player1_pieces = 3
        self.player2_pieces = 4
        
        # Reset inner circle piece counts
        self.player1_inner_pieces = 0
        self.player2_inner_pieces = 0
        
        # Set current player
        self.current_player = 1


class OrbitalCaptureWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.game = OrbitalCaptureGame()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Orbital Capture")
        self.setMinimumSize(600, 650)
        
        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Create status layout
        status_layout = QHBoxLayout()
        
        # Player 1 info
        self.player1_label = QLabel("Player 1 (Red): 8 pieces")
        self.player1_label.setStyleSheet("color: #FF3232; font-weight: bold;")
        status_layout.addWidget(self.player1_label)
        
        # Current turn indicator
        self.turn_label = QLabel("Player 1's Turn")
        self.turn_label.setAlignment(Qt.AlignCenter)
        self.turn_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        status_layout.addWidget(self.turn_label)
        
        # Player 2 info
        self.player2_label = QLabel("Player 2 (Blue): 8 pieces")
        self.player2_label.setStyleSheet("color: #3232FF; font-weight: bold;")
        self.player2_label.setAlignment(Qt.AlignRight)
        status_layout.addWidget(self.player2_label)
        
        main_layout.addLayout(status_layout)
        
        # Create inner circle status layout
        inner_circle_layout = QHBoxLayout()
        
        # Inner circle info for player 1
        self.player1_inner_label = QLabel(f"Inner Circle (Red): 0/{self.game.inner_circle_threshold}")
        self.player1_inner_label.setStyleSheet("color: #FF3232;")
        inner_circle_layout.addWidget(self.player1_inner_label)
        
        # Inner circle target info
        inner_circle_target = QLabel(f"First to {self.game.inner_circle_threshold} in center wins!")
        inner_circle_target.setAlignment(Qt.AlignCenter)
        inner_circle_target.setStyleSheet("font-style: italic;")
        inner_circle_layout.addWidget(inner_circle_target)
        
        # Inner circle info for player 2
        self.player2_inner_label = QLabel(f"Inner Circle (Blue): 0/{self.game.inner_circle_threshold}")
        self.player2_inner_label.setStyleSheet("color: #3232FF;")
        self.player2_inner_label.setAlignment(Qt.AlignRight)
        inner_circle_layout.addWidget(self.player2_inner_label)
        
        main_layout.addLayout(inner_circle_layout)
        
        # Create board widget
        self.board_widget = BoardWidget()
        self.board_widget.piece_clicked.connect(self.on_piece_clicked)
        self.board_widget.move_made.connect(self.on_move_made)
        main_layout.addWidget(self.board_widget)
        
        # Create buttons layout
        buttons_layout = QHBoxLayout()
        
        # Reset button
        reset_button = QPushButton("New Game")
        reset_button.clicked.connect(self.reset_game)
        buttons_layout.addWidget(reset_button)
        
        # Test Stalemate button
        test_button = QPushButton("Test Stalemate")
        test_button.clicked.connect(self.setup_test_board)
        buttons_layout.addWidget(test_button)
        
        # Rules button
        rules_button = QPushButton("Rules")
        rules_button.clicked.connect(self.show_rules)
        buttons_layout.addWidget(rules_button)
        
        main_layout.addLayout(buttons_layout)
        
        # Set central widget
        self.setCentralWidget(central_widget)
        
        # Update the display
        self.update_status_display()
    
    def on_piece_clicked(self, ring, spoke):
        # Only allow selecting current player's pieces
        if self.game.board[ring, spoke] == self.game.current_player:
            valid_moves = self.game.get_valid_moves(ring, spoke)
            self.board_widget.set_selected_piece(ring, spoke, valid_moves)
        else:
            self.board_widget.clear_selection()
    
    def on_move_made(self, from_ring, from_spoke, to_ring, to_spoke):
        # Make the move in the game logic
        result = self.game.move(from_ring, from_spoke, to_ring, to_spoke)
        
        # Update the board display
        self.board_widget.update_board(self.game.board)
        
        # Show capture animation/message if any pieces were captured
        if result["captured"]:
            captured_text = f"Player {3 - self.game.current_player} captured {len(result['captured'])} piece(s)!"
            self.statusBar().showMessage(captured_text, 3000)
        
        # Check for game over
        if result["game_over"]:
            self.game_over(result["winner"], result["reason"])
        
        # Update the status display
        self.update_status_display()
    
    def update_status_display(self):
        # Update player piece counts
        self.player1_label.setText(f"Player 1 (Red): {self.game.player1_pieces} pieces")
        self.player2_label.setText(f"Player 2 (Blue): {self.game.player2_pieces} pieces")
        
        # Update inner circle counts
        self.player1_inner_label.setText(f"Inner Circle (Red): {self.game.player1_inner_pieces}/{self.game.inner_circle_threshold}")
        self.player2_inner_label.setText(f"Inner Circle (Blue): {self.game.player2_inner_pieces}/{self.game.inner_circle_threshold}")
        
        # Update turn indicator
        self.turn_label.setText(f"Player {self.game.current_player}'s Turn")
        
        # Update turn indicator color
        if self.game.current_player == 1:
            self.turn_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #FF3232;")
        else:
            self.turn_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #3232FF;")
    
    def game_over(self, winner, reason):
        scores = self.game.calculate_score()
        
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Game Over")
        msg_box.setText(f"Player {winner} wins!")
        msg_box.setInformativeText(f"Reason: {reason}\n\nFinal scores:\nPlayer 1: {scores[1]}\nPlayer 2: {scores[2]}\n\nInner circle pieces:\nPlayer 1: {self.game.player1_inner_pieces}\nPlayer 2: {self.game.player2_inner_pieces}")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
    
    def reset_game(self):
        self.game = OrbitalCaptureGame()
        self.board_widget.reset_board()
        self.update_status_display()
        self.statusBar().showMessage("New game started", 3000)
    
    def setup_test_board(self):
        """Set up the test board for the stalemate condition"""
        self.game.set_test_board()
        self.board_widget.update_board(self.game.board)
        self.update_status_display()
        self.statusBar().showMessage("Test board set up with stalemate condition", 3000)
        
        # Check if the game is over in this position
        game_over, winner, reason = self.game.check_game_over()
        if game_over:
            self.game_over(winner, reason)
    
    def show_rules(self):
        rules_text = """
        <h3>Orbital Capture Rules</h3>
        
        <h4>Setup</h4>
        <ul>
            <li>The board consists of 4 concentric rings (orbits) and 8 radial lines (spokes)</li>
            <li>Each player begins with 8 pieces on the outermost ring</li>
        </ul>
        
        <h4>Movement Rules</h4>
        <ul>
            <li>Players take turns moving one piece per turn</li>
            <li>A piece can move along its current ring to an adjacent empty intersection</li>
            <li>A piece can move inward one ring along its current spoke if that intersection is empty</li>
            <li>A piece cannot move outward to a higher-numbered ring</li>
        </ul>
        
        <h4>Capture Rules</h4>
        <ul>
            <li>A piece is captured when it becomes "surrounded" by opponent pieces</li>
            <li>A piece is considered surrounded when opponent pieces occupy both adjacent positions on its ring AND the next inner ring position on its spoke</li>
            <li>When a piece is captured, it's removed from the board</li>
        </ul>
        
        <h4>Inner Circle Victory</h4>
        <ul>
            <li>The first player to place {0} pieces in the innermost circle wins immediately</li>
        </ul>
        
        <h4>End Game</h4>
        <ul>
            <li>If no player achieves an inner circle victory, the game ends when one player has no legal moves or when a player has fewer than 3 pieces remaining</li>
            <li>The player with more pieces on the board wins</li>
            <li>If both players have the same number of pieces, the player with more pieces on inner rings wins</li>
            <li>If neither player can make a legal move (stalemate), the player with more pieces wins</li>
        </ul>
        """.format(self.game.inner_circle_threshold)
        
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Orbital Capture Rules")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(rules_text)
        msg_box.exec_()


def main():
    app = QApplication(sys.argv)
    window = OrbitalCaptureWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()