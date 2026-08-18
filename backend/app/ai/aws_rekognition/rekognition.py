import boto3
import io
from typing import Dict, List
from app.config import settings

class AWSRekognitionService:
    def __init__(self):
        self.client = boto3.client(
            "rekognition",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )

    async def analyze_faces(self, image_bytes: bytes) -> Dict:
        try:
            response = self.client.detect_faces(
                Image={"Bytes": image_bytes},
                Attributes=["ALL"]
            )

            if not response["FaceDetails"]:
                return {"error": "No face detected by Rekognition"}

            face = response["FaceDetails"][0]

            return {
                "confidence": face.get("Confidence"),
                "age_range": face.get("AgeRange"),
                "gender": face.get("Gender", {}).get("Value"),
                "gender_confidence": face.get("Gender", {}).get("Confidence"),
                "emotions": [
                    {"type": e["Type"], "confidence": e["Confidence"]}
                    for e in face.get("Emotions", [])
                ],
                "smile": {
                    "value": face.get("Smile", {}).get("Value"),
                    "confidence": face.get("Smile", {}).get("Confidence"),
                },
                "eyeglasses": face.get("Eyeglasses", {}).get("Value"),
                "sunglasses": face.get("Sunglasses", {}).get("Value"),
                "beard": face.get("Beard", {}).get("Value"),
                "mustache": face.get("Mustache", {}).get("Value"),
                "eyes_open": face.get("EyesOpen", {}).get("Value"),
                "mouth_open": face.get("MouthOpen", {}).get("Value"),
                "quality": face.get("Quality", {}),
                "bounding_box": face.get("BoundingBox", {}),
                "landmarks": [
                    {"type": lm["Type"], "x": lm["X"], "y": lm["Y"]}
                    for lm in face.get("Landmarks", [])
                ],
            }
        except Exception as e:
            return {"error": str(e)}

    async def compare_faces(self, source_bytes: bytes, target_bytes: bytes) -> Dict:
        try:
            response = self.client.compare_faces(
                SourceImage={"Bytes": source_bytes},
                TargetImage={"Bytes": target_bytes},
                SimilarityThreshold=70,
            )
            return {
                "matches": len(response.get("FaceMatches", [])),
                "similarity": response["FaceMatches"][0]["Similarity"] if response.get("FaceMatches") else 0,
                "unmatched_faces": len(response.get("UnmatchedFaces", [])),
            }
        except Exception as e:
            return {"error": str(e)}

    async def detect_labels(self, image_bytes: bytes) -> Dict:
        try:
            response = self.client.detect_labels(
                Image={"Bytes": image_bytes},
                MaxLabels=50,
                MinConfidence=70,
            )
            return {
                "labels": [
                    {
                        "name": label["Name"],
                        "confidence": label["Confidence"],
                        "parents": [p["Name"] for p in label.get("Parents", [])],
                    }
                    for label in response.get("Labels", [])
                ],
            }
        except Exception as e:
            return {"error": str(e)}
