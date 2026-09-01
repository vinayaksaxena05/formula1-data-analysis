CREATE OR REPLACE VIEW vw_driver_telemetry AS

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

    f.avg_brake_distance,
    f.avg_entry_speed,
    f.avg_exit_speed,
    f.avg_speed_reduction,
    f.full_throttle_ratio,
    f.brake_usage_ratio,
    f.gear_change_rate,
    f.drs_usage_ratio

FROM fact_driver_race_telemetry_metrics f

JOIN dim_seasons s
    ON f.season_key = s.season_key

JOIN dim_races r
    ON f.race_key = r.race_key

JOIN dim_drivers d
    ON f.driver_key = d.driver_key;