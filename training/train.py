from pathlib import Path

import joblib
import pandas as pd  # type: ignore
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


def load_data() -> pd.DataFrame:
    data_path = Path("data/raw_data/results.csv")  # type: ignore
    df = pd.read_csv(data_path)
    return df


def preprocess(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:

    df["Top10"] = (df["Position"] <= 10).astype(int)

    features = [
        "Season",
        "Round",
        "CircuitID",
        "DriverID",
        "ConstructorName",
        "Grid",
    ]

    target = "Top10"

    X = df[features]

    y = df[target]

    return X, y


def main():

    df = load_data()

    X, y = preprocess(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y
    )
    """
    print(f" X_train Shape : {X_train.shape}")
    print(f" X_test Shape : {X_test.shape}")
    print(f" y_train Shape : {y_train.shape}")
    print(f" y_test Shape : {y_test.shape}")
    """

    categorical_features = [
        "CircuitID",
        "DriverID",
        "ConstructorName",
    ]

    """
    numerical_features = [
        "Season",
        "Round",
        "Grid",
    ]
    """

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore"),
                categorical_features,
            ),
        ],
        remainder="passthrough",
    )

    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", RandomForestClassifier(random_state=42)),
        ]
    )

    model.fit(X_train, y_train)

    """
    feature_names = model.named_steps["preprocessor"].get_feature_names_out()
    importances = model.named_steps["classifier"].feature_importances_

    importance_df = pd.DataFrame(
        {
        "Feature": feature_names,
        "Importance": importances,
        }
    )

    importance_df = importance_df.sort_values(
    by="Importance",
    ascending=False,
    )

    print("\nTop 20 Most Important Features")

    print(importance_df.head(20))
    """

    print("Training Model completed !!! \n")

    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)

    print(f"accuracy : {accuracy:.4f}")

    print("\n Classification report ")
    print(classification_report(y_test, y_pred))

    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)
    joblib.dump(model, artifacts_dir / "model.pkl")
    print("Model Saved Succesfully !")


if __name__ == "__main__":
    main()
