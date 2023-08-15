#STARK Code Generator component.
#Produces the customized static content for a STARK system

#Python Standard Library
import base64
import textwrap

#Private modules
import convert_friendly_to_system as converter

def create(data, breadcrumb):

    project = data["Project Name"]
    
    if breadcrumb != "_HomePage":
        entity  = data["Entity"]
        #Convert human-friendly names to variable-friendly names
        entity_varname = converter.convert_to_system_name(entity)

    source_code = f"""\
        <body>
        <div id="mySidenav" class="sidenav">
            <a href="javascript:void(0)" class="closebtn" onclick="closeNav()">&times;</a>
            <template v-for="(group, index) in modules" id="nav-groups-template">
                <h4>
                    <a v-b-toggle class="text-decoration-none" :href="'#nav-group-collapse-'+index" @click.prevent>
                        <span class="when-open"><img src="images/chevron-up.svg" class="filter-fill-svg-link" height="20rem"></span>
                        <span class="when-closed"><img src="images/chevron-down.svg" class="filter-fill-svg-link" height="20rem"></span>
                        <span class="align-bottom">{{{{ group.group_name }}}}</span>
                    </a>
                </h4>
                <b-collapse :id="'nav-group-collapse-'+index" visible class="mt-0 mb-2 pl-2">
                    <div class="dropdown-container">
                        <template v-for="module in group.modules" id="nav-modules-template">
                            <div class="dropdown-btn" :onclick="'window.location.href=\\''  + module.href + '\\''">
                                <a href="#"><img class="filter-fill-svg" :src="module.image" alt="Card image cap" height="25rem"> {{{{module.title}}}} </a>
                            </div>
                        </template>
                    </div>
                </b-collapse>
            </template>
        </div>

        <div class="container-fluid" id="vue-root">

            <div class="row bg-primary mb-3 p-3 text-white" style="background-image: url('images/banner_generic_blue.png')">
                <div class="col-12 col-md-10">
                <h2>
                    <span id="main-burger-menu" style="cursor:pointer;" onclick="openNav()">&#9776;</span>
                    {project}
                </h2>
                </div>
                <div class="col-12 col-md-2 text-right">
                    <b-button 
                        v-b-tooltip.hover title="Settings"
                        class="mt-3" 
                        variant="light" 
                        size="sm">
                        <img src="images/settings.png" height="20px">
                    </b-button>
                    <b-button 
                        v-b-tooltip.hover title="Log out"
                        class="mt-3" 
                        variant="light" 
                        size="sm"
                        onClick="STARK.logout()">
                        <img src="images/logout.png" height="20px">
                    </b-button>
                </div>
            </div>
"""
    if breadcrumb == "_Listview":
        source_code += f"""\
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item"><a href="home.html">Home</a></li>
                    <li class="breadcrumb-item active" aria-current="page">{entity}</li>
                </ol>
            </nav>

"""
    elif breadcrumb == "_HomePage":
        source_code += f"""\
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item active" aria-current="page">Home</li>
                </ol>
            </nav>

"""
    else:
        source_code += f"""\
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item"><a href="home.html">Home</a></li>
                    <li class="breadcrumb-item"><a href="{entity_varname}.html">{entity}</a></li>
                    <li class="breadcrumb-item active" aria-current="page">{breadcrumb}</li>
                </ol>
            </nav>

"""

    return source_code
