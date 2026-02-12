from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    ld = LaunchDescription()

    # 1. Le Simulateur
    turtlesim_node = Node(
        package="turtlesim",
        executable="turtlesim_node"
    )

    # 2. Le Spawner (Maître du jeu)
    spawner_node = Node(
        package="catch_me_if_you_can",
        executable="turtle_spawner"
    )

    # 3. Le Contrôleur (Chasseur)
    controller_node = Node(
        package="catch_me_if_you_can",
        executable="turtle_controller",
        parameters=[
            {"catch_closest_turtle_first": True} # On passe le paramètre ici !
        ]
    )

    # On ajoute tout à la liste de lancement
    ld.add_action(turtlesim_node)
    ld.add_action(spawner_node)
    ld.add_action(controller_node)

    return ld