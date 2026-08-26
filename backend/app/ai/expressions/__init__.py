from .analyzer import ExpressionAnalyzer


def _combine_results_without_nameerror(
    self,
    deepface_emotions,
    eyes,
    smile,
    eyebrows,
    mouth,
):
    """Compatibility hotfix for analyzer scoring helpers that referenced `smile` out of scope."""
    angry_score = 0.0
    if eyebrows["furrow_score"] > 0.5:
        angry_score += 0.45
    if eyebrows["elevation_score"] < 0.2:
        angry_score += 0.30
    if mouth["corners_down"] > 0.2 and not smile.get("detected", False):
        angry_score += 0.25
    angry_score = min(1.0, angry_score)

    disgust_score = 0.0
    if eyebrows["furrow_score"] > 0.4 and eyebrows["elevation_score"] < 0.3:
        disgust_score += 0.40
    if mouth["corners_down"] > 0.2:
        disgust_score += 0.30
    if not smile.get("detected", False):
        disgust_score += 0.30
    disgust_score = min(1.0, disgust_score)

    heuristic = {
        "neutral": self._score_neutral(eyes, smile, eyebrows, mouth),
        "happy": smile["score"],
        "surprise": self._score_surprise(eyes, eyebrows, mouth),
        "sad": self._score_sad(eyes, eyebrows, mouth),
        "angry": angry_score,
        "fear": self._score_fear(eyes, eyebrows, mouth),
        "disgust": disgust_score,
    }

    if deepface_emotions:
        combined = {}
        for emotion in heuristic:
            df_score = deepface_emotions.get(emotion, 0)
            h_score = heuristic[emotion]
            combined[emotion] = round(df_score * 0.6 + h_score * 0.4, 3)
        return combined

    return heuristic


# The analyzer currently has two helpers that reference a local `smile` variable.
# Override only the aggregation entry point so production no longer raises NameError
# while preserving the intended scoring behavior.
ExpressionAnalyzer._combine_results = _combine_results_without_nameerror
