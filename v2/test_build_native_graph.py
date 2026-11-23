import copy
import json
import pathlib
import unittest

from build_native_graph import build_definition, normalized_readback


class NativeGraphDefinitionTests(unittest.TestCase):
    def setUp(self):
        self.model = json.loads(
            (pathlib.Path(__file__).parent / "airport-model.json").read_text(encoding="utf-8")
        )
        self.workspace = "11111111-1111-4111-8111-111111111111"
        self.lakehouse = "22222222-2222-4222-8222-222222222222"

    def test_corrected_relationships_preserve_their_direction_and_keys(self):
        parts = build_definition(self.model, self.workspace, self.lakehouse)
        edge_types = {edge["labels"][0]: edge for edge in parts["graphType.json"]["edgeTypes"]}
        edge_tables = {
            edge["edgeTypeAlias"]: edge for edge in parts["graphDefinition.json"]["edgeTables"]
        }
        for name, source, destination, source_column, destination_column in [
            ("affectedFlight", "MaintenanceEvent", "Flight", "maintenance_id", "related_flight_id"),
            ("basedAt", "CrewMember", "Airport", "roster_id", "base_airport"),
        ]:
            with self.subTest(relationship=name):
                edge = edge_types[name]
                self.assertEqual(edge["sourceNodeType"]["alias"], source + "_nodeType")
                self.assertEqual(edge["destinationNodeType"]["alias"], destination + "_nodeType")
                mapping = edge_tables[edge["alias"]]
                self.assertEqual(mapping["sourceNodeKeyColumns"], [source_column])
                self.assertEqual(mapping["destinationNodeKeyColumns"], [destination_column])

    def test_graph_uses_static_copies_without_changing_time_series_model(self):
        original = copy.deepcopy(self.model)
        parts = build_definition(self.model, self.workspace, self.lakehouse)
        nodes = {node["labels"][0]: node for node in parts["graphType.json"]["nodeTypes"]}
        gate_properties = {p["name"]: p["type"] for p in nodes["GateAssignment"]["properties"]}
        self.assertEqual(gate_properties["scheduled_start"], "DATETIME")
        self.assertEqual(self.model, original)
        sources = parts["dataSources.json"]
        self.assertEqual(sources["itemReferences"][0]["item"], {
            "workspaceId": self.workspace, "itemId": self.lakehouse
        })
        self.assertIn("Tables/dbo/lkh_gate_assignments", {
            source["properties"]["path"] for source in sources["dataSources"]
        })
        self.assertNotIn("Tables/dbo/gate_assignments", {
            source["properties"]["path"] for source in sources["dataSources"]
        })

    def test_invalid_key_or_relationship_endpoint_blocks_definition(self):
        bad_key = copy.deepcopy(self.model)
        bad_key["entities"][0]["key"] = "missing"
        missing_endpoint = copy.deepcopy(self.model)
        missing_endpoint["relationships"][0]["destination"] = "MissingEntity"
        for model in [bad_key, missing_endpoint]:
            with self.subTest(model=model["entities"][0]["key"]):
                with self.assertRaises(ValueError):
                    build_definition(model, self.workspace, self.lakehouse)

    def test_only_known_null_defaults_are_ignored_in_service_readback(self):
        prepared = build_definition(self.model, self.workspace, self.lakehouse)
        actual = copy.deepcopy(prepared)
        actual["graphDefinition.json"]["edgeTables"][0]["edgeIdMapping"] = None
        actual["stylingConfiguration.json"]["scenario"] = None
        actual["stylingConfiguration.json"]["visualFormat"]["Flight_nodeType"]["shape"] = None
        self.assertEqual(normalized_readback(actual), prepared)
        actual["graphDefinition.json"]["edgeTables"][0]["sourceNodeKeyColumns"] = ["wrong"]
        self.assertNotEqual(normalized_readback(actual), prepared)


if __name__ == "__main__":
    unittest.main()
