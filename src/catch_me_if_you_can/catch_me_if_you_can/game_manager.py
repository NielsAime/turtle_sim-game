#
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

import time
import math

# Custom Interfaces
from my_robot_interfaces.msg import GameState
from my_robot_interfaces.action import GameSession
from my_robot_interfaces.srv import TogglePause
from turtlesim.msg import Pose
from std_msgs.msg import Empty # To signal score updates to the GUI

class GameManagerNode(Node):
    def __init__(self):
        super().__init__("game_manager")
        
        # Declare Parameters (loaded from YAML later)
        self.declare_parameter("initial_energy", 100.0)
        self.declare_parameter("energy_drain_idle", 0.5)
        self.declare_parameter("energy_drain_move", 10.0)
        # Dans le __init__ de GameManagerNode
        self.declare_parameter("catch_score_reward", 10)
        self.declare_parameter("catch_energy_reward", 10.0)
        # Internal Game Variables
        self.current_energy = 0.0
        self.current_score = 0
        self.game_state = GameState.IDLE
        self.is_paused = False
        
        # Physics tracking (to calculate speed for energy drain)
        self.previous_pose = None
        self.current_pose = None

        # Communication Setup
        self.current_mode = "none" # Ajout
        # Publisher: Broadcast the state to everyone (Controller, Spawner)
        self.game_state_publisher_ = self.create_publisher(
            GameState, "game_state", 10)
        
        # Subscriber: Listen to turtle position to calculate energy consumption
        self.pose_subscriber_ = self.create_subscription(
            Pose, "/turtle1/pose", self.callback_pose, 10)
            
        self.create_subscription(Empty, "score_event", self.callback_score_event, 10)
        # Service: Allow UI to pause/resume the game
        # We use a ReentrantCallbackGroup to allow this service to be called 
        # even while the Action Server loop is running.
        self.service_cb_group = ReentrantCallbackGroup()
        self.pause_service_ = self.create_service(
            TogglePause, 
            "toggle_pause", 
            self.callback_toggle_pause, 
            callback_group=self.service_cb_group)

        # Action Server: The main game loop engine
        self.game_action_server_ = ActionServer(
            self,
            GameSession,
            "game_session",
            execute_callback=self.execute_game_callback,
            callback_group=self.service_cb_group,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback
        )

        self.get_logger().info("Game Manager is ready! Waiting for action goal...")
        self.publish_game_state(GameState.IDLE, "none")

    #  CALLBACKS & LOGIC
    def callback_score_event(self, msg):
        if self.game_state == GameState.RUNNING:
            # 1. Récupération des valeurs depuis les paramètres
            score_reward = self.get_parameter("catch_score_reward").value
            energy_reward = self.get_parameter("catch_energy_reward").value
            max_energy = self.get_parameter("initial_energy").value
            
            # 2. Mise à jour du score
            self.current_score += score_reward
            
            # 3. Mise à jour de l'énergie avec plafonnement (Clamping)
            # On ne peut pas dépasser l'énergie initiale (100%)
            self.current_energy = min(self.current_energy + energy_reward, max_energy)
            
            self.get_logger().info(f"Miam ! Score +{score_reward}, Énergie +{energy_reward}")


    def callback_pose(self, msg):
        # Update pose for physics calculations
        self.current_pose = msg
        if self.previous_pose is None:
            self.previous_pose = msg

    def callback_toggle_pause(self, request, response):
        # Simply flip the boolean state
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            self.get_logger().info("Game PAUSED via Service.")
            self.publish_game_state(GameState.PAUSED, self.current_mode)
        else:
            self.get_logger().info("Game RESUMED.")
            self.publish_game_state(GameState.RUNNING, self.current_mode)
            
        response.is_paused = self.is_paused
        return response

    def goal_callback(self, goal_request):
        # Accept the game request for the name
        self.get_logger().info(f"Game request received for player: {goal_request.player_name}")
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        # Allow the client to stop the game prematurely
        self.get_logger().info("Game aborted by client.")
        return CancelResponse.ACCEPT

    def execute_game_callback(self, goal_handle):
        self.get_logger().info(" STARTING NEW GAME SESSION ")
        
        #  Initialize Game Session
        goal = goal_handle.request
        self.current_mode = goal.mode
        self.current_energy = self.get_parameter("initial_energy").value
        drain_idle = self.get_parameter("energy_drain_idle").value
        drain_move = self.get_parameter("energy_drain_move").value
        
        self.current_score = 0
        self.is_paused = False
        remaining_time = float(goal.duration_sec)
        
        # Publish start state
        self.publish_game_state(GameState.RUNNING, goal.mode)
        
        feedback_msg = GameSession.Feedback()
        result_msg = GameSession.Result()
        
        # Loop frequency ( 10 Hz)
        loop_rate = self.create_rate(10.0) 
        dt = 0.1 # Delta time for physics (speed calcutlation (1/10hz))

        # Main Game Loop
        while rclpy.ok() and remaining_time > 0 and self.current_energy > 0:
            
            # Check if client requested cancellation
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                self.publish_game_state(GameState.IDLE, "none")
                result_msg.success = False
                result_msg.final_score = self.current_score
                return result_msg

            # Handle PAUSE Logic
            if self.is_paused:
                # Don't drain energy or time, just wait
                # We still publish feedback to keep the UI updated on status
                feedback_msg.remaining_time_sec = remaining_time
                feedback_msg.current_energy = self.current_energy
                feedback_msg.current_score = self.current_score
                goal_handle.publish_feedback(feedback_msg)
                loop_rate.sleep()
                continue

            #  PHYSICS & GAMEPLAY LOGIC 
            
            # Calculate speed (v) based on distance traveled since last frame
            distance = 0.0
            if self.current_pose and self.previous_pose:
                dx = self.current_pose.x - self.previous_pose.x
                dy = self.current_pose.y - self.previous_pose.y
                distance = math.sqrt(dx**2 + dy**2)
                # Update previous pose for next iteration
                self.previous_pose = self.current_pose
            
            # Speed v = distance / dt
            speed = distance / dt
            
            # Energy Formula: E = E - (idle + move_factor * v^2) * dt
            if goal.mode == "basic": # no loss of energy in basic mode
                energy_loss = 0.0
            else:
                
                energy_loss = (drain_idle + (drain_move * (speed**2))) * dt
            
            self.current_energy -= energy_loss
            
            # Update Timer
            remaining_time -= dt

            # Update Feedback
            feedback_msg.remaining_time_sec = remaining_time
            feedback_msg.current_energy = max(0.0, self.current_energy)
            feedback_msg.current_score = self.current_score # Score will be updated by spawner callbacks later
            
            goal_handle.publish_feedback(feedback_msg)
            
            # Wait for next cycle
            loop_rate.sleep()

        # 3. Game Over Logic
        self.get_logger().info(" GAME OVER ")
        
        if self.current_energy <= 0:
            self.get_logger().warn("Battery depleted!")
        else:
            self.get_logger().info("Time's up!")

        # Reset State
        self.publish_game_state(GameState.IDLE, "none")
        
        # Return Result
        goal_handle.succeed()
        result_msg.success = True
        result_msg.final_score = self.current_score
        
        return result_msg

    def publish_game_state(self, state, mode):
        self.game_state = state
        msg = GameState()
        msg.state = state
        msg.active_mode = mode
        self.game_state_publisher_.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = GameManagerNode()
    
    # We use MultiThreadedExecutor to allow the Action Server and the Service 
    # to run in parallel without blocking each other.
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()