from pathlib import Path

import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from ml.preprocess import TextPreprocessor


BASE_DIR = Path(__file__).resolve().parent.parent

DATASET_PATH = BASE_DIR / "data" / "intents" / "intents.csv"

MODEL_PATH = BASE_DIR / "trained_models" / "intent_classifier.pkl"


class IntentModelTrainer:

    def __init__(self):

        self.pipeline = Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(),
                ),
                (
                    "classifier",
                    LogisticRegression(
                        max_iter=1000,
                        random_state=42,
                    ),
                ),
            ]
        )

    def load_dataset(self):

        dataframe = pd.read_csv(DATASET_PATH)

        dataframe["text"] = dataframe["text"].apply(
            TextPreprocessor.clean
        )

        return dataframe

    def train(self):

        dataframe = self.load_dataset()

        X_train, X_test, y_train, y_test = train_test_split(
            dataframe["text"],
            dataframe["intent"],
            test_size=0.2,
            random_state=42,
            stratify=dataframe["intent"],
        )

        self.pipeline.fit(
            X_train,
            y_train,
        )

        predictions = self.pipeline.predict(
            X_test,
        )

        print(
            classification_report(
                y_test,
                predictions,
            )
        )

        MODEL_PATH.parent.mkdir(
            exist_ok=True,
        )

        joblib.dump(
            self.pipeline,
            MODEL_PATH,
        )

        print(
            f"\nModel saved to:\n{MODEL_PATH}"
        )


if __name__ == "__main__":

    trainer = IntentModelTrainer()

    trainer.train()