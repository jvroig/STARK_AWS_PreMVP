#STARK Code Generator component.
#Produces the customized static content for a STARK system

def create():

    source_code = f"""\
        <div>
            <b-modal id="loading-modal"
                no-close-on-backdrop
                no-close-on-esc
                hide-header
                hide-footer
                centered
                size="sm">
                <div class="text-center p-3">
                    <div class="spinner-border" style="width: 5rem; height: 5rem" role="status">
                        <span class="sr-only">Loading...</span>
                    </div>
                    <div class="mt-3">
                        Loading...
                    </div>
                </div>
            </b-modal>
        </div>
"""

    return source_code
