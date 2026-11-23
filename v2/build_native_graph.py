"""Pure native graph definition builder; performs no network or authentication operations."""
import copy
import re
import uuid
SCHEMA_BASE = 'https://developer.microsoft.com/json-schemas/fabric/item/graphIndex/definition'
GRAPH_TYPES = {'String': 'STRING', 'Int64': 'INT', 'Double': 'FLOAT', 'Boolean': 'BOOLEAN', 'DateTime': 'DATETIME'}

def normalized_readback(definitions):
    normalized = copy.deepcopy(definitions)
    graph_definition = normalized.get('graphDefinition.json', {})
    for edge in graph_definition.get('edgeTables', []):
        if 'edgeIdMapping' in edge and edge['edgeIdMapping'] is None:
            del edge['edgeIdMapping']
    styling = normalized.get('stylingConfiguration.json', {})
    if 'scenario' in styling and styling['scenario'] is None:
        del styling['scenario']
    for style in styling.get('visualFormat', {}).values():
        if 'shape' in style and style['shape'] is None:
            del style['shape']
    return normalized

def build_definition(model, workspace_id, lakehouse_id):
    uuid.UUID(workspace_id)
    uuid.UUID(lakehouse_id)
    if not re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', model['schema']):
        raise ValueError('Unsafe Lakehouse schema identifier')
    entities = model['entities']
    relationships = model['relationships']
    by_name = {entity['name']: entity for entity in entities}
    if len(by_name) != len(entities):
        raise ValueError('Duplicate entity name')
    if len({edge['name'] for edge in relationships}) != len(relationships):
        raise ValueError('Duplicate relationship name')
    for entity in entities:
        if entity['key'] not in entity['properties']:
            raise ValueError(f"Unmapped key for {entity['name']}")
        for value in [entity['name'], entity['table'], *entity['properties']]:
            if not re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', value):
                raise ValueError(f'Unsafe logical identifier: {value}')
        for value in entity['properties'].values():
            if value not in GRAPH_TYPES:
                raise ValueError(f'Unsupported property type: {value}')
        time_series = entity.get('timeSeries')
        if time_series and (not set(time_series['properties']) <= entity['properties'].keys()):
            raise ValueError(f"Unmapped time-series properties for {entity['name']}")
    for edge in relationships:
        if edge['source'] not in by_name or edge['destination'] not in by_name:
            raise ValueError(f"Unresolved edge endpoint: {edge['name']}")
        for value in [edge['name'], edge['table'], edge['sourceColumn'], edge['destinationColumn']]:
            if not re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', value):
                raise ValueError(f'Unsafe relationship identifier: {value}')
    tables = sorted({entity['table'] for entity in entities} | {edge['table'] for edge in relationships})
    reference_name = 'AirportLakehouse'

    def schema(name, version='1.0.0'):
        return f'{SCHEMA_BASE}/{name}/{version}/schema.json'

    def identity(name):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f'prague-airport/{workspace_id}/{lakehouse_id}/{name}'))
    graph_type = {'$schema': schema('graphType'), 'nodeTypes': [{'alias': f"{entity['name']}_nodeType", 'labels': [entity['name']], 'primaryKeyProperties': [entity['key']], 'properties': [{'name': name, 'type': GRAPH_TYPES[data_type]} for name, data_type in entity['properties'].items()]} for entity in entities], 'edgeTypes': [{'alias': f"{edge['name']}_edgeType", 'labels': [edge['name']], 'sourceNodeType': {'alias': f"{edge['source']}_nodeType"}, 'destinationNodeType': {'alias': f"{edge['destination']}_nodeType"}, 'properties': []} for edge in relationships]}
    data_sources = {'$schema': schema('dataSources', '1.1.0'), 'itemReferences': [{'name': reference_name, 'item': {'workspaceId': workspace_id, 'itemId': lakehouse_id}}], 'dataSources': [{'name': table, 'type': 'DeltaTable', 'properties': {'referenceName': reference_name, 'path': f"Tables/{model['schema']}/{table}"}} for table in tables]}
    graph_definition = {'$schema': schema('graphDefinition'), 'nodeTables': [{'id': identity('node/' + entity['name']), 'nodeTypeAlias': f"{entity['name']}_nodeType", 'dataSourceName': entity['table'], 'propertyMappings': [{'propertyName': name, 'sourceColumn': name} for name in entity['properties']]} for entity in entities], 'edgeTables': [{'id': identity('edge/' + edge['name']), 'edgeTypeAlias': f"{edge['name']}_edgeType", 'dataSourceName': edge['table'], 'sourceNodeKeyColumns': [edge['sourceColumn']], 'destinationNodeKeyColumns': [edge['destinationColumn']], 'propertyMappings': []} for edge in relationships]}
    positions = {'Flight': (0, 0), 'Airline': (-330, -180), 'Airport': (330, -80), 'WeatherObservation': (-330, 80), 'CrewMember': (120, 300), 'GateAssignment': (-170, 300), 'MaintenanceEvent': (400, 230)}
    colors = ['#38BDF8', '#2DD4BF', '#A78BFA', '#60A5FA', '#FBBF24', '#FB7185', '#34D399']
    display = {'Airline': 'airline_name', 'Airport': 'airport_code', 'CrewMember': 'crew_name', 'Flight': 'flight_number', 'GateAssignment': 'gate', 'MaintenanceEvent': 'aircraft_registration', 'WeatherObservation': 'date'}
    styling = {'$schema': schema('stylingConfiguration'), 'modelLayout': {'positions': {f"{entity['name']}_nodeType": {'x': positions.get(entity['name'], (index * 150, 0))[0], 'y': positions.get(entity['name'], (index * 150, 0))[1]} for index, entity in enumerate(entities)}, 'styles': {f"{entity['name']}_nodeType": {'size': 40} for entity in entities}, 'pan': {'x': 0, 'y': 0}, 'zoomLevel': 1}, 'visualFormat': {f"{entity['name']}_nodeType": {'defaultDisplayProperty': display.get(entity['name'], entity['key']), 'color': colors[index % len(colors)]} for index, entity in enumerate(entities)}}
    return {'graphType.json': graph_type, 'dataSources.json': data_sources, 'graphDefinition.json': graph_definition, 'stylingConfiguration.json': styling}
