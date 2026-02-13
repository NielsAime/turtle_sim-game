#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from functools import partial
import random
import math

from turtlesim.srv import Spawn, Kill
from my_robot_interfaces.srv import CatchTurtle
from my_robot_interfaces.msg import Turtle, TurtleArray
from my_robot_interfaces.msg import Turtle, TurtleArray, GameState 
from std_msgs.msg import Empty # just to tell that a turtle was eaten to update the score
class TurtleSpawnerNode(Node): 
    def __init__(self):
        super().__init__("turtle_spawner") 
        self.declare_parameter("spawn_frequency", 2.0)
        self.spawn_rate = self.get_parameter("spawn_frequency").value

        # Data
        self.alive_turtles_ = []
        self.turtle_names = ["Victor", "Ethan", "Victoire", "Alexandre", "Remi", "Robin", 
                             "Alexis", "Lucas", "Cyprien", "Hugo", "Niels", "Chelsea", 
                             "Tony", "Malcom", "Raphael", "Lylou", "Oscar", "Nicolas", 
                             "Romael", "Thelma", "Abdullah", "Samuel", "Benjamin", "Youssouf", "Oussama"]
        
        self.is_game_running = False
        # Communication
        self.cb_group = ReentrantCallbackGroup() # Allows parallel processing

        self.alive_turtles_publisher_ = self.create_publisher(TurtleArray, "alive_turtles", 10)
        self.score_publisher_ = self.create_publisher(Empty, "score_event", 10)

        self.spawn_client_ = self.create_client(Spawn, "/spawn")
        self.kill_client_ = self.create_client(Kill, "/kill")
        
        self.catch_service_ = self.create_service(
            CatchTurtle, 
            "catch_turtle", 
            self.callback_catch_turtle,
            callback_group=self.cb_group)
        
        #to know whento start the game and when to stop spawning turtles
        self.create_subscription(GameState, "game_state", self.callback_game_state, 10)
        # Wait for Turtlesim
        while not self.spawn_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("Waiting for Turtlesim...")

        # Timer
        self.spawn_timer_ = self.create_timer(self.spawn_rate, self.spawn_turtle_logic)
        self.get_logger().info("Turtle Spawner V2 Ready!")

    def spawn_turtle_logic(self):

        if not self.is_game_running:
            return
        # Random Position
        
        x = random.uniform(0.5, 10.5) # Avoid edges
        y = random.uniform(0.5, 10.5)
        theta = random.uniform(0.0, 2 * math.pi)

        # Unique Name Generation
        raw_name = random.choice(self.turtle_names)
        unique_name = self.get_unique_name(raw_name)

        request = Spawn.Request()
        request.x = x
        request.y = y
        request.theta = theta
        request.name = unique_name

        future = self.spawn_client_.call_async(request)
        future.add_done_callback(
            partial(self.callback_spawn_response, x=x, y=y, theta=theta, name=unique_name)
        )
    def get_unique_name(self, base_name):
        """Cherche un nom disponible (ex: Victor, puis Victor_1, puis Victor_2...)"""
        count = 1
        candidate = base_name
        
        # On vérifie si 'candidate' est déjà présent dans la liste des tortues vivantes
        # any(...) renvoie True si on trouve une correspondance
        while any(t.name == candidate for t in self.alive_turtles_):
            candidate = f"{base_name}_{count}"
            count += 1
            
        return candidate
    
    def callback_spawn_response(self, future, x, y, theta, name):
        try:
            response = future.result()
            if response.name: # If success (sometimes turtlesim returns empty if failed)
                # Confirm the name used by turtlesim
                actual_name = response.name 
                
                new_turtle = Turtle()
                new_turtle.name = actual_name
                new_turtle.x = x
                new_turtle.y = y
                new_turtle.theta = theta
                
                self.alive_turtles_.append(new_turtle)
                self.publish_alive_turtles()
                self.get_logger().info(f"Spawned {actual_name} at ({x:.1f}, {y:.1f})")
        except Exception as e:
            self.get_logger().error(f"Spawn failed for {name}: {e}")

    def callback_catch_turtle(self, request, response):
        target = request.name
        
        # Find and remove
        turtle_to_remove = None
        for t in self.alive_turtles_:
            if t.name == target:
                turtle_to_remove = t
                break
        
        if turtle_to_remove:
            self.alive_turtles_.remove(turtle_to_remove)
            self.publish_alive_turtles()
            
            # Kill in Turtlesim
            kill_req = Kill.Request()
            kill_req.name = target
            self.kill_client_.call_async(kill_req)
            
            response.success = True

            self.score_publisher_.publish(Empty())
            self.get_logger().info(f"Caught {target}!")
        else:
            response.success = False
            self.get_logger().warn(f"Failed to catch {target}: Not in list.")
            self.publish_alive_turtles()
        return response

    def callback_game_state(self, msg):
        if msg.state == GameState.RUNNING:
            self.is_game_running = True
        else:
            self.is_game_running = False

    def publish_alive_turtles(self):
        msg = TurtleArray()
        msg.turtles = self.alive_turtles_
        self.alive_turtles_publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = TurtleSpawnerNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == "__main__":
    main()