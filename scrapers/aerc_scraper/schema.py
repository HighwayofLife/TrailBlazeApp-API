"""Schema definitions for AERC event data."""

AERC_EVENT_SCHEMA = {
    'type': 'object',
    'properties': {
        'rideName': {'type': 'string'},
        'date': {'type': 'string', 'format': 'date'},
        'region': {'type': 'string'},
        'location': {'type': 'string'},
        'distances': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'distance': {'type': 'string'},
                    'date': {'type': 'string', 'format': 'date'},
                    'startTime': {'type': 'string'}
                },
                'required': ['distance', 'date']
            }
        },
        'rideManager': {'type': 'string'},
        'rideManagerContact': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'email': {'type': 'string', 'format': 'email'},
                'phone': {'type': 'string'}
            }
        },
        'controlJudges': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'role': {'type': 'string'},
                    'name': {'type': 'string'}
                },
                'required': ['role', 'name']
            }
        },
        'mapLink': {'type': 'string'},
        'hasIntroRide': {'type': 'boolean'},
        'tag': {'type': 'integer'},
        'is_canceled': {'type': 'boolean'}
    },
    'required': ['rideName', 'date', 'region', 'location']
}
