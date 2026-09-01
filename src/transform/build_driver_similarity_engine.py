import sys
import pandas as pd
from pathlib import Path

from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity

# Project root
ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT_DIR))

from src.utils.cli import get_year


def build_driver_similarity(year=2025):

    print(f"Project root: {ROOT_DIR}")

    processed_folder = (
        ROOT_DIR
        / "data"
        / "processed"
    )

    feature_matrix_file = (
        processed_folder
        / f"driver_feature_matrix_{year}.csv"
    )

    if not feature_matrix_file.exists():

        raise FileNotFoundError(
            f"Could not find "
            f"{feature_matrix_file}"
        )

    print(
        f"Loading "
        f"{feature_matrix_file.name}"
    )

    feature_matrix = pd.read_csv(
        feature_matrix_file
    )

    drivers = feature_matrix[
        "Driver"
    ]

    features = feature_matrix.drop(
        columns=["Driver"]
    )

    print(
        f"Scaling "
        f"{len(features.columns)} "
        f"features"
    )

    scaler = StandardScaler()

    scaled_features = (
        scaler.fit_transform(
            features
        )
    )

    print(
        "Computing cosine similarity"
    )

    similarity_matrix = (
        cosine_similarity(
            scaled_features
        )
    )

    similarity_df = pd.DataFrame(
        similarity_matrix,
        index=drivers,
        columns=drivers
    )

    all_similarity = []

    for driver in similarity_df.index:

        similarities = (
            similarity_df
            .loc[driver]
            .drop(driver)
            .sort_values(
                ascending=False
            )
        )

        top_match = (
            similarities.index[0]
        )

        similarity_score = (
            similarities.iloc[0]
        )

        all_similarity.append(
            {
                "Driver":
                    driver,
                "MostSimilarDriver":
                    top_match,
                "SimilarityScore":
                    similarity_score
            }
        )

    driver_similarity = pd.DataFrame(
        all_similarity
    )

    output_file = (
        processed_folder
        / f"driver_similarity_{year}.csv"
    )

    driver_similarity.to_csv(
        output_file,
        index=False
    )

    print("\n--------------------------------")
    print("Transformation complete")
    print(
        f"Created "
        f"{len(driver_similarity)} "
        f"driver similarity records"
    )
    print(
        f"Saved to "
        f"{output_file}"
    )


if __name__ == "__main__":
    year = get_year(default=2025)
    build_driver_similarity(year=year)
