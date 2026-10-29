import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')

        self.declare_parameter('source', '0')
        self.declare_parameter('fps', 30.0)
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)

        source_param = str(self.get_parameter('source').value)
        fps = float(self.get_parameter('fps').value)
        self.width = int(self.get_parameter('width').value)
        self.height = int(self.get_parameter('height').value)

        if source_param.isdigit():
            self.video_source = int(source_param)
            self.is_file = False
        else:
            self.video_source = source_param
            self.is_file = True

        self.cap = cv2.VideoCapture(self.video_source)
        if not self.is_file:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        self.publisher_ = self.create_publisher(Image, '/camera/image_raw', 10)
        self.bridge = CvBridge()

        if fps > 0:
            timer_period = 1.0 / fps
        else:
            timer_period = 1.0 / 30.0

        self.timer = self.create_timer(timer_period, self.timer_callback)

        self.get_logger().info(f'Camera node berjalan! Source: {source_param}, FPS: {fps}')

    def timer_callback(self):
        ret, frame = self.cap.read()

        if not ret:
            if self.is_file:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if not ret:
                    return
            else:
                return

        frame = cv2.resize(frame, (self.width, self.height))
        frame = cv2.flip(frame, 1) 

        msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera_frame'
        self.publisher_.publish(msg)

    def destroy_node(self):
        self.cap.release()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
