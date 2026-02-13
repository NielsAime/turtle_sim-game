import math
from geometry_msgs.msg import Twist
from .base_strategy import TurtleStrategy

class SimpleStrategy(TurtleStrategy):
    def __init__(self):
        super().__init__()
        self.target_turtle = None
        self.Kp_linear = 1.0
        self.Kp_angular = 6.0
        self.catch_distance = 0.5

    def update(self, my_pose, alive_turtles, current_energy, teleop_cmd):
        cmd = Twist()
        self.target_turtle = None # On remet à zéro pour forcer le recalcul
        min_dist = float('inf')

        # 1. On scanne TOUTES les tortues à chaque fois (Mode Opportuniste V1)
        if alive_turtles:
            for t in alive_turtles:
                dx = t.x - my_pose.x
                dy = t.y - my_pose.y
                dist = math.sqrt(dx**2 + dy**2)
                
                # Si on trouve plus proche, on change de cible immédiatement
                if dist < min_dist:
                    min_dist = dist
                    self.target_turtle = t

        # 2. Si on a trouvé une cible, on fonce
        if self.target_turtle:
            # Calculs vecteurs
            dist_x = self.target_turtle.x - my_pose.x
            dist_y = self.target_turtle.y - my_pose.y
            distance = math.sqrt(dist_x**2 + dist_y**2)

            # Capture
            if distance < self.catch_distance:
                return Twist(), self.target_turtle.name
            
            # Mouvement PID
            goal_theta = math.atan2(dist_y, dist_x)
            diff_angle = goal_theta - my_pose.theta

            # Normalisation angle
            while diff_angle > math.pi: diff_angle -= 2*math.pi
            while diff_angle < -math.pi: diff_angle += 2*math.pi

            cmd.linear.x = self.Kp_linear * distance
            cmd.angular.z = self.Kp_angular * diff_angle
        
        return cmd, None