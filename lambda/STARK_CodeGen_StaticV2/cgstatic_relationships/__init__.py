#STARK Code Generator component.
#Helper for dealing with relationships between entities

#Python Standard Library
import base64
import textwrap

#Private modules
import convert_friendly_to_system as converter

def get(data):

    col_type = data['col_type']

    related_entities = []

    if isinstance(col_type, dict):
        if col_type["type"] == "relationship":
            has_one = col_type.get('has_one', '')
            has_many = col_type.get('has_many', '')
            if has_one != '':
                related_entities.append(has_one)
            elif has_many != '':
                related_entities.append(has_many)

                      

    return related_entities