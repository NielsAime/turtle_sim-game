#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from turtlesim.msg import Pose
from geometry_msgs.msg import Twist
import math # Indispensable pour atan2 et sqrt

# On import la structure du msg du topic alive_turtles, qui contient la liste de tortues vivantes.
from my_robot_interfaces.msg import TurtleArray

from my_robot_interfaces.srv import CatchTurtle
from functools import partial

class TurtleControllerNode(Node): 
    def __init__(self):
        super().__init__("turtle_controller") 
        
        # Déclaration du paramètre avec True par défaut
        self.declare_parameter("catch_closest_turtle_first", True)
        # Par défaut, on n'a pas de cible
        self.target_x = None
        self.target_y = None
        self.target_name = None # On doit mémoriser qui on chasse
        self.catch_turtle_client_ = self.create_client(CatchTurtle, "catch_turtle")

        # SUBSCRIBER ( équivalent à capteur position) 
        self.pose_ = None 
        self.pose_subscriber_ = self.create_subscription(
            Pose, "/turtle1/pose", self.callback_pose, 10) # 10 = taille du buffer

        # SUBSCRIBER (Liste des tortues vivantes) 
        self.alive_turtles_subscriber_ = self.create_subscription(
            TurtleArray, "alive_turtles", self.callback_alive_turtles, 10)

        # PUBLISHER (Commande Moteurs) 
        self.cmd_vel_publisher_ = self.create_publisher(
            Twist, "/turtle1/cmd_vel", 10)

        #  TIMER (Boucle de contrôle) 
        # 100 Hz (0.01s) pour une réaction fluide
        self.control_loop_timer_ = self.create_timer(0.01, self.control_loop)
        
        self.get_logger().info("Turtle Controller démarré ! Cible : x=9, y=9")

    def callback_pose(self, msg):
        self.pose_ = msg

    def callback_alive_turtles(self, msg):
        # Sécurité : Si pas de tortues ou si on ne connait pas encore notre propre position
        if len(msg.turtles) == 0 or self.pose_ is None:
            return

        # On récupère la valeur actuelle du paramètre (True ou False)
        catch_closest = self.get_parameter("catch_closest_turtle_first").value

        if catch_closest:
            #  STRATÉGIE INTELLIGENTE : LA PLUS PROCHE 
            closest_turtle = None
            min_distance = float('inf') # Infini au départ

            for turtle in msg.turtles:
                # Pythagore pour chaque proie
                dist_x = turtle.x - self.pose_.x
                dist_y = turtle.y - self.pose_.y
                distance = math.sqrt(dist_x**2 + dist_y**2)

                # Si cette tortue est plus proche que la précédente trouvée
                if distance < min_distance:
                    min_distance = distance
                    closest_turtle = turtle
            
            # On verrouille la cible la plus proche
            if closest_turtle is not None:
                self.target_x = closest_turtle.x
                self.target_y = closest_turtle.y
                self.target_name = closest_turtle.name

        else:
            #  STRATÉGIE BASIQUE : LA PREMIÈRE 
            first_turtle = msg.turtles[0]
            self.target_x = first_turtle.x
            self.target_y = first_turtle.y
            self.target_name = first_turtle.name

    def control_loop(self):
        # 0. SECURITE : Si on n'a pas de position ou pas de cible, on annule.
        if self.pose_ is None or self.target_x is None:
            return

        # 1. CALCUL DE L'ERREUR (Vecteurs)
        dist_x = self.target_x - self.pose_.x
        dist_y = self.target_y - self.pose_.y
        distance = math.sqrt(dist_x**2 + dist_y**2)
        
        goal_theta = math.atan2(dist_y, dist_x)
        diff_angle = goal_theta - self.pose_.theta
        
        # Normalisation de l'angle (Toujours prendre le chemin le plus court)
        if diff_angle > math.pi:
            diff_angle -= 2*math.pi
        elif diff_angle < -math.pi:
            diff_angle += 2*math.pi

        msg = Twist()

        #  MARGE DE DISTANCE (Tolerance pour "manger") 
        tolerance = 0.5 

        # 2. PRISE DE DECISION
        if distance > tolerance:
            # ETAT : EN CHASSE (On est trop loin)
            
            # Contrôleur P (Proportionnel)
            msg.linear.x = 1.0 * distance 
            msg.angular.z = 6.0 * diff_angle
            
        else:
            # ETAT : CIBLE ATTEINTE (Distance <= 0.5m)
            
            # On stoppe les moteurs
            msg.linear.x = 0.0
            msg.angular.z = 0.0
            
            # Si on a bien un nom de cible en mémoire (pour ne pas appeler dans le vide)
            if self.target_name is not None:
                self.get_logger().info(f"Cible atteinte ! Je mange {self.target_name}...")
                
                # 3. APPEL DU SERVICE (On demande au spawner de la tuer)
                from my_robot_interfaces.srv import CatchTurtle # Import au cas où
                request = CatchTurtle.Request()
                request.name = self.target_name
                
                # Envoi asynchrone (On n'attend pas bloqué ici)
                self.catch_turtle_client_.call_async(request)
                
                # TRES IMPORTANT : On "oublie" le nom de cette cible.
                # Pourquoi ? Pour éviter de renvoyer 100 requêtes de meurtre par seconde 
                # au serveur pendant que Turtlesim gère l'animation de disparition.
                self.target_name = None

        # 4. ENVOI AUX MOTEURS
        self.cmd_vel_publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = TurtleControllerNode() 
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == "__main__":
    main()