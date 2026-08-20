import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from ai.image_triage.engine import ImageTriageEngine


def test_profile_right_diagnostic():
    engine = ImageTriageEngine()
    dataset_path = os.path.join(
        os.path.dirname(__file__),
        'fixtures',
        'visagism',
        'dataset_001',
    )
    results = engine.process_dataset(dataset_path)
    interesting = {
        '03_tres_quartos_A.jpg',
        '04_tres_quartos_B.jpg',
        '05_perfil_A.jpg',
        '06_perfil_B.jpg',
    }
    print('\nPROFILE_RIGHT_DIAGNOSTIC_BEGIN')
    for result in results:
        if result.filename not in interesting:
            continue

        image_path = os.path.join(dataset_path, result.filename)
        img_array = np.array(Image.open(image_path).convert('RGB'))
        pose = engine._analyze_pose(img_array)
        face = engine._analyze_face(img_array)
        posterior_score = engine._detect_posterior(img_array, pose, face)

        print(
            f"{result.filename} | category={result.category.value} | "
            f"yaw={result.scores.get('yaw')} | "
            f"eye_compression={result.scores.get('eye_compression')} | "
            f"pitch={result.scores.get('pitch')} | "
            f"smile_score={result.scores.get('smile_score')} | "
            f"confidence={result.confidence} | "
            f"face_detected={face.get('has_face')} | "
            f"posterior_score={posterior_score}"
        )

        landmarks = pose.get('landmarks', [])
        if len(landmarks) >= 13:
            values = []
            for idx, name in (
                (0, 'nose'),
                (2, 'left_eye'),
                (5, 'right_eye'),
                (7, 'left_ear'),
                (8, 'right_ear'),
                (11, 'left_shoulder'),
                (12, 'right_shoulder'),
            ):
                lm = landmarks[idx]
                values.append(
                    f"{name}(x={lm.get('x'):.4f},vis={lm.get('visibility'):.4f})"
                )
            print(f"POSE {result.filename} | " + ' | '.join(values))

    print('PROFILE_RIGHT_DIAGNOSTIC_END')
    assert False, 'Temporary diagnostic: inspect captured metrics above'
