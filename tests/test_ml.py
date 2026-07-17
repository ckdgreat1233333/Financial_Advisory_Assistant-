from ml.intent_classifier import IntentClassifier


classifier = IntentClassifier()

queries = [
    "What documents are required for a home loan?",
    "Upload my salary slip.",
    "Why was my application rejected?",
    "Is this application high risk?",
    "Hello"
]

for query in queries:
    print(f"{query}")
    print(f"→ {classifier.predict(query)}")
    print()