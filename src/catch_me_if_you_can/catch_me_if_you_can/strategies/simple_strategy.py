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
        self.target_turtle = None # we put to 0 to force the calcul (had problem otherwise)
        min_dist = float('inf')

        # We scan for the closest turtle and set it as target
        if alive_turtles:
            for t in alive_turtles:
                dx = t.x - my_pose.x
                dy = t.y - my_pose.y
                dist = math.sqrt(dx**2 + dy**2)
                
                # We change target if we found a closer one
                if dist < min_dist:
                    min_dist = dist
                    self.target_turtle = t

        # Controls:
        if self.target_turtle:
            
            dist_x = self.target_turtle.x - my_pose.x
            dist_y = self.target_turtle.y - my_pose.y
            distance = math.sqrt(dist_x**2 + dist_y**2)

          
            if distance < self.catch_distance:
                return Twist(), self.target_turtle.name
            
            
            goal_theta = math.atan2(dist_y, dist_x)
            diff_angle = goal_theta - my_pose.theta

            
            while diff_angle > math.pi: diff_angle -= 2*math.pi
            while diff_angle < -math.pi: diff_angle += 2*math.pi

            cmd.linear.x = self.Kp_linear * distance
            cmd.angular.z = self.Kp_angular * diff_angle
        
        return cmd, None