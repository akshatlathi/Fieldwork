"""Small model classes shared by training and runtime (so saved heads load anywhere)."""

import numpy as np
from sklearn.linear_model import LogisticRegression


class OrdinalHead:
    """K-1 threshold classifiers; P(y=k) from differences of P(y>k)."""

    def __init__(self, levels: list[int], C: float = 1.0):
        self.levels = levels
        self.models = [LogisticRegression(C=C, max_iter=2000) for _ in levels[:-1]]

    def fit(self, X, y):
        for k, m in zip(self.levels[:-1], self.models):
            m.fit(X, (y > k).astype(int))
        return self

    def proba(self, X) -> np.ndarray:
        gt = np.column_stack([m.predict_proba(X)[:, 1] for m in self.models])  # P(y > k)
        gt = np.minimum.accumulate(gt, axis=1)  # keep thresholds monotone
        p = np.column_stack([1 - gt[:, 0], gt[:, :-1] - gt[:, 1:], gt[:, -1]])
        p = np.clip(p, 1e-6, None)
        return p / p.sum(axis=1, keepdims=True)


class SoftmaxHead:
    """Multiclass logistic alternative with the same runtime probability interface."""

    def __init__(self, levels: list[int], C: float = 1.0):
        self.levels = levels
        self.model = LogisticRegression(C=C, max_iter=2000)

    def fit(self, X, y):
        self.model.fit(X, y)
        return self

    def proba(self, X):
        p = np.zeros((len(X), len(self.levels)))
        predicted = self.model.predict_proba(X)
        for j, label in enumerate(self.model.classes_):
            p[:, self.levels.index(int(label))] = predicted[:, j]
        return p
