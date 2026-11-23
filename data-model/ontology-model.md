# Ontology Model — Prague Airport Operations (Fabric IQ)

## Overview

This ontology defines the semantic model for Prague Airport operations within Microsoft Fabric IQ. It creates a unified business vocabulary across two data stores (Lakehouse + Eventhouse), enabling graph-based reasoning, multi-hop traversals, and cross-domain analytics through a single semantic layer.

For new deployments, [the V2-first implementation](../setup-guide/02c-configure-ontology-v2.md) supplies seven entity types, 63 properties, eight directed table-backed relationships and three Eventhouse time-series groups. `../v2/airport-model.json` is the executable logical model, **not** a legacy ontology definition. The independent native graph uses the full Lakehouse copies; it does not replace Eventhouse time-series bindings.

## Architecture

```
Ontology (Fabric IQ)
├── Binds to Lakehouse (SQL Endpoint)
│   ├── flights      → Flight entity type
│   ├── airlines     → Airline entity type
│   ├── airports     → Airport entity type
│   ├── weather      → WeatherObservation entity type
│   ├── lkh_gate_assignments   → GateAssignment static identity/properties
│   ├── lkh_crew_rosters       → CrewMember static identity/properties
│   └── lkh_maintenance_events → MaintenanceEvent static identity/properties
│
└── Binds to Eventhouse (KQL Database)
    ├── gate_assignments    → GateAssignment entity type
    ├── crew_rosters        → CrewMember entity type
    └── maintenance_events  → MaintenanceEvent entity type
```

## Entity Types

### 1. Flight

The central entity representing an individual flight event (arrival or departure).

| Property | Type | Key | Bound To |
|----------|------|-----|----------|
| flight_id | Integer | ✅ PK | Lakehouse → flights.flight_id |
| flight_number | String | | flights.flight_number |
| airline_code | String | | flights.airline_code |
| flight_type | String | | flights.flight_type |
| origin_airport_code | String | | flights.origin_airport_code |
| destination_airport_code | String | | flights.destination_airport_code |
| scheduled_datetime | DateTime | | flights.scheduled_datetime |
| actual_datetime | DateTime | | flights.actual_datetime |
| status | String | | flights.status |
| delay_minutes | Integer | | flights.delay_minutes |
| delay_reason | String | | flights.delay_reason |
| terminal | String | | flights.terminal |
| gate | String | | flights.gate |
| aircraft_type | String | | flights.aircraft_type |
| passenger_count | Integer | | flights.passenger_count |

**Data Source:** Lakehouse → `flights` table

### 2. Airline

Reference entity for airline carriers.

| Property | Type | Key | Bound To |
|----------|------|-----|----------|
| airline_code | String | ✅ PK | Lakehouse → airlines.airline_code |
| airline_name | String | | airlines.airline_name |
| country | String | | airlines.country |
| alliance | String | | airlines.alliance |

**Data Source:** Lakehouse → `airlines` table

### 3. Airport

Reference entity for airports connected to Prague.

| Property | Type | Key | Bound To |
|----------|------|-----|----------|
| airport_code | String | ✅ PK | Lakehouse → airports.airport_code |
| airport_name | String | | airports.airport_name |
| city | String | | airports.city |
| country | String | | airports.country |
| region | String | | airports.region |
| latitude | Double | | airports.latitude |
| longitude | Double | | airports.longitude |

**Data Source:** Lakehouse → `airports` table

### 4. WeatherObservation

Daily weather conditions at Prague Airport.

| Property | Type | Key | Bound To |
|----------|------|-----|----------|
| weather_id | String | ✅ PK | Lakehouse → weather.weather_id |
| date | DateTime (source DATE) | | Lakehouse → weather.date |
| temperature_celsius | Double | | weather.temperature_celsius |
| wind_speed_kmh | Double | | weather.wind_speed_kmh |
| visibility_km | Double | | weather.visibility_km |
| precipitation_mm | Double | | weather.precipitation_mm |
| condition | String | | weather.condition |

**Data Source:** Lakehouse → `weather` table

### 5. GateAssignment

Operational entity tracking gate allocation for flights.

| Property | Type | Key | Bound To |
|----------|------|-----|----------|
| gate_assignment_id | Integer | ✅ PK | Lakehouse → lkh_gate_assignments.gate_assignment_id |
| flight_id | Integer | | lkh_gate_assignments.flight_id |
| gate | String | | lkh_gate_assignments.gate |
| terminal | String | | lkh_gate_assignments.terminal |
| scheduled_start | TimeSeries&lt;dateTime&gt; | | gate_assignments.scheduled_start |
| scheduled_end | TimeSeries&lt;dateTime&gt; | | gate_assignments.scheduled_end |
| actual_start | TimeSeries&lt;dateTime&gt; | | gate_assignments.actual_start |
| actual_end | TimeSeries&lt;dateTime&gt; | | gate_assignments.actual_end |
| turnaround_minutes | Integer | | lkh_gate_assignments.turnaround_minutes |
| status | String | | lkh_gate_assignments.status |

**Data Sources:** Static identity/properties from Lakehouse `lkh_gate_assignments`; the four datetime values are `TimeSeries<dateTime>` properties from Eventhouse `gate_assignments`, joined on `gate_assignment_id`, ordered by `scheduled_start`.

### 6. CrewMember

Operational entity representing one roster entry assigned to a flight, not one distinct person.

| Property | Type | Key | Bound To |
|----------|------|-----|----------|
| roster_id | Integer | ✅ PK | Lakehouse → lkh_crew_rosters.roster_id |
| flight_id | Integer | | lkh_crew_rosters.flight_id |
| crew_member_id | String | | lkh_crew_rosters.crew_member_id |
| crew_name | String | | lkh_crew_rosters.crew_name |
| role | String | | lkh_crew_rosters.role |
| license_number | String | | lkh_crew_rosters.license_number |
| nationality | String | | lkh_crew_rosters.nationality |
| base_airport | String | | lkh_crew_rosters.base_airport |
| roster_datetime | TimeSeries&lt;dateTime&gt; | | crew_rosters.roster_datetime (timeseries timestamp) |

**Data Sources:** Static identity/properties from Lakehouse `lkh_crew_rosters`; `roster_datetime` is a `TimeSeries<dateTime>` property from Eventhouse `crew_rosters`, joined on `roster_id`, ordered by `roster_datetime`. `base_airport` is a foreign key, not the entity identity.

### 7. MaintenanceEvent

Operational entity for aircraft maintenance activities.

| Property | Type | Key | Bound To |
|----------|------|-----|----------|
| maintenance_id | Integer | ✅ PK | Lakehouse → lkh_maintenance_events.maintenance_id |
| aircraft_type | String | | lkh_maintenance_events.aircraft_type |
| aircraft_registration | String | | lkh_maintenance_events.aircraft_registration |
| event_type | String | | lkh_maintenance_events.event_type |
| category | String | | lkh_maintenance_events.category |
| description | String | | lkh_maintenance_events.description |
| start_datetime | TimeSeries&lt;dateTime&gt; | | maintenance_events.start_datetime |
| end_datetime | TimeSeries&lt;dateTime&gt; | | maintenance_events.end_datetime |
| duration_hours | Double | | lkh_maintenance_events.duration_hours |
| related_flight_id | Integer | | lkh_maintenance_events.related_flight_id |
| resolved | Boolean | | lkh_maintenance_events.resolved |

**Data Sources:** Static identity/properties from Lakehouse `lkh_maintenance_events`; `start_datetime` and `end_datetime` are `TimeSeries<dateTime>` properties from Eventhouse `maintenance_events`, joined on `maintenance_id`, ordered by `start_datetime`. Nullable `related_flight_id` is a foreign key, not the entity identity.

The operational property tables above use short column names: all non-datetime columns bind to the corresponding `lkh_*` Lakehouse table; datetime value properties bind to Eventhouse. Flight status codes are exactly lowercase `on_time`, `delayed`, `cancelled`, `diverted`.

## Relationship Types

> **Note:** Relationship mappings use existing Lakehouse tables: `flights`, `rel_weather_flight`, and the three `lkh_*` operational copies. Notebook 02 does **not** create `rel_flight_gate`, `rel_flight_crew`, `rel_flight_maintenance`, or `rel_crew_airport`. V2 logical `map_*` table aliases reference existing partitions; they do not require new physical tables.

| # | Name | Source Entity | Target Entity | Source Data Table (Lakehouse) | Source → Source Key | Source → Target Key | Cardinality | Description |
|---|------|--------------|---------------|-------------------------------|---------------------|---------------------|-------------|-------------|
| 1 | operates | Airline | Flight | flights | airline_code | flight_id | 1:N | An airline operates many flights |
| 2 | originOf | Airport | Flight | flights | origin_airport_code | flight_id | 1:N | An airport is the origin of many departures |
| 3 | destinationOf | Airport | Flight | flights | destination_airport_code | flight_id | 1:N | An airport is the destination of many arrivals |
| 4 | observedOn | WeatherObservation | Flight | rel_weather_flight | weather_id | flight_id | 1:N | Weather observed on the day a flight operates |
| 5 | assignedTo | Flight | GateAssignment | lkh_gate_assignments | flight_id | gate_assignment_id | 1:1 | A flight is assigned to one gate slot |
| 6 | crewedBy | Flight | CrewMember | lkh_crew_rosters | flight_id | roster_id | 1:N | A flight has multiple roster entries |
| 7 | affectedFlight | MaintenanceEvent | Flight | lkh_maintenance_events | maintenance_id | related_flight_id | N:1 | A maintenance event may affect a specific flight |
| 8 | basedAt | CrewMember | Airport | lkh_crew_rosters | roster_id | base_airport | N:1 | A roster entry has a base airport |

### Relationship Binding Details

**1. operates** (Airline → Flight)
- Source data table: `flights` (Lakehouse)
- Source entity (Airline) column: `airline_code` → matches `airlines.airline_code`
- Target entity (Flight) column: `flight_id` → matches `flights.flight_id`

**2. originOf** (Airport → Flight)
- Source data table: `flights` (Lakehouse)
- Source entity (Airport) column: `origin_airport_code` → matches `airports.airport_code`
- Target entity (Flight) column: `flight_id`
- Filter: Only applies to flights where the airport is the origin

**3. destinationOf** (Airport → Flight)
- Source data table: `flights` (Lakehouse)
- Source entity (Airport) column: `destination_airport_code` → matches `airports.airport_code`
- Target entity (Flight) column: `flight_id`
- Filter: Only applies to flights where the airport is the destination

**4. observedOn** (WeatherObservation → Flight)
- Source data table: `rel_weather_flight` (Lakehouse bridge table)
- Source entity (WeatherObservation) column: `weather_id` → matches `weather.weather_id`
- Target entity (Flight) column: `flight_id`

**5. assignedTo** (Flight → GateAssignment)
- Source data table: `lkh_gate_assignments` (Lakehouse operational copy)
- Source entity (Flight) column: `flight_id`
- Target entity (GateAssignment) column: `gate_assignment_id`

**6. crewedBy** (Flight → CrewMember)
- Source data table: `lkh_crew_rosters` (Lakehouse operational copy)
- Source entity (Flight) column: `flight_id`
- Target entity (CrewMember) column: `roster_id`

**7. affectedFlight** (MaintenanceEvent → Flight)
- Source data table: `lkh_maintenance_events` (Lakehouse operational copy)
- Source entity (MaintenanceEvent) column: `maintenance_id`
- Target entity (Flight) column: `related_flight_id`
- Note: Only applies where `related_flight_id IS NOT NULL`

**8. basedAt** (CrewMember → Airport)
- Source data table: `lkh_crew_rosters` (Lakehouse operational copy)
- Source entity (CrewMember) column: `roster_id`
- Target entity (Airport) column: `base_airport` → matches `airports.airport_code`

## Graph Visualization

When the ontology is published, the graph view displays:

```
                        ┌──────────┐
                        │ Airline  │
                        └────┬─────┘
                             │ operates
                             ▼
┌──────────┐  originOf  ┌──────────┐  assignedTo  ┌────────────────┐
│ Airport  │───────────→│  Flight  │─────────────→│ GateAssignment │
│          │───────────→│          │              └────────────────┘
│          │destinationOf│         │  crewedBy    ┌────────────────┐
└──────────┘            │          │─────────────→│  CrewMember    │──basedAt──→ Airport
     ▲                  └────┬─────┘              └────────────────┘
     │                       ▲
     │                       │ affectedFlight
     │                  ┌────┴──────────────┐
     │                  │ MaintenanceEvent  │
     │                  └───────────────────┘
     │
┌────┴─────────────────┐
│ WeatherObservation   │──observedOn──→ Flight
└──────────────────────┘
```

## Example Graph Traversals

### 1. Multi-hop: Storm → Flight → Crew
*"Which crew members were on flights delayed during storms?"*
```
WeatherObservation[condition='storm'] 
  → observedOn → Flight[status='delayed'] 
    → crewedBy → CrewMember
```

### 2. Root Cause: Maintenance → Flight → Delay
*"Were delayed flights caused by unscheduled maintenance?"*
```
MaintenanceEvent[event_type='unscheduled'] 
  → affectedFlight → Flight[status='delayed']
```

### 3. Operational Chain: Airline → Flight → Gate → Turnaround
*"What is the average turnaround time for Ryanair flights?"*
```
Airline[airline_code='FR'] 
  → operates → Flight 
    → assignedTo → GateAssignment[turnaround_minutes]
```

### 4. Cross-domain: Crew → Flight → Weather + Maintenance
*"For captain Jan Novák, show flights with bad weather or maintenance issues"*
```
CrewMember[crew_name='Jan Novák', role='captain'] 
  ← crewedBy ← Flight
    → observedOn⁻¹ → WeatherObservation[condition IN ('storm','fog','snow')]
    ← affectedFlight ← MaintenanceEvent
```

### 5. Impact Analysis: Airport → Flights → Gate + Crew + Weather
*"Show all entities connected to London Heathrow within 2 hops"*
```
Airport[airport_code='LHR'] 
  → originOf/destinationOf → Flight 
    → assignedTo → GateAssignment
    → crewedBy → CrewMember
    → observedOn⁻¹ → WeatherObservation
```
