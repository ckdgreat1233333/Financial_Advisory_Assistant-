"""
ML & NLP Tests for Intent Classification
"""
import pytest
from pathlib import Path

from ml.intent_classifier import IntentClassifier
from ml.preprocess import TextPreprocessor
from utils.enums import IntentType


class TestTextPreprocessor:
    """Test text preprocessing for ML pipeline."""

    def test_clean_lowercase(self):
        assert TextPreprocessor.clean("HELLO WORLD") == "hello world"

    def test_clean_remove_punctuation(self):
        result = TextPreprocessor.clean("What's the coverage? \u20b950,000")
        assert "?" not in result
        assert "\u20b9" not in result
        assert "'" not in result
        assert TextPreprocessor.clean("\u201d") == ""
        assert TextPreprocessor.clean("\u2014") == ""
        assert TextPreprocessor.clean("\u20b950,000") == "50000"

    def test_clean_collapse_whitespace(self):
        assert TextPreprocessor.clean("hello    world") == "hello world"
        assert TextPreprocessor.clean("  hello world  ") == "hello world"

    def test_clean_preserves_important_numbers(self):
        result = TextPreprocessor.clean("claim amount 50000 rupees")
        assert "50000" in result


class TestIntentClassifier:
    """Test ML-based intent classification pipeline."""

    @classmethod
    def setup_class(cls):
        cls.classifier = IntentClassifier()

    def test_predict_policy_query(self):
        queries = [
            "What is the coverage for fire damage?",
            "Are pre existing conditions excluded?",
            "Tell me about the waiting period",
        ]
        for query in queries:
            intent = self.classifier.predict(query)
            assert intent == IntentType.POLICY_QUERY, f"'{query}' should be POLICY_QUERY, got {intent}"

    def test_predict_document_processing(self):
        queries = [
            "Upload my claim form",
            "Process this PDF document",
            "Verify my proof of loss",
            "Where do I submit the medical report?",
        ]
        for query in queries:
            intent = self.classifier.predict(query)
            assert intent == IntentType.DOCUMENT_PROCESSING, f"'{query}' should be DOCUMENT_PROCESSING, got {intent}"

    def test_predict_claim_status(self):
        queries = [
            "Where is my claim status?",
            "Show me the current claim status",
            "Has my claim been accepted?",
        ]
        for query in queries:
            intent = self.classifier.predict(query)
            assert intent == IntentType.CLAIM_STATUS, f"'{query}' should be CLAIM_STATUS, got {intent}"

    def test_predict_claim_explanation(self):
        queries = [
            "Why was my claim rejected?",
            "Explain the claim decision",
            "What is the reason for denial?",
        ]
        for query in queries:
            intent = self.classifier.predict(query)
            assert intent == IntentType.CLAIM_EXPLANATION, f"'{query}' should be CLAIM_EXPLANATION, got {intent}"

    def test_predict_next_steps(self):
        queries = [
            "What are the next steps?",
            "How do I appeal the decision?",
            "What happens after review?",
        ]
        for query in queries:
            intent = self.classifier.predict(query)
            assert intent == IntentType.NEXT_STEPS, f"'{query}' should be NEXT_STEPS, got {intent}"

    def test_predict_general_query(self):
        queries = [
            "Hello",
            "Thank you",
            "Who are you?",
            "Good morning",
        ]
        for query in queries:
            intent = self.classifier.predict(query)
            assert intent == IntentType.GENERAL_QUERY, f"'{query}' should be GENERAL_QUERY, got {intent}"


class TestIntentModelTrainer:
    """Test the model training pipeline including evaluation metrics."""

    def test_dataset_exists(self):
        dataset_path = Path(__file__).resolve().parent.parent / "data" / "intents" / "intents.csv"
        assert dataset_path.exists(), f"Training dataset not found: {dataset_path}"

    def test_dataset_has_required_classes(self):
        import pandas as pd
        dataset_path = Path(__file__).resolve().parent.parent / "data" / "intents" / "intents.csv"
        df = pd.read_csv(dataset_path)

        required_intents = {
            IntentType.POLICY_QUERY.name,
            IntentType.DOCUMENT_PROCESSING.name,
            IntentType.CLAIM_STATUS.name,
            IntentType.CLAIM_EXPLANATION.name,
            IntentType.NEXT_STEPS.name,
            IntentType.GENERAL_QUERY.name,
        }
        actual_intents = set(df["intent"].unique())
        missing = required_intents - actual_intents
        assert not missing, f"Dataset missing intents: {missing}"

    def test_dataset_has_no_legacy_intents(self):
        import pandas as pd
        dataset_path = Path(__file__).resolve().parent.parent / "data" / "intents" / "intents.csv"
        df = pd.read_csv(dataset_path)

        legacy = {"APPLICATION_STATUS", "RISK_QUERY"}
        actual_intents = set(df["intent"].unique())
        assert not (legacy & actual_intents), f"Dataset contains legacy loan intents: {legacy & actual_intents}"

    def test_trained_model_exists(self):
        model_path = Path(__file__).resolve().parent.parent / "trained_models" / "intent_classifier.pkl"
        assert model_path.exists(), f"Trained model not found: {model_path}"

    def test_training_pipeline_creates_model(self):
        try:
            from ml.model import IntentModelTrainer
        except ImportError:
            pytest.skip("PyTorch / transformers not available")
        trainer = IntentModelTrainer()
        df = trainer.load_dataset()
        assert len(df) > 0, "Dataset should have training examples"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
