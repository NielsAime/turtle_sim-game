#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from my_robot_interfaces.action import GameSession
from my_robot_interfaces.srv import TogglePause

class GameGuiNode(Node):
    def __init__(self, gui_app):
        super().__init__("game_gui")
        self.gui_app = gui_app
        
        # Action client to start/manage the game session
        self.action_client = ActionClient(self, GameSession, "game_session")
        
        # Service client to toggle pause state
        self.pause_client = self.create_client(TogglePause, "toggle_pause")

    def call_pause_toggle(self):
        # Check if service is available before calling
        if not self.pause_client.wait_for_service(timeout_sec=1.0):
            self.gui_app.update_status("Pause Service not available!")
            return

        req = TogglePause.Request()
        future = self.pause_client.call_async(req)
        future.add_done_callback(self.response_pause)

    def response_pause(self, future):
        try:
            response = future.result()
            # update the button text based on the new state
            self.gui_app.update_pause_button(response.is_paused)
        except Exception as e:
            self.get_logger().error(f"Service call failed: {e}")

    def send_goal(self, duration, mode, player_name):
        # wait for action server to be ready
        if not self.action_client.wait_for_server(timeout_sec=2.0):
            self.gui_app.update_status("Error: Game Manager not found!")
            return

        goal_msg = GameSession.Goal()
        goal_msg.duration_sec = duration
        goal_msg.mode = mode
        goal_msg.player_name = player_name

        self.gui_app.update_status("Sending goal...")
        
        # send goal with feedback callback linked to UI update
        self.send_goal_future = self.action_client.send_goal_async(
            goal_msg, 
            feedback_callback=self.feedback_callback
        )
        self.send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.gui_app.update_status("Goal rejected by server.")
            return

        self.gui_app.update_status("Game Started!")
        self.gui_app.set_running_state(True)
        
        # get the final result asynchronously
        self.result_future = goal_handle.get_result_async()
        self.result_future.add_done_callback(self.get_result_callback)

    def feedback_callback(self, feedback_msg):
        fb = feedback_msg.feedback
        # update real-time metrics in the UI
        self.gui_app.update_metrics(
            fb.remaining_time_sec,
            fb.current_energy,
            fb.current_score
        )

    def get_result_callback(self, future):
        result = future.result().result
        status_msg = f"Game Over! Final Score: {result.final_score}"
        self.gui_app.update_status(status_msg)
        self.gui_app.set_running_state(False)
        self.gui_app.show_game_over(result.final_score, result.success)

class CatchMeGui:
    def __init__(self, root):
        self.root = root
        self.root.title("Catch Me If You Can - Control Center")
        self.root.geometry("400x550")
        self.ros_node = None
        
        # --- UI LAYOUT ---
        
        # 1. Configuration Section
        config_frame = ttk.LabelFrame(root, text="Game Configuration", padding=10)
        config_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(config_frame, text="Player Name:").grid(row=0, column=0, sticky="w")
        self.name_entry = ttk.Entry(config_frame)
        self.name_entry.insert(0, "Nga")
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(config_frame, text="Mode:").grid(row=1, column=0, sticky="w")
        self.mode_var = tk.StringVar(value="basic")
        modes = ["basic", "manual", "smart"]
        self.mode_combo = ttk.Combobox(config_frame, textvariable=self.mode_var, values=modes)
        self.mode_combo.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(config_frame, text="Duration (s):").grid(row=2, column=0, sticky="w")
        self.duration_entry = ttk.Entry(config_frame)
        self.duration_entry.insert(0, "60")
        self.duration_entry.grid(row=2, column=1, padx=5, pady=5)

        # 2. Control Section
        control_frame = ttk.Frame(root, padding=10)
        control_frame.pack(fill="x", padx=10)

        self.start_btn = ttk.Button(control_frame, text="START GAME", command=self.on_start_click)
        self.start_btn.pack(side="left", expand=True, fill="x", padx=5)

        self.pause_btn = ttk.Button(control_frame, text="PAUSE", command=self.on_pause_click, state="disabled")
        self.pause_btn.pack(side="right", expand=True, fill="x", padx=5)

        # 3. Monitor Section
        monitor_frame = ttk.LabelFrame(root, text="Live Monitor", padding=10)
        monitor_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.status_label = ttk.Label(monitor_frame, text="Status: Ready", font=("Arial", 10, "bold"))
        self.status_label.pack(pady=5)

        # Timer progress
        ttk.Label(monitor_frame, text="Time Remaining:").pack(anchor="w")
        self.time_progress = ttk.Progressbar(monitor_frame, orient="horizontal", length=300, mode="determinate")
        self.time_progress.pack(pady=2, fill="x")
        self.time_label = ttk.Label(monitor_frame, text="60.0 s")
        self.time_label.pack()

        # Energy progress
        ttk.Label(monitor_frame, text="Energy:").pack(anchor="w", pady=(10, 0))
        self.energy_progress = ttk.Progressbar(monitor_frame, orient="horizontal", length=300, mode="determinate")
        self.energy_progress.pack(pady=2, fill="x")
        self.energy_label = ttk.Label(monitor_frame, text="100 %")
        self.energy_label.pack()

        # Score display
        self.score_label = ttk.Label(monitor_frame, text="Score: 0", font=("Arial", 24, "bold"))
        self.score_label.pack(pady=20)

    def set_ros_node(self, node):
        self.ros_node = node

    def on_start_click(self):
        try:
            name = self.name_entry.get()
            mode = self.mode_var.get()
            duration = int(self.duration_entry.get())
            
            # reset UI elements for the new session
            self.time_progress["maximum"] = duration
            self.time_progress["value"] = duration
            self.energy_progress["value"] = 100
            
            if self.ros_node:
                self.ros_node.send_goal(duration, mode, name)
            
        except ValueError:
            messagebox.showerror("Error", "Duration must be a number")

    def on_pause_click(self):
        if self.ros_node:
            self.ros_node.call_pause_toggle()

    def update_pause_button(self, is_paused):
        # swap text based on game pause state
        if is_paused:
            self.pause_btn.config(text="RESUME")
            self.update_status("Game Paused")
        else:
            self.pause_btn.config(text="PAUSE")
            self.update_status("Game Resumed")

    def set_running_state(self, is_running):
        # toggle widget availability based on game state
        state = "disabled" if is_running else "normal"
        self.start_btn.config(state=state)
        self.name_entry.config(state=state)
        self.mode_combo.config(state=state)
        self.duration_entry.config(state=state)
        
        # enable pause button only when game is running
        self.pause_btn.config(state="normal" if is_running else "disabled")
        if not is_running:
            self.pause_btn.config(text="PAUSE")

    def update_status(self, text):
        self.status_label.config(text=f"Status: {text}")

    def update_metrics(self, time_left, energy, score):
        # update real-time visual progress
        self.time_label.config(text=f"{time_left:.1f} s")
        self.time_progress["value"] = time_left
        
        self.energy_label.config(text=f"{energy:.1f} %")
        self.energy_progress["value"] = energy
        
        self.score_label.config(text=f"Score: {score}")

    def show_game_over(self, score, success):
        # show final message box to the user
        msg = "Mission Complete!" if success else "Mission Failed!"
        messagebox.showinfo("Game Over", f"{msg}\nFinal Score: {score}")

def main(args=None):
    rclpy.init(args=args)
    
    root = tk.Tk()
    gui = CatchMeGui(root)
    
    ros_node = GameGuiNode(gui)
    gui.set_ros_node(ros_node)
    
    # run ROS loop in a separate thread to keep Tkinter responsive
    thread = threading.Thread(target=rclpy.spin, args=(ros_node,), daemon=True)
    thread.start()
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()

if __name__ == "__main__":
    main()