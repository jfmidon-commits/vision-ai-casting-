import cv2
import numpy as np
from typing import Dict, List


class MediaPipeService:
    def __init__(self):
        self._face_mesh = None
        self._pose = None
        self._hands = None
        self._initialized = False
        self._init_error = None

    def _init_models(self):
        if self._initialized or self._init_error:
            return

        try:
            import mediapipe as mp

            self.mp_face_mesh = mp.solutions.face_mesh
            self.mp_pose = mp.solutions.pose
            self.mp_hands = mp.solutions.hands
            self.mp_drawing = mp.solutions.drawing_utils

            self._face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
            )

            self._pose = self.mp_pose.Pose(
                static_image_mode=True,
                model_complexity=2,
                min_detection_confidence=0.5,
            )

            self._hands = self.mp_hands.Hands(
                static_image_mode=True,
                max_num_hands=2,
                min_detection_confidence=0.5,
            )

            self._initialized = True
        except Exception as exc:
            self._init_error = str(exc)

    async def analyze_face_mesh(self, image) -> Dict:
        self._init_models()

        if not self._initialized:
            return {
                "error": f"MediaPipe unavailable: {self._init_error or 'initialization failed'}",
                "landmarks_count": 0,
                "landmarks": [],
            }

        try:
            img_array = np.array(image.convert("RGB"))
            # PIL already yields RGB. MediaPipe expects RGB, so do not swap channels.
            results = self._face_mesh.process(img_array)

            if not results.multi_face_landmarks:
                return {"error": "No face detected", "landmarks_count": 0, "landmarks": []}

            landmarks = [
                {"x": lm.x, "y": lm.y, "z": lm.z}
                for lm in results.multi_face_landmarks[0].landmark
            ]

            return {
                "landmarks_count": len(landmarks),
                # The visagism measurement engine uses indices up to 454; it needs
                # the complete mesh, not a ten-landmark preview.
                "landmarks": landmarks,
                "symmetry_score": round(self._calculate_symmetry(landmarks), 3),
                "facial_proportions": self._calculate_facial_proportions(landmarks),
                "face_shape": self._classify_face_shape(landmarks),
                "eye_aspect_ratio": self._calculate_ear(landmarks),
                "mouth_aspect_ratio": self._calculate_mar(landmarks),
            }
        except Exception as exc:
            # Never manufacture random biometric measurements on a production path.
            return {"error": str(exc), "landmarks_count": 0, "landmarks": []}

    async def analyze_pose(self, image) -> Dict:
        self._init_models()
        if not self._initialized:
            return {
                "error": f"MediaPipe unavailable: {self._init_error or 'initialization failed'}",
                "landmarks_count": 0,
                "landmarks": [],
            }

        try:
            img_array = np.array(image.convert("RGB"))
            results = self._pose.process(img_array)
            if not results.pose_landmarks:
                return {"error": "No pose detected", "landmarks_count": 0, "landmarks": []}

            landmarks = [
                {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility}
                for lm in results.pose_landmarks.landmark
            ]
            return {
                "landmarks_count": len(landmarks),
                "landmarks": landmarks,
                "posture_score": self._calculate_posture_score(landmarks),
                "body_symmetry": self._calculate_body_symmetry(landmarks),
            }
        except Exception as exc:
            return {"error": str(exc), "landmarks_count": 0, "landmarks": []}

    def _calculate_symmetry(self, landmarks: List[Dict]) -> float:
        symmetry_pairs = [
            (33, 263), (133, 362), (159, 386), (145, 374),
            (61, 291), (0, 17), (234, 454), (10, 152),
        ]
        center_x = landmarks[1]["x"] if len(landmarks) > 1 else 0.5
        scores = []
        for left_idx, right_idx in symmetry_pairs:
            if left_idx < len(landmarks) and right_idx < len(landmarks):
                left_dist = abs(landmarks[left_idx]["x"] - center_x)
                right_dist = abs(landmarks[right_idx]["x"] - center_x)
                if left_dist + right_dist > 0:
                    scores.append(1 - abs(left_dist - right_dist) / (left_dist + right_dist))
        return sum(scores) / len(scores) if scores else 0.5

    def _calculate_facial_proportions(self, landmarks: List[Dict]) -> Dict:
        if len(landmarks) < 468:
            return {}
        top = landmarks[10]["y"]
        brow = landmarks[105]["y"]
        nose = landmarks[1]["y"]
        chin = landmarks[152]["y"]
        total = chin - top
        if total <= 0:
            return {}
        return {
            "upper_third": round((brow - top) / total, 3),
            "middle_third": round((nose - brow) / total, 3),
            "lower_third": round((chin - nose) / total, 3),
            "face_width": abs(landmarks[234]["x"] - landmarks[454]["x"]),
            "face_height": abs(landmarks[10]["y"] - landmarks[152]["y"]),
        }

    def _classify_face_shape(self, landmarks: List[Dict]) -> str:
        if len(landmarks) < 468:
            return "unknown"
        face_width = abs(landmarks[234]["x"] - landmarks[454]["x"])
        face_height = abs(landmarks[10]["y"] - landmarks[152]["y"])
        jaw_width = abs(landmarks[58]["x"] - landmarks[288]["x"])
        ratio = face_height / face_width if face_width > 0 else 1.3
        jaw_ratio = jaw_width / face_width if face_width > 0 else 0.8
        if ratio > 1.5:
            return "oblong"
        if ratio < 1.2 and jaw_ratio > 0.85:
            return "round"
        if jaw_ratio < 0.75:
            return "heart"
        if abs(ratio - 1.3) < 0.1 and jaw_ratio > 0.78:
            return "oval"
        if jaw_ratio > 0.88:
            return "square"
        return "mixed"

    def _calculate_ear(self, landmarks: List[Dict]) -> float:
        if len(landmarks) < 468:
            return 0.0
        left_eye = [landmarks[i] for i in [33, 160, 158, 133, 153, 144]]
        a = np.linalg.norm([left_eye[1]["y"] - left_eye[5]["y"], left_eye[1]["x"] - left_eye[5]["x"]])
        b = np.linalg.norm([left_eye[2]["y"] - left_eye[4]["y"], left_eye[2]["x"] - left_eye[4]["x"]])
        c = np.linalg.norm([left_eye[0]["y"] - left_eye[3]["y"], left_eye[0]["x"] - left_eye[3]["x"]])
        return (a + b) / (2.0 * c) if c > 0 else 0.0

    def _calculate_mar(self, landmarks: List[Dict]) -> float:
        if len(landmarks) < 468:
            return 0.0
        mouth = [landmarks[i] for i in [61, 291, 13, 14]]
        height = abs(mouth[2]["y"] - mouth[3]["y"])
        width = abs(mouth[0]["x"] - mouth[1]["x"])
        return height / width if width > 0 else 0.0

    def _calculate_posture_score(self, landmarks: List[Dict]) -> float:
        if len(landmarks) < 33:
            return 0.5
        left_shoulder, right_shoulder = landmarks[11], landmarks[12]
        shoulder_diff = abs(left_shoulder["y"] - right_shoulder["y"])
        center_x = (left_shoulder["x"] + right_shoulder["x"]) / 2
        head_alignment = 1 - abs(landmarks[0]["x"] - center_x)
        return round((1 - shoulder_diff) * 0.5 + head_alignment * 0.5, 3)

    def _calculate_body_symmetry(self, landmarks: List[Dict]) -> float:
        if len(landmarks) < 33:
            return 0.5
        pairs = [(11, 12), (13, 14), (15, 16), (23, 24), (25, 26), (27, 28)]
        scores = [1 - abs(landmarks[l]["y"] - landmarks[r]["y"]) for l, r in pairs]
        return round(sum(scores) / len(scores), 3) if scores else 0.5
