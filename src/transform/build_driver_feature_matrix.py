import sys
import pandas as pd
from pathlib import Path

# Project root
ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT_DIR))

from src.utils.cli import get_year


def build_driver_feature_matrix(year=2025):

    print(f"Project root: {ROOT_DIR}")

    processed_folder = (
        ROOT_DIR
        / "data"
        / "processed"
    )

    race_metrics_file = (
        processed_folder
        / f"fact_driver_race_metrics_{year}.csv"
    )

    style_metrics_file = (
        processed_folder
        / f"fact_driver_style_metrics_{year}.csv"
    )

    braking_metrics_file = (
        processed_folder
        / f"fact_braking_metrics_{year}.csv"
    )

    tire_metrics_file = (
        processed_folder
        / f"fact_tire_degradation_{year}.csv"
    )

    required_files = [
        race_metrics_file,
        style_metrics_file,
        braking_metrics_file,
        tire_metrics_file
    ]

    for file in required_files:

        if not file.exists():

            raise FileNotFoundError(
                f"Could not find {file}"
            )

    print("Loading datasets")

    race_metrics = pd.read_csv(
        race_metrics_file
    )

    style_metrics = pd.read_csv(
        style_metrics_file
    )

    braking_metrics = pd.read_csv(
        braking_metrics_file
    )

    tire_metrics = pd.read_csv(
        tire_metrics_file
    )

    print(
        f"Loaded "
        f"{len(race_metrics)} race metrics"
    )

    print(
        f"Loaded "
        f"{len(style_metrics)} style metrics"
    )

    print(
        f"Loaded "
        f"{len(braking_metrics)} braking metrics"
    )

    print(
        f"Loaded "
        f"{len(tire_metrics)} tire metrics"
    )

    print(
        "\nBuilding pace features"
    )

    pace_features = (
        race_metrics
        .groupby(
            "Driver"
        )
        .agg(
            RelativePace=(
                "RelativePace",
                "mean"
            ),
            PaceStdDev=(
                "PaceStdDev",
                "mean"
            ),
            FastestLapDelta=(
                "FastestLapDelta",
                "mean"
            )
        )
        .reset_index()
    )

    print(
        "\nBuilding style features"
    )

    style_features = (
        style_metrics
        .groupby(
            "Driver"
        )
        .agg(
            FullThrottleRatio=(
                "FullThrottleRatio",
                "mean"
            ),
            BrakeUsageRatio=(
                "BrakeUsageRatio",
                "mean"
            ),
            GearChangeRate=(
                "GearChangeRate",
                "mean"
            )
        )
        .reset_index()
    )

    print(
        "\nBuilding braking features"
    )

    braking_features = (
        braking_metrics
        .groupby(
            "Driver"
        )
        .agg(
            AvgBrakeDistance=(
                "AvgBrakeDistance",
                "mean"
            ),
            AvgEntrySpeed=(
                "AvgEntrySpeed",
                "mean"
            ),
            AvgExitSpeed=(
                "AvgExitSpeed",
                "mean"
            ),
            AvgSpeedReduction=(
                "AvgSpeedReduction",
                "mean"
            )
        )
        .reset_index()
    )

    print(
        "\nBuilding tire features"
    )

    tire_features = (
        tire_metrics
        .groupby(
            "Driver"
        )
        .agg(
            DegradationRate=(
                "DegradationRate",
                "mean"
            ),
            PaceDropoff=(
                "PaceDropoff",
                "mean"
            )
        )
        .reset_index()
    )

    print(
        "\nMerging feature tables"
    )

    feature_matrix = (
        pace_features
        .merge(
            style_features,
            on="Driver",
            how="inner"
        )
        .merge(
            braking_features,
            on="Driver",
            how="inner"
        )
        .merge(
            tire_features,
            on="Driver",
            how="inner"
        )
    )

    print(
        f"Created "
        f"{len(feature_matrix)} "
        f"driver profiles"
    )

    output_file = (
        processed_folder
        / f"driver_feature_matrix_{year}.csv"
    )

    feature_matrix.to_csv(
        output_file,
        index=False
    )

    print("\n--------------------------------")
    print("Transformation complete")
    print(
        f"Saved to "
        f"{output_file}"
    )


if __name__ == "__main__":
    year = get_year(default=2025)
    build_driver_feature_matrix(year=year)
