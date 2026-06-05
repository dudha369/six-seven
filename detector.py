import cv2
import mediapipe as mp
import numpy as np


class MovementDetector:
    def __init__(self, movement_threshold=0.03):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.movement_threshold = movement_threshold

        # Храним предыдущие координаты Y запястий
        self.prev_left_y = None
        self.prev_right_y = None

    def calculate_angle(self, a, b, c):
        """Вычисляет угол между тремя точками (плечо, локоть, запястье)"""
        a = np.array(a)
        b = np.array(b)
        c = np.array(c)

        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        if angle > 180.0:
            angle = 360 - angle
        return angle

    def process_frame(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb_frame)

        trigger_sound = False

        if results.pose_landmarks:
            self.mp_draw.draw_landmarks(
                frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS
            )

            landmarks = results.pose_landmarks.landmark

            # Индексы точек: 11/12 - плечи, 13/14 - локти, 15/16 - запястья
            l_shoulder = [landmarks[11].x, landmarks[11].y]
            l_elbow = [landmarks[13].x, landmarks[13].y]
            l_wrist = [landmarks[15].x, landmarks[15].y]

            r_shoulder = [landmarks[12].x, landmarks[12].y]
            r_elbow = [landmarks[14].x, landmarks[14].y]
            r_wrist = [landmarks[16].x, landmarks[16].y]

            # 1. Проверяем, согнуты ли локти (угол меньше 110 градусов)
            l_angle = self.calculate_angle(l_shoulder, l_elbow, l_wrist)
            r_angle = self.calculate_angle(r_shoulder, r_elbow, r_wrist)
            elbows_bent = l_angle < 110 and r_angle < 110

            # 2. Проверяем движение в разные стороны
            curr_left_y = l_wrist[1]
            curr_right_y = r_wrist[1]

            if elbows_bent and self.prev_left_y is not None and self.prev_right_y is not None:
                # Разница координат (отрицательная - движение вверх, положительная - вниз)
                dy_left = curr_left_y - self.prev_left_y
                dy_right = curr_right_y - self.prev_right_y

                # Если dy_left и dy_right имеют разные знаки (одно больше 0, другое меньше) -> движение в разные стороны
                moving_opposite = (dy_left * dy_right) < 0

                # Проверяем амплитуду, чтобы не реагировать на микротряску
                amplitude_sufficient = abs(dy_left) > self.movement_threshold and abs(
                    dy_right) > self.movement_threshold

                if moving_opposite and amplitude_sufficient:
                    trigger_sound = True

            self.prev_left_y = curr_left_y
            self.prev_right_y = curr_right_y

        return frame, trigger_sound
