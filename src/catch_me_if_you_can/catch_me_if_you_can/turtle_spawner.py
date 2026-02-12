
from urllib import response
import rclpy
# on écrit ça juste pour éviter dee fqire un .node à chaque fois. 
from rclpy.node import Node
import random
import math


from turtlesim.srv import Spawn
from functools import partial

# On importe les outils 
from turtlesim.srv import Kill
from my_robot_interfaces.srv import CatchTurtle

# On importe les strucutres de données pour les messages pour turtle et turtle array, qui sont définies dans le package d'interfaces.
from my_robot_interfaces.msg import Turtle       
from my_robot_interfaces.msg import TurtleArray

class TurtleSpawnerNode(Node): 
    # Init en ros est le constructeur de la classe, enfin du noeud
    # Il est donc appelé une fois dans le main où 
    # on y met ses attributs, on initialise le trigger, pour le service
    # on y crée tout le cablage du noeud, sa structure de mémoire interne et son cablage avec l'extérieur.
    # C'est à dire suscriber, publisher, serveur, client, ... 
    # donc ici le timer  qui appel la fonction générant la requete de spawn.
    def __init__(self):
        super().__init__("turtle_spawner") 
        self.get_logger().info("Turtle Spawner démarré !")
        # mémoire : 
        # On crée une liste vide pour stocker nos futures victimes
        self.alive_turtles_ = []
        #service client pour spaw
        # 
        # publisher :

        self.alive_turtles_publisher_ = self.create_publisher(
            TurtleArray, "alive_turtles", 10)
        #10 = taille de la queue, c'est à dire le nombre de messages que le publisher peut stocker avant de les envoyer.

        # Le Client pour effacer la tortue de l'écran (service de Turtlesim)
        self.kill_client_ = self.create_client(Kill, "/kill")
        # Le Serveur (Service Custom) que le Contrôleur va appeler
        self.catch_turtle_server_ = self.create_service(
            CatchTurtle, "catch_turtle", self.callback_catch_turtle)
        self.spawn_client_ = self.create_client(Spawn, "/spawn")
        self.index = 0

        while not self.spawn_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("J'attends que Turtlesim démarre...")


        self.spawn_timer_ = self.create_timer(2.0, self.spawn_turtle_logic)

    def spawn_turtle_logic(self):

        x = random.uniform(0.0, 11.0)
        y = random.uniform(0.0, 11.0)
        theta = random.uniform(0.0, 2 * math.pi)

        names =["Victor", "Ethan", "Victoire", "Alexandre", "Remi", "Robin", "Alexis", "Lucas", "Cyprien", 
                "Hugo", "Niels", "Chelsea", "Tony", "Malcom", "Raphael", "Lylou", "Oscar",
                 "Nicolas", "Romael", "Thelma", "Abdullah", "Samuel", "Hugo", "Benjamin", "Youssouf", "Oussama"]
        


        request = Spawn.Request()
        request.x = x
        request.y = y
        request.theta = theta
       
       # on utilise le modulo taille de la liste pour ne pas dépasser le nombre de noms dispo
        request.name = names[self.index % len(names)]
        self.index += 1

        #ON ajoute pas tout de suite la tortue à la mémoire, on attend la réponse du serveur pour être sûr qu'elle a été créée avant de l'ajouter à la liste.
        future = self.spawn_client_.call_async(request)
        

        future.add_done_callback(partial(self.callback_spawn_response, x=x, y=y, theta=theta))
        # le partial permet d'attacher des arguments qui ne sont pas encore vraiment disponible au moment de la création. c'est un avantag de python. ils seront disponibles au momentde l'appel. 
    def callback_spawn_response(self, future, x, y, theta):
        # ON utilise un futur pour attendre un retour du serveur sans bloquer le client.
        # Il faut donc absolument mettre le futur en paramètre pour que le systeme attende la reponse serveur.
        
           
        try:

            # On vérifie la réponse du serveur
            response = future.result()
            
            # On récupère le nom depuis la réponse officielle du serveur ( on le fait pas avant pour quand la liste est finie, puisque turtlesim ajoute un nombre).
            name = response.name
            #  On crée un objet Turtle 
            new_turtle = Turtle()
            new_turtle.name = name
            new_turtle.x = x
            new_turtle.y = y
            new_turtle.theta = theta 
            
            # On l'ajoute à la mémoire interne
            self.alive_turtles_.append(new_turtle)
            
            # 3. On publie la liste mise à jour
            self.publish_alive_turtles()

            self.get_logger().info(f"Tortue {name} créée en ({x:.2f}, {y:.2f})")
        except Exception as e:
            self.get_logger().error(f"L'appel au service a échoué : {e}")
    def publish_alive_turtles(self):
        # On prépare le message "Valise" qui contient la liste
        # fonction appelée dans le callback à chaque fois qu'on ajoute une tortue
        # POur publier la liste mise à jour sur le topic. 
        msg = TurtleArray()
        msg.turtles = self.alive_turtles_
        self.alive_turtles_publisher_.publish(msg)


    #fonction de callback du service de capture, qui est appelée à chaque fois que le contrôleur appelle le service pour attraper une tortue.
    def callback_catch_turtle(self, request, response):
    # request.name contient le nom de la tortue attrapée (ex: "turtle2")
    
    # 1. On cherche la tortue dans notre liste mémoire
        for turtle in self.alive_turtles_:
            if turtle.name == request.name:
            # 2. On la supprime de la liste Python
                self.alive_turtles_.remove(turtle)
            
            # 3. On publie immédiatement la nouvelle liste (mise à jour)
                self.publish_alive_turtles()
            
            # 4. On demande à Turtlesim de l'effacer de l'écran
                kill_request = Kill.Request()
                kill_request.name = request.name
                self.kill_client_.call_async(kill_request)
            
                self.get_logger().info(f"Miam ! {request.name} a été mangée.")
                response.success = True
                return response
            
    # Si on ne l'a pas trouvée (erreur ou déjà mangée)
        response.success = False
        return response

def main(args=None):
    rclpy.init(args=args)
    node = TurtleSpawnerNode() 
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == "__main__":
    main()