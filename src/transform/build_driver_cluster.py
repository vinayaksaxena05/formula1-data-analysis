import pandas as pd
from pathlib import Path

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

# Project root
ROOT_DIR = Path(__file__).resolve().parents[2]


def build_driver_clusters(year=2025):

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

    print(
        f"Loaded "
        f"{len(feature_matrix)} "
        f"driver profiles"
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
        f" features"
    )

    scaler = StandardScaler()

    X = scaler.fit_transform(
        features
    )

    print(
        "Running KMeans clustering"
    )

    kmeans = KMeans(
        n_clusters=4,
        random_state=42,
        n_init=10
    )

    clusters = kmeans.fit_predict(
        X
    )

    driver_clusters = (
        feature_matrix[
            ["Driver"]
        ]
        .copy()
    )

    driver_clusters[
        "Cluster"
    ] = clusters

    print(
        f"Created "
        f"{driver_clusters['Cluster'].nunique()} "
        f"clusters"
    )

    print(
        "\nCluster Sizes"
    )

    print(
        driver_clusters[
            "Cluster"
        ].value_counts()
    )

    print(
        "\nBuilding cluster profiles"
    )

    cluster_profiles = (
        feature_matrix
        .copy()
    )

    cluster_profiles[
        "Cluster"
    ] = clusters

    cluster_summary = (
        cluster_profiles
        .groupby(
            "Cluster"
        )
        .mean(
            numeric_only=True
        )
        .reset_index()
    )

    print(
        "\nGenerating PCA coordinates"
    )

    pca = PCA(
        n_components=2
    )

    X_pca = pca.fit_transform(
        X
    )

    pca_df = pd.DataFrame(
        {
            "Driver":
                drivers,
            "Cluster":
                clusters,
            "PC1":
                X_pca[:, 0],
            "PC2":
                X_pca[:, 1]
        }
    )

    clusters_file = (
        processed_folder
        / f"driver_clusters_{year}.csv"
    )

    summary_file = (
        processed_folder
        / f"cluster_summary_{year}.csv"
    )

    pca_file = (
        processed_folder
        / f"driver_pca_{year}.csv"
    )

    driver_clusters.to_csv(
        clusters_file,
        index=False
    )

    cluster_summary.to_csv(
        summary_file,
        index=False
    )

    pca_df.to_csv(
        pca_file,
        index=False
    )

    print("\n--------------------------------")
    print("Transformation complete")

    print(
        f"Saved clusters to "
        f"{clusters_file}"
    )

    print(
        f"Saved cluster summary to "
        f"{summary_file}"
    )

    print(
        f"Saved PCA coordinates to "
        f"{pca_file}"
    )


if __name__ == "__main__":
    build_driver_clusters()