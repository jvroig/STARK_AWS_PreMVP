#STARK Code Generator component.
#Produces the customized dynamic content for a STARK system

#Python Standard Library
import base64
import textwrap
import os

#Private modules
import convert_friendly_to_system as converter

def create():

    source_code = f"""\
        {{
            "Parameters" : {{
                "UserCodeGenBucketNameParameter" : "{os.environ['CODEGEN_BUCKET_NAME']}"
            }}
        }}
        """

    return textwrap.dedent(source_code)