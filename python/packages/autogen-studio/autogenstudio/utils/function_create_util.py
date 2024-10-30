def create_dynamic_function(
        function_name: str, args_info: dict, method: str, url: str, auth_provider_id: str
):
    arg_str = ", ".join(
        f"{arg_name}: {arg_type}" for arg_name, arg_type in args_info.items()
    )

    data_payload = ", ".join(
        f"'{arg_name}': {arg_name}" for arg_name in args_info.keys()
    )
    data_str = (
        f"params={{ {data_payload} }}"
        if method.lower() == "get"
        else f"json={{ {data_payload} }}"
    )

    function_code = f"""
def {function_name}({arg_str}) -> dict:
    import requests

    headers= {{"Authorization": "Bearer token-123"}}
    response = requests.{method}(url="{url}", headers=headers, {data_str})
    return response.json()
"""

    local_namespace = {}
    exec(function_code, globals(), local_namespace)

    return local_namespace[function_name]
