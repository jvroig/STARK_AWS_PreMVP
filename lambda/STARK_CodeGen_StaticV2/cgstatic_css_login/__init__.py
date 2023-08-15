#STARK Code Generator component.
#Produces the customized static content for a STARK system

#Python Standard Library
import textwrap

def create(data):

    source_code = f"""\
    .blank_placeholder {{
        /* Yes, currently empty. Login page is has no custom design for the moment. */
    }}
    """
    


    return textwrap.dedent(source_code)