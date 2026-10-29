import rclpy
from rclpy.node import Node
from rcl_interfaces.msg import SetParametersResult
from sensor_msgs.msg import Image
from std_msgs.msg import Int32
from std_srvs.srv import Trigger
from cv_bridge import CvBridge
import cv2
import numpy as np
import random
import math

class Ball:
    def __init__(self, frame_w, frame_h, radius, speed):
        self.radius = radius
        self.respawn(frame_w, frame_h, speed)

    def respawn(self, frame_w, frame_h, speed):
        margin = self.radius + 5
        self.x = float(random.randint(margin, max(margin + 1, frame_w - margin)))
        self.y = float(random.randint(margin, max(margin + 1, frame_h - margin)))
        angle = random.uniform(0, 2 * math.pi)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = (random.randint(80, 255), random.randint(80, 255), random.randint(80, 255))
        self.hold_timer = 0.0

    def update_speed_and_radius(self, new_speed, new_radius):
        self.radius = new_radius
        current_angle = math.atan2(self.vy, self.vx)
        self.vx = math.cos(current_angle) * new_speed
        self.vy = math.sin(current_angle) * new_speed

    def move(self, dt, frame_w, frame_h):
        self.x += self.vx * dt
        self.y += self.vy * dt

        if self.x - self.radius < 0:
            self.x = float(self.radius)
            self.vx *= -1
        elif self.x + self.radius > frame_w:
            self.x = float(frame_w - self.radius)
            self.vx *= -1

        if self.y - self.radius < 0:
            self.y = float(self.radius)
            self.vy *= -1
        elif self.y + self.radius > frame_h:
            self.y = float(frame_h - self.radius)
            self.vy *= -1


class GameNode(Node):
    def __init__(self):
        super().__init__('game_node')

        self.declare_parameter('hsv_lower', [90, 30, 60])
        self.declare_parameter('hsv_upper', [135, 255, 255])
        self.declare_parameter('num_balls', 3)
        self.declare_parameter('hold_duration', 2.0)
        self.declare_parameter('ball_radius', 45)
        self.declare_parameter('ball_speed', 120.0)
        self.declare_parameter('min_area', 250)

        self.load_parameters()

        self.add_on_set_parameters_callback(self.parameter_callback)

        self.sub_image = self.create_subscription(Image, '/camera/image_raw', self.image_callback, 10)
        self.pub_debug = self.create_publisher(Image, '/game/debug_image', 10)
        self.pub_score = self.create_publisher(Int32, '/game/score', 10)

        self.srv_reset = self.create_service(Trigger, '/game/reset', self.reset_game_callback)

        self.bridge = CvBridge()
        self.balls = []
        self.score = 0
        self.last_time = None
        self.frame_w = 640
        self.frame_h = 480
        self.current_hsv_frame = None

        self.smoothed_centroid = None
        self.alpha = 0.6

        cv2.namedWindow("Kalibrasi HSV", cv2.WINDOW_NORMAL)
        cv2.createTrackbar("H_min", "Kalibrasi HSV", int(self.hsv_lower[0]), 179, lambda x: None)
        cv2.createTrackbar("S_min", "Kalibrasi HSV", int(self.hsv_lower[1]), 255, lambda x: None)
        cv2.createTrackbar("V_min", "Kalibrasi HSV", int(self.hsv_lower[2]), 255, lambda x: None)
        cv2.createTrackbar("H_max", "Kalibrasi HSV", int(self.hsv_upper[0]), 179, lambda x: None)
        cv2.createTrackbar("S_max", "Kalibrasi HSV", int(self.hsv_upper[1]), 255, lambda x: None)
        cv2.createTrackbar("V_max", "Kalibrasi HSV", int(self.hsv_upper[2]), 255, lambda x: None)

        cv2.namedWindow("Layar Game (Klik Objek Untuk Kalibrasi Otomatis)", cv2.WINDOW_NORMAL)
        cv2.setMouseCallback("Layar Game (Klik Objek Untuk Kalibrasi Otomatis)", self.mouse_click_callback)

        self.publish_score()
        self.get_logger().info('Game node siap! Klik kiri pada objek di jendela Layar Game untuk kalibrasi warna instan.')

    def mouse_click_callback(self, event, x, y, flags, param):
        """Fitur Klik Kiri Mouse: Otomatis mengunci warna benda yang diklik!"""
        if event == cv2.EVENT_LBUTTONDOWN and self.current_hsv_frame is not None:
            pixel_hsv = self.current_hsv_frame[y, x]
            h, s, v = int(pixel_hsv[0]), int(pixel_hsv[1]), int(pixel_hsv[2])
            
            h_min = max(0, h - 18)
            h_max = min(179, h + 18)
            s_min = max(15, s - 50)
            s_max = 255
            v_min = max(40, v - 60)
            v_max = 255

            cv2.setTrackbarPos("H_min", "Kalibrasi HSV", h_min)
            cv2.setTrackbarPos("S_min", "Kalibrasi HSV", s_min)
            cv2.setTrackbarPos("V_min", "Kalibrasi HSV", v_min)
            cv2.setTrackbarPos("H_max", "Kalibrasi HSV", h_max)
            cv2.setTrackbarPos("S_max", "Kalibrasi HSV", s_max)
            cv2.setTrackbarPos("V_max", "Kalibrasi HSV", v_max)
            self.get_logger().info(f'Warna dikalibrasi otomatis via klik! HSV Lower: [{h_min}, {s_min}, {v_min}], Upper: [{h_max}, {s_max}, {v_max}]')

    def reset_game_callback(self, request, response):
        self.score = 0
        self.publish_score()
        for ball in self.balls:
            ball.respawn(self.frame_w, self.frame_h, self.ball_speed)
        response.success = True
        response.message = "Game dan skor berhasil di-reset ke 0!"
        self.get_logger().info(response.message)
        return response

    def load_parameters(self):
        self.hsv_lower = np.array(self.get_parameter('hsv_lower').value, dtype=np.uint8)
        self.hsv_upper = np.array(self.get_parameter('hsv_upper').value, dtype=np.uint8)
        self.num_balls = int(self.get_parameter('num_balls').value)
        self.hold_duration = float(self.get_parameter('hold_duration').value)
        self.ball_radius = int(self.get_parameter('ball_radius').value)
        self.ball_speed = float(self.get_parameter('ball_speed').value)
        self.min_area = int(self.get_parameter('min_area').value)

    def parameter_callback(self, params):
        for param in params:
            if param.name == 'hsv_lower':
                self.hsv_lower = np.array(param.value, dtype=np.uint8)
                cv2.setTrackbarPos("H_min", "Kalibrasi HSV", int(self.hsv_lower[0]))
                cv2.setTrackbarPos("S_min", "Kalibrasi HSV", int(self.hsv_lower[1]))
                cv2.setTrackbarPos("V_min", "Kalibrasi HSV", int(self.hsv_lower[2]))
            elif param.name == 'hsv_upper':
                self.hsv_upper = np.array(param.value, dtype=np.uint8)
                cv2.setTrackbarPos("H_max", "Kalibrasi HSV", int(self.hsv_upper[0]))
                cv2.setTrackbarPos("S_max", "Kalibrasi HSV", int(self.hsv_upper[1]))
                cv2.setTrackbarPos("V_max", "Kalibrasi HSV", int(self.hsv_upper[2]))
            elif param.name == 'num_balls':
                self.num_balls = int(param.value)
                while len(self.balls) < self.num_balls:
                    self.balls.append(Ball(self.frame_w, self.frame_h, self.ball_radius, self.ball_speed))
                while len(self.balls) > self.num_balls:
                    self.balls.pop()
            elif param.name == 'hold_duration':
                self.hold_duration = float(param.value)
            elif param.name == 'ball_radius':
                self.ball_radius = int(param.value)
                for b in self.balls:
                    b.update_speed_and_radius(self.ball_speed, self.ball_radius)
            elif param.name == 'ball_speed':
                self.ball_speed = float(param.value)
                for b in self.balls:
                    b.update_speed_and_radius(self.ball_speed, self.ball_radius)
            elif param.name == 'min_area':
                self.min_area = int(param.value)
        self.get_logger().info('Parameter berhasil diubah secara runtime!')
        return SetParametersResult(successful=True)

    def publish_score(self):
        msg = Int32()
        msg.data = self.score
        self.pub_score.publish(msg)

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        self.frame_h, self.frame_w, _ = frame.shape

        if len(self.balls) == 0:
            for _ in range(self.num_balls):
                self.balls.append(Ball(self.frame_w, self.frame_h, self.ball_radius, self.ball_speed))

        current_time = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        if current_time == 0.0:
            current_time = self.get_clock().now().nanoseconds * 1e-9

        if self.last_time is None:
            dt = 0.0
        else:
            dt = current_time - self.last_time
            if dt < 0 or dt > 0.5:
                dt = 0.033
        self.last_time = current_time

        h_min = cv2.getTrackbarPos("H_min", "Kalibrasi HSV")
        s_min = cv2.getTrackbarPos("S_min", "Kalibrasi HSV")
        v_min = cv2.getTrackbarPos("V_min", "Kalibrasi HSV")
        h_max = cv2.getTrackbarPos("H_max", "Kalibrasi HSV")
        s_max = cv2.getTrackbarPos("S_max", "Kalibrasi HSV")
        v_max = cv2.getTrackbarPos("V_max", "Kalibrasi HSV")
        self.hsv_lower = np.array([h_min, s_min, v_min], dtype=np.uint8)
        self.hsv_upper = np.array([h_max, s_max, v_max], dtype=np.uint8)

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        self.current_hsv_frame = hsv
        mask = cv2.inRange(hsv, self.hsv_lower, self.hsv_upper)

        kernel = np.ones((7, 7), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        object_centroid = None
        bbox = None

        max_allowed_area = (self.frame_w * self.frame_h) * 0.35
        valid_contours = [c for c in contours if self.min_area <= cv2.contourArea(c) <= max_allowed_area]

        if valid_contours:
            largest_contour = max(valid_contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            raw_cx = x + w // 2
            raw_cy = y + h // 2

            if self.smoothed_centroid is None:
                self.smoothed_centroid = (float(raw_cx), float(raw_cy))
            else:
                sx = self.alpha * raw_cx + (1.0 - self.alpha) * self.smoothed_centroid[0]
                sy = self.alpha * raw_cy + (1.0 - self.alpha) * self.smoothed_centroid[1]
                self.smoothed_centroid = (sx, sy)

            object_centroid = (int(self.smoothed_centroid[0]), int(self.smoothed_centroid[1]))
            bbox = (x, y, w, h)
        else:
            self.smoothed_centroid = None

        for ball in self.balls:
            ball.move(dt, self.frame_w, self.frame_h)

        closest_ball = None
        min_dist = float('inf')

        if object_centroid is not None:
            cx, cy = object_centroid
            for ball in self.balls:
                dist = math.hypot(cx - ball.x, cy - ball.y)
                if dist <= ball.radius:
                    if dist < min_dist:
                        min_dist = dist
                        closest_ball = ball

        for ball in self.balls:
            if ball == closest_ball:
                ball.hold_timer += dt
                if ball.hold_timer >= self.hold_duration:
                    self.score += 1
                    self.publish_score()
                    self.get_logger().info(f'SKOR BERTAMBAH! Skor saat ini: {self.score}')
                    ball.respawn(self.frame_w, self.frame_h, self.ball_speed)
            else:
                ball.hold_timer = 0.0

        for ball in self.balls:
            bx, by = int(ball.x), int(ball.y)
            cv2.circle(frame, (bx, by), ball.radius, ball.color, -1)
            cv2.circle(frame, (bx, by), ball.radius, (255, 255, 255), 2)

            if ball.hold_timer > 0:
                progress = min(ball.hold_timer / self.hold_duration, 1.0)
                bar_w = ball.radius * 2
                bar_h = 10
                bar_x = bx - ball.radius
                bar_y = by - ball.radius - 15
                cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 50, 50), -1)
                cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_w * progress), bar_y + bar_h), (0, 255, 0), -1)

        if bbox is not None and object_centroid is not None:
            x, y, w, h = bbox
            cx, cy = object_centroid
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
            cv2.circle(frame, (cx, cy), 6, (0, 0, 255), -1)
            cv2.putText(frame, "Objek", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        cv2.rectangle(frame, (10, 10), (190, 55), (0, 0, 0), -1)
        cv2.putText(frame, f'Score: {self.score}', (20, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        cv2.imshow("Kalibrasi HSV", mask)
        cv2.imshow("Layar Game (Klik Objek Untuk Kalibrasi Otomatis)", frame)
        cv2.waitKey(1)

        debug_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        debug_msg.header = msg.header
        self.pub_debug.publish(debug_msg)


def main(args=None):
    rclpy.init(args=args)
    node = GameNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
