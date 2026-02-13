import math
import random
import numpy as np
from geometry_msgs.msg import Twist
from .base_strategy import TurtleStrategy

class SmartStrategy(TurtleStrategy):
    def __init__(self):
        super().__init__()
        
        # --- Reinforcement Learning Parameters ---
        # Actions: Available speeds (m/s)
        self.actions = [0.5, 1.5, 3.0] 
        
        # Q-Table: Stores the value of (State, Action) pairs
        # Rows: Distance States (0: Close, 1: Medium, 2: Far)
        # Cols: Actions (Speeds)
        # We initialize with zeros.
        self.q_table = np.zeros((3, len(self.actions)))
        
        # Hyperparameters
        self.alpha = 0.1      # Learning Rate: How much we accept new information
        self.gamma = 0.9      # Discount Factor: Importance of future rewards
        self.epsilon = 0.2    # Exploration Rate: Probability of trying a random speed
        
        # --- Control & Memory ---
        self.target_turtle = None
        self.last_energy = None
        self.last_state_idx = 0
        self.last_action_idx = 0
        
        # PID Constants for precise steering (Angle)
        self.Kp_angular = 6.0
        self.catch_distance = 0.5
        
        # We limit the RL decision frequency to avoid chaos (decide every 0.2s)
        self.decision_timer = 0
        self.decision_interval = 0.2 # seconds

    def get_state_index(self, distance):
        """
        Discretizes the continuous distance into 3 categories (States).
        """
        if distance < 1.5:
            return 0 # State: Close
        elif distance < 4.0:
            return 1 # State: Medium
        else:
            return 2 # State: Far

    def choose_action(self, state_idx):
        """
        Epsilon-Greedy Strategy:
        Sometimes we explore (random action), mostly we exploit (best known action).
        """
        if random.uniform(0, 1) < self.epsilon:
            # Exploration: Choose a random speed
            return random.randint(0, len(self.actions) - 1)
        else:
            # Exploitation: Choose the speed with the highest Q-value for this state
            return np.argmax(self.q_table[state_idx])

    def learn(self, state, action, reward, next_state):
        """
        Q-Learning Update Rule (The Brain).
        Q(s,a) = Q(s,a) + alpha * (Reward + gamma * max(Q(s',:)) - Q(s,a))
        """
        predict = self.q_table[state, action]
        target = reward + self.gamma * np.max(self.q_table[next_state])
        self.q_table[state, action] += self.alpha * (target - predict)

    def update(self, my_pose, alive_turtles, current_energy, teleop_cmd):
        cmd = Twist()
        dt = 0.01 # Frequency of the controller (100Hz)
        
        # 1. Initialize memory on first run
        if self.last_energy is None:
            self.last_energy = current_energy

        # 2. Find the closest target (Standard logic)
        self.target_turtle = None
        min_dist = float('inf')
        
        if alive_turtles:
            for t in alive_turtles:
                dx = t.x - my_pose.x
                dy = t.y - my_pose.y
                dist = math.sqrt(dx**2 + dy**2)
                if dist < min_dist:
                    min_dist = dist
                    self.target_turtle = t

        # If no target, stop and do nothing
        if not self.target_turtle:
            self.last_energy = current_energy
            return cmd, None

        # 3. Calculate Physics to Target
        dist_x = self.target_turtle.x - my_pose.x
        dist_y = self.target_turtle.y - my_pose.y
        distance = math.sqrt(dist_x**2 + dist_y**2)

        # Check for catch immediately
        if distance < self.catch_distance:
            # We assume catch is successful, reset memory for next episode
            self.last_energy = current_energy 
            return Twist(), self.target_turtle.name

        # 4. REINFORCEMENT LEARNING LOOP (Every 0.2s)
        self.decision_timer += dt
        
        if self.decision_timer >= self.decision_interval:
            self.decision_timer = 0
            
            # A. Observe current State (Distance)
            current_state_idx = self.get_state_index(distance)
            
            # B. Calculate Reward
            # Reward = Change in Energy. 
            # If we moved: Energy dropped (Negative Reward).
            # If we caught: Energy spiked (Positive Reward).
            reward = current_energy - self.last_energy
            
            # C. LEARN: Update the Q-Table based on what happened
            self.learn(self.last_state_idx, self.last_action_idx, reward, current_state_idx)
            
            # D. DECIDE: Choose the new speed for the next interval
            self.last_action_idx = self.choose_action(current_state_idx)
            
            # E. Update Memory
            self.last_state_idx = current_state_idx
            self.last_energy = current_energy

        # 5. Execute Movement
        # Angular: PID (Always precise)
        goal_theta = math.atan2(dist_y, dist_x)
        diff_angle = goal_theta - my_pose.theta
        while diff_angle > math.pi: diff_angle -= 2*math.pi
        while diff_angle < -math.pi: diff_angle += 2*math.pi
        cmd.angular.z = self.Kp_angular * diff_angle
        
        # Linear: The speed chosen by RL
        chosen_speed = self.actions[self.last_action_idx]
        
        # Safety: If angle is too big, slow down to turn first
        if abs(diff_angle) > 0.5:
            cmd.linear.x = 0.0
        else:
            cmd.linear.x = chosen_speed

        return cmd, None