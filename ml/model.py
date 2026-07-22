from pathlib import Path

import torch
import torch.nn as nn
import pandas as pd
import joblib
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from ml.preprocess import TextPreprocessor
from utils.enums import IntentType


BASE_DIR = Path(__file__).resolve().parent.parent

DATASET_PATH = BASE_DIR / "data" / "intents" / "intents.csv"

MODEL_PATH = BASE_DIR / "trained_models" / "intent_classifier.pth"
TOKENIZER_PATH = BASE_DIR / "trained_models" / "intent_classifier_tokenizer.pkl"


class IntentTransformerClassifier(nn.Module):

    def __init__(self, model_name="distilbert-base-uncased", num_classes=5):
        super().__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(0.3)
        self.classifier = nn.Linear(self.bert.config.hidden_size, num_classes)

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = outputs.pooler_output
        pooled_output = self.dropout(pooled_output)
        return self.classifier(pooled_output)


class IntentModelTrainer:

    def __init__(self, model_name="distilbert-base-uncased"):
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

    def load_dataset(self):

        dataframe = pd.read_csv(DATASET_PATH)

        dataframe["text"] = dataframe["text"].apply(
            TextPreprocessor.clean
        )

        return dataframe

    def encode_labels(self, labels):

        id_to_label = {i: label for i, label in enumerate(IntentType)}
        label_to_id = {label.value: i for i, label in enumerate(IntentType)}

        encoded = [label_to_id[label] for label in labels]
        return encoded, label_to_id

    def train(self):

        dataframe = self.load_dataset()

        X = dataframe["text"].tolist()
        y = dataframe["intent"].tolist()

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        train_encodings = self._tokenize_batch(X_train)
        test_encodings = self._tokenize_batch(X_test)

        from torch.utils.data import DataLoader, TensorDataset

        train_labels, label_to_id = self.encode_labels(y_train)
        test_labels, _ = self.encode_labels(y_test)

        train_dataset = TensorDataset(
            torch.tensor(train_encodings["input_ids"]),
            torch.tensor(train_encodings["attention_mask"]),
            torch.tensor(train_labels),
        )
        test_dataset = TensorDataset(
            torch.tensor(test_encodings["input_ids"]),
            torch.tensor(test_encodings["attention_mask"]),
            torch.tensor(test_labels),
        )

        train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=16)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        model = IntentTransformerClassifier(num_classes=5).to(device)
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5)

        epochs = 3

        for epoch in range(epochs):
            model.train()
            total_loss = 0

            for batch in train_loader:
                input_ids, attention_mask, labels = [b.to(device) for b in batch]

                optimizer.zero_grad()

                outputs = model(input_ids, attention_mask)

                loss = criterion(outputs, labels)
                total_loss += loss.item()

                loss.backward()
                optimizer.step()

            avg_loss = total_loss / len(train_loader)
            print(f"Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.4f}")

        model.eval()

        with torch.no_grad():
            predictions = []
            true_labels = []

            for batch in test_loader:
                input_ids, attention_mask, labels = [b.to(device) for b in batch]

                outputs = model(input_ids, attention_mask)
                _, predicted = torch.max(outputs, 1)

                predictions.extend(predicted.cpu().numpy())
                true_labels.extend(labels.cpu().numpy())

        from sklearn.metrics import classification_report

        id_to_label = {v: k for k, v in label_to_id.items()}
        pred_labels = [id_to_label[p] for p in predictions]
        true_labels_str = [id_to_label[l] for l in true_labels]

        print("\nClassification Report:")
        print(
            classification_report(
                true_labels_str,
                pred_labels,
                target_names=list(IntentType),
            )
        )

        MODEL_PATH.parent.mkdir(
            exist_ok=True,
        )

        torch.save({
            "model_state_dict": model.state_dict(),
            "model_name": self.model_name,
            "label_to_id": label_to_id,
            "id_to_label": id_to_label,
        }, MODEL_PATH)

        joblib.dump(self.tokenizer, TOKENIZER_PATH)

        print(f"\nModel saved to:\n{MODEL_PATH}")
        print(f"Tokenizer saved to:\n{TOKENIZER_PATH}")

    def _tokenize_batch(self, texts, max_length=128):

        encodings = self.tokenizer(
            texts,
            max_length=max_length,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )

        return encodings.to_dict()


if __name__ == "__main__":

    trainer = IntentModelTrainer()

    trainer.train()