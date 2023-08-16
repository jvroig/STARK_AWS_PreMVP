#STARK Code Generator component.
#Produces the customized static content for a STARK system

#Python Standard Library
import textwrap
import os
import importlib

#Private modules
prepend_dir = ""
if 'libstark' in os.listdir():
    prepend_dir = "libstark.STARK_CodeGen_Static."

cg_header   = importlib.import_module(f"{prepend_dir}cgstatic_html_generic_header")
cg_footer   = importlib.import_module(f"{prepend_dir}cgstatic_html_generic_footer")
cg_bodyhead = importlib.import_module(f"{prepend_dir}cgstatic_html_generic_bodyhead")
cg_loadmod  = importlib.import_module(f"{prepend_dir}cgstatic_html_generic_loadingmodal")
cg_loadspin = importlib.import_module(f"{prepend_dir}cgstatic_html_generic_loadingspinner")

def create(data):

    source_code  = cg_header.create(data, "HomePage")
    source_code += cg_bodyhead.create(data, "_HomePage")

    source_code += f"""\
            <template v-for="(group, index) in modules" id="groups-template">
                <!-- <b-button squared size="lg" v-b-toggle="'group-collapse-'+index" variant="light" class="mb-0 pl-2"> -->        
                <h4>
                    <a v-b-toggle class="text-decoration-none" :href="'#group-collapse-'+index" @click.prevent>
                        <span class="when-open"><img src="images/chevron-up.svg" class="filter-fill-svg-link" height="20rem"></span><span class="when-closed"><img src="images/chevron-down.svg" class="filter-fill-svg-link" height="20rem"></span>
                        <span class="align-bottom">{{{{ group.group_name }}}}</span>
                    </a>
                </h4>
                <!-- </b-button> -->
                <b-collapse :id="'group-collapse-'+index" visible class="mt-0 mb-2 pl-2">
                    <div class="d-flex align-content-start flex-wrap">
                        <template v-for="module in group.modules" id="modules-template">
                            <div class="card p-0 m-2 border module_card" id="modules_list" :onclick="'window.location.href=\\''  + module.href + '\\''">
                                <img class="card-img-top p-3 m-0 filter-fill-svg" :src="module.image" alt="Card image cap" height="100rem">
                                <div class="card-body bg-info p-2 rounded-bottom">
                                    <p class="card-text text-light font-weight-bold text-center">{{{{module.title}}}}</p>
                                </div>
                            </div>
                        </template>
                    </div>
                </b-collapse>
                <hr><br>
            </template>

        </div>
"""
    source_code += cg_loadspin.create()
    source_code += cg_loadmod.create()
    source_code += cg_footer.create()

    return textwrap.dedent(source_code)
