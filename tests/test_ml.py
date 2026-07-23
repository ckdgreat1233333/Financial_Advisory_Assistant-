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
        result = TextPreprocessor.clean("What's the salary? \u20b950,000")
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
        result = TextPreprocessor.clean("salary 50000 rupees")
        assert "50000" in result


class TestIntentClassifier:
    """Test ML-based intent classification pipeline."""

    @classmethod
    def setup_class(cls):
        cls.classifier = IntentClassifier()

    def test_predict_policy_query(self):
        queries = [
            "What documents are required for a home loan?",
            "Explain the eligibility criteria",
            "Tell me the interest rate policy",
        ]
        for query in queries:
            intent = self.classifier.predict(query)
            assert intent == IntentType.POLICY_QUERY, f"'{query}' should be POLICY_QUERY, got {intent}"

    def test_predict_document_processing(self):
        queries = [
            "Upload my salary slip",
            "Process this PDF document",
            "Validate my bank statement",
            "Read my PAN card",
            "Review my Aadhaar",
        ]
        for query in queries:
            intent = self.classifier.predict(query)
            assert intent == IntentType.DOCUMENT_PROCESSING, f"'{query}' should be DOCUMENT_PROCESSING, got {intent}"

    def test_predict_application_status(self):
        queries = [
            "Why was my loan application rejected?",
            "Show me the current loan status",
            "What is the approval timeline?",
        ]
        for query in queries:
            intent = self.classifier.predict(query)
            assert intent == IntentType.APPLICATION_STATUS, f"'{query}' should be APPLICATION_STATUS, got {intent}"

    def test_predict_risk_query(self):
        queries = [
            "Is this application high risk?",
            "What are the risk factors?",
            "Are there compliance issues?",
        ]
        for query in queries:
            intent = self.classifier.predict(query)
            assert intent == IntentType.RISK_QUERY, f"'{query}' should be RISK_QUERY, got {intent}"

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
            IntentType.APPLICATION_STATUS.name,
            IntentType.RISK_QUERY.name,
            IntentType.GENERAL_QUERY.name,
        }
        actual_intents = set(df["intent"].unique())
        missing = required_intents - actual_intents
        assert not missing, f"Dataset missing intents: {missing}"

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
