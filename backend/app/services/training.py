"""Leakage-safe model training shared by API training workflows."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from fastapi import HTTPException
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import (
    KFold,
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

MODEL_NAMES = (
    "linear",
    "tree",
    "forest",
    "boosting",
    "svm",
    "knn",
    "mlp",
)


def _model(name: str, task: str):
    normalized = name.strip().lower().replace("-", " ")
    normalized = {
        "linear regression": "linear",
        "logistic regression": "linear",
        "decision tree": "tree",
        "random forest": "forest",
        "gradient boosting": "boosting",
        "support vector machine": "svm",
        "k nearest neighbors": "knn",
        "k-nearest neighbors": "knn",
        "neural network (mlp)": "mlp",
    }.get(normalized, normalized)
    if normalized in {"auto", ""}:
        normalized = "forest"
    models = {
        "classification": {
            "linear": LogisticRegression(max_iter=1000, random_state=42),
            "tree": DecisionTreeClassifier(random_state=42),
            "forest": RandomForestClassifier(
                n_estimators=100, random_state=42, n_jobs=-1
            ),
            "boosting": GradientBoostingClassifier(n_estimators=100, random_state=42),
            "svm": SVC(probability=True, random_state=42),
            "knn": KNeighborsClassifier(n_neighbors=5),
            "mlp": MLPClassifier(max_iter=500, random_state=42),
        },
        "regression": {
            "linear": LinearRegression(),
            "tree": DecisionTreeRegressor(random_state=42),
            "forest": RandomForestRegressor(
                n_estimators=100, random_state=42, n_jobs=-1
            ),
            "boosting": GradientBoostingRegressor(n_estimators=100, random_state=42),
            "svm": SVR(),
            "knn": KNeighborsRegressor(n_neighbors=5),
            "mlp": MLPRegressor(max_iter=500, random_state=42),
        },
    }
    if normalized not in models[task]:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{name}'. Choose one of: {', '.join(MODEL_NAMES)}.",
        )
    return models[task][normalized], normalized


def _task_type(target: pd.Series, requested: str) -> str:
    if requested in {"classification", "regression"}:
        return requested
    if pd.api.types.is_numeric_dtype(target):
        return "classification" if target.nunique(dropna=True) <= 10 else "regression"
    return "classification"


def _preprocessor(x: pd.DataFrame) -> ColumnTransformer:
    numeric = x.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical = [column for column in x.columns if column not in numeric]
    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "onehot",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        ),
                    ]
                ),
                categorical,
            ),
        ],
        remainder="drop",
    )


def _can_stratify(y: pd.Series, test_size: float) -> bool:
    counts = y.value_counts()
    test_count = (
        int(np.ceil(len(y) * test_size)) if isinstance(test_size, float) else test_size
    )
    return len(counts) > 1 and counts.min() >= 2 and test_count >= len(counts)


def _metrics(task: str, y_true: Any, y_pred: Any) -> Dict[str, float]:
    if task == "classification":
        return {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(
                precision_score(y_true, y_pred, average="weighted", zero_division=0)
            ),
            "recall": float(
                recall_score(y_true, y_pred, average="weighted", zero_division=0)
            ),
            "f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        }
    mse = mean_squared_error(y_true, y_pred)
    return {
        "r2": float(r2_score(y_true, y_pred)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "mse": float(mse),
        "rmse": float(np.sqrt(mse)),
    }


def train_model(
    df: pd.DataFrame,
    x_columns: List[str],
    y_columns: List[str],
    model_name: str,
    task_type: str = "auto",
    test_size: float = 0.2,
    random_state: int = 42,
    cv_folds: int = 5,
) -> Dict[str, Any]:
    if len(y_columns) != 1:
        raise HTTPException(status_code=400, detail="Exactly one target is required")
    if len(df) < 10:
        raise HTTPException(status_code=400, detail="At least 10 rows are required")

    x_df = df[x_columns].copy()
    raw_target = df[y_columns[0]].copy()
    task = _task_type(raw_target, task_type)
    if task == "regression":
        target = pd.to_numeric(raw_target, errors="coerce")
        if target.isna().any():
            raise HTTPException(
                status_code=400,
                detail=f"Regression target '{y_columns[0]}' contains unparseable values.",
            )
    else:
        valid = raw_target.notna()
        x_df = x_df.loc[valid]
        raw_target = raw_target.loc[valid]
        target = raw_target.astype("string")

    if len(target) < 10:
        raise HTTPException(status_code=400, detail="Not enough valid target rows")

    estimator, resolved_model = _model(model_name, task)
    pipeline = Pipeline([("preprocess", _preprocessor(x_df)), ("model", estimator)])
    stratify = (
        target
        if task == "classification" and _can_stratify(target, test_size)
        else None
    )
    x_train, x_test, y_train, y_test = train_test_split(
        x_df,
        target,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify,
    )

    started = time.perf_counter()
    pipeline.fit(x_train, y_train)
    training_time = float(time.perf_counter() - started)
    y_pred = pipeline.predict(x_test)
    metrics = _metrics(task, y_test, y_pred)

    cv_std = None
    if cv_folds and cv_folds >= 2:
        folds = min(cv_folds, len(y_train))
        if task == "classification":
            class_counts = y_train.value_counts()
            folds = min(folds, int(class_counts.min()))
        if folds >= 2:
            splitter = (
                StratifiedKFold(folds, shuffle=True, random_state=random_state)
                if task == "classification"
                else KFold(folds, shuffle=True, random_state=random_state)
            )
            scores = cross_val_score(
                pipeline,
                x_train,
                y_train,
                cv=splitter,
                scoring="accuracy" if task == "classification" else "r2",
            )
            metrics["cv_mean"] = float(np.mean(scores))
            metrics["cv_std"] = float(np.std(scores))
            cv_std = metrics["cv_std"]

    return {
        "pipeline": pipeline,
        "task_type": task,
        "model_name": resolved_model,
        "metrics": metrics,
        "cv_std": cv_std,
        "total_rows": int(len(df)),
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "feature_count": int(len(x_columns)),
        "x_columns": x_columns,
        "y_columns": y_columns,
        "training_time": training_time,
        "stratified": stratify is not None,
    }
