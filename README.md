# Formula 1 Telemetry Analytics Platform

## Project Overview

The Formula 1 Telemetry Analytics Platform is an end-to-end data engineering, analytics, and business intelligence project built using FastF1, Python, SQL, and Power BI.

The project collects Formula One race and telemetry data through the FastF1 API, processes and transforms the data using ETL pipelines, stores it in a relational database, and presents actionable insights through interactive Power BI dashboards.

The platform aims to answer key questions regarding driver performance, driving styles, race strategy, consistency, and the impact of Formula One regulation changes.

---

# Project Objectives

## Primary Objective

To build a complete Formula One analytics ecosystem capable of ingesting telemetry and race data, transforming it into analytical datasets, and generating meaningful performance insights through interactive dashboards.

---

## Technical Objectives

### Data Engineering

* Develop automated data ingestion pipelines using FastF1.
* Create ETL workflows for data extraction, transformation, and loading.
* Design and implement a relational database for Formula One analytics.
* Build analytical data models optimized for business intelligence reporting.

### Analytics

* Analyze race pace and qualifying performance trends.
* Compare driving styles using telemetry metrics.
* Investigate braking and cornering behavior.
* Evaluate consistency and race performance across drivers.
* Quantify the impact of Formula One regulation changes.

### Business Intelligence

* Develop interactive Power BI dashboards.
* Create KPI-driven reports for race and driver performance.
* Enable dynamic filtering by season, circuit, team, and driver.

---

# Research Questions

## 1. Regulation Impact Analysis

### Research Question

How have the 2026 Formula One regulations influenced race and qualifying performance compared to the 2025 season?

### Metrics

* Pole Position Lap Time
* Average Race Pace
* Qualifying Pace
* Race Pace Differential
* Sector Performance
* Tire Degradation

### Expected Insights

* Performance evolution between seasons
* Team adaptation effectiveness
* Changes in race competitiveness

---

## 2. Driver Braking Analysis

### Research Question

How do braking characteristics vary among Formula One drivers?

### Metrics

* Braking Distance
* Braking Duration
* Deceleration Rate
* Corner Entry Speed
* Downshift Locations

### Expected Insights

* Late braking tendencies
* Aggressive versus conservative approaches
* Driver adaptation patterns

---

## 3. Driving Style Analysis

### Research Question

How do leading Formula One drivers differ in driving style?

### Metrics

* Speed Profiles
* Throttle Application
* Brake Usage
* Gear Selection
* Corner Entry Speed
* Corner Exit Speed

### Expected Insights

* Driver-specific driving characteristics
* Cornering strategies
* Acceleration and braking patterns

---

## 4. Driver Similarity Engine

### Research Question

Which drivers exhibit the most similar performance and driving characteristics?

### Methodology

Driver profiles are generated using telemetry and performance metrics.

Similarity measures include:

* Cosine Similarity
* Euclidean Distance

### Output

* Driver Similarity Rankings
* Driver Clusters
* Style-Based Comparisons

### Applications

* Driver Profiling
* Talent Identification
* Performance Benchmarking

---

# System Architecture

```text
FastF1 API
    ↓
Raw Data Layer
    ↓
ETL Pipeline (Python + Pandas)
    ↓
SQLite Database
    ↓
Analytics Tables
    ↓
Power BI Data Model
    ↓
Interactive Dashboards
```

---

# Technology Stack

## Data Collection

* FastF1

## Programming

* Python

## Data Processing

* Pandas
* NumPy

## Database

* SQLite

## Visualization & BI

* Power BI

## Data Visualization

* Matplotlib
* Plotly

## Development Tools

* Git
* GitHub
* Jupyter Notebook

---

# Data Sources

The project utilizes official Formula One timing and telemetry data accessible through FastF1.

## Session Data

* Race Sessions
* Qualifying Sessions
* Sprint Sessions
* Practice Sessions

## Lap Data

* Lap Times
* Sector Times
* Tire Compounds
* Stints
* Position Data

## Telemetry Data

* Speed
* Gear Selection
* Throttle Application
* Brake Usage
* RPM
* DRS Usage
* Distance
* Time

## Environmental Data

* Air Temperature
* Track Temperature
* Humidity
* Wind Conditions

---

# ETL Pipeline

## Extract

Data is retrieved from FastF1 APIs for selected seasons, circuits, drivers, and sessions.

### Extracted Data

* Session Results
* Lap Information
* Telemetry Streams
* Weather Data

---

## Transform

Data processing includes:

### Data Cleaning

* Missing value handling
* Datetime conversion
* Data validation

### Feature Engineering

Creation of analytical metrics such as:

* Average Race Pace
* Qualifying Pace
* Consistency Index
* Braking Distance
* Corner Entry Speed
* Corner Exit Speed
* Tire Degradation Rate
* Driver Performance Scores

---

## Load

Processed datasets are stored in SQLite and transformed into analytical tables optimized for Power BI reporting.

---

# Database Design

## Dimension Tables

### dim_driver

* Driver ID
* Driver Name
* Team

### dim_team

* Team ID
* Team Name

### dim_race

* Race ID
* Circuit
* Country
* Season

### dim_season

* Season ID
* Year

---

## Fact Tables

### fact_laps

* Lap Time
* Sector Times
* Tire Compound
* Stint Information

### fact_telemetry

* Speed
* Gear
* Throttle
* Brake
* RPM
* DRS
* Distance

### fact_driver_metrics

* Average Pace
* Consistency
* Entry Speed
* Exit Speed
* Braking Metrics

---

# Power BI Dashboard

## Dashboard 1: Executive Overview

Purpose:

Provide a high-level overview of season and race performance.

### KPIs

* Total Drivers
* Total Races
* Fastest Driver
* Most Consistent Driver
* Average Race Pace

### Visualizations

* Driver Standings
* Team Standings
* Fastest Lap Rankings

---

## Dashboard 2: Driver Performance Analysis

Purpose:

Analyze race pace and consistency.

### Visualizations

* Lap Time Boxplots
* Pace Distributions
* Consistency Metrics
* Driver Rankings

### Filters

* Driver
* Team
* Season
* Circuit

---

## Dashboard 3: Telemetry Analysis

Purpose:

Compare telemetry characteristics between drivers.

### Visualizations

* Speed vs Distance
* Gear vs Distance
* Brake vs Distance
* Throttle vs Distance

### Use Cases

* Driver Comparisons
* Corner Analysis
* Driving Style Evaluation

---

## Dashboard 4: Driving Style Analysis

Purpose:

Investigate driver-specific performance characteristics.

### Metrics

* Braking Aggressiveness
* Throttle Application
* Corner Entry Speed
* Corner Exit Speed

### Visualizations

* Radar Charts
* Comparative Metrics
* Driver Profiles

---

## Dashboard 5: Regulation Impact Analysis

Purpose:

Compare performance between the 2025 and 2026 Formula One seasons.

### Visualizations

* Qualifying Pace Comparison
* Race Pace Comparison
* Sector Analysis
* Team Adaptation Metrics

---

## Dashboard 6: Driver Similarity Engine

Purpose:

Identify drivers with similar performance characteristics.

### Visualizations

* Similarity Rankings
* Driver Comparison Tables
* Cluster Analysis

---

# Key Analytical Outputs

The platform generates insights related to:

* Driver Consistency
* Race Pace Analysis
* Qualifying Performance
* Driving Style Characteristics
* Braking Strategies
* Tire Management
* Regulation Impact Assessment
* Driver Similarity Profiling

---

# Skills Demonstrated

## Data Engineering

* API Integration
* ETL Development
* Data Warehousing Concepts
* Relational Database Design

## Analytics

* Exploratory Data Analysis
* Statistical Analysis
* Performance Metrics
* Feature Engineering

## Business Intelligence

* Data Modeling
* Dashboard Design
* KPI Development
* Interactive Reporting

## Motorsport Analytics

* Telemetry Analysis
* Driver Performance Evaluation
* Driving Style Profiling
* Race Strategy Analysis

---

# Future Enhancements

* Machine Learning Driver Clustering
* Predictive Race Pace Models
* Tire Strategy Optimization
* Historical Driver Comparison Engine
* Automated Insight Generation
* Cloud-Based Data Warehouse Integration

---

# Author

**Vinayak Saxena**

B.Tech Student | Data Analytics Enthusiast | Formula One Analytics Project

This project was developed to explore the intersection of data engineering, business intelligence, analytics, and motorsport performance analysis using real-world Formula One telemetry data.
