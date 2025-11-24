import json

try:
    with open('service_account.json', 'r') as f:
        data = json.load(f)
    
    toml_content = "[gcp_service_account]\n"
    for key, value in data.items():
        # Escape newlines in private key
        if isinstance(value, str):
            value = value.replace('\n', '\\n')
            toml_content += f'{key} = "{value}"\n'
        else:
            toml_content += f'{key} = {json.dumps(value)}\n'
            
    with open('secrets_copy_paste.txt', 'w') as f:
        f.write(toml_content)
        
    print("Successfully created secrets_copy_paste.txt")
    
except Exception as e:
    print(f"Error: {e}")
