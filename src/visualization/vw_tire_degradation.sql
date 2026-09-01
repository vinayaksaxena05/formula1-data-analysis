CREATE OR REPLACE VIEW vw_tire_degradation AS

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

    f.compound,
    f.stint,
    f.stint_length,

    f.avg_pace,
    f.first_three_avg,
    f.last_three_avg,
    f.pace_dropoff,
    f.degradation_rate

FROM fact_tire_degradation f

JOIN dim_seasons s
    ON f.season_key = s.season_key

JOIN dim_races r
    ON f.race_key = r.race_key

JOIN dim_drivers d
    ON f.driver_key = d.driver_key;