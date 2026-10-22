from dojoflow.main import app


def _is_untyped(schema: dict) -> bool:
    if not schema:
        return True

    if '$ref' in schema or schema.get('type') == 'array':
        return False

    return schema.get('type') == 'object' and 'properties' not in schema


def test_web_routes_declare_typed_responses() -> None:
    openapi = app.openapi()
    untyped = []

    for path, operations in openapi['paths'].items():
        if not path.startswith('/api/v1'):
            continue

        for method, operation in operations.items():
            for code, response in operation['responses'].items():
                if not code.startswith('2') or code == '204':
                    continue

                content = response.get('content', {})
                schema = content.get('application/json', {}).get('schema', {})

                if _is_untyped(schema):
                    untyped.append(f'{method.upper()} {path} -> {code}')

    assert untyped == []
