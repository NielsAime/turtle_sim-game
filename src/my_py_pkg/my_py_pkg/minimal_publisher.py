import rclpy	
from rclpy.node import Node

from example_interfaces.msg import String

class MinimalPublisherNode(Node):																
    def __init__(self):
        super().__init__("minimal_publisher")
        self.publisher_ = self.create_publisher(String,"topic",10) 
        self.timer_ = self.create_timer(0.5,self.timer_callback)
        self.i = 0	
        self.get_logger().info("Minimal publisher node has been started")													
    def timer_callback(self):
        msg = String()
        msg.data = "Hello World: %d" % self.i
        self.publisher_.publish(msg) 							
        self.i += 1

def main(args=None):
    rclpy.init(args=args)
    node = MinimalPublisherNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == "__main__":
    main()