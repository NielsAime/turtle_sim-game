import math
from geometry_msgs.msg import Twist
from .base_strategy import TurtleStrategy

class ManualStrategy(TurtleStrategy):
    def __init__(self):
        super().__init__()
        self.catch_distance = 0.5
        self.catch_distance = 0.5
        # Speed multiplier to adjust default keyboard speed
        self.linear_scale = 2.0  # 2x faster forward
        self.angular_scale = 1.5 # 1.5x faster turning

    def update(self, my_pose, alive_turtles, current_energy, teleop_cmd):
        # Safety check for energy
        # If no energy, we force a stop
        if current_energy <= 0:
            return Twist(), None

        # Check if we are close enough to any turtle to catch it
        # We iterate through all turtles because the human is driving blindly
        target_name = None
        if alive_turtles:
            for t in alive_turtles:
                dx = t.x - my_pose.x
                dy = t.y - my_pose.y
                distance = math.sqrt(dx**2 + dy**2)
                
                if distance < self.catch_distance:
                    target_name = t.name
                    break
        # Apply scaling to the command received from keyboard
        final_cmd = Twist()
        final_cmd.linear.x = teleop_cmd.linear.x * self.linear_scale
        final_cmd.angular.z = teleop_cmd.angular.z * self.angular_scale
        # We pass the keyboard command directly to the motors, no name catched, than return none
        return teleop_cmd, target_name