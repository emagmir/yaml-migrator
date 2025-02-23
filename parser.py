import yaml

def load_openapi_spec(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def extract_spec_path(spec, target_paths):
    paths = spec.get("paths", {})
    return {path: paths.get(path, {}) for path in target_paths if path in paths}

def find_ref(spec, ref_path):
    parts = ref_path.lstrip("#/").split("/")
    ref_data = spec
    for part in parts:
        ref_data = ref_data.get(part, {})
    return ref_data

def extract_referenced_components(spec, spec_paths, processed_refs=None):
    if processed_refs is None:
        processed_refs = set()
    
    referenced_params = {}
    referenced_schemas = {}
    
    def process_reference(ref_path):
        ref_key = ref_path.split("/")[-1]
        if ref_key in processed_refs:
            return None
        processed_refs.add(ref_key)
        return find_ref(spec, ref_path)
    
    def extract_from_dict(details):
        if isinstance(details, dict):
            for key, value in details.items():
                if isinstance(value, dict):
                    if "$ref" in value:
                        ref_key = value["$ref"].split("/")[-1]
                        ref_value = process_reference(value["$ref"])
                        if ref_value:
                            if "parameters" in value["$ref"]:
                                referenced_params[ref_key] = ref_value
                            elif "schemas" in value["$ref"]:
                                referenced_schemas[ref_key] = ref_value
                                extract_from_dict(ref_value)  # Recursively extract nested references
                    extract_from_dict(value)  # Recursively check all nested structures
                elif isinstance(value, list):
                    for item in value:
                        extract_from_dict(item)
    
    for methods in spec_paths.values():
        for details in methods.values():
            if isinstance(details, dict):
                if "parameters" in details:
                    for param in details["parameters"]:
                        if "$ref" in param:
                            ref_key = param["$ref"].split("/")[-1]
                            ref_value = process_reference(param["$ref"])
                            if ref_value:
                                referenced_params[ref_key] = ref_value
                extract_from_dict(details)
                
                # Also check requestBody for schema references
                if "requestBody" in details and "content" in details["requestBody"]:
                    for content_type, content_value in details["requestBody"]["content"].items():
                        if "schema" in content_value:
                            extract_from_dict(content_value["schema"])
                
                # Also check responses for schema references
                if "responses" in details:
                    for response in details["responses"].values():
                        if "content" in response:
                            for content_type, content_value in response["content"].items():
                                if "schema" in content_value:
                                    extract_from_dict(content_value["schema"])
    
    return referenced_params, referenced_schemas

def print_combined_spec(spec, endpoints):
    spec_paths = extract_spec_path(spec, endpoints)
    
    if not spec_paths:
        print("No specified paths found in the OpenAPI specification.")
        return
    
    referenced_params, referenced_schemas = extract_referenced_components(spec, spec_paths)
    
    output = {"paths": spec_paths}
    if referenced_params or referenced_schemas:
        components = {}
        if referenced_params:
            components["parameters"] = referenced_params
        if referenced_schemas:
            components["schemas"] = referenced_schemas
        output["components"] = components
    
    print(yaml.dump(output, default_flow_style=False))

def read_endpoints(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file if line.strip()]

if __name__ == "__main__":
    spec_file_path = "openapispec.yaml"  # Update this path if necessary
    endpoints_file_path = "endpoints.txt"  # File containing endpoints
    
    spec = load_openapi_spec(spec_file_path)
    endpoints = read_endpoints(endpoints_file_path)
    
    print_combined_spec(spec, endpoints)













# from openapi_parser import parse

# specification = parse('openapispec.yaml')

# for path in specification.paths:
#     supported_methods = ','.join([x.method.value for x in path.operations])

#     print(f"Operation: {path.url}, methods: {supported_methods}")

# for param in specification.parameters:

#     print(f"Parameter: {param.url}")

# # Output
# #
# # >> Operation: /users, methods: get,post
# # >> Operation: /users/{uuid}, methods: get,put