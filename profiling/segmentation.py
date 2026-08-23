"""Embedding-based customer semantic segmentation.

Each customer profile summary is embedded with the same MiniLM model used for
document retrieval, then clustered with KMeans. Cluster labels are assigned by
ranking centroid feature statistics relative to the other clusters, so names
stay stable even when the overall data distribution shifts.
"""
from __future__ import annotations

import numpy as np


class CustomerSegmenter:

    def __init__(self, k: int = 5, random_state: int = 42):
        self.k = k
        self.random_state = random_state
        self.embedder = None
        self.labels: dict[str, str] = {}
        self.cluster_summaries: list[dict] = []

    def _ensure_embedder(self):
        if self.embedder is None:
            from advisory.embedder import Embedder
            self.embedder = Embedder()

    def fit(self, profiles: dict) -> "CustomerSegmenter":
        if not profiles:
            return self
        self._ensure_embedder()
        ids = sorted(profiles.keys())
        texts = [profiles[cid].summary_text() for cid in ids]
        embeddings = self.embedder.embed(texts)

        from sklearn.cluster import KMeans
        km = KMeans(n_clusters=self.k, n_init=10, random_state=self.random_state)
        cluster_ids = km.fit_predict(embeddings)

        stats = self._cluster_stats(profiles, ids, cluster_ids)
        labels_by_cluster = self._rank_based_labels(stats)
        self.cluster_summaries = [labels_by_cluster[c] for c in sorted(labels_by_cluster)]
        label_of = {c: labels_by_cluster[c]["label"] for c in labels_by_cluster}
        for cid, cl in zip(ids, cluster_ids):
            profiles[cid].segment = label_of[int(cl)]
            self.labels[cid] = profiles[cid].segment
        return self

    def _cluster_stats(self, profiles, ids, cluster_ids) -> dict:
        buckets: dict[int, list] = {}
        for cid, cl in zip(ids, cluster_ids):
            buckets.setdefault(int(cl), []).append(profiles[cid])
        stats = {}
        for cl, members in buckets.items():
            stats[cl] = {
                "size": len(members),
                "avg_age": float(np.mean([m.age for m in members])),
                "avg_savings_rate": float(np.mean([m.savings_rate for m in members])),
                "avg_buffer": float(np.mean([m.emergency_buffer_months for m in members])),
                "avg_investing": float(np.mean([m.investing_activity_score for m in members])),
            }
        return stats

    def _rank_based_labels(self, stats: dict) -> dict[int, dict]:
        clusters = sorted(stats.keys())
        n = len(clusters)
        pool = set(clusters)
        named: dict[int, str] = {}

        oldest = max(pool, key=lambda c: (stats[c]["avg_age"], c))
        if stats[oldest]["avg_age"] >= 45 and n >= 3:
            named[oldest] = "Pre-Retirement Preservers"
            pool.discard(oldest)

        if pool:
            top_saver = max(pool, key=lambda c: (stats[c]["avg_savings_rate"], c))
            rest_rates = [stats[c]["avg_savings_rate"] for c in pool if c != top_saver]
            if not rest_rates or stats[top_saver]["avg_savings_rate"] > float(np.median(rest_rates)):
                named[top_saver] = "High-Saving Wealth Builders"
                pool.discard(top_saver)

        if pool:
            young_agg = min(pool, key=lambda c: (-stats[c]["avg_investing"], stats[c]["avg_age"], -c))
            if stats[young_agg]["avg_age"] < stats[oldest]["avg_age"] - 5 or len(pool) <= 1:
                named[young_agg] = "Young Aggressive Accumulators" \
                    if stats[young_agg]["avg_age"] < 40 else "Engaged Investors"
                pool.discard(young_agg)

        if pool:
            strained = min(pool, key=lambda c: (stats[c]["avg_savings_rate"] + stats[c]["avg_buffer"] / 12, c))
            others = [stats[c]["avg_savings_rate"] + stats[c]["avg_buffer"] / 12
                      for c in pool if c != strained]
            if not others or (stats[strained]["avg_savings_rate"] + stats[strained]["avg_buffer"] / 12) < float(np.median(others)):
                named[strained] = "Cash-Strapped Family Builders"
                pool.discard(strained)

        used = {v for v in named.values()}
        fallbacks = ["Stable Middle-Income Savers", "Balanced Family Financiers",
                     "Emerging Steady Savers"]
        fi = 0
        for c in sorted(pool):
            while fi < len(fallbacks) and fallbacks[fi] in used:
                fi += 1
            label = fallbacks[fi] if fi < len(fallbacks) else f"Savers Group {c + 1}"
            named[c] = label
            used.add(label)
            fi += 1

        return {c: {"label": named[c], **{k: round(v, 3) for k, v in stats[c].items()}}
                for c in clusters}

    def describe_segments(self) -> list[dict]:
        return self.cluster_summaries


_default_segmenter: CustomerSegmenter | None = None


def get_segmenter(k: int = 5) -> CustomerSegmenter:
    """Lazily fitted singleton so API calls reuse one clustering."""
    global _default_segmenter
    if _default_segmenter is None:
        from profiling.profile_builder import ProfileBuilder
        profiles = ProfileBuilder().build_all()
        _default_segmenter = CustomerSegmenter(k=k).fit(profiles)
    return _default_segmenter
