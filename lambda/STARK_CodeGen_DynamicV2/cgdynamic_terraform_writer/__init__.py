##TODO: 
#1 resource group and locations are hardcoded using var.rgname and var.location for now. make it so that it will be 
#  using the resource group created through terraform and the location from the environment variable.
#2 make SAS start and end date dynamic
                             

import convert_friendly_to_system as converter
import textwrap

def compose_stark_tf_script(data):
    tf_script = []

    database_main_source_code = tf_writer_azure_config(data)
    tf_script.append({
        'filePath': "terraform/database/main.tf",
        'fileContent': database_main_source_code.encode()
    })

    resource_group_source_code = tf_writer_resource_group(data)
    tf_script.append({
        'filePath': "terraform/database/resource_group.tf",
        'fileContent': resource_group_source_code.encode()
    })

    # MongoDB 
    db_source_code = tf_writer_cosmosdb_account(data)
    tf_script.append({
        'filePath': "terraform/database/database.tf",
        'fileContent': db_source_code.encode()
    }) 

    business_modules_collection = tf_writer_cosmosdb_business_modules(data)
    tf_script.append({
        'filePath': "terraform/database/business_modules_collection.tf",
        'fileContent': business_modules_collection.encode()
    })
    
    stark_modules_collection = tf_writer_cosmosdb_stark_modules(data)
    tf_script.append({
        'filePath': "terraform/database/stark_modules_collection.tf",
        'fileContent': stark_modules_collection.encode()
    })

    main_source_code = tf_writer_azure_config(data)
    tf_script.append({
        'filePath': "terraform/main.tf",
        'fileContent': main_source_code.encode()
    })

    # Static Site Hosting
    data["type"] = "static"
    data["storage_account_name"] = converter.convert_to_system_name(data['project_name'], 'az-storage-account')
    storage_source_code = ""
    storage_source_code += tf_writer_storage_account(data)

    tf_script.append({
        'filePath': "terraform/static_site_hosting.tf",
        'fileContent': storage_source_code.encode()
    })

    # API Gateway
    api_management_source_code = ""
    api_management_source_code += tf_writer_api_management(data)
    api_management_source_code += tf_writer_api_management_operations(data)

    tf_script.append({
        'filePath': "terraform/api_management.tf",
        'fileContent': api_management_source_code.encode()
    })

    # Functions
    functions_source_code = ""
    data["type"] = "zip-deploy"
    data["storage_account_name"] = converter.convert_to_system_name(data['project_name'], 'az-storage-account')
    functions_source_code += tf_writer_storage_account(data)
    functions_source_code += tf_writer_function_app(data)

    tf_script.append({
        'filePath': "terraform/functions.tf",
        'fileContent': functions_source_code.encode()
    })

    ## Variables
    var_source_code = tf_writer_variables(data)
    tf_script.append({
        'filePath': "terraform/variables.tf",
        'fileContent': var_source_code.encode()
    })


    return tf_script

def tf_writer_azure_config(data):

    ##FIXME: must find a way to make sure azurerm is using the latest version
    source_code = f"""
    # Configure the Azure provider
    terraform {{
        required_providers {{
            azurerm = {{
            source  = "hashicorp/azurerm"
            version = "~> 3.45"
            }}
        }}

        required_version = ">= 1.1.0"
    }}

    provider "azurerm" {{
        features {{}}
    }}

    variable "rglocation" {{
        type = string 
        default = "Southeast Asia"
    }}
    
    """
    
    return textwrap.dedent(source_code)

def tf_writer_resource_group(data):
    source_code = f"""
     resource "azurerm_resource_group" "stark_rg" {{
        name     = "{data['stark_resource_group_name']}"
        location = var.rglocation
    }}
    
    """

    return textwrap.dedent(source_code)

def tf_writer_storage_account(data):
    project_name = data["project_name"]
    type = data["type"] ##zip deployment for function or for static website

    resource_name = data['storage_account_name']
    source_code = f"""
    resource "azurerm_storage_account" "{resource_name}" {{
        name                     = "{resource_name}"
        resource_group_name      = var.rgname
        location                 = "westus"
        account_tier             = "Standard"
        account_replication_type = "LRS"
    """

    if type == "static":
        source_code += f"""
        #STATIC WEBSITE SETTINGS
        static_website {{
            index_document     = "index.html"
            error_404_document = "error.html"
        }}
    }}

    locals {{
        mime_types = {{
            "css"  = "text/css"
            "html" = "text/html"
            "ico"  = "image/vnd.microsoft.icon"
            "js"   = "application/javascript"
            "json" = "application/json"
            "map"  = "application/json"
            "png"  = "image/png"
            "svg"  = "image/svg+xml"
            "txt"  = "text/plain"
        }}
    }}

    resource "azurerm_storage_blob" "static_blobs" {{
        for_each        = fileset("../static", "**/*.*")
        name                   = "${{each.value}}"
        type                   = "Block"
        source                 = "../static/${{each.value}}"
        storage_account_name   = azurerm_storage_account.{resource_name}.name
        storage_container_name = "$web"
        content_type = lookup(tomap(local.mime_types), element(split(".", each.value), length(split(".", each.value)) - 1))
    }}
    
    
    output "static_website_url" {{
        description = "static site url"
        value       = azurerm_storage_account.{resource_name}.primary_web_endpoint
    }}
    """
    else:
        source_code += f"""
    }}
    resource "azurerm_storage_container" "{resource_name}-container" {{
        name                  = "{resource_name}-container"
        storage_account_name  = azurerm_storage_account.{resource_name}.name
        container_access_type = "private"
    }}
    """
    
    return textwrap.dedent(source_code)

def tf_writer_cosmosdb_account(data):
    project_name = converter.convert_to_system_name(data["project_name"], "az-cosmos-db") 
    source_code = f"""

    resource "azurerm_cosmosdb_account" "stark_storage_account" {{
        name                 = "{project_name}"
        location             = var.rglocation
        resource_group_name  = azurerm_resource_group.stark_rg.name
        offer_type           = "Standard"
        kind                 = "MongoDB"
        mongo_server_version = 4.2
        consistency_policy {{
            consistency_level = "Session"
        }}

        geo_location {{
            location          = var.rglocation
            failover_priority = 0
        }}

        capabilities {{
            name = "EnableServerless"
        }}

        tags = {{
            environment = "dev"
        }}
    }}

    resource "azurerm_cosmosdb_mongo_database" "db_name" {{
        name                = "{project_name}-mongodb"
        resource_group_name = azurerm_resource_group.stark_rg.name
        account_name        = azurerm_cosmosdb_account.stark_storage_account.name
    }}

    output "mongodb_database_name" {{
        description = "Database name of the MongoDB instance"
        value       = azurerm_cosmosdb_mongo_database.db_name.name
    }}

    output "mongodb_connection_string" {{
        sensitive = true
        description = "Connection string for the MongoDB instance"
        value       = azurerm_cosmosdb_account.stark_storage_account.connection_strings[0]
    }}    
    """
    
    return textwrap.dedent(source_code)

def tf_writer_cosmosdb_business_modules(data):
    project_name = data["project_name"]
    entities = data["entities"]
    source_code = "##Business Modules"
    for entity in entities: 
        entity_varname = converter.convert_to_system_name(entity) 
        source_code += f"""
    resource "azurerm_cosmosdb_mongo_collection" "stark_{entity_varname}_collection" {{
        name                = "{entity_varname}"
        resource_group_name = azurerm_resource_group.stark_rg.name
        account_name        = azurerm_cosmosdb_account.stark_storage_account.name
        database_name       = azurerm_cosmosdb_mongo_database.db_name.name

        index {{
            keys    = ["_id"]
            unique = true
        }}

    }}
        """
    return textwrap.dedent(source_code)

def tf_writer_cosmosdb_stark_modules(data):    
    source_code = f"""

    ##STARK Modules
    resource "azurerm_cosmosdb_mongo_collection" "stark_user_collection" {{
        name                = "STARK_User"
        resource_group_name = azurerm_resource_group.stark_rg.name
        account_name        = azurerm_cosmosdb_account.stark_storage_account.name
        database_name       = azurerm_cosmosdb_mongo_database.db_name.name

        index {{
            keys    = ["_id"]
            unique = true
        }}

    }}

    resource "azurerm_cosmosdb_mongo_collection" "stark_user_roles_collection" {{
        name                = "STARK_User_Roles"
        resource_group_name = azurerm_resource_group.stark_rg.name
        account_name        = azurerm_cosmosdb_account.stark_storage_account.name
        database_name       = azurerm_cosmosdb_mongo_database.db_name.name

        index {{
            keys    = ["_id"]
            unique = true
        }}

    }}

    resource "azurerm_cosmosdb_mongo_collection" "stark_modules_collection" {{
        name                = "STARK_Module"
        resource_group_name = azurerm_resource_group.stark_rg.name
        account_name        = azurerm_cosmosdb_account.stark_storage_account.name
        database_name       = azurerm_cosmosdb_mongo_database.db_name.name

        index {{
            keys    = ["_id"]
            unique = true
        }}

    }}

    resource "azurerm_cosmosdb_mongo_collection" "stark_module_groups_collection" {{
        name                = "STARK_Module_Groups"
        resource_group_name = azurerm_resource_group.stark_rg.name
        account_name        = azurerm_cosmosdb_account.stark_storage_account.name
        database_name       = azurerm_cosmosdb_mongo_database.db_name.name

        index {{
            keys    = ["_id"]
            unique = true
        }}

    }}

    resource "azurerm_cosmosdb_mongo_collection" "stark_user_permissions_collection" {{
        name                = "STARK_User_Permissions"
        resource_group_name = azurerm_resource_group.stark_rg.name
        account_name        = azurerm_cosmosdb_account.stark_storage_account.name
        database_name       = azurerm_cosmosdb_mongo_database.db_name.name

        index {{
            keys    = ["_id"]
            unique = true
        }}

    }}

    resource "azurerm_cosmosdb_mongo_collection" "stark_user_sessions_collection" {{
        name                = "STARK_User_Sessions"
        resource_group_name = azurerm_resource_group.stark_rg.name
        account_name        = azurerm_cosmosdb_account.stark_storage_account.name
        database_name       = azurerm_cosmosdb_mongo_database.db_name.name

            index {{
                keys    = ["_id"]
                unique = true
            }}

        }}

    """
    
    return textwrap.dedent(source_code)

def tf_writer_function_app(data):
    project_name = data["project_name"]
    storage_account_name = data['storage_account_name']
    function_app_name = converter.convert_to_system_name(project_name, 'az-cosmos-db') 

    source_code = f"""
    data "archive_file" "functions" {{
        type        = "zip"
        source_dir  = "../functions_package"
        output_path = "../functions_package.zip"
    }}

    resource "azurerm_storage_blob" "function-zip-blob" {{
        name                   = "functions-${{substr(data.archive_file.functions.output_md5, 0, 6)}}.zip"
        type                   = "Block"
        source                 = "../functions_package.zip"
        content_md5            = data.archive_file.functions.output_md5
        storage_account_name   = azurerm_storage_account.{storage_account_name}.name
        storage_container_name = azurerm_storage_container.{storage_account_name}-container.name
        content_type           = "application/zip"
    }}

    
    data "azurerm_storage_account_blob_container_sas" "blob_container_sas" {{
        connection_string = azurerm_storage_account.{storage_account_name}.primary_connection_string
        container_name    = azurerm_storage_container.{storage_account_name}-container.name
        https_only = true
        start = "2023-03-21"
        expiry = "2028-03-21"
        permissions {{
            read = true
            write = false
            delete = false
            list = false
            add = false
            create = false
        }}
    }}
    
    resource "azurerm_service_plan" "{project_name}_sp" {{
        name                = "{project_name}_sp"
        location            = var.rglocation
        resource_group_name = var.rgname
        os_type             = "Linux"
        sku_name            = "Y1"
    }}

    resource "azurerm_application_insights" "{project_name}_ai" {{
        name                = "{project_name}_ai"
        location            = var.rglocation
        resource_group_name = var.rgname
        application_type    = "other"
    }}

    resource "azurerm_linux_function_app" "starkzipdeployment" {{
        name                = "{function_app_name}-zip-deploy"
        location            = var.rglocation
        resource_group_name = var.rgname
        service_plan_id     = azurerm_service_plan.{project_name}_sp.id

        storage_account_name       = azurerm_storage_account.{storage_account_name}.name
        storage_account_access_key = azurerm_storage_account.{storage_account_name}.primary_access_key

            app_settings = {{
            FUNCTIONS_WORKER_RUNTIME                   = "python"
            APPINSIGHTS_INSTRUMENTATIONKEY             = azurerm_application_insights.{project_name}_ai.instrumentation_key
            ApplicationInsightsAgent_EXTENSION_VERSION = "~3"
            WEBSITE_CONTENTAZUREFILECONNECTIONSTRING   = azurerm_storage_account.{storage_account_name}.primary_connection_string
            WEBSITE_RUN_FROM_PACKAGE                   = "${{azurerm_storage_blob.function-zip-blob.url}}${{data.azurerm_storage_account_blob_container_sas.blob_container_sas.sas}}"
            PYTHON_ENABLE_WORKER_EXTENSIONS            = 1
            }}

        site_config {{
            cors {{
                allowed_origins = ["*"]
            }}
            application_stack {{
                python_version = "3.9"
            }}
        }}
    }}
    """
    
    return textwrap.dedent(source_code)

def tf_writer_api_management(data):
    
    project_name = data["project_name"]
    api_name = data['api_name']
    sku_name = "Consumption_0" ##Configuration for serverless implementation
    storage_account_name = data['storage_account_name']
    source_code = f"""
    resource "azurerm_api_management" "{project_name}" {{
        name                = "{api_name}"
        location            = var.rglocation
        resource_group_name = var.rgname
        publisher_name      = "My Company"
        publisher_email     = "company@terraform.io"
        sku_name            = "{sku_name}"
    }}

    resource "azurerm_api_management_api" "{project_name}" {{
        for_each = var.function_map
        name                = "api-integrate-${{each.value.name}}"
        display_name        = "${{each.value.name}} Integration in API Management"
        path                = "${{each.value.name}}"
        resource_group_name = var.rgname
        api_management_name = azurerm_api_management.{project_name}.name
        revision            = 1
        protocols           = ["https", "http"]
        service_url         = "https://${{azurerm_linux_function_app.starkzipdeployment.default_hostname}}/api/${{each.value.name}}"
        subscription_required = false
        depends_on = [
            azurerm_storage_account.{storage_account_name}
        ]
    }}


    """
    return textwrap.dedent(source_code)

def tf_writer_api_management_operations(data):
    project_name = data["project_name"]
    storage_account_name = data['storage_account_name']
    source_code = f"""

    resource "azurerm_api_management_api_operation" "post_operation" {{
        for_each = var.function_map
        operation_id          = "${{each.value.name}}-post"
        api_name              = azurerm_api_management_api.{project_name}[each.value.name].name
        display_name          = "${{each.value.name}} API"
        method                = "POST"
        url_template          = ""
        api_management_name   = azurerm_api_management.{project_name}.name
        resource_group_name   = var.rgname
        description           = "${{each.value.name}} api"
    
    }}

    resource "azurerm_api_management_api_operation" "get_operation" {{
        for_each = var.function_map
        operation_id          = "${{each.value.name}}-get"
        api_name              = azurerm_api_management_api.{project_name}[each.value.name].name
        display_name          = "${{each.value.name}} API"
        method                = "GET"
        url_template          = ""
        api_management_name   = azurerm_api_management.{project_name}.name
        resource_group_name   = var.rgname
        description           = "${{each.value.name}} api"
    
    }}

    resource "azurerm_api_management_api_operation" "put_operation" {{
        for_each = var.function_map
        operation_id          = "${{each.value.name}}-put"
        api_name              = azurerm_api_management_api.{project_name}[each.value.name].name
        display_name          = "${{each.value.name}} API"
        method                = "PUT"
        url_template          = ""
        api_management_name   = azurerm_api_management.{project_name}.name
        resource_group_name   = var.rgname
        description           = "${{each.value.name}} api"
    
    }}

    resource "azurerm_api_management_api_operation" "delete_operation" {{
        for_each = var.function_map
        operation_id          = "${{each.value.name}}-delete"
        api_name              = azurerm_api_management_api.{project_name}[each.value.name].name
        display_name          = "${{each.value.name}} API"
        method                = "DELETE"
        url_template          = ""
        api_management_name   = azurerm_api_management.{project_name}.name
        resource_group_name   = var.rgname
        description           = "${{each.value.name}} api"
    
    }}

    resource "azurerm_api_management_api" "access_api" {{
        for_each            = var.access_api
        name                = "api-integrate-${{each.value.name}}"
        display_name        = "${{each.value.name}} Integration in API Management"
        path                = "${{each.value.name}}"
        resource_group_name = var.rgname
        api_management_name = azurerm_api_management.{project_name}.name
        revision            = 1
        protocols           = ["https", "http"]
        service_url         = "https://${{azurerm_linux_function_app.starkzipdeployment.default_hostname}}/api/${{each.value.name}}?"
        subscription_required = false
    }}

    resource "azurerm_api_management_api_operation" "access_operations" {{
        for_each              = var.access_api
        operation_id          = "${{each.value.name}}"
        api_name              = azurerm_api_management_api.access_api[each.value.name].name
        display_name          = "${{each.value.name}} API"
        method                = "POST"
        url_template          = ""
        api_management_name   = azurerm_api_management.{project_name}.name
        resource_group_name   = var.rgname
        description           = "${{each.value.name}} API operations"
    
    }}

    resource "azurerm_api_management_api_policy" "access_cors" {{
        for_each = var.access_api
        api_name            = azurerm_api_management_api_operation.access_operations[each.value.name].api_name
        api_management_name = azurerm_api_management.{project_name}.name
        resource_group_name = var.rgname

        xml_content = <<XML
        <policies>
            <inbound>
                <base />
                <cors allow-credentials="true">
                    <allowed-origins>
                        <origin>${{azurerm_storage_account.{storage_account_name}.primary_web_endpoint}}</origin>
                        <origin>http://localhost</origin>
                    </allowed-origins>
                    <allowed-methods preflight-result-max-age="200">
                        <method>POST</method>
                    </allowed-methods>
                    <allowed-headers>
                        <header>content-type</header>
                    </allowed-headers>
                </cors>
            </inbound>
            <backend>
                <base />
            </backend>
            <outbound>
                <base />
            </outbound>
            <on-error>
                <base />
            </on-error>
        </policies>
        XML

    }}

    resource "azurerm_api_management_api_policy" "api_cors" {{
        for_each = var.function_map
        api_name            = azurerm_api_management_api_operation.post_operation[each.value.name].api_name
        api_management_name = azurerm_api_management.{project_name}.name
        resource_group_name = var.rgname

        xml_content = <<XML
        <policies>
            <inbound>
                <base />
                <cors allow-credentials="true">
                    <allowed-origins>
                        <origin>${{azurerm_storage_account.{storage_account_name}.primary_web_endpoint}}</origin>
                        <origin>http://localhost</origin>
                    </allowed-origins>
                    <allowed-methods preflight-result-max-age="200">
                        <method>GET</method>
                        <method>POST</method>
                        <method>PUT</method>
                        <method>DELETE</method>
                    </allowed-methods>
                    <allowed-headers>
                        <header>content-type</header>
                    </allowed-headers>
                </cors>
                <choose>
                    <!--
                        If a cache miss call external authorizer
                    -->
                    <when condition="@(!context.Variables.ContainsKey("status"))">
                        <!-- Invoke -->
                        <send-request mode="new" response-variable-name="response" timeout="10" ignore-error="false">
                            <set-url>https://${{azurerm_linux_function_app.starkzipdeployment.default_hostname}}/api/authorizer_default?</set-url>
                            <set-method>GET</set-method>
                            <set-header name="Authorization" exists-action="override">
                                <value>@(context.Request.Headers.GetValueOrDefault("Authorization"))</value>
                            </set-header>
                            <set-header name="Cookie" exists-action="override">
                                <value>@(context.Request.Headers.GetValueOrDefault("Cookie"))</value>
                            </set-header>
                        </send-request>
                        <!-- Extract authorization status from authorizer's response -->
                        <set-variable name="response-body" value="@(((IResponse)context.Variables["response"]).Body.As<JObject>())" />
                        <trace source="MyTraceSource" severity="information">
                            <message>@("Newly fetched " +((JObject)context.Variables["response-body"]).ToString())</message>
                        </trace>
                        <set-variable name="status" value="@(((JObject)context.Variables["response-body"])["isAuthorized"].ToString())" />
                        <set-variable name="username" value="@(((JObject)((JObject)context.Variables["response-body"])["context"])["Username"].ToString())" />

                        <!-- Cache authorization result -->
                        <set-header name="x-STARK-Username" exists-action="override">
                            <value>@((string)context.Variables["username"])</value>
                        </set-header>
                        <trace source="MyTraceSource" severity="information">
                            <message>@((string)context.Variables["status"] + " : " + " : " + (string)context.Variables["username"])</message>
                        </trace>
                        <cache-store-value key="@(context.Request.Headers.GetValueOrDefault("Authorization"))" value="@((string)context.Variables["username"])" duration="5" />
                    </when>
                </choose>
                <choose>
                    <when condition="@((string)context.Variables["status"] == "403")">
                        <return-response>
                            <set-status code="403" reason="Forbidden" />
                        </return-response>
                    </when>
                </choose>
            </inbound>
            <backend>
                <base />
            </backend>
            <outbound>
                <base />
            </outbound>
            <on-error>
                <base />
            </on-error>
        </policies>
        XML

    }}

    """
    return textwrap.dedent(source_code)

def tf_writer_variables(data):
    entities = data["entities"]
    stark_entities = [
            "STARK_Module",
            "STARK_Module_Groups", 
            "STARK_User" ,
            "STARK_User_Permissions", 
            "STARK_User_Roles",
            "STARK_User_Sessions" 
    ]
    combined_entities = entities + stark_entities
    source_code = f"""\
        variable "rgname" {{
            type = string
            default = "{data['stark_resource_group_name']}"
        }}

        variable "origin" {{
            type = string
            default = "test for now"
        }}

        variable "access_api" {{
            type    = map(object({{
                name = string
            }}))
            default = {{
                "stark_login" = {{
                name = "stark_login"
                }},
                "stark_logout" = {{
                name = "stark_logout"
                }}
            }}
        }}

        variable "function_map" {{
            type    = map(object({{
                name = string
            }}))
            default = {{"""
    for entity in combined_entities: 
        entity_varname = converter.convert_to_system_name(entity) 
        source_code += f"""
                "{entity_varname}" = {{
                name = "{entity_varname}"
                }},
        """
    source_code += f"""
                "stark_auth" = {{
                name = "stark_auth"
                }}
            }}
        }}
    """
    return textwrap.dedent(source_code)