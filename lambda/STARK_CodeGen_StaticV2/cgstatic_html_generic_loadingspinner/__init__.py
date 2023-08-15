#STARK Code Generator component.
#Produces the customized static content for a STARK system

def create():

    source_code = f"""\
        <div class="d-flex justify-content-center" id="loading-spinner" :style="{{visibility: visibility}}">
            <div class="spinner-border" role="status">
                <span class="sr-only">Loading...</span>
            </div>
        </div>
"""

    return source_code
