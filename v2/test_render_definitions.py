import base64
import copy
import json
import unittest

from render_definitions import render_ontology


class V2TemplateTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "workspaceId": "11111111-1111-4111-8111-111111111111",
            "lakehouseId": "22222222-2222-4222-8222-222222222222",
            "eventhouseId": "33333333-3333-4333-8333-333333333333",
            "workspaceName": "Prague_Airport",
            "kustoUri": "https://test.z1.kusto.fabric.microsoft.com",
        }

    def parts(self, config):
        return {
            part["path"]: base64.b64decode(part["payload"]).decode()
            for part in render_ontology(config)["definition"]["parts"]
        }

    def test_source_identities_and_kusto_database_are_parameterized(self):
        config = dict(self.config, kqlDatabaseName="AirportOperations")
        parts = self.parts(config)
        joined = "\n".join(parts.values())
        self.assertNotIn("{{", joined)
        self.assertIn(self.config["workspaceId"], joined)
        self.assertIn(self.config["lakehouseId"], parts["expressions.tmdl"])
        operational = parts["tables/crew_rosters.tmdl"]
        self.assertIn("ONT_ItemId = " + self.config["eventhouseId"], operational)
        self.assertIn('AzureDataExplorer.Contents("https://test.z1.kusto.fabric.microsoft.com", "AirportOperations"', operational)

    def test_ordering_and_identity_notes_survive_rendering(self):
        parts = self.parts(self.config)
        joined = "\n".join(parts.values())
        for timestamp in ("roster_datetime", "scheduled_start", "start_datetime"):
            self.assertIn("orderingColumn " + timestamp, joined)
        self.assertIn("roster_id", joined)
        self.assertIn("related_flight_id", parts["entityRelationships.tmdl"])
        self.assertIn("on_time, delayed, cancelled, diverted", joined)

    def test_unsafe_configuration_is_rejected_before_writing(self):
        for field, value in [
            ("eventhouseId", "00000000-0000-0000-0000-000000000000"),
            ("kustoUri", "https://example.org"),
            ("kustoUri", "https://user:secret@test.z1.kusto.fabric.microsoft.com"),
            ("workspaceName", 'Airport"\nannotation unexpected = x'),
        ]:
            config = copy.deepcopy(self.config)
            config[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                render_ontology(config)


if __name__ == "__main__":
    unittest.main()
