#STARK Code Generator component.
#Produces the customized static content for a STARK system

#Python Standard Library
import base64
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

import convert_friendly_to_system as converter

def create(data):

    #project = data["Project Name"]
    entity  = data["Entity"]
    cols    = data["Columns"]
    pk      = data["PK"]
    rel_model   = data["Rel Model"]

    #Convert human-friendly names to variable-friendly names
    entity_varname = converter.convert_to_system_name(entity)
    pk_varname     = converter.convert_to_system_name(pk)

    source_code  = cg_header.create(data, "View")
    source_code += cg_bodyhead.create(data, "View")

    source_code += f"""\
        
        <!--<div class="container-unauthorized" v-if="!stark_permissions['{entity}|View']">UNAUTHORIZED!</div>
        <div class="main-continer" v-if="stark_permissions['{entity}|View']"> -->
            <div class="container hidden" :style="{{visibility: visibility}}">
                <div class="row">
                    <div class="col">
                        <div class="my-auto">
                            <form class="border p-3">
                            <input type="hidden" id="orig_{pk_varname}" v-model="{entity_varname}.{pk_varname}">
                            <div class="form-group row">
                                <label for="{pk_varname}" class="col-sm-2 col-form-label">{pk}</label>
                                <div class="col-sm-10">
                                    <input type="text" class="form-control-plaintext" readonly id="{pk_varname}" placeholder="" v-model="{entity_varname}.{pk_varname}">
                                </div>
                            </div>"""

    for col, col_type in cols.items():
        col_varname = converter.convert_to_system_name(col)
        if isinstance(col_type, dict):
            if col_type["type"] == "relationship":
                has_one = col_type.get('has_one', '')
                has_many = col_type.get('has_many', '')
                has_many_ux = col_type.get('has_many_ux', None)

                if  has_one != '':
                    source_code += f"""
                            <div class="form-group row">
                                <label for="{col_varname}" class="col-sm-2 col-form-label">{col}</label>
                                <div class="col-sm-10">"""
                #simple 1-1 relationship
                    foreign_entity  = converter.convert_to_system_name(has_one)
                    source_code += f"""
                                    <input type="text" class="form-control-plaintext" readonly id="{foreign_entity}" placeholder="" v-model="{entity_varname}.{foreign_entity}">"""
                    source_code += f"""
                                </div>
                            </div>"""
                if  has_many != '':
                # 1-M relationship
                    foreign_entity  = converter.convert_to_system_name(has_many)
                    if has_many_ux == None:
                        source_code += f"""
                            <div class="form-group row">
                                <label for="{col_varname}" class="col-sm-2 col-form-label">{col}</label>
                                <div class="col-sm-10">
                                    <b-form-group label-for="tags-with-dropdown">
                                        <b-form-tags id="tags-with-dropdown" v-model="multi_select_values.{foreign_entity}" no-outer-focus class="mb-2">
                                            <template v-slot="{{ tags, disabled, addTag, removeTag }}">
                                                <ul v-if="tags.length > 0" class="list-inline d-inline-block mb-2">
                                                    <li v-for="tag in tags" :key="tag" class="list-inline-item">
                                                        <b-form-tag 
                                                            @remove="removeTag(tag)" 
                                                            :title="tag" 
                                                            :disabled="true" 
                                                            variant="info" >
                                                            {{{{ tag_display_text(tag) }}}}
                                                        </b-form-tag>
                                                    </li>
                                                </ul>
                                            </template>
                                        </b-form-tags>
                                    </b-form-group>
                                </div>
                            </div>"""  
                    else:
                        rel_pk = rel_model[has_many].get('pk')
                        rel_pk_varname = converter.convert_to_system_name(rel_pk)
                        child_entity_varname = converter.convert_to_system_name(foreign_entity)
                        source_code += f"""
                            <template>
                            <a v-b-toggle class="text-decoration-none" @click.prevent>
                                <span class="when-open"><img src="images/chevron-up.svg" class="filter-fill-svg-link" height="20rem"></span><span class="when-closed"><img src="images/chevron-down.svg" class="filter-fill-svg-link" height="20rem"></span>
                                <span class="align-bottom">{has_many}</span>
                            </a>
                            <b-collapse visible class="mt-0 mb-2 pl-2">
                                <div class="row">
                                    <div class="col-12">
                                        <div class="card">
                                            <div class="card-body">
                                                <form class="repeater" enctype="multipart/form-data">
                                                    <div class="row" v-for="(field, index) in many_entity.{child_entity_varname}.module_fields">
                                                        <div class="form-group">
                                                            <b-form-group class="form-group" label="#">
                                                                {{{{ index + 1 }}}}
                                                            </b-form-group>
                                                        </div>
                                                        <b-form-group class="form-group col-sm"  label="{rel_pk}" label-for="{rel_pk_varname}">
                                                            <b-form-input type="text" class="form-control" readonly id="{rel_pk_varname}" placeholder="" v-model="field.{rel_pk_varname}"></b-form-input>
                                                        </b-form-group>"""

                        for rel_col_key, rel_col_type in rel_model.get(has_many).get('data').items():
                            rel_col_varname = converter.convert_to_system_name(rel_col_key)
                            if isinstance(rel_col_type, dict) and rel_col_type["type"] == "file-upload":
                                source_code += f"""
                                                        <b-form-group class="form-group col-sm" label="{rel_col_key}" label-for="{rel_col_varname}">
                                                            <a :href="'https://'+ object_url_prefix + many_entity.{col_varname}.STARK_uploaded_s3_keys.{rel_col_varname}[index]">
                                                                <b-form-input type="text" class="form-control-link" readonly id="{rel_col_varname}" placeholder="" v-model="field.{rel_col_varname}">
                                                            </a>
                                                        </b-form-group>"""
                            else:
                                source_code += f"""
                                                        <b-form-group class="form-group col-sm" label="{rel_col_key}" label-for="{rel_col_varname}">
                                                            <b-form-input type="text" class="form-control" readonly id="{rel_col_varname}" placeholder="" v-model="field.{rel_col_varname}">
                                                        </b-form-group>"""

                        source_code += f"""
                                                    </div>
                                                </form>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </b-collapse>
                            <hr><br>
                            </template>"""
            elif col_type["type"] == 'file-upload':
                source_code += f""" 
                            <div class="form-group row">
                                <label for="{col_varname}" class="col-sm-2 col-form-label">{col}</label>
                                    <a :href="'https://'+ object_url_prefix + {entity_varname}.STARK_uploaded_s3_keys.{col_varname}">
                                        <span class="form-control-plaintext form-control-link" readonly id="{col_varname}" placeholder="" >{{{{{entity_varname}.{col_varname}}}}}</span>   
                                    </a>
                                    <template v-if="show_preview({entity_varname}.STARK_uploaded_s3_keys.{col_varname})">
                                    <img src="images/search.svg" id="{col_varname}_Preview" class ="ml-2" alt="">
                                        <b-tooltip target="{col_varname}_Preview" title="Preview" triggers="hover" placement="topright">
                                            <img :src="'https://'+ object_url_prefix + {entity_varname}.STARK_uploaded_s3_keys.{col_varname}" alt="" class="img-preview">
                                        </b-tooltip>
                                    </template>
                                </div>"""  
            else:
                source_code += f"""
                            <div class="form-group row">
                                <label for="{col_varname}" class="col-sm-2 col-form-label">{col}</label>
                                <div class="col-sm-10">
                                    <input type="text" class="form-control-plaintext" readonly id="{col_varname}" placeholder="" v-model="{entity_varname}.{col_varname}">
                                </div>
                            </div>"""
        else:
            source_code += f"""
                            <div class="form-group row">
                                <label for="{col_varname}" class="col-sm-2 col-form-label">{col}</label>
                                <div class="col-sm-10">
                                    <input type="text" class="form-control-plaintext" readonly id="{col_varname}" placeholder="" v-model="{entity_varname}.{col_varname}">
                                </div>
                            </div>"""
    source_code += f"""
                            <button type="button" class="btn btn-secondary" onClick="window.location.href='{entity_varname}.html'">Back</button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
        
    source_code += cg_loadmod.create()
    source_code += cg_footer.create()

    return textwrap.dedent(source_code)