# Formula 1 Telemetry Data Platform

An end-to-end **Formula 1 data engineering and analytics platform** built around FastF1 telemetry and race data.

The project ingests Formula 1 session data, transforms it into analytical datasets, loads it into a **PostgreSQL data warehouse**, exposes curated SQL views for analytics, validates the warehouse, and feeds the resulting data into Power BI.

The goal is not just to build F1 dashboards. It is to demonstrate how a real-world data pipeline can move from raw motorsport data to a structured analytical platform.

---

## Architecture

```text
                         Formula 1 Data
                              │
                              ▼
                         ┌──────────┐
                         │ FastF1   │
                         └────┬─────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │    Extraction    │
                    │ Python + FastF1  │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Transformation  │
                    │ Pandas + NumPy  │
                    └────────┬─────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ PostgreSQL Warehouse │
                  │                      │
                  │ Dimensions + Facts   │
                  └──────────┬───────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Analytical Views │
                    │       SQL        │
                    └────────┬─────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
             ┌─────────────┐   ┌──────────────┐
             │ Data Quality│   │   Power BI   │
             │ Validation  │   │  Dashboards  │
             └─────────────┘   └──────────────┘
```

The pipeline is orchestrated through `run_pipeline.py`, with lightweight pipeline-state caching to avoid unnecessarily re-running completed stages.

---

## Why this project?

Formula 1 produces an unusually rich combination of structured race data and high-frequency telemetry. That makes it a useful environment for exploring data engineering concepts at multiple levels of granularity.

The platform brings together:

- API-based data extraction
- ETL and feature engineering
- Relational data warehousing
- Dimensional modeling
- Race- and driver-level analytical facts
- SQL-based semantic views
- Data quality validation
- Pipeline orchestration and caching
- Motorsport analytics and machine learning
- Business intelligence through Power BI

---

## Technology Stack

| Layer | Technology |
|---|---|
| Data source | FastF1 |
| Language | Python |
| Data processing | Pandas, NumPy |
| Machine learning | scikit-learn |
| Data warehouse | PostgreSQL |
| Database access | psycopg2 |
| Configuration | python-dotenv |
| Analytics layer | PostgreSQL SQL views |
| BI | Power BI |
| Development | Git, GitHub, Jupyter |

Dependencies are maintained in [`requirements.txt`](requirements.txt).

---

# Data Pipeline

The pipeline is executed from the repository root using `run_pipeline.py`.

```text
1. Extract
      ↓
2. Transform
      ↓
3. Create / Load Dimensions
      ↓
4. Create / Load Facts
      ↓
5. Create Analytical Views
      ↓
6. Validate Data Quality
```

### 1. Extraction

FastF1 is used to retrieve Formula 1 race and telemetry data for the selected season.

Current extraction components include:

- Race/session data
- Driver telemetry
- Lap and session information
- Race results and related metadata

FastF1's own caching mechanism is used to reduce repeated upstream downloads.

### 2. Transformation

Raw extracted data is converted into analytical datasets using Python and Pandas.

Transformations currently cover:

- Season dimension
- Team dimension
- Driver dimension
- Race dimension
- Championship standings
- Driver braking metrics
- Driver pace metrics
- Driver race telemetry metrics
- Driver stints
- Pit stop summaries
- Tire degradation analysis

Additional analytical transformations support driver feature engineering, similarity analysis, and clustering.

### 3. Warehouse Loading

The transformed datasets are loaded into PostgreSQL using a dimensional warehouse design.

The warehouse separates relatively stable descriptive entities into dimensions and measurable analytical events into fact tables.

### 4. Analytical Views

PostgreSQL views provide a cleaner analytical layer for downstream reporting.

Current views include:

- `vw_championship`
- `vw_driver_race_performance`
- `vw_driver_style`
- `vw_driver_telemetry`
- `vw_pitstops`
- `vw_tire_degradation`

### 5. Data Quality Validation

The pipeline includes automated validation after view creation.

Validation checks include:

- Dimension and fact table population
- Analytical view population
- Required warehouse keys
- Foreign-key integrity checks
- Season presence
- Expected race coverage
- Duplicate race/driver grains
- Basic pipeline completeness

---

# Pipeline Usage

Run the pipeline from the project root:

```bash
python run_pipeline.py
```

If no year is supplied, the pipeline prompts for the season and defaults to `2025`.

The resolved year is passed explicitly to each child pipeline stage so the individual scripts operate on the same season.

To run a specific season without the interactive prompt:

```bash
python run_pipeline.py 2025
```

To force every pipeline stage to run regardless of cached state:

```bash
python run_pipeline.py 2025 --force
```

The pipeline records completed stages in:

```text
.pipeline/state.json
```

This is separate from FastF1's cache. FastF1 caching prevents unnecessary upstream downloads, while the project pipeline cache prevents unnecessary re-execution of completed ETL stages.

> **Note:** Pipeline caching is intentionally lightweight. Dependency-aware invalidation and more advanced lineage/fingerprint handling are planned improvements.

---

# Data Warehouse

The PostgreSQL warehouse follows a dimensional modeling approach.

## Dimension Tables

### `dim_seasons`

Stores season-level identifiers.

- `season_key`
- `season`

### `dim_teams`

Stores constructor/team information.

- Team identifier
- Team name
- Team attributes used by the analytical model

### `dim_drivers`

Stores driver-level descriptive attributes.

Team membership is not treated as a permanent driver attribute because drivers can change teams across seasons.

### `dim_races`

Stores race/event-level descriptive information including season and round context.

---

## Fact Tables

### `fact_championship_standings`

Season championship standings and points-related metrics.

### `fact_driver_race_metrics`

Race-level driver performance and pace metrics.

### `fact_driver_race_telemetry_metrics`

Race-level telemetry-derived driver metrics.

### `fact_driver_stints`

Driver stint and tire information across races.

### `fact_pitstops`

Pit stop information and derived pit stop metrics.

### `fact_tire_degradation`

Tire degradation metrics derived from stint and lap data.

### `fact_braking_metrics`

Driver braking characteristics derived from telemetry.

### `fact_driver_style_metrics`

Driver-level driving style metrics used for comparative analysis.

---

# Analytical Layer

The platform currently supports several categories of analysis.

## Championship Analysis

Analyze season standings and race-by-race championship progression.

## Race Performance

Compare drivers across races using pace and performance metrics.

## Telemetry Analysis

Explore telemetry-derived characteristics including:

- Speed
- Throttle
- Brake usage
- Gear
- RPM
- DRS
- Distance

## Braking Analysis

Analyze driver braking behavior using telemetry-derived metrics such as braking distance, braking duration, deceleration, and related corner-entry characteristics.

## Driving Style Analysis

Build driver profiles from telemetry and performance features to compare how drivers approach acceleration, braking, and cornering.

## Tire Degradation

Analyze degradation patterns across driver stints and tire compounds.

## Pit Stop Analysis

Compare pit stop performance and race-level pit stop behavior.

---

# Machine Learning & Driver Analytics

The project also contains a small machine learning / analytical layer built on top of the engineered driver features.

### Driver Feature Matrix

Driver-level features combine multiple aspects of performance and telemetry-derived behavior.

### Driver Similarity

Driver profiles can be standardized and compared using similarity metrics such as cosine similarity.

### Driver Clustering

K-Means clustering is used to group drivers based on engineered performance and telemetry characteristics.

This layer is intentionally separated from the core warehouse pipeline so that machine learning experiments can evolve without coupling them to the ingestion and storage architecture.

---

# Power BI

Power BI sits downstream of the PostgreSQL analytical layer.

The reporting layer is designed around curated SQL views rather than directly exposing every raw warehouse table.

Current analytical areas include:

- Championship standings
- Driver race performance
- Driver telemetry
- Driving style
- Pit stops
- Tire degradation

This keeps the BI layer focused on analysis while the warehouse remains responsible for structured storage and transformation.

---

# Project Structure

```text
formula1-data-analysis/
│
├── data/
│   └── processed/
│
├── notebooks/
│
├── src/
│   ├── extract/
│   │   ├── driver_telemetry.py
│   │   └── race_data.py
│   │
│   ├── transform/
│   │   ├── build_season_dimension.py
│   │   ├── build_team_dimension.py
│   │   ├── build_driver_dimension.py
│   │   ├── build_race_dimension.py
│   │   ├── build_championship_standings.py
│   │   ├── build_driver_braking_metrics.py
│   │   ├── build_driver_pace_metrics.py
│   │   ├── build_driver_race_telemetry_metrics.py
│   │   ├── build_driver_stints.py
│   │   ├── build_pitstop_summary.py
│   │   ├── build_tire_degradation_analysis.py
│   │   ├── build_driver_feature_matrix.py
│   │   ├── build_driver_similarity_engine.py
│   │   └── build_driver_cluster.py
│   │
│   ├── load/
│   │   ├── connection.py
│   │   ├── create_dimensions.py
│   │   ├── load_dimensions.py
│   │   ├── create_facts.py
│   │   ├── load_facts.py
│   │   ├── create_views.py
│   │   └── validate_pipeline.py
│   │
│   ├── visualization/
│   │   └── *.sql
│   │
│   └── utils/
│       ├── cli.py
│       ├── pipeline_cache.py
│       └── schedule.py
│
├── .pipeline/
├── .env
├── requirements.txt
├── run_pipeline.py
├── CHANGELOG.md
└── README.md
```

> `.env`, `.pipeline/`, Python cache files, and other local/generated artifacts should remain excluded from version control.

---

# Configuration

PostgreSQL connection details are loaded from environment variables using `python-dotenv`.

Create a local `.env` file containing the database configuration expected by `src/load/connection.py`.

Example structure:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database
DB_USER=your_user
DB_PASSWORD=your_password
```

Do **not** commit real credentials to GitHub.

---

# Data Model at a Glance

```text
                  ┌──────────────┐
                  │  dim_seasons │
                  └──────┬───────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
       ┌───────────┐ ┌─────────┐ ┌───────────┐
       │ dim_races │ │dim_drivers││ dim_teams │
       └─────┬─────┘ └────┬────┘ └─────┬─────┘
             │             │            │
             └─────────────┼────────────┘
                           ▼
                 ┌──────────────────┐
                 │   Fact Tables    │
                 │                  │
                 │ Race Metrics     │
                 │ Telemetry        │
                 │ Stints           │
                 │ Pit Stops        │
                 │ Tire Degradation │
                 │ Braking          │
                 │ Style Metrics    │
                 │ Championship     │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Analytical Views │
                 └──────────────────┘
```

---

# Current Status

| Component | Status |
|---|---|
| FastF1 extraction | ✅ Complete |
| Python transformations | ✅ Complete |
| PostgreSQL warehouse | ✅ Complete |
| Dimension tables | ✅ Complete |
| Fact tables | ✅ Complete |
| Analytical SQL views | ✅ Complete |
| Data quality validation | ✅ Complete |
| Pipeline orchestration | ✅ Complete |
| Basic pipeline caching | ✅ Complete |
| Driver similarity analysis | ✅ Complete |
| Driver clustering | ✅ Complete |
| Power BI analytical layer | ✅ Complete |
| Dependency-aware cache invalidation | 🚧 Planned |
| Automated unit/integration tests | 🚧 Planned |
| Apache Airflow orchestration | 🚧 Planned |
| CI/CD | 🚧 Planned |
| Cloud deployment | 🔭 Future |

---

# Roadmap

The next engineering improvements are focused on making the platform more production-like rather than simply adding more dashboards.

### 1. Dependency-aware pipeline caching

Move beyond independent stage flags and invalidate downstream stages when their inputs or transformation logic changes.

### 2. Automated testing

Add unit and integration tests for transformations, warehouse loading, analytical grains, and data quality checks.

### 3. Apache Airflow

Move orchestration from the local Python runner into an explicit DAG-based workflow with task dependencies, retries, scheduling, and observability.

### 4. CI/CD

Run automated tests and validation through GitHub Actions before changes are merged.

### 5. Cloud deployment

Evaluate moving the warehouse and orchestration stack to cloud infrastructure once the local pipeline is stable.

---

# What this project demonstrates

### Data Engineering

- API-based data ingestion
- ETL pipeline development
- Dimensional data modeling
- PostgreSQL data warehousing
- Analytical SQL
- Pipeline orchestration
- Data quality validation
- Pipeline caching

### Analytics

- Feature engineering
- Telemetry analysis
- Driver performance analysis
- Tire degradation analysis
- Braking analysis
- Similarity analysis
- Machine learning clustering

### Business Intelligence

- Analytical data modeling
- SQL semantic views
- Power BI reporting
- KPI and comparative analysis

---

# Author

**Vinayak Saxena**

Computer Science Undergraduate | Data Engineering & Analytics

This project explores the intersection of **data engineering, analytics, machine learning, and motorsport telemetry** using real-world Formula 1 data.

---

## Data Source

This project uses the [FastF1](https://github.com/theOehrly/Fast-F1) Python library to access Formula 1 timing, telemetry, session, and related motorsport data.

Formula 1 data is used for educational, analytical, and portfolio purposes.
