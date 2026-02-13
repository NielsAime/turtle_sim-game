from geometry_msgs.msg import Twist

class TurtleStrategy:
    def __init__(self):
        pass

    def update(self, my_pose, alive_turtles, current_energy, teleop_cmd):
        """
        Calculates the next command based on the strategy.
        Args:
            my_pose: Current position of the hunter turtle
            alive_turtles: List of Turtle objects (enemies)
            current_energy: Float representing remaining battery
            teleop_cmd: Twist message received from keyboard (for manual mode)
        Returns:
            (Twist command, String target_name_to_catch)
        """
        return Twist(), None