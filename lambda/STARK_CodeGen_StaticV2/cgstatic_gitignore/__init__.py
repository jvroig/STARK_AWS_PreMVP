#STARK Code Generator component.
#Produces the customized static content for a STARK system

#Python Standard Library
import textwrap

def create():

    source_code = f"""\
    __pycache__/
    .DS_Store
    """
    return textwrap.dedent(source_code)