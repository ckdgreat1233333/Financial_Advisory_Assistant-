from pathlib import Path

import joblib

from utils.enums import IntentType


BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    BASE_DIR
    / "trained_models"
    / "intent_classifier.pkl"
)


class IntentClassifier:

    def __init__(self):

        self.pipeline = joblib.load(MODEL_PATH)

    def predict(
        self,
        query: str,
    ) -> IntentType:

        prediction = self.pipeline.predict(
            [query]
        )[0]

        return IntentType[prediction]