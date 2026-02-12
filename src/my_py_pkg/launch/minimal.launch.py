from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    ld = LaunchDescription()
    minimal_publisher_node = Node(
    package= "my_py_pkg",
    executable= "minimal_publisher"
    )
    minimal_subscriber_node = Node(
    package= "my_py_pkg",
    executable= "minimal_subscriber"
    )
    ld.add_action(minimal_publisher_node)
    ld.add_action(minimal_subscriber_node)
    return ld