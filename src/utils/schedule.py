import fastf1


def get_race_folder_name(event_name):
    """Derive the raw-data folder name used for an event, matching the
    naming convention applied during extraction (src/extract/*.py)."""

    race_name = event_name.replace(" Grand Prix", "")

    return race_name.lower().replace(" ", "_")


def get_round_map(year):
    """Return {folder_name: RoundNumber} for a season, sourced from the
    FastF1 event schedule so downstream transforms never have to infer
    chronological race order from filesystem iteration order."""

    schedule = fastf1.get_event_schedule(year)

    races = schedule[schedule["EventName"] != "Pre-Season Testing"]

    round_map = {}

    for _, row in races.iterrows():

        folder_name = get_race_folder_name(row["EventName"])

        round_map[folder_name] = int(row["RoundNumber"])

    return round_map
