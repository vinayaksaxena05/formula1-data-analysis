import pandas as pd
from pathlib import Path

# Project root
ROOT_DIR = Path(__file__).resolve().parents[2]


def build_driver_style_metrics(year=2025):

    print(f"Project root: {ROOT_DIR}")

    raw_folder = (
        ROOT_DIR
        / "data"
        / "raw"
        / str(year)
    )

    print(f"Raw folder: {raw_folder}")

    if not raw_folder.exists():

        raise FileNotFoundError(
            f"Could not find {raw_folder}"
        )

    races = [
        race
        for race in raw_folder.iterdir()
        if race.is_dir()
    ]

    print(f"Found {len(races)} races")

    all_driver_metrics = []

    for race_folder in races:

        race_name = race_folder.name

        print("\n--------------------------------")
        print(f"Processing {race_name}")

        telemetry_folder = (
            race_folder
            / "telemetry"
        )

        if not telemetry_folder.exists():

            print(
                f"Skipping {race_name} "
                f"(telemetry folder not found)"
            )

            continue

        drivers = [
            driver
            for driver in telemetry_folder.iterdir()
            if driver.suffix == ".csv"
        ]

        print(
            f"Found {len(drivers)} "
            f"driver telemetry files"
        )

        for driver in drivers:

            driver_name = (
                driver.name
                .replace(".csv", "")
            )

            telemetry = pd.read_csv(
                driver
            )

            required_columns = [
                "Throttle",
                "Brake",
                "nGear",
                "Speed",
                "DRS"
            ]

            missing_columns = [
                col
                for col in required_columns
                if col not in telemetry.columns
            ]

            if missing_columns:

                print(
                    f"Skipping {driver_name} "
                    f"(missing columns: "
                    f"{missing_columns})"
                )

                continue

            full_throttle_ratio = (
                telemetry["Throttle"] >= 95
            ).mean()

            brake_usage_ratio = (
                telemetry["Brake"] > 0
            ).mean()

            braking_samples = telemetry[
                telemetry["Brake"] > 0
            ]

            avg_brake = (
                braking_samples["Brake"]
                .mean()
            )

            avg_gear = (
                telemetry["nGear"]
                .mean()
            )

            gear_change_rate = (
                telemetry["nGear"]
                .diff()
                .abs()
                .sum()
                / len(telemetry)
            )

            avg_speed = (
                telemetry["Speed"]
                .mean()
            )

            top_speed = (
                telemetry["Speed"]
                .max()
            )

            drs_usage_ratio = (
                telemetry["DRS"] > 0
            ).mean()

            all_driver_metrics.append(
                {
                    "Race": race_name,
                    "Driver": driver_name,
                    "FullThrottleRatio":
                        full_throttle_ratio,
                    "BrakeUsageRatio":
                        brake_usage_ratio,
                    "AvgBrake":
                        avg_brake,
                    "AvgGear":
                        avg_gear,
                    "GearChangeRate":
                        gear_change_rate,
                    "AvgSpeed":
                        avg_speed,
                    "TopSpeed":
                        top_speed,
                    "DRSUsageRatio":
                        drs_usage_ratio
                }
            )

        print(
            f"Finished {race_name}"
        )

    if len(all_driver_metrics) == 0:

        raise ValueError(
            "No driver style metrics generated"
        )

    driver_style_metrics = pd.DataFrame(
        all_driver_metrics
    )

    output_folder = (
        ROOT_DIR
        / "data"
        / "processed"
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        output_folder
        / f"fact_driver_style_metrics_{year}.csv"
    )

    driver_style_metrics.to_csv(
        output_file,
        index=False
    )

    print("\n--------------------------------")
    print("Transformation complete")
    print(
        f"Created "
        f"{len(driver_style_metrics)} "
        f"records"
    )
    print(
        f"Saved to "
        f"{output_file}"
    )


if __name__ == "__main__":
    build_driver_style_metrics()