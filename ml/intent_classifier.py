from pathlib import Path

from utils.enums import IntentType


BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    BASE_DIR
    / "trained_models"
    / "intent_classifier.pkl"
)

# Keyword rules used when the trained model is unavailable or
# produces an unknown label. Keeps the customer assistant working
# without requiring model retraining.
_INSURANCE_RULES = [
    (["status", "where is my", "what is the status", "has my claim", "progress"], IntentType.CLAIM_STATUS),
    (["why", "reason", "explain", "denied", "rejected", "approved", "outcome"], IntentType.CLAIM_EXPLANATION),
    (["next step", "next steps", "appeal", "what should i do", "documents should", "happens after"], IntentType.NEXT_STEPS),
    (["covered", "coverage", "exclude", "exclusion", "policy", "pre existing", "waiting period", "reporting window"], IntentType.POLICY_QUERY),
    (["document", "upload", "proof of loss", "claim form", "medical report", "verify"], IntentType.DOCUMENT_PROCESSING),
    (["hi", "hello", "hey", "thank", "thanks", "who are you", "what can you do", "good morning", "good evening", "help"], IntentType.GENERAL_QUERY),
]


class IntentClassifier:

    def __init__(self):
        self.pipeline = None
        try:
            import joblib
            self.pipeline = joblib.load(MODEL_PATH)
        except Exception:
            self.pipeline = None

    def predict(self, query: str) -> IntentType:

        text = query.lower()

        for keywords, intent in _INSURANCE_RULES:
            for kw in keywords:
                if kw in text:
                    return intent

        if self.pipeline is not None:
            try:
                prediction = self.pipeline.predict([query])[0]
                try:
                    return IntentType[prediction]
                except KeyError:
                    pass  # label no longer in enum
            except Exception:
                pass

        return IntentType.GENERAL_QUERY
