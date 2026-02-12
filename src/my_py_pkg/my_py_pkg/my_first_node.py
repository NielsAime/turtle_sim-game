#!/usr/bin/env python3
import rclpy
from rclpy.node import Node

class MyNode(Node):
    def __init__(self):
        # On initialise le noeud avec le nom "py_test"
        super().__init__("py_test")
        # On affiche un log dans la console
        self.get_logger().info("Hello ROS2")

def main(args=None):
    # 1. Initialiser la communication ROS 2
    rclpy.init(args=args)
    
    # 2. Créer le noeud
    node = MyNode()
    
    # 3. Laisser le noeud tourner (boucle infinie)
    # Ici, comme il n'y a pas de timer, il va juste afficher le message et attendre
    rclpy.spin(node)
    
    # 4. Arrêter proprement
    rclpy.shutdown()

if __name__ == "__main__":
    main()