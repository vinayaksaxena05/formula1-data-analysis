from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]


def build_driver_race_telemetry_metrics(year=2025):

    print(f"Project root: {ROOT_DIR}")

    processed_folder = (
        ROOT_DIR
        / "data"
        / "processed"
    )

    braking_file = (
        processed_folder
        / f"fact_braking_metrics_{year}.csv"
    )

    style_file = (
        processed_folder
        / f"fact_driver_style_metrics_{year}.csv"
    )

    if not braking_file.exists():

        raise FileNotFoundError(
            f"Could not find {braking_file}"
        )

    if not style_file.exists():

        raise FileNotFoundError(
            f"Could not find {style_file}"
        )

    print("Loading braking metrics...")

    braking = pd.read_csv(braking_file)

    print("Loading driver style metrics...")

    style = pd.read_csv(style_file)

    merge_columns = [
        "Race",
        "Driver"
    ]

    telemetry = braking.merge(
        style,
        on=merge_columns,
        how="inner"
    )

    telemetry = telemetry[
        [
            "Race",
            "Driver",

            "AvgBrakeDistance",
            "AvgEntrySpeed",
            "AvgExitSpeed",
            "AvgSpeedReduction",

            "FullThrottleRatio",
            "BrakeUsageRatio",
            "GearChangeRate",
            "DRSUsageRatio"
        ]
    ]

    telemetry = (
        telemetry
        .sort_values(
            ["Race", "Driver"]
        )
        .reset_index(drop=True)
    )

    output_file = (
        processed_folder
        / f"fact_driver_race_telemetry_metrics_{year}.csv"
    )

    telemetry.to_csv(
        output_file,
        index=False
    )

    print("\n--------------------------------")

    print(
        f"Created {len(telemetry)} rows"
    )

    print(
        f"Saved to {output_file}"
    )


if __name__ == "__main__":

    build_driver_race_telemetry_metrics()