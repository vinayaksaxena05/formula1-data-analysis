CREATE OR REPLACE VIEW vw_driver_race_performance AS

SELECT
    s.season,
    r.race_key,
    r.round_number,
    r.race,
    r.country,
    r.location,
    r.event_date,

    d.driver_key,
    d.abbreviation,
    d.full_name,

    f.representative_pace,
    f.relative_pace,
    f.fastest_lap_delta,
    f.pace_std_dev

FROM fact_driver_race_metrics f

JOIN dim_seasons s
    ON f.season_key = s.season_key

JOIN dim_races r
    ON f.race_key = r.race_key

JOIN dim_drivers d
    ON f.driver_key = d.driver_key;