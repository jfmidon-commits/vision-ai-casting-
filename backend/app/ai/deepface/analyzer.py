from typing import Dict, List
import numpy as np
from PIL import Image

class DeepFaceService:
    def __init__(self):
        self._models_loaded = False

    def _load_models(self):
        if not self._models_loaded:
            try:
                from deepface import DeepFace
                self._deepface = DeepFace
                self._models_loaded = True
            except ImportError:
                pass

    async def analyze(self, image) -> Dict:
        self._load_models()

        if not self._models_loaded:
            return self._mock_analysis()

        try:
            import tempfile
            import os

            # Save image to temp file
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                image.save(tmp.name, "JPEG")
                tmp_path = tmp.name

            # Analyze with DeepFace
            analysis = self._deepface.analyze(
                img_path=tmp_path,
                actions=["age", "gender", "emotion", "race"],
                enforce_detection=False,
                silent=True,
            )

            if isinstance(analysis, list):
                analysis = analysis[0]

            # Clean up
            os.unlink(tmp_path)

            return {
                "age": analysis.get("age"),
                "gender": analysis.get("dominant_gender"),
                "gender_confidence": max(analysis.get("gender", {}).values()) if analysis.get("gender") else None,
                "emotion": analysis.get("dominant_emotion"),
                "emotion_scores": analysis.get("emotion", {}),
                "race": analysis.get("dominant_race"),
                "race_scores": analysis.get("race", {}),
            }
        except Exception as e:
            return {**self._mock_analysis(), "error": str(e)}

    def _mock_analysis(self) -> Dict:
        import random
        emotions = ["happy", "sad", "angry", "fear", "surprise", "disgust", "neutral"]
        emotion_scores = {e: round(random.uniform(5, 30), 2) for e in emotions}
        emotion_scores["neutral"] = round(random.uniform(30, 60), 2)
        dominant = max(emotion_scores, key=emotion_scores.get)

        return {
            "age": random.randint(20, 45),
            "gender": random.choice(["Man", "Woman"]),
            "gender_confidence": round(random.uniform(90, 99), 2),
            "emotion": dominant,
            "emotion_scores": emotion_scores,
            "race": random.choice(["latino hispanic", "white", "black", "asian", "middle eastern"]),
            "race_scores": {},
            "note": "Mock analysis - DeepFace not available",
        }

    async def verify_identity(self, img1, img2) -> Dict:
        self._load_models()
        if not self._models_loaded:
            return {"verified": False, "distance": 0.5, "similarity": 0.5}

        try:
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp1:
                img1.save(tmp1.name, "JPEG")
                path1 = tmp1.name

            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp2:
                img2.save(tmp2.name, "JPEG")
                path2 = tmp2.name

            result = self._deepface.verify(
                img1_path=path1,
                img2_path=path2,
                enforce_detection=False,
            )

            os.unlink(path1)
            os.unlink(path2)

            return {
                "verified": result.get("verified", False),
                "distance": result.get("distance", 1.0),
                "similarity": 1 - result.get("distance", 1.0),
                "threshold": result.get("threshold", 0.4),
                "model": result.get("model", "VGG-Face"),
            }
        except Exception as e:
            return {"verified": False, "error": str(e)}

    async def find_similar(self, img, db_path: str) -> List[Dict]:
        self._load_models()
        if not self._models_loaded:
            return []

        try:
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                img.save(tmp.name, "JPEG")
                path = tmp.name

            results = self._deepface.find(
                img_path=path,
                db_path=db_path,
                enforce_detection=False,
            )

            os.unlink(path)

            return [
                {
                    "identity": r.get("identity"),
                    "distance": r.get("distance"),
                    "similarity": 1 - r.get("distance", 1.0),
                }
                for r in results
            ]
        except Exception as e:
            return [{"error": str(e)}]
