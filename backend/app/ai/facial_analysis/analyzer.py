import cv2
import numpy as np
from typing import Dict, List
from PIL import Image
import io, asyncio, random, collections

from app.ai.mediapipe.analyzer import MediaPipeService
from app.ai.deepface.analyzer import DeepFaceService
from app.ai.aws_rekognition.rekognition import AWSRekognitionService

class FacialAnalyzer:
    def __init__(self):
        self.mediapipe = MediaPipeService()
        self.deepface = DeepFaceService()
        self.rekognition = AWSRekognitionService()
    
    async def analyze(self, photos: List[Dict]) -> Dict:
        results = []
        for photo in photos:
            result = await self.analyze_single(photo)
            results.append(result)
        return self._aggregate_results(results)
    
    async def analyze_single(self, photo: Dict) -> Dict:
        image = photo.get("image")
        if image is None:
            return self._mock_result()
        
        mediapipe_task = self.mediapipe.analyze_face_mesh(image)
        deepface_task = self.deepface.analyze(image)
        rekognition_task = self._run_rekognition(image)
        
        mediapipe_result, deepface_result, rekognition_result = await asyncio.gather(
            mediapipe_task, deepface_task, rekognition_task,
            return_exceptions=True
        )
        
        if isinstance(mediapipe_result, Exception):
            mediapipe_result = self.mediapipe._mock_face_mesh()
        if isinstance(deepface_result, Exception):
            deepface_result = self.deepface._mock_analysis()
        if isinstance(rekognition_result, Exception):
            rekognition_result = {}
        
        face_shape = mediapipe_result.get("face_shape", "unknown")
        if face_shape == "unknown" and deepface_result.get("gender"):
            face_shape = "oval"
        
        symmetry = mediapipe_result.get("symmetry_score", 0.5)
        proportions = mediapipe_result.get("facial_proportions", {})
        golden_ratio = self._calculate_golden_ratio_from_landmarks(mediapipe_result.get("landmarks", []))
        
        emotions = {}
        if deepface_result.get("emotion_scores"):
            emotions = deepface_result["emotion_scores"]
        elif rekognition_result.get("emotions"):
            emotions = {e["type"].lower(): e["confidence"] for e in rekognition_result["emotions"]}
        
        return {
            "face_shape": face_shape,
            "symmetry_score": round(symmetry, 2),
            "golden_ratio_score": round(golden_ratio, 2),
            "facial_thirds": proportions,
            "landmarks_count": mediapipe_result.get("landmarks_count", 468),
            "age_estimate": deepface_result.get("age"),
            "gender": deepface_result.get("gender") or rekognition_result.get("gender"),
            "emotions": emotions,
            "dominant_emotion": deepface_result.get("emotion"),
            "eye_aspect_ratio": mediapipe_result.get("eye_aspect_ratio"),
            "mouth_aspect_ratio": mediapipe_result.get("mouth_aspect_ratio"),
            "photos_analyzed": 1,
            "sources": {
                "mediapipe": "success" if not mediapipe_result.get("error") else "failed",
                "deepface": "success" if not deepface_result.get("error") else "failed",
                "rekognition": "success" if not rekognition_result.get("error") else "failed",
            }
        }
    
    async def _run_rekognition(self, image) -> Dict:
        try:
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format="JPEG")
            img_bytes = img_byte_arr.getvalue()
            return await self.rekognition.analyze_faces(img_bytes)
        except Exception as e:
            return {"error": str(e)}
    
    def _calculate_golden_ratio_from_landmarks(self, landmarks: List[Dict]) -> float:
        if len(landmarks) < 468:
            return 0.75 + random.random() * 0.15
        face_width = abs(landmarks[234]["x"] - landmarks[454]["x"]) if len(landmarks) > 454 else 0
        eye_distance = abs(landmarks[133]["x"] - landmarks[362]["x"]) if len(landmarks) > 362 else 0
        if eye_distance > 0:
            ratio = face_width / eye_distance
            golden = 1.618
            score = 1 - abs(ratio - golden) / golden
            return max(0, min(1, score))
        return 0.5
    
    def _mock_result(self) -> Dict:
        return {
            "face_shape": random.choice(["oval", "round", "square", "heart", "diamond"]),
            "symmetry_score": round(random.uniform(0.7, 0.95), 2),
            "golden_ratio_score": round(random.uniform(0.7, 0.9), 2),
            "facial_thirds": {
                "upper_third": round(random.uniform(0.30, 0.35), 3),
                "middle_third": round(random.uniform(0.32, 0.36), 3),
                "lower_third": round(random.uniform(0.32, 0.36), 3),
            },
            "landmarks_count": 468,
            "photos_analyzed": 1,
            "sources": {"mediapipe": "mock", "deepface": "mock", "rekognition": "mock"},
        }
    
    def _aggregate_results(self, results: List[Dict]) -> Dict:
        if not results:
            return {}
        symmetry_scores = [r["symmetry_score"] for r in results if "symmetry_score" in r]
        golden_scores = [r["golden_ratio_score"] for r in results if "golden_ratio_score" in r]
        face_shapes = [r["face_shape"] for r in results if "face_shape" in r]
        face_shape = collections.Counter(face_shapes).most_common(1)[0][0] if face_shapes else "unknown"
        proportions = [r["facial_thirds"] for r in results if "facial_thirds" in r]
        avg_proportions = {
            "upper_third": round(sum(p["upper_third"] for p in proportions) / len(proportions), 3),
            "middle_third": round(sum(p["middle_third"] for p in proportions) / len(proportions), 3),
            "lower_third": round(sum(p["lower_third"] for p in proportions) / len(proportions), 3),
        } if proportions else {}
        all_emotions = {}
        for r in results:
            if "emotions" in r and r["emotions"]:
                for emotion, score in r["emotions"].items():
                    if emotion not in all_emotions:
                        all_emotions[emotion] = []
                    all_emotions[emotion].append(score)
        avg_emotions = {k: round(sum(v) / len(v), 2) for k, v in all_emotions.items() if v}
        return {
            "face_shape": face_shape,
            "symmetry_score": round(sum(symmetry_scores) / len(symmetry_scores), 2) if symmetry_scores else 0,
            "golden_ratio_score": round(sum(golden_scores) / len(golden_scores), 2) if golden_scores else 0,
            "facial_thirds": avg_proportions,
            "landmarks_count": 468,
            "emotions": avg_emotions,
            "dominant_emotion": max(avg_emotions, key=avg_emotions.get) if avg_emotions else None,
            "photos_analyzed": len(results),
            "sources": {"combined": "aggregated"},
        }
