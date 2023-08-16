name = "STARK Validation"

def validate_form(payload, metadata):
    
    bad_request_attributes = {}
    for key, items in metadata.items():
        value = payload[key]

        if items['required']:
            if value == "":
                bad_request_attributes[key] = 'This field is required.'
                
        if items['max_length'] != '':
            if(len(value) > items['max_length']):
                bad_request_attributes[key] = f"This field must not exceed {items['max_length']} characters."
            
    return bad_request_attributes