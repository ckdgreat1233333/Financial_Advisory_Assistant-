"""Customer profiling pipeline.

Turns raw customer rows + transaction history into a feature-rich
CustomerProfile used by segmentation, the suitability engine and the LLM.
"""
from models.advisory import CustomerProfile  # noqa: F401  (re-export)
