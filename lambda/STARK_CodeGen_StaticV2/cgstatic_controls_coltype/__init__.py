#STARK Code Generator component.
#Produces HTML code for different controls, depending on column type

#Python Standard Library
import base64
import textwrap

#Private modules
import convert_friendly_to_system as converter

def create(data):

    col             = data['col']
    col_type        = data['col_type']
    col_varname     = data['col_varname']
    entity          = data['entity']
    entity_varname  = data['entity_varname']
    html_code       = ""
    is_many_control = data['is_many_control']
    state_control   = ""
    # rel_model       = data["Rel Model"]

    if isinstance(col_type, str):
        col_type = col_type.lower()

    if is_many_control:
        state_control = f':state="many_entity.{entity_varname}.validation_properties[index].{col_varname}.state"'
        field_entity_varname = 'field'
        file_upload_col_varname = f"{col_varname}[index]"
        js_object = f'many_entity.{entity_varname}'
        dot_compound = "."
        s3_upload_index_param = ", index"
        rel_list = f'many_{entity_varname}'
        date_picker = f':id="{col_varname}[index]"'
        preview_class = ""
        preview_tooltip = ""
    else:
        state_control = f':state="validation_properties.{col_varname}.state"'  
        field_entity_varname = entity_varname
        file_upload_col_varname = col_varname
        dot_compound = ""
        js_object = f'' 
        s3_upload_index_param = ""
        rel_list = f'root' 
        date_picker = f'id="{col_varname}"'
        preview_class = f':class="{{show_preview_icon:show_preview({field_entity_varname}.STARK_uploaded_s3_keys.{file_upload_col_varname})}}"'
        preview_tooltip = f'''
                        <template v-if="show_preview({field_entity_varname}.STARK_uploaded_s3_keys.{file_upload_col_varname})">        
                            <b-button style="width:5%"><img src="images/search.svg" id="{file_upload_col_varname}_Preview"></b-button>
                            <b-tooltip target="{file_upload_col_varname}_Preview" title="Preview" triggers="hover" placement="left">
                                <img :src="STARK_upload_elements.{file_upload_col_varname}.tmp_location" alt="" class="img-preview">
                            </b-tooltip>
                        </template>'''


    if col_type == "date":
        html_code=f"""<b-form-datepicker {date_picker} show-decade-nav v-model="{field_entity_varname}.{col_varname}" class="mb-2" {state_control}></b-form-datepicker>"""

    elif col_type == "time":
        html_code=f"""<b-form-timepicker id="{col_varname}" v-model="{field_entity_varname}.{col_varname}" class="mb-2" {state_control}></b-form-timepicker>"""

    elif col_type == "number":
        html_code=f"""<b-form-input type="number" class="form-control" id="{col_varname}" placeholder="" v-model="{field_entity_varname}.{col_varname}" {state_control}></b-form-input>"""

    elif col_type == "int":
        html_code=f"""<b-form-input type="number"  min="0" step="1" class="form-control" id="{col_varname}" placeholder="" v-model="{field_entity_varname}.{col_varname}" {state_control}></b-form-input>"""

    elif col_type in [ "yes-no", "boolean" ]:
        if col_type == "yes-no":
            checked   ="Yes"
            unchecked ="No"
        elif col_type == "boolean":
            checked   ="True"
            unchecked ="False"

        html_code=f"""<b-form-checkbox id="{col_varname}" v-model="{field_entity_varname}.{col_varname}" class="mb-2" value="{checked}" unchecked-value="{unchecked}" {state_control}>{{{{ {field_entity_varname}.{col_varname} }}}}</b-form-checkbox>"""

    elif col_type == "multi-line-string":
        html_code=f"""<b-form-textarea id="{col_varname}" v-model="{field_entity_varname}.{col_varname}" class="mb-2" rows="4" max-rows="8" {state_control}></b-form-textarea>"""

    elif isinstance(col_type, list):
        html_code=f"""
                        <b-form-select id="{col_varname}" v-model="{field_entity_varname}.{col_varname}" :options="lists.{col_varname}" {state_control}>
                            <template v-slot:first>
                                <b-form-select-option :value="null" disabled>-- Please select an option --</b-form-select-option>
                            </template>
                        </b-form-select>"""

    elif isinstance(col_type, dict):
        #These are the complex data types that need additional settings as part of their spec
        #   All col_type dicts follow this format:
        #       { "type": "columntype", "type-specific attrib1": "value", "type-specific attrib2": "value" }
        #   Only the "type" index is fixed. All the other indexes may vary depending on the column type specified

        #Spinbutton - useful as a user-friendly int chooser. 
        #   Can also be transformed to a generic string chooser, as long as the internal value is mapped to integers
        #       We should probably handle that as a different col type, though
        if col_type["type"] in [ "int-spinner", "decimal-spinner"]:

            spin_wrap = "wrap"
            spin_min  = 0

            if col_type["type"] == "int-spinner":
                spin_step = 1
                spin_max  = 99
            else:
                spin_step = 0.1
                spin_max  = 10
            
            if int(col_type.get('min', 0)) != 0:
                spin_min = int(col_type.get('min'))

            if int(col_type.get('max', 0)) != 0:
                spin_max = int(col_type.get('max'))

            if float(col_type.get('spin_step', 0)) != 0:
                spin_step = float(col_type.get('spin_step', 0))

            if col_type.get('wrap','') == "no-wrap":
                spin_wrap = ""

            html_code=f"""<b-form-spinbutton class="mb-2" id="{col_varname}" v-model="{field_entity_varname}.{col_varname}" {spin_wrap} min="{spin_min}" max="{spin_max}" step="{spin_step}" {state_control}>"""


        #Tags input - really user-friendly UX for multiple values in a field (think of the "To:" fields in email)
        #FIXME: This has more capabilities built-in, please add them here too (like validators and the other props)
        elif col_type["type"] == "tags":
            tag_limit = 5
            attribs_for_tags_list = ''
            datalist_helper = ''

            if int(col_type.get('limit', 0)) != 0:
                tag_limit = int(col_type.get('limit', 0))
            if col_type.get('values','') != '':
                #Do not include validator for now, that's for later sprint
                #attribs_for_tags_list = f""":input-attrs="{{ list: '{col_varname}-tags-list', autocomplete: 'off' }}" :tag-validator="validate_{field_entity_varname}" add-on-change"""
                attribs_for_tags_list = f""":input-attrs="{{ list: '{col_varname}-tags-list', autocomplete: 'off' }}" add-on-change"""
                datalist_helper = f"""<b-form-datalist id="{col_varname}-tags-list" :options="lists.{col_varname}"></b-form-datalist>"""

            html_code=f"""<b-form-tags input-id="{col_varname}" v-model="{field_entity_varname}.{col_varname}" :limit="{tag_limit}" remove-on-delete {attribs_for_tags_list} {state_control}></b-form-tags>"""

            if datalist_helper != '':
                html_code+=f"""
                            {datalist_helper}"""
            #FIXME: Eventually (later sprint) we may have to make datalist helper creation more generic (reusable by most other control types)

        #Rating - nice UI to give a 1-5 (or 1-N) feedback
        elif col_type["type"] == "rating":
            rating_max = 5

            if int(col_type.get('max', 0)) != 0:
                rating_max = int(col_type.get('max', 0))

            html_code=f"""<b-form-rating id="{col_varname}" v-model="{field_entity_varname}.{col_varname}" stars="{rating_max}" show-value {state_control}></b-form-rating>"""

        #A group of check boxes for multiple choice inputs
        elif col_type["type"] == "multiple choice":

            values = col_type.get('values', [])

            html_code=f"""<b-form-checkbox-group id="{col_varname}" v-model="{field_entity_varname}.{col_varname}" :options="lists.{col_varname}" {state_control}></b-form-checkbox-group>"""

        elif col_type["type"] in [ "radio button", "radio bar" ]:

            values  = col_type.get('values', [])
            buttons = ""

            #FIXME: no ugly hack needed once we use BootstrapVue b-form-group instead of basic Bootstrap form groups
            ugly_hack = "" #need for now to force radio bar to render under the label like the others, instead of beside the label
            if col_type["type"] == "radio bar":
                buttons = 'buttons button-variant="outline-secondary"'
                ugly_hack = "<br>"

            html_code=f"""{ugly_hack}<b-form-radio-group id="{col_varname}" v-model="{field_entity_varname}.{col_varname}" :options="lists.{col_varname}" {buttons} {state_control}></b-form-radio-group>"""
        elif col_type["type"] == "multi select combo":
            dropup_flag = col_type.get('dropup',"false") #dropup by default is false as for now, only reporting is using this property
            html_code =f"""<b-form-group label-for="tags-with-dropdown">
                                <b-form-tags id="tags-with-dropdown" v-model="multi_select_values.{col_varname}" no-outer-focus {state_control}>
                                    <template v-slot="{{ tags, disabled, addTag, removeTag, inputAttrs, inputHandlers}}">
                                        <b-form-tags style="border:0px" no-outer-focus input-id="{col_varname}" v-model="multi_select_values.{col_varname}" remove-on-delete :input-attrs="{{autocomplete: 'off' }}" add-on-change>
                                            <b-input-group>
                                                <input v-bind="inputAttrs" v-on="inputHandlers" class="form-control" v-model= "custom_report.{col_varname}.value" no-outer-focus @keyup.enter="custom_report.{col_varname}.value=''">
                                                <b-input-group-append>
                                                    <b-dropdown variant="outline-secondary" :dropup="{dropup_flag}" right no-flip ref="{col_varname}" >
                                                        <template #button-content>
                                                            <b-icon icon="tag-fill"></b-icon>
                                                        </template>
                                                        <b-dropdown-form @submit.stop.prevent="() => {{}}">
                                                            <b-form-group label="Search tags" label-for="tag-search-input" label-cols-sm="auto" class="mb-2" label-size="sm" :description="{col_varname}_search_desc" :disabled="disabled">
                                                                <b-form-input v-model="search.{col_varname}" id="tag-search-input" type="search" size="sm" style="width:500px" autocomplete="off" ></b-form-input>
                                                            </b-form-group>
                                                        </b-dropdown-form>
                                                        <b-dropdown-divider></b-dropdown-divider>
                                                        <b-dropdown-form style="max-height: 350px; overflow-y: scroll;">
                                                            <b-dropdown-item-button v-for="option in {col_varname}" :key="option" @click="onOptionClick({{ option, addTag }}, '{col_varname}')" >
                                                                {{{{ option.text }}}}
                                                            </b-dropdown-item-button>
                                                        </b-dropdown-form>
                                                        <b-dropdown-text v-if="{col_varname}.length === 0">
                                                            There are no tags available to select
                                                        </b-dropdown-text>
                                                    </b-dropdown>    
                                                </b-input-group-append>
                                            </b-input-group>
                                        </b-form-tags>  
                                        <ul v-if="tags.length > 0" class="list-inline d-inline-block">
                                            <li v-for="tag in tags" :key="tag" class="list-inline-item mt-2">
                                                <b-form-tag  @remove="removeTag(tag)"  :title="tag"  :disabled="disabled"  variant="info">
                                                    {{{{ tag }}}}
                                                </b-form-tag>
                                            </li>
                                        </ul>  
                                    </template>
                                </b-form-tags>
                            </b-form-group>
            """
        elif col_type["type"] == "file-upload":
            html_code=f"""<b-form-file {preview_class} v-model="{js_object}{dot_compound}STARK_upload_elements.{file_upload_col_varname}.file" :placeholder="{js_object}{dot_compound}STARK_upload_elements.{file_upload_col_varname}.file" drop-placeholder="Drop file here..." @input="{js_object}{dot_compound}s3upload('{col_varname}'{s3_upload_index_param})" v-b-hover="init_s3_access" onfocus="root.init_s3_access()" {state_control}></b-form-file>
                            {preview_tooltip}
                        <b-progress :value="{js_object}{dot_compound}STARK_upload_elements.{file_upload_col_varname}.progress_bar_val" :max="100" class="mt-2"></b-progress>"""
        elif col_type["type"] == "relationship":
            has_one = col_type.get('has_one', '')
            has_many = col_type.get('has_many', '')

            if  has_one != '':
                #simple 1-1 relationship
                foreign_entity  = converter.convert_to_system_name(has_one)

                html_code=f"""<b-form-select id="{col_varname}" v-model="{field_entity_varname}.{col_varname}" :options="lists.{col_varname}" onmouseover="root{dot_compound}{js_object}.list_{foreign_entity}()" onfocus="root{dot_compound}{js_object}.list_{foreign_entity}()" {state_control}>
                                <template v-slot:first>
                                    <b-form-select-option :value="null" disabled>-- Please select an option --</b-form-select-option>
                                </template>
                            </b-form-select>"""

            if  has_many != '':
                # 1-M relationship
                foreign_entity  = converter.convert_to_system_name(has_many)
                has_many_ux = col_type.get('has_many_ux', '')

                if has_many_ux == 'something':
                    #FIXME: placeholder for other design of has many
                    placeholder = "replace me with actual element design"
                elif has_many_ux == 'repeater':
                    #FIXME: placeholder for other design of has many for repeater
                    placeholder = ""
                else:
                    #default has many ux
                    #multi-select pill
                    html_code=f"""
                            <b-form-group label-for="tags-with-dropdown">
                                <b-form-tags id="tags-with-dropdown" v-model="multi_select_values.{foreign_entity}" no-outer-focus class="mb-2">
                                    <template v-slot="{{ tags, disabled, addTag, removeTag }}">
                                        <b-dropdown size="sm" variant="outline-secondary" block menu-class="w-50" right no-flip ref="{foreign_entity}" onmouseover="root.list_{foreign_entity}()" onfocus="root.list_{foreign_entity}()">
                                            <template #button-content>
                                                <b-icon icon="tag-fill"></b-icon> Choose {has_many.lower()}s
                                            </template>
                                            <b-dropdown-form @submit.stop.prevent="() => {{}}">
                                                <b-form-group label="Search {has_many.lower()}s" label-for="tag-search-input" label-cols-md="auto" class="mb-2" label-size="sm" :description="{foreign_entity}_search_desc" :disabled="disabled" >
                                                    <b-form-input v-model="search.{foreign_entity}" id="tag-search-input" type="search" size="sm" autocomplete="off"></b-form-input>
                                                </b-form-group>
                                            </b-dropdown-form>
                                            <b-dropdown-divider></b-dropdown-divider>
                                            <b-dropdown-form style="max-height: 350px; overflow-y: scroll;">
                                                <b-dropdown-item-button  v-for="option in {foreign_entity}" :key="option" @click="onOptionClick({{ option, addTag }},'{foreign_entity}')">
                                                    {{{{ option.text }}}}
                                                </b-dropdown-item-button>
                                            </b-dropdown-form>
                                            <b-dropdown-text v-if="{foreign_entity}.length === 0">
                                                There are no {has_many.lower()}s available to select
                                            </b-dropdown-text>
                                        </b-dropdown>
                                        <ul v-if="tags.length > 0" class="list-inline d-inline-block mt-1">
                                            <li v-for="tag in tags" :key="tag" class="list-inline-item">
                                                <b-form-tag @remove="removeTag(tag)" :title="tag" :disabled="disabled" variant="info" >{{{{ tag_display_text(tag) }}}}</b-form-tag>
                                            </li>
                                        </ul>
                                    </template>
                                </b-form-tags>
                            </b-form-group>"""
            
            

    else:
        html_code=f"""<b-form-input type="text" class="form-control" id="{col_varname}" placeholder="" v-model="{field_entity_varname}.{col_varname}" {state_control}></b-form-input>"""


                      

    return html_code


def create_list(data):

    col         = data['col']
    col_type    = data['col_type']
    col_varname = data['col_varname']
    js_code     = ""
    listable    = False

    if isinstance(col_type, str):
        col_type = col_type.lower()

    #We only make lists for specific column types and just return immediately for anything else
    print(col_type)
    if isinstance(col_type, list) or ( 
        isinstance(col_type, dict) and col_type["type"] in [ "multiple choice", "radio button", "radio bar", "multi select combo"] 
    ) or ( 
        isinstance(col_type, dict) and col_type["type"] == "relationship" and (col_type.get('has_one','') != '' or col_type.get('has_many','') != '')
    ) or (
        isinstance(col_type, dict) and col_type["type"] == "tags" and col_type.get('values','') != '' 
    ):
        listable = True

    if not listable: 
        return None

    ##############
    #Our list begins with a declaration of the list, based on the column's variable name
    js_code += f"""'{col_varname}': ["""

    if isinstance(col_type, list):
        for item in col_type:
            js_code += f"""
                        {{ value: '{item}', text: '{item}' }},"""

    elif isinstance(col_type, dict):
        items = col_type.get('values', [])

        for item in items:
            js_code += f"""
                        {{ value: '{item}', text: '{item}' }},"""


    #############
    #Close the list to end
    js_code += f"""
                    ],"""

    return js_code