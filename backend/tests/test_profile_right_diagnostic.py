import os
import sys

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
        if result.filename in interesting:
            print(
                f"{result.filename} | category={result.category.value} | "
                f"yaw={result.scores.get('yaw')} | "
                f"eye_compression={result.scores.get('eye_compression')} | "
                f"pitch={result.scores.get('pitch')} | "
                f"smile_score={result.scores.get('smile_score')} | "
                f"confidence={result.confidence}"
            )
    print('PROFILE_RIGHT_DIAGNOSTIC_END')
    assert False, 'Temporary diagnostic: inspect captured metrics above'
