import rclpy
from rclpy.node import Node

from example_interfaces.msg import String

class MinimalSubscriberNode(Node):

    def __init__(self):
        super().__init__("minimal_subscriber")
        self.subscription_ = self.create_subscription(String,"topic",self.subscriber_callback,10)
        self.get_logger().info("Minimal subscriber node has been started")

    def subscriber_callback(self,msg):
        self.get_logger().info("I heard: %s" % msg.data)

def main(args=None):
    rclpy.init(args=args)
    node = MinimalSubscriberNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == "__main__":
    main()