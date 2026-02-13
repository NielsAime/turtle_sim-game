# Game State Constants
int8 IDLE=0       # Waiting for a game to start
int8 RUNNING=1    # Game is active
int8 PAUSED=2     # Game is paused (optional feature)

# The current state of the game
int8 state

# The active strategy/mode (useful for the controller to switch behavior)
string active_mode