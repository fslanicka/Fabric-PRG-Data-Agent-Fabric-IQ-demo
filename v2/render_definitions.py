"""Render native V2 and independent graph definitions offline."""
import argparse
import base64
import datetime
import json
import pathlib
import re
import uuid
from urllib.parse import urlparse

from build_native_graph import build_definition

ROOT = pathlib.Path(__file__).resolve().parent


def render_ontology(config):
    values = dict(config)
    for field in ("workspaceId", "lakehouseId", "eventhouseId"):
        identifier = uuid.UUID(values[field])
        if identifier.int == 0:
            raise ValueError(f"{field} must be the actual discovered item identity")
        values[field] = str(identifier)
    uri = urlparse(values["kustoUri"])
    if (
        uri.scheme != "https" or uri.username or uri.password
        or uri.port not in (None, 443) or uri.query or uri.fragment
        or uri.path not in ("", "/")
        or not re.fullmatch(r"[a-z0-9.-]+\.kusto\.fabric\.microsoft\.com", uri.hostname or "")
    ):
        raise ValueError("Use the discovered public-cloud Eventhouse queryServiceUri")
    values["kustoUri"] = values["kustoUri"].rstrip("/")
    for field, default in {
        "lakehouseName": "PRGFlightData", "eventhouseName": "PRGOperations",
        "kqlDatabaseName": "PRGOperations", "ontologyName": "PRGAirportOntology",
    }.items():
        values.setdefault(field, default)
    for field in ("workspaceName", "lakehouseName", "eventhouseName", "kqlDatabaseName", "ontologyName"):
        if not re.fullmatch(r"[A-Za-z0-9_. -]+", values[field]):
            raise ValueError(f"{field} contains unsupported template characters")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", values["ontologyName"]):
        raise ValueError("Use an ontology name with letters, digits and underscores")
    values["pinnedAtUtc"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    template = json.loads((ROOT / "ontology-template.json").read_text(encoding="utf-8"))
    parts = []
    for path, text in template.items():
        rendered = re.sub(r"\{\{([A-Za-z]+)\}\}", lambda match: values[match[1]], text)
        if "{{" in rendered or "}}" in rendered:
            raise ValueError(f"Unresolved placeholder in {path}")
        parts.append({
            "path": path, "payload": base64.b64encode(rendered.encode("utf-8")).decode("ascii"),
            "payloadType": "InlineBase64",
        })
    return {"definition": {"parts": parts}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    ontology = render_ontology(config)
    model = json.loads((ROOT / "airport-model.json").read_text(encoding="utf-8"))
    graph_parts = build_definition(model, config["workspaceId"], config["lakehouseId"])
    graph = {
        "displayName": "PRGAirportGraph",
        "description": "Independent Lakehouse graph complementing the V2 ontology and Eventhouse time series.",
        "definition": {"format": "json", "parts": [
            {"path": path, "payload": base64.b64encode(json.dumps(value).encode("utf-8")).decode("ascii"),
             "payloadType": "InlineBase64"}
            for path, value in graph_parts.items()
        ]},
    }
    args.output.mkdir(parents=True, exist_ok=True)
    for name, envelope in [("ontology-update.json", ontology), ("graph-create.json", graph)]:
        (args.output / name).write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    print("Rendered 32 native V2 parts and an independent graph; no remote writes performed.")


if __name__ == "__main__":
    main()
