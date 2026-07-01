import pickle
import re
from typing import Optional

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline

_RULES: list[tuple[re.Pattern, str]] = [
    # Groceries
    (re.compile(r"lidl|biedronka|carrefour|auchan|tesco|aldi|kaufland|zabka"
                r"|aldi|delikatesy|piekarnia|warzywniak|rybny|mięsny"
                r"|lewitat|społem|stokrotka|dino|netto|groszek", re.I), "groceries"),
    # Dining
    (re.compile(r"restauracja|pizza|kfc|mcdonald|burger\s?king|kebab|sushi"
                r"|starbucks|costa\s?coffee|kawiarnia|bar\s|bistro"
                r"|obiad|kolacja|lunch|jedzenie|stołówka", re.I), "dining"),
    # Transport
    (re.compile(r"pkp|pks|uber|bolt|taxi|orlen|bp|shell|circle\s?k"
                r"|stacja\s?paliw|paliwo|ztm|parking|autostrada"
                r"|bilet|metro|tramwaj|bus|lot|palivo", re.I), "transport"),
    # Housing
    (re.compile(r"czynsz|rent|wynajem|najem|administracja"
                r"|fundusz\s?remont|mieszkanie|flat|apartment", re.I), "housing"),
    # Utilities
    (re.compile(r"tauron|pge|energa|orange|play|plus|t-mobile|vodafone"
                r"|internet|gaz|woda|śmieci|mpo|psg|mpwik|prąd"
                r"|telefon|abonament", re.I), "utilities"),
    # Healthcare
    (re.compile(r"apteka|dolek|przychodnia|szpital|dentysta|stomatolog"
                r"|okulista|lekarz|wizyta|badanie|rehabilitacja"
                r"|zdrowie|medycyna|recepta|lek.", re.I), "healthcare"),
    # Income
    (re.compile(r"wynagrodzenie|salary|pensja|płaca|przelew\s?wynagrodzenia"
                r"|umowa\s?zlecenie|freelance|kontrakt|zasiłek|dywidenda"
                r"|zwrot\s?podatku|dochód", re.I), "income"),
    # Shopping
    (re.compile(r"allegro|amazon|zalando|mediamarkt|rtv\s?euro\s?agd"
                r"|ikea|decathlon|h&m|reserved|empik|rossmann"
                r"|zakupy|odzież|buty|ecommerce|smyk|pepco", re.I), "shopping"),
    # Entertainment
    (re.compile(r"netflix|spotify|hbo|disney|cinema|kino|teatr|koncert"
                r"|siłownia|fitness|basen|sport|club|muzyka"
                r"|gry|gra|bilet", re.I), "entertainment"),
    # Education
    (re.compile(r"coursera|udemy|szkolenie|kurs|studia|uniwersytet"
                r"|podręcznik|edukacja|nauka|language|jezyk"
                r"|certyfikat|dyplom", re.I), "education"),
    # Transfer
    (re.compile(r"przelew\s?własny|transfer|przelew\s?między"
                r"|wpłata|wypłata|bankomat|gotówka|przychodzący"
                r"|wychodzący|elixir|sor|sepa", re.I), "transfer"),
]


class TransactionClassifier:
    """Scikit-learn pipeline for transaction category prediction.

    Combines:
    1. Rule-based matching (fast, deterministic)
    2. ML model (TF-IDF + LogisticRegression) trained on seed data
       and user-confirmed transactions

    Usage::

        clf = TransactionClassifier()
        clf.train()
        result = clf.predict("Lidl", "", -45.99)
        # {"slug": "groceries", "confidence": 0.92, "source": "rule"}
    """

    def __init__(self, seed_data: Optional[list[dict]] = None):
        self._seed = seed_data or []
        self._model: Optional[Pipeline] = None
        self._classes: list[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def train(self, additional_data: Optional[list[dict]] = None) -> None:
        """Fit the ML model on seed data plus any optional extra examples.

        Each item in *data* must have ``description``, ``counterparty``,
        ``amount`` (numeric), and ``category_slug`` keys.
        """
        data = list(self._seed)
        if additional_data:
            data.extend(additional_data)

        if not data:
            self._model = None
            self._classes = []
            return

        texts = [
            f"{d['description']} {d.get('counterparty', '')}".strip()
            for d in data
        ]
        labels = [d["category_slug"] for d in data]

        text_pipe = make_pipeline(
            TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 5),
                max_features=2000,
                min_df=1,
                sublinear_tf=True,
            ),
            LogisticRegression(C=10.0, max_iter=1000, class_weight="balanced"),
        )
        clf = CalibratedClassifierCV(text_pipe, cv=3, method="sigmoid")

        self._model = Pipeline([
            ("classifier", clf),
        ])
        self._model.fit(texts, labels)
        self._classes = list(clf.classes_) if hasattr(clf, "classes_") else sorted(set(labels))

    def predict(
        self,
        description: str,
        counterparty_name: Optional[str],
        amount: float,
    ) -> dict:
        """Predict category for a single transaction.

        Returns dict with keys:
          - ``slug``: predicted category slug
          - ``confidence``: float 0.0–1.0
          - ``source``: ``"rule"``, ``"ml"``, or ``None`` if no prediction
        """
        # 1. Try rule-based first
        rule_slug = self._apply_rules(description, counterparty_name)
        if rule_slug:
            return {"slug": rule_slug, "confidence": 0.95, "source": "rule"}

        # 2. Fall back to ML model
        if self._model is None or not self._classes:
            return {"slug": "other", "confidence": 0.0, "source": None}

        text = f"{description} {counterparty_name or ''}".strip()
        text_arr = [text]

        try:
            probs = self._model.predict_proba(text_arr)[0]
            idx = int(np.argmax(probs))
            slug = self._classes[idx]
            confidence = float(probs[idx])

            if confidence < 0.3:
                return {"slug": "other", "confidence": confidence, "source": None}

            return {"slug": slug, "confidence": confidence, "source": "ml"}
        except Exception:
            return {"slug": "other", "confidence": 0.0, "source": None}

    def predict_proba(self, text: str) -> dict[str, float]:
        """Return probability distribution over all known categories."""
        if self._model is None or not self._classes:
            return {}
        try:
            probs = self._model.predict_proba([text])[0]
            return dict(zip(self._classes, (float(p) for p in probs)))
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def dumps(self) -> bytes:
        """Serialize the trained model + classes to bytes."""
        payload = {"model": self._model, "classes": self._classes}
        return pickle.dumps(payload)

    @classmethod
    def loads(cls, data: bytes, seed_data: Optional[list[dict]] = None) -> "TransactionClassifier":
        """Deserialize from bytes returned by *dumps*."""
        clf = cls(seed_data=seed_data)
        payload = pickle.loads(data)
        clf._model = payload["model"]
        clf._classes = payload["classes"]
        return clf

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_rules(description: str, counterparty: Optional[str]) -> Optional[str]:
        combined = f"{description} {counterparty or ''}"
        for pattern, slug in _RULES:
            if pattern.search(combined):
                return slug
        return None


def train_default() -> TransactionClassifier:
    """Convenience factory: build a classifier trained on the built-in seed data."""
    from app.ml.seed_data import SEED_TRANSACTIONS
    clf = TransactionClassifier(seed_data=SEED_TRANSACTIONS)
    clf.train()
    return clf
