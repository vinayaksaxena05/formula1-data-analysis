CREATE OR REPLACE VIEW vw_championship AS
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

    f.position,
    f.points,
    f.cumulative_points,
    f.championship_position

FROM fact_championship_standings f

JOIN dim_seasons s
    ON f.season_key = s.season_key

JOIN dim_races r
    ON f.race_key = r.race_key

JOIN dim_drivers d
    ON f.driver_key = d.driver_key;