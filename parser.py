import yaml
import re
import sys
import os

# Validate command-line arguments
if len(sys.argv) != 3:
    print("Usage: python script.py <endpoints.txt> <openapispec.yaml>")
    sys.exit(1)

# Command-line arguments
endpoints_file = sys.argv[1]
yaml_file = sys.argv[2]

# Output file: replace .txt with .yaml
output_file = os.path.splitext(endpoints_file)[0] + ".yaml"

# Regular expression to match references: #/components/{value1}/{schemaOrParamName}
ref_pattern = re.compile(r"^#/components/(?P<value1>\w+)/(?P<schemaOrParamName>[\w-]+)$")

# Read and parse the YAML file
try:
    with open(yaml_file, "r") as file:
        data = yaml.safe_load(file)

    # Extract the 'paths' key
    paths = data.get("paths", {})

    # Read the list of endpoints from the file
    try:
        with open(endpoints_file, "r") as file:
            endpoint_paths = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"Error: File '{endpoints_file}' not found.")
        sys.exit(1)

    # Store extracted path definitions and components
    extracted_paths = {}
    extracted_components = {}

    # Function to recursively search for `$ref` occurrences
    def find_references(obj, refs=None):
        if refs is None:
            refs = set()
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "$ref" and isinstance(value, str):
                    match = ref_pattern.match(value)
                    if match:
                        ref_tuple = (match.group("value1"), match.group("schemaOrParamName"))
                        if ref_tuple not in refs:
                            refs.add(ref_tuple)
                else:
                    find_references(value, refs)
        elif isinstance(obj, list):
            for item in obj:
                find_references(item, refs)
        return refs

    def extract_component(value1, schema_or_param):
        """Extract a referenced component and search inside it for more references."""
        if value1 not in data.get("components", {}):
            return  # Skip if the component category does not exist
        
        component_dict = data["components"][value1]
        
        if schema_or_param in component_dict:
            # Add the schema/parameter to extracted components
            if value1 not in extracted_components:
                extracted_components[value1] = {}
            extracted_components[value1][schema_or_param] = component_dict[schema_or_param]

            # Recursively search inside the extracted schema
            new_refs = find_references(component_dict[schema_or_param])
            for new_value1, new_schema_or_param in new_refs:
                if new_schema_or_param not in extracted_components.get(new_value1, {}):
                    extract_component(new_value1, new_schema_or_param)

    # Process each path from the file
    for target_path in endpoint_paths:
        if target_path not in paths:
            print(f"Warning: Path '{target_path}' not found in the YAML file.")
            continue

        # Store the full path definition
        extracted_paths[target_path] = paths[target_path]

        # Extract references
        references = find_references(paths[target_path])

        for value1, schema_or_param in references:
            extract_component(value1, schema_or_param)

    # Prepare output data
    output_data = {
        "paths": extracted_paths,
        "components": extracted_components
    }

    # Write output to a file
    with open(output_file, "w") as file:
        yaml.dump(output_data, file, default_flow_style=False, sort_keys=False)

    print(f"Extraction complete. Output saved to '{output_file}'.")

except FileNotFoundError:
    print(f"Error: File '{yaml_file}' not found.")
    sys.exit(1)
except yaml.YAMLError as e:
    print(f"Error parsing YAML: {e}")
    sys.exit(1)
