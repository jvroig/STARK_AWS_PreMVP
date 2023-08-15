#This will handle all pre-launch tasks - final things to do after the entirety of the new system's infra and code have been deployed,
#   such as necessary system entries into the applicaiton's database (default user, permissions, list of modules, etc.)

#Python Standard Library
import datetime
import time
import os

#Extra modules
import yaml
import boto3
from pymongo import MongoClient

#Private modules
import convert_friendly_to_system as converter
import suggest_graphic as set_graphic
import get_relationship as get_rel

s3  = boto3.client('s3')
timestamp = int(time.time())

def lambda_handler(event, context):
    project_name    = event.get('ResourceProperties', {}).get('Project','')    
    ddb_table_name  = event.get('ResourceProperties', {}).get('DDBTable','')
    db_connection   = event.get('ResourceProperties', {}).get('DBConnection','')
    project_varname = converter.convert_to_system_name(project_name)
    client            = MongoClient(db_connection)
    mdb_database      = client[ddb_table_name]
    
    #Access Keys
    # WebBucket_AccessKeyID     = event.get('ResourceProperties', {}).get('WebBucket_AccessKeyID','')
    # WebBucket_SecretAccessKey = event.get('ResourceProperties', {}).get('WebBucket_SecretAccessKey','')

    #Cloud resources document
    codegen_bucket_name = os.environ['CODEGEN_BUCKET_NAME']
    response = s3.get_object(
        Bucket=codegen_bucket_name,
        Key=f'codegen_dynamic/{project_varname}/{project_varname}.yaml'
    )
    cloud_resources = yaml.safe_load(response['Body'].read().decode('utf-8')) 

    #Default password
    response = s3.get_object(
        Bucket=codegen_bucket_name,
        Key=f'codegen_dynamic/{project_varname}/default_password.txt'
    )
    def_password = response['Body'].read().decode('utf-8')

    models   = cloud_resources["Data Model"]
    entities = []
    for entity in models: entities.append(entity)    
    # print(entities)
    # print(entities[0])

    business_permissions = ''
    module_types = ['Add', 'Edit', 'Delete', 'View', 'Report']
    for entity in entities:
        for module_type in module_types:
            business_permissions = business_permissions + entity + '|' + module_type + ', '

    business_permissions = business_permissions[:-2]
    print(business_permissions)

    system_permissions = ''
    with open('system_modules.yml') as f:
        system_modules_raw = f.read()
        system_modules_yml = yaml.safe_load(system_modules_raw)

        for system_module in system_modules_yml:
            system_permissions = system_permissions + system_module + ', '

    system_permissions = system_permissions[:-2]  
    print(system_permissions)

    all_permissions = system_permissions + ', ' + business_permissions
    
    #################################
    #Create sequence table
    # for entity in entities:
    #     if "sequence" in models[entity]:
    #         pk              = entity
    #         current_counter = models[entity]['sequence']['current_counter']
    #         prefix          = models[entity]['sequence']['prefix']
    #         left_pad        = models[entity]['sequence']['left_pad']

    #         business_module                      = {}
    #         business_module['pk']                = {'S' : pk}
    #         business_module['sk']                = {'S' : "STARK|sequence"}
    #         business_module['Current_Counter']   =  str(current_countr
    #         business_module['Prefix']            = {'S' : prefix}
    #         business_module['Left_Pad']          = {'S' : str(left_pad)}
    #         business_module['STARK-ListView-sk'] = {'S' : pk}

    #         response = ddb.put_item(
    #             TableName=ddb_table_name,
    #             Item=business_module,
    #         )
    #         print(response)

    #################################
    #Create default user and password
    user = "root"    
    
    #FIXME: Default password is static right now, but in prod, this should be random each time and then saved to dev's local machine 
    #           (i.e., where he triggered the Stark CLI for the system generation request)
    # password = "welcome-2-STARK!"
    # hashed   = scrypt.create_hash(password)
    hashed = def_password

    item                     = {}
    item['_id']              =  user
    item['Role']             =  "Super Admin"
    item['Full_Name']        =  "The Amazing Mr. Root"
    item['Nickname']         =  "Root"
    item['Password_Hash']    =  hashed
    item['Last_Access']      =  str(datetime.datetime.now())
    item['Permissions']      =  ""
    item['STARK-Created-By'] =  "SYSTEM"
    item['STARK-Created-TS'] =  str(timestamp)

    collection = mdb_database["STARK_User"]
    collection.insert_one(item)

    #Module Group
    with open('module_group.yml') as f:
            module_group_raw = f.read()
            module_group_yml = yaml.safe_load(module_group_raw)

    module_group_list = []
    for module_group in module_group_yml:
        module_grp                      = {}
        module_grp['_id']                =  module_group
        module_grp['Description']       =  module_group_yml[module_group]["Description"]
        module_grp['Icon']              =  module_group_yml[module_group]["Icon"]
        module_grp['Priority']          =  module_group_yml[module_group]["Priority"]
        module_grp['STARK-Created-By']  =  "SYSTEM"
        module_grp['STARK-Created-TS']  =  str(timestamp)
        module_group_list.append(module_grp)

    collection = mdb_database["STARK_Module_Groups"]
    collection.insert_many(module_group_list)

    #System Modules
    with open('system_modules.yml') as f:
        system_modules_raw = f.read()
        system_modules_yml = yaml.safe_load(system_modules_raw)

    modules_list = []
    for system_modules in system_modules_yml:
        sys_modules                      = {}
        sys_modules['_id']               =  system_modules
        sys_modules['Target']            =  system_modules_yml[system_modules]["Target"]
        sys_modules['Descriptive_Title'] =  system_modules_yml[system_modules]["Descriptive_Title"]
        sys_modules['Description']       =  system_modules_yml[system_modules]["Description"]
        sys_modules['Module_Group']      =  system_modules_yml[system_modules]["Module_Group"]
        sys_modules['Is_Menu_Item']      =  system_modules_yml[system_modules]["Is_Menu_Item"]
        sys_modules['Is_Enabled']        =  system_modules_yml[system_modules]["Is_Enabled"]
        sys_modules['Icon']              =  system_modules_yml[system_modules]["Icon"]
        sys_modules['Image_Alt']         =  system_modules_yml[system_modules]["Image_Alt"]
        sys_modules['Priority']          =  system_modules_yml[system_modules]["Priority"]
        sys_modules['STARK-Created-By']  =  "SYSTEM"
        sys_modules['STARK-Created-TS']  =  str(timestamp)
        modules_list.append(sys_modules)


    
    for entity in entities:
        for module_type in module_types:
            pk = entity + '|' + module_type 
            entity_varname = converter.convert_to_system_name(entity)
            if module_type == 'View':
                target = entity_varname + '.html'
                title = entity
                is_menu_item = True
            else:
                target = entity_varname + '_' + module_type + '.html'
                title = module_type + ' ' + entity
                is_menu_item = False
            
            relationships = get_rel.get_relationship(models, entity, entity)
            for relationship in relationships.get('belongs_to', []):
                if relationship.get('rel_type') == 'has_many':
                    is_menu_item = False
                
            icon = 'images/' + set_graphic.suggest_graphic(entity)

            business_module                      = {}
            business_module['_id']               =  pk
            business_module['Target']            =  target
            business_module['Descriptive_Title'] =  title
            business_module['Description']       =  ""
            business_module['Module_Group']      =  "Default"
            business_module['Is_Menu_Item']      =  is_menu_item
            business_module['Is_Enabled']        =  True
            business_module['Icon']              =  icon
            business_module['Image_Alt']         =  ""
            business_module['Priority']          =  0
            business_module['STARK-Created-By']  =  "SYSTEM"
            business_module['STARK-Created-TS']  =  str(timestamp)
            modules_list.append(business_module)

    collection = mdb_database["STARK_Module"]
    collection.insert_many(modules_list)

    #User Permissions
    item                      = {}
    item['_id']               =  "root"
    item['Permissions']       =  all_permissions
    item['STARK-ListView-sk'] =  "root"
    item['STARK-Created-By']  =  "SYSTEM"
    item['STARK-Created-TS']  =  str(timestamp)

    collection = mdb_database["STARK_User_Permissions"]
    collection.insert_one(item)

    #User Roles
    user_roles_list = []
    item                      = {}
    item['_id']               =  "Super Admin"
    item['Description']       =  "Super Admin, all permissions"
    item['Permissions']       =  all_permissions
    item['STARK-Created-By']  =  "SYSTEM"
    item['STARK-Created-TS']  =  str(timestamp)
    user_roles_list.append(item)

    item                      = {}
    item['_id']               =  "Admin"
    item['Description']       =  "All system management permissions, no business permissions"
    item['Permissions']       =  system_permissions
    item['STARK-Created-By']  =  "SYSTEM"
    item['STARK-Created-TS']  =  str(timestamp)
    user_roles_list.append(item)

    item                      = {}
    item['_id']               = "General User"
    item['sk']                = "STARK|role"
    item['Description']       = "Business permissions only"
    item['Permissions']       = business_permissions
    item['STARK-Created-By']  =  "SYSTEM"
    item['STARK-Created-TS']  =  str(timestamp)
    user_roles_list.append(item)

    collection = mdb_database["STARK_User_Roles"]
    collection.insert_many(user_roles_list)




