import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    ld = LaunchDescription()

    # Path to config file
    config_file = os.path.join(
        get_package_share_directory('catch_me_if_you_can'),
        'config',
        'game_config.yaml'
    )

    # Turtlesim node
    turtlesim_node = Node(
        package="turtlesim",
        executable="turtlesim_node",
        name="turtlesim"
    )

    # Spawner node
    spawner_node = Node(
        package="catch_me_if_you_can",
        executable="turtle_spawner",
        parameters=[{"spawn_frequency": 1.5}]
    )

    # Game manager node
    manager_node = Node(
        package="catch_me_if_you_can",
        executable="game_manager",
        parameters=[config_file]
    )

    #  Controller Node 
    controller_node = Node(
        package="catch_me_if_you_can",
        executable="turtle_controller",
        # Parameters can be added here if needed later
    )

    # Game interface
    gui_node = Node(
        package="catch_me_if_you_can",
        executable="game_gui",
        name="game_gui"
    )

    ld.add_action(turtlesim_node)
    ld.add_action(spawner_node)
    ld.add_action(manager_node)
    ld.add_action(controller_node)
    ld.add_action(gui_node)

    return ld