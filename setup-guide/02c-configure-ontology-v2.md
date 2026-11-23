# Step 2c: V2-first ontology and independent native graph

This path was exercised end to end on a separate Fabric F8 capacity: native V2 creation, persisted TMDL readback, all seven node/eight edge counts, ontology MCP consumption, rendered Map, and published preview Data Agent SQL/KQL/GQL results. It creates no legacy ontology. The renderer is **offline**, not an automatic deployment or a claim that generic item creation selects the new experience.

## 1. Prepare and discover sources

Run both notebooks using the same Lakehouse. Verify all seven entity keys are unique/non-null and the nine foreign-key checks have no orphans. Record the actual workspace, Lakehouse and **parent Eventhouse** item IDs, Eventhouse `queryServiceUri`, KQL database name, and display names. The KQL database ID belongs in the agent's KQL source, **not** in ontology Eventhouse bindings.

Use an isolated Azure CLI profile and explicitly select the target tenant/subscription. Do not change shared machine authentication. All Fabric REST calls below, including LRO polls, require `x-ms-fabric-skill: ontology-cli`, a token for `https://api.fabric.microsoft.com`, and the appropriate workspace/source permissions.

## 2. Create a native new-experience item

In the target workspace, create `PRGAirportOntology` through **New item > Ontology**, selecting the new experience. Record its item ID. For an existing legacy item, native **Create copy** makes a separate V2 item; preserve the original until consumers are verified.

Do not import legacy `EntityTypes/.../definition.json` to create V2. The public [Ontology definition API](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/ontology-definition) describes the supported native TMDL ALM format used here.

## 3. Render and persist V2 TMDL

Copy `v2/config.example.json` to an ignored `deployment.local.json` and replace all identity/URI placeholders with discovered values. Match the workspace and source display names; defaults reflect this demo's standard names.

```powershell
python v2\render_definitions.py --config deployment.local.json --output generated
python -m unittest discover -s v2 -v
```

POST `generated/ontology-update.json` to:

```text
https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items/{ontologyId}/updateDefinition?updateMetadata=true
```

Respect `Retry-After` and poll a `202` to terminal success; HTTP acceptance alone is not success. Read back with `POST .../items/{ontologyId}/getDefinition` and decode each `InlineBase64` part.

Verify 32 parts, compatibility level `1000000`, a default namespace, seven entities, 63 properties, three time-series groups/seven time-series values, eight table-backed entity relationships, and 19 physical joins. Static model tables hold 56 columns; operational datetime properties live in Eventhouse companion tables.

| Entity | Static Lakehouse table / identity | Eventhouse table | orderingColumn |
|---|---|---|---|
| CrewMember | lkh_crew_rosters / roster_id | crew_rosters | roster_datetime |
| GateAssignment | lkh_gate_assignments / gate_assignment_id | gate_assignments | scheduled_start |
| MaintenanceEvent | lkh_maintenance_events / maintenance_id | maintenance_events | start_datetime |

Each relationship uses a logical `map_*` table alias with two joins to endpoint identities. Its DirectLake partition references an **existing physical table**, not a fabricated bridge. Check all directions against [the specification](../data-model/ontology-model.md), particularly `MaintenanceEvent -> Flight` and `CrewMember -> Airport`.

The service may reorder annotations/references or omit derived SQL hints. Do not ignore changed item IDs, URIs, keys, physical columns, ordering or mapping direction as "normalization."

## 4. Create and load the independent graph

Dual Lakehouse/Eventhouse-bound entities can reject ontology-managed graph projection with `Unsupported Datasource`. Keep the real Eventhouse bindings and create the independent graph from full Lakehouse copies instead.

POST `generated/graph-create.json` to `.../workspaces/{workspaceId}/graphModels`. Resolve the returned item ID and read its definition back. It uses `dataSources` schema **1.1.0**, `itemReferences`, `Tables/dbo/...` paths and `visualFormat` styling. `build_native_graph.normalized_readback` permits only observed null defaults.

**Open the REST-created graph in the portal once before its first refresh.** Then use the native Refresh action or the graph Refresh job API, and wait for completion. Do not mistake the ontology-managed child graph for `PRGAirportGraph`.

Execute native GQL with:

```text
POST .../workspaces/{workspaceId}/graphModels/{graphId}/executeQuery?beta=true
{"query":"MATCH (n:Flight) RETURN count(n) AS row_count"}
```

Require application status `00000` and a `TABLE` result, not HTTP 200 alone. Follow opaque continuation tokens without double encoding. Validate all seven node counts and eight edge counts against the actual source tables. For `affectedFlight`, compare only non-null, resolving `related_flight_id` rows.

Verified aggregate syntax:

```gql
MATCH (c:CrewMember)-[:basedAt]->(a:Airport)
LET base_airport = a.airport_code
RETURN base_airport, count(c) AS roster_count
GROUP BY base_airport ORDER BY roster_count DESC
```

Also verify lowercase `cancelled`, crew-base counts, and typed operational timestamps. Crew nodes count **roster entries**, not unique people. Refresh after source data changes. Graph capacity/cache billing applies, including the documented minimum cache allocation; this workaround is not free.

## 5. Ground and publish the Data Agent

Create a Data Agent with exactly three execution sources: `PRGFlightData` Lakehouse, `PRGOperations` KQL database and independent `PRGAirportGraph`. Use native **Add an ontology** to select the actual V2 item, and finish the schema-matching confirmation. Selecting the picker alone does not persist context.

Retain source instructions/descriptions/examples. For graph examples use only queries already executed successfully. Select **Preview** runtime for this tested configuration; publish natively. Publishing to Microsoft Copilot is a separate choice and is not necessary.

After ontology changes, hover its own source row, open its context menu, choose **Refresh**, then **Download ontology context**. The general schema refresh control is not this action. Context is read-only: update shared ontology descriptions/bindings, not downloaded text. Shared notes explicitly distinguish primary identity from FK joins and record all ordering columns because compact `TS(...)` context can omit ordering information. See [ontology context guidance](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-ontology-sources).

Republish and read back the published configuration: exactly three sources with correct IDs, seven selected ontology entities, retained examples and preview settings. Use `tools/list` before calling the discovered tools on the V2 ontology MCP and published Data Agent MCP endpoints:

```text
/v1/mcp/dataPlane/workspaces/{workspaceId}/items/{ontologyId}/ontologyEndpoint
/v1/mcp/workspaces/{workspaceId}/dataagents/{agentId}/agent
```

The V2 endpoint must offer `ask_ontology`; do not fall back to legacy search. Ask ontology questions through that MCP agent, not manually composed replacement SQL/KQL.

Compare executed published-agent CSV results with independent source results: flight/cancellation totals, maintenance totals/unresolved counts, and nine crew-base groups. Preview MCP exposes genuine result datasets and response deep links, **not necessarily the literal generated query text**. Inspect native response run steps for query diagnostics; do not present illustrative SQL as the executed statement. Native graph CSV can JSON-quote string codes; CSV-parse and JSON-decode the known IATA field once, never indiscriminately strip quotes from arbitrary values.

Finally ask the published agent, without supplying expected answers, for `basedAt`/`affectedFlight` endpoint **primary identity keys** and all three time-series ordering columns. Confirm against the persisted TMDL and downloaded context. Retain failed responses and fixes as evidence, rather than overwriting them with success.

## Additional V2 opportunities

Shared entity definitions and governed rules can centralize cancellation, AOG and turnaround semantics; an operator app can combine relationship navigation with Eventhouse time-series inspection; semantic-model metrics can extend the business vocabulary; namespaces/versioned TMDL support controlled reuse and ALM. These are follow-on capabilities, not silently provisioned demo features. All displayed data remains synthetic 2024-2025 scenario data, not live airport activity. Sharing an agent does not grant access to its sources.
