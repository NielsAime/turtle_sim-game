#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from functools import partial
from turtlesim.msg import Pose
from geometry_msgs.msg import Twist
from my_robot_interfaces.msg import TurtleArray, GameState
from my_robot_interfaces.srv import CatchTurtle

from catch_me_if_you_can.strategies.simple_strategy import SimpleStrategy
from catch_me_if_you_can.strategies.manual_strategy import ManualStrategy

class TurtleControllerNode(Node): 
    def __init__(self):
        super().__init__("turtle_controller")
        
        # Strategy Management
        self.strategies = {
            "basic": SimpleStrategy(),
            "manual": ManualStrategy(),
        }
        self.current_strategy = self.strategies["basic"]
        self.active_mode = "basic"

        # Data Attributes
        self.pose = None
        self.alive_turtles = []
        self.current_energy = 100.0
        self.latest_teleop_cmd = Twist()

        # memory 
        self.catch_in_progress_name = None
        
        # Communication Setup
        self.cb_group = ReentrantCallbackGroup()

        # Subscribers
        self.create_subscription(Pose, "/turtle1/pose", self.callback_pose, 10)
        self.create_subscription(TurtleArray, "alive_turtles", self.callback_alive_turtles, 10)
        self.create_subscription(GameState, "game_state", self.callback_game_state, 10)
        
        # Subscriber for manual control (keyboard)
        self.create_subscription(Twist, "/cmd_vel_teleop", self.callback_teleop, 10)

        # Publishers & Clients
        self.cmd_vel_publisher_ = self.create_publisher(Twist, "/turtle1/cmd_vel", 10)
        self.catch_client_ = self.create_client(CatchTurtle, "catch_turtle", callback_group=self.cb_group)

        # Control Loop
        self.create_timer(0.01, self.control_loop)
        
        self.get_logger().info("Turtle Controller V2 ready")

    def callback_pose(self, msg):
        self.pose = msg

    def callback_alive_turtles(self, msg):
        self.alive_turtles = msg.turtles

    def callback_teleop(self, msg):
        # We store the latest command from the keyboard
        self.latest_teleop_cmd = msg

    def callback_game_state(self, msg):
        if msg.active_mode in self.strategies:
            if self.active_mode != msg.active_mode:
                self.get_logger().info(f"Switching strategy to: {msg.active_mode}")
                self.current_strategy = self.strategies[msg.active_mode]
                self.active_mode = msg.active_mode
        
        if msg.state == GameState.IDLE or msg.state == GameState.PAUSED:
            self.active_mode = "STOP"

    def control_loop(self):
        if self.pose is None or self.active_mode == "STOP":
            return

        # Pass the full context including teleop command to the strategy
        cmd, catch_target = self.current_strategy.update(
            self.pose, 
            self.alive_turtles, 
            self.current_energy,
            self.latest_teleop_cmd
        )

        if catch_target:
            
            # On vérifie si on n'est pas deja en train d'essayer d'attraper celle-ci
            if catch_target != self.catch_in_progress_name:
                self.get_logger().info(f"Envoi demande capture pour: {catch_target}")
                self.call_catch_service(catch_target)
                self.catch_in_progress_name = catch_target # On verrouille
            
            # On arrête le moteur dans tous les cas tant qu'on cible quelqu'un
            cmd = Twist()
           
            
        else:
            
            self.catch_in_progress_name = None

        self.cmd_vel_publisher_.publish(cmd)

    def call_catch_service(self, turtle_name):
        req = CatchTurtle.Request()
        req.name = turtle_name
        future = self.catch_client_.call_async(req)
        future.add_done_callback(partial(self.callback_catch_response, name=turtle_name))

    def callback_catch_response(self, future, name):
        try:
            response = future.result()
            if not response.success:
                self.get_logger().warn(f"Échec capture {name}. Suppression locale.")
                self.alive_turtles = [t for t in self.alive_turtles if t.name != name]
            
            
            if self.catch_in_progress_name == name:
                self.catch_in_progress_name = None
           

        except Exception as e:
            self.get_logger().error(f"Service call failed: {e}")
            self.catch_in_progress_name = None 

def main(args=None):
    rclpy.init(args=args)
    node = TurtleControllerNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    executor.spin()
    rclpy.shutdown()

if __name__ == "__main__":
    main()