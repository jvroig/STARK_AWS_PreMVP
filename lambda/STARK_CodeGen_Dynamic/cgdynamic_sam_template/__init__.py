#STARK Code Generator component.
#Produces the customized dynamic content for a STARK system
#This creates the SAM template.yml file to create the end-user's system infra

#Python Standard Library
import base64
from html import entities
import json
import os
import textwrap
from uuid import uuid4

#Extra modules
import yaml
import boto3

#Private modules
import convert_friendly_to_system as converter


def create(data, cli_mode=False):

    cloud_resources = data['cloud_resources']

    #Get environment type - this will allow us to take different branches depending on whether we are LOCAL or PROD (or any other future valid value)
    ENV_TYPE = os.environ['STARK_ENVIRONMENT_TYPE']
    if ENV_TYPE == "PROD" or cli_mode == True:
        default_response_headers = { "Content-Type": "application/json" }
        s3  = boto3.client('s3')

        if cli_mode == True:
            cleaner_service_token   = data['Cleaner_ARN']
            prelaunch_service_token = data['Prelaunch_ARN']
            cicd_bucket_name        = data['CICD_Bucket_Name']
            codegen_bucket_name     = data['CodeGen_Bucket_Name']
        else:
            codegen_bucket_name = os.environ['CODEGEN_BUCKET_NAME']

            response = s3.get_object(
                Bucket=codegen_bucket_name,
                Key=f'STARKConfiguration/STARK_config.yml'
            )
            config = yaml.safe_load(response['Body'].read().decode('utf-8'))
            cleaner_service_token   = config['Cleaner_ARN']
            prelaunch_service_token = config['Prelaunch_ARN']
            cicd_bucket_name        = config['CICD_Bucket_Name']

    else:
        #We only have to do this because `SAM local start-api` doesn't follow CORS info from template.yml, which is bullshit
        default_response_headers = {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        }
        codegen_bucket_name      = "codegen-fake-local-bucket"
        cleaner_service_token    = "CleanerService-FakeLocalToken"


    #Get Project Name
    #FIXME: Project Name is used here as unique identifier. For now it's a user-supplied string, which is unreliable
    #       as a unique identifier. Make this a GUID for prod use.
    #       We do still need a user-supplied project name for display purposes (header of each HTML page, login screen, etc), though.
    project_name      = cloud_resources["Project Name"]
    project_varname   = converter.convert_to_system_name(project_name)
    project_stackname = converter.convert_to_system_name(project_name, 'cf-stack')

    ###############################################################################################################
    #Load and sanitize data here, for whatever IaC rules that govern them (e.g., S3 Bucket names must be lowercase)

    #S3-related data
    s3_bucket_name           = cloud_resources["S3 webserve"]["Bucket Name"].lower()
    s3_raw_bucket_name       = cloud_resources["S3 webserve"]["Analytics Buckets"]["raw"].lower()
    s3_processed_bucket_name = cloud_resources["S3 webserve"]["Analytics Buckets"]["processed"].lower()
    s3_athena_bucket_name    = cloud_resources["S3 webserve"]["Analytics Buckets"]["athena"].lower()
    s3_error_document        = cloud_resources["S3 webserve"]["Error Document"]
    s3_index_document        = cloud_resources["S3 webserve"]["Index Document"]

    #DynamoDB-related data
    ddb_table_name            = cloud_resources["DynamoDB"]['Table Name']
    ddb_capacity_type         = cloud_resources["DynamoDB"]['Capacity Type'].upper()
    ddb_surge_protection      = cloud_resources["DynamoDB"]['Surge Protection']
    ddb_surge_protection_fifo = cloud_resources["DynamoDB"]['Surge Protection FIFO']
    ddb_rcu_provisioned       = cloud_resources["DynamoDB"].get("RCU", 0)
    ddb_wcu_provisioned       = cloud_resources["DynamoDB"].get("WCU", 0)
    ddb_auto_scaling          = cloud_resources["DynamoDB"].get("Auto Scaling", '')

    #CloudFront distribution config
    cdn_distribution_config = cloud_resources.get('CloudFront', '')
    cdn_price_class         = "PriceClass_" + str(cdn_distribution_config.get('price_class',"200"))
    cdn_enabled             = cdn_distribution_config.get('enabled','')
    cdn_default_root_object = cdn_distribution_config.get('default_root_object','')
    cdn_custom_domain_name  = cdn_distribution_config.get('custom_domain_name','')
    cdn_viewer_certificate  = cdn_distribution_config.get('viewer_certificate_arn','')

    #Analytics config
    analytics_config    = cloud_resources.get('Analytics', '')
    analytics_enabled   = analytics_config.get('enabled', False)
    analytics_activated = analytics_config.get('activated', False)
    analytics_cron      = analytics_config.get('cron','')

    #Lambda-related data
    entities = cloud_resources['Data Model']


    #FIXME: Should this transformation be here or in the Parser?
    #Let this remain here now, but probably should be the job of the parser in the future.
    if ddb_capacity_type != "PROVISIONED":
        ddb_capacity_type = "PAY_PER_REQUEST"

    #Some default values not yet from the Parser, but should be added to Parser later
    s3_versioning     = "Enabled"
    s3_access_control = "PublicRead"

    #User and access key related config
    web_bucket_user = "stark_" + project_varname + "_web_bucket"

    #Update Token - this token forces CloudFormation to update the resources that do dynamic code generation,
    update_token = str(uuid4())

    #Initialize our template
    #This is where we can use triple-quoted f-strings + textwrap.dedent(), instead of manually placing tabs and nl, unreadable!
    #The forward slash ( \ ) is so that we don't have an empty blank line at the top of our resulting file.
    #FIXME: instead of a RegionMap Mappings section here, can we just use pure python to handle the inconsistency in S3 website endpoints?
    #       Perhaps the prepackaged boto3 in Lambda already has region info baked in, we can then simplify this CF template and handle the
    #       inconsistency in S3 endpoints like we did in STARK_Deploy_Check 
    cf_template = f"""\
    AWSTemplateFormatVersion: '2010-09-09'
    Transform: AWS::Serverless-2016-10-31
    Description: STARK-generated serverless application, Project [{project_name}]
    Parameters:
        UserCICDPipelineBucketNameParameter:
            Type: String
            Description: Name for user bucket that will be used for the default STARK CI/CD pipeline.
        UserWebsiteBucketNameParameter:
            Type: String
            Description: Name for user bucket that will be used as the website bucket for the project.
    Mappings:
        RegionMap:
            us-east-2:
                s3endpoint: "s3-website.us-east-2.amazonaws.com"
                s3bucket: "s3.us-east-2.amazonaws.com"
            us-east-1:
                s3endpoint: "s3-website-us-east-1.amazonaws.com"
                s3bucket: "s3-us-east-1.amazonaws.com"
            us-west-1:
                s3endpoint: "s3-website-us-west-1.amazonaws.com"
                s3bucket: "s3-us-west-1.amazonaws.com"
            us-west-2:
                s3endpoint: "s3-website-us-west-2.amazonaws.com"
                s3bucket: "s3-us-west-2.amazonaws.com"
            af-south-1:
                s3endpoint: "s3-website.af-south-1.amazonaws.com"
                s3bucket: "s3.af-south-1.amazonaws.com"
            ap-east-1:
                s3endpoint: "s3-website.ap-east-1.amazonaws.com"
                s3bucket: "s3.ap-east-1.amazonaws.com"
            ap-south-1:
                s3endpoint: "s3-website.ap-south-1.amazonaws.com"
                s3bucket: "s3.ap-south-1.amazonaws.com"
            ap-northeast-3:
                s3endpoint: "s3-website.ap-northeast-3.amazonaws.com"
                s3bucket: "s3.ap-northeast-3.amazonaws.com"
            ap-northeast-2:
                s3endpoint: "s3-website.ap-northeast-2.amazonaws.com"
                s3bucket: "s3.ap-northeast-2.amazonaws.com"
            ap-southeast-1:
                s3endpoint: "s3-website-ap-southeast-1.amazonaws.com"
                s3bucket: "s3-ap-southeast-1.amazonaws.com"
            ap-southeast-2:
                s3endpoint: "s3-website-ap-southeast-2.amazonaws.com"
                s3bucket: "s3-ap-southeast-2.amazonaws.com"
            ap-northeast-1:
                s3endpoint: "s3-website-ap-northeast-1.amazonaws.com"
                s3bucket: "s3-ap-northeast-1.amazonaws.com"
            ca-central-1:
                s3endpoint: "s3-website.ca-central-1.amazonaws.com"
                s3bucket: "s3.ca-central-1.amazonaws.com"
            cn-northwest-1:
                s3endpoint: "s3-website.cn-northwest-1.amazonaws.com.cn"
                s3bucket: "s3.cn-northwest-1.amazonaws.com.cn"
            eu-central-1:
                s3endpoint: "s3-website.eu-central-1.amazonaws.com"
                s3bucket: "s3.eu-central-1.amazonaws.com"
            eu-west-1:
                s3endpoint: "s3-website-eu-west-1.amazonaws.com"
                s3bucket: "s3-eu-west-1.amazonaws.com"
            eu-west-2:
                s3endpoint: "s3-website.eu-west-2.amazonaws.com"
                s3bucket: "s3.eu-west-2.amazonaws.com"
            eu-south-1:
                s3endpoint: "s3-website.eu-south-1.amazonaws.com"
                s3bucket: "s3.eu-south-1.amazonaws.com"
            eu-west-3:
                s3endpoint: "s3-website.eu-west-3.amazonaws.com"
                s3bucket: "s3.eu-west-3.amazonaws.com"
            eu-north-1:
                s3endpoint: "s3-website.eu-north-1.amazonaws.com"
                s3bucket: "s3.eu-north-1.amazonaws.com"
            ap-southeast-3:
                s3endpoint: "s3-website.ap-southeast-3.amazonaws.com"
                s3bucket: "s3.ap-southeast-3.amazonaws.com"
            me-south-1:
                s3endpoint: "s3-website.me-south-1.amazonaws.com"
                s3bucket: "s3.me-south-1.amazonaws.com"
            sa-east-1:
                s3endpoint: "s3-website-sa-east-1.amazonaws.com"
                s3bucket: "s3-sa-east-1.amazonaws.com"
            us-gov-east-1:
                s3endpoint: "s3-website.us-gov-east-1.amazonaws.com"
                s3bucket: "s3.us-gov-east-1.amazonaws.com"
            us-gov-west-1:
                s3endpoint: "s3-website-us-gov-west-1.amazonaws.com"
                s3bucket: "s3-us-gov-west-1.amazonaws.com"

    Resources:
        STARKSystemBucket:
            Type: AWS::S3::Bucket
            Properties:
                LifecycleConfiguration:
                    Rules:
                        - Id: clean_up_tmp
                          ExpirationInDays: 1
                          NoncurrentVersionExpiration:
                            NewerNoncurrentVersions: 1
                            NoncurrentDays: 1
                          Prefix: tmp/
                          Status: Enabled
                CorsConfiguration:
                    CorsRules:
                        - AllowedHeaders:
                            - '*'
                          AllowedMethods:
                            - PUT
                            - POST
                          AllowedOrigins:
                            - '*'
                          ExposedHeaders:
                            - ETag
                BucketName: !Ref UserWebsiteBucketNameParameter
                VersioningConfiguration:
                    Status: {s3_versioning}"""
    if not cdn_enabled:
        cf_template +=f"""
                AccessControl: {s3_access_control}
                WebsiteConfiguration:
                    ErrorDocument: {s3_error_document}
                    IndexDocument: {s3_index_document}"""
    if analytics_enabled:
        cf_template +=f"""
        STARKAnalyticsRawBucket:
            Type: AWS::S3::Bucket
            Properties:
                BucketName: {s3_raw_bucket_name}
                PublicAccessBlockConfiguration:
                    BlockPublicAcls: True
                    BlockPublicPolicy: True
                    IgnorePublicAcls: True
                    RestrictPublicBuckets: True
        STARKAnalyticsProcessedBucket:
            Type: AWS::S3::Bucket
            Properties:
                BucketName: {s3_processed_bucket_name}
                PublicAccessBlockConfiguration:
                    BlockPublicAcls: True
                    BlockPublicPolicy: True
                    IgnorePublicAcls: True
                    RestrictPublicBuckets: True
        STARKAnalyticsAthenaBucket:
            Type: AWS::S3::Bucket
            Properties:
                BucketName: {s3_athena_bucket_name}
                PublicAccessBlockConfiguration:
                    BlockPublicAcls: True
                    BlockPublicPolicy: True
                    IgnorePublicAcls: True
                    RestrictPublicBuckets: True
        STARKAnalyticsGlueDatabase:
            Type: AWS::Glue::Database
            Properties:
                CatalogId: !Ref AWS::AccountId
                DatabaseInput:
                    Name: stark_{project_varname.lower()}_db
        STARKAnalyticsAthenaWorkGroup:
            Type: AWS::Athena::WorkGroup
            Properties:
                Name: STARK_{project_varname}_workgroup
                Description: My WorkGroup Updated
                State: ENABLED
                WorkGroupConfiguration:
                    BytesScannedCutoffPerQuery: 200000000
                    EnforceWorkGroupConfiguration: false
                    PublishCloudWatchMetricsEnabled: false
                    RequesterPaysEnabled: true
                    ResultConfiguration:
                        OutputLocation: s3://{s3_athena_bucket_name}/output/
            DependsOn:
                - STARKAnalyticsAthenaBucket
        STARKAnalyticsGlueJobRole:
            Type: AWS::IAM::Role
            Properties:
                AssumeRolePolicyDocument:
                    Version: '2012-10-17'
                    Statement: 
                        - 
                            Effect: Allow
                            Principal:
                                Service: 
                                    - 'glue.amazonaws.com'
                            Action: 'sts:AssumeRole'
                ManagedPolicyArns:
                    - 'arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole'
                Policies:
                    - 
                        PolicyName: PolicyForSTARKAnalyticsGlueJobRole
                        PolicyDocument:
                            Version: '2012-10-17'
                            Statement:
                                - 
                                    Sid: VisualEditor0
                                    Effect: Allow
                                    Action:
                                        - 's3:PutObject'
                                        - 's3:GetObject'
                                    Resource: 
                                        - !Join [ "",  [ "arn:aws:s3:::", "{s3_processed_bucket_name}", "/*"] ]
                                        - !Join [ "",  [ "arn:aws:s3:::", "{s3_processed_bucket_name}"] ]
                                        - !Join [ "",  [ "arn:aws:s3:::", !Ref UserCICDPipelineBucketNameParameter, "/{project_varname}/*"] ]
                                        - "*" 
        STARKProjectSchedulerInvokeRole:
            Type: AWS::IAM::Role
            Properties:
                AssumeRolePolicyDocument:
                    Version: '2012-10-17'
                    Statement: 
                        - 
                            Effect: Allow
                            Principal:
                                Service: 
                                    - 'scheduler.amazonaws.com'
                            Action: 'sts:AssumeRole'
                Policies:
                    - 
                        PolicyName: PolicyForSTARKProjectSchedulerInvokeRole
                        PolicyDocument:
                            Version: '2012-10-17'
                            Statement:
                                - 
                                    Sid: VisualEditor0
                                    Effect: Allow
                                    Action:
                                        - 'lambda:InvokeFunction'
                                    Resource:
                                        - !Join [ ":", [!GetAtt STARKBackendApiForSTARKAnalytics.Arn ] ]
                                        - !Join [ ":", [!GetAtt STARKBackendApiForSTARKAnalytics.Arn, "*" ] ]"""
    if analytics_activated:    
        cf_template +=f"""
        STARKProjectAnalyticsScheduler:
            Type: AWS::Scheduler::Schedule
            Properties: 
                Description: Triggers dumping of data of each business entity in CSV formatted files 
                FlexibleTimeWindow: 
                    MaximumWindowInMinutes: 2
                    Mode: FLEXIBLE
                ScheduleExpression: cron(0 0 * * ? *)
                ScheduleExpressionTimezone: Hongkong
                State: ENABLED
                Target:
                    Arn: !GetAtt STARKBackendApiForSTARKAnalytics.Arn
                    RoleArn: !GetAtt STARKProjectSchedulerInvokeRole.Arn"""
        
    cf_template +=f"""
        STARKSystemBucketUser:
            Type: AWS::IAM::User
            Properties: 
                Policies:
                    - 
                        PolicyName: PolicyForSTARKSystemBucketUser
                        PolicyDocument:
                            Version: "2012-10-17"
                            Statement:
                                - 
                                    Effect: Allow
                                    Action:
                                        - 's3:PutObject'
                                        - 's3:PutObjectACL'
                                    Resource: !Join [ "",  [ !GetAtt STARKSystemBucket.Arn, "/*"] ]
                UserName: {web_bucket_user}
        STARKSystemBucketAccessKey:
            Type: AWS::IAM::AccessKey
            Properties: 
                Status: Active
                UserName: !Ref STARKSystemBucketUser
        STARKBucketCleaner:
            Type: AWS::CloudFormation::CustomResource
            Properties:
                ServiceToken: {cleaner_service_token}
                UpdateToken: {update_token}
                Bucket:
                    Ref: STARKSystemBucket
                Remarks: This will empty the STARKSystemBucket for DELETE STACK operations
            DependsOn:
                -   STARKSystemBucket
        STARKProjectDefaultLambdaServiceRole:
            Type: AWS::IAM::Role
            Properties:
                AssumeRolePolicyDocument:
                    Version: '2012-10-17'
                    Statement: 
                        - 
                            Effect: Allow
                            Principal:
                                Service: 
                                    - 'lambda.amazonaws.com'
                            Action: 'sts:AssumeRole'
                ManagedPolicyArns:
                    - 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
                    - 'arn:aws:iam::aws:policy/AmazonAthenaFullAccess'
                Policies:
                    - 
                        PolicyName: PolicyForSTARKProjectDefaultLambdaServiceRole
                        PolicyDocument:
                            Version: '2012-10-17'
                            Statement:
                                - 
                                    Sid: VisualEditor0
                                    Effect: Allow
                                    Action:
                                        - 'iam:GetRole'
                                        - 'dynamodb:BatchGetItem'
                                        - 'dynamodb:BatchWriteItem'
                                        - 'dynamodb:ConditionCheckItem'
                                        - 'dynamodb:PutItem'
                                        - 'dynamodb:DeleteItem'
                                        - 'dynamodb:GetItem'
                                        - 'dynamodb:Scan'
                                        - 'dynamodb:Query'
                                        - 'dynamodb:UpdateItem'
                                        - 's3:PutObject'
                                        - 's3:PutObjectAcl'
                                        - 's3:GetObject'
                                        - 's3:GetObjectAcl'
                                        - 's3:ListBucket'
                                        - 's3:DeleteObject'
                                    Resource: 
                                        - !Join [ ":", [ "arn:aws:dynamodb", !Ref AWS::Region, !Ref AWS::AccountId, "table/{ddb_table_name}"] ]
                                        - !Join [ ":", [ "arn:aws:dynamodb", !Ref AWS::Region, !Ref AWS::AccountId, "table/{ddb_table_name}/index/STARK-ListView-Index", ] ]
                                        - !Join [ "",  [ "arn:aws:s3:::", "{s3_bucket_name}", "/tmp/*"] ]
                                        - !Join [ "",  [ "arn:aws:s3:::", "{s3_bucket_name}", "/uploaded_files/*"] ]
        STARKProjectAnalyticsLambdaServiceRole:
            Type: AWS::IAM::Role
            Properties:
                AssumeRolePolicyDocument:
                    Version: '2012-10-17'
                    Statement: 
                        - 
                            Effect: Allow
                            Principal:
                                Service: 
                                    - 'lambda.amazonaws.com'
                            Action: 'sts:AssumeRole'
                ManagedPolicyArns:
                    - 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
                    - 'arn:aws:iam::aws:policy/AmazonAthenaFullAccess'
                Policies:
                    - 
                        PolicyName: PolicyForSTARKProjectAnalyticsLambdaServiceRole
                        PolicyDocument:
                            Version: '2012-10-17'
                            Statement:
                                - 
                                    Sid: VisualEditor0
                                    Effect: Allow
                                    Action:
                                        - 'iam:GetRole'
                                        - 'dynamodb:BatchGetItem'
                                        - 'dynamodb:BatchWriteItem'
                                        - 'dynamodb:ConditionCheckItem'
                                        - 'dynamodb:PutItem'
                                        - 'dynamodb:DeleteItem'
                                        - 'dynamodb:GetItem'
                                        - 'dynamodb:Scan'
                                        - 'dynamodb:Query'
                                        - 'dynamodb:UpdateItem'
                                        - 's3:PutObject'
                                        - 's3:PutObjectAcl'
                                        - 's3:GetObject'
                                        - 's3:GetObjectAcl'
                                        - 's3:ListBucket'
                                        - 's3:DeleteObject'
                                    Resource: 
                                        - !Join [ ":", [ "arn:aws:dynamodb", !Ref AWS::Region, !Ref AWS::AccountId, "table/{ddb_table_name}"] ]
                                        - !Join [ ":", [ "arn:aws:dynamodb", !Ref AWS::Region, !Ref AWS::AccountId, "table/{ddb_table_name}/index/STARK-ListView-Index", ] ]
                                        - !Join [ "",  [ "arn:aws:s3:::", "{s3_bucket_name}", "/tmp/*"] ]
                                        - !Join [ "",  [ "arn:aws:s3:::", "{s3_bucket_name}", "/uploaded_files/*"] ]
                                        - !Join [ "",  [ "arn:aws:s3:::", "{s3_raw_bucket_name}"] ]
                                        - !Join [ "",  [ "arn:aws:s3:::", "{s3_raw_bucket_name}", "/*"] ]
                                        - !Join [ "",  [ "arn:aws:s3:::", "{s3_processed_bucket_name}"] ]
                                        - !Join [ "",  [ "arn:aws:s3:::", "{s3_processed_bucket_name}", "/*"] ]
                                        - !Join [ "",  [ "arn:aws:s3:::", "{s3_athena_bucket_name}"] ]
                                        - !Join [ "",  [ "arn:aws:s3:::", "{s3_athena_bucket_name}", "/*"] ]
        STARKProjectDefaultAuthorizerInvokeRole:
            Type: AWS::IAM::Role
            Properties:
                AssumeRolePolicyDocument:
                    Version: '2012-10-17'
                    Statement: 
                        - 
                            Effect: Allow
                            Principal:
                                Service: 
                                    - 'apigateway.amazonaws.com'
                            Action: 'sts:AssumeRole'
                Policies:
                    - 
                        PolicyName: PolicyForSTARKProjectDefaultAuthorizerInvokeRole
                        PolicyDocument:
                            Version: '2012-10-17'
                            Statement:
                                - 
                                    Sid: VisualEditor0
                                    Effect: Allow
                                    Action:
                                        - 'lambda:InvokeFunction'
                                    Resource: !GetAtt STARKDefaultAuthorizerFunc.Arn
        CFCustomResourceHelperLayer:
            Type: AWS::Lambda::LayerVersion
            Properties:
                Content:
                    S3Bucket: !Ref UserCICDPipelineBucketNameParameter
                    S3Key: {project_varname}/STARKLambdaLayers/CF_CustomResourceHelper_py39.zip
                Description: Lambda-backed custom resource library for CloudFormation
                LayerName: {project_varname}_CF_CustomResourceHelper
                CompatibleArchitectures:
                    - x86_64
                    - arm64
                CompatibleRuntimes:
                    - python3.6
                    - python3.7
                    - python3.8
                    - python3.9
        PyYamlLayer:
            Type: AWS::Lambda::LayerVersion
            Properties:
                Content:
                    S3Bucket: !Ref UserCICDPipelineBucketNameParameter
                    S3Key: {project_varname}/STARKLambdaLayers/yaml_py39.zip
                Description: YAML module for Python 3.x
                LayerName: {project_varname}_PyYAML
                CompatibleArchitectures:
                    - x86_64
                    - arm64
                CompatibleRuntimes:
                    - python3.6
                    - python3.7
                    - python3.8
                    - python3.9
        OpenAILayer:
            Type: AWS::Lambda::LayerVersion
            Properties:
                Content:
                    S3Bucket: !Ref UserCICDPipelineBucketNameParameter
                    S3Key: {project_varname}/STARKLambdaLayers/OpenAI_layer.zip
                Description: OpenAI module for Python 3.x
                LayerName: {project_varname}_OpenAI
                CompatibleArchitectures:
                    - x86_64
                CompatibleRuntimes:
                    - python3.10
        RequestsLayer:
            Type: AWS::Lambda::LayerVersion
            Properties:
                Content:
                    S3Bucket: !Ref UserCICDPipelineBucketNameParameter
                    S3Key: {project_varname}/STARKLambdaLayers/requests_py39.zip
                Description: Requests module for Python 3.x
                LayerName: {project_varname}_Requests
                CompatibleArchitectures:
                    - x86_64
                    - arm64
                CompatibleRuntimes:
                    - python3.6
                    - python3.7
                    - python3.8
                    - python3.9
        Fpdf2Layer:
            Type: AWS::Lambda::LayerVersion
            Properties:
                Content:
                    S3Bucket: !Ref UserCICDPipelineBucketNameParameter
                    S3Key: {project_varname}/STARKLambdaLayers/fpdf2_py39.zip
                Description: Fpdf2 module for Python 3.x
                LayerName: {project_varname}_Fpdf2
                CompatibleArchitectures:
                    - x86_64
                    - arm64
                CompatibleRuntimes:
                    - python3.6
                    - python3.7
                    - python3.8
                    - python3.9
        STARKFriendlyToSystemNamesLayer:
            Type: AWS::Lambda::LayerVersion
            Properties:
                Content:
                    S3Bucket: !Ref UserCICDPipelineBucketNameParameter
                    S3Key: {project_varname}/STARKLambdaLayers/STARK_friendly_to_system_name_py39.zip
                Description: STARK module for converting user-supplied, human-friendly identifiers into system-friendly entity or variable names
                LayerName: {project_varname}_friendly_to_system_name
                CompatibleArchitectures:
                    - x86_64
                    - arm64
                CompatibleRuntimes:
                    - python3.6
                    - python3.7
                    - python3.8
                    - python3.9
        STARKScryptLayer:
            Type: AWS::Lambda::LayerVersion
            Properties:
                Content:
                    S3Bucket: !Ref UserCICDPipelineBucketNameParameter
                    S3Key:  {project_varname}/STARKLambdaLayers/STARK_scrypt_py39.zip
                Description: STARK module for working with scrypt from the Python stdlib
                LayerName: {project_varname}_scrypt
                CompatibleArchitectures:
                    - x86_64
                    - arm64
                CompatibleRuntimes:
                    - python3.6
                    - python3.7
                    - python3.8
                    - python3.9
        STARKLayerMakerFunc:
            Type: AWS::Serverless::Function
            Properties:
                Runtime: python3.9
                Handler: LayerMaker.lambda_handler
                CodeUri: 
                    Bucket: {codegen_bucket_name}
                    Key: STARKLambdaFunctions/STARK_LayerMaker.zip
                Environment:
                    Variables:
                        STARK_ENVIRONMENT_TYPE: PROD
                        Project_Name: {project_name}
                        CICD_Bucket_Name: {cicd_bucket_name}
                Policies:
                    - AmazonS3FullAccess
                Layers:
                    - !Ref PyYamlLayer
                    - !Ref STARKFriendlyToSystemNamesLayer
                Architectures:
                    - arm64
                MemorySize: 128
                Timeout: 60
        STARKDefaultAuthorizerFunc:
            Type: AWS::Serverless::Function
            Properties:
                Runtime: python3.9
                Handler: authorizer_default.lambda_handler
                CodeUri: lambda/authorizer_default
                Role: !GetAtt STARKProjectDefaultLambdaServiceRole.Arn
                Architectures:
                    - arm64
                MemorySize: 128
                Timeout: 5
        STARKCloudFront:
            Type: AWS::CloudFront::Distribution
            Properties: 
                DistributionConfig: 
                    PriceClass: {cdn_price_class}
                    DefaultRootObject: {cdn_default_root_object}
                    Enabled: {cdn_enabled}
                    Origins:
                        - Id: !Join [ "", [ "{s3_bucket_name}.", !FindInMap [ RegionMap, !Ref AWS::Region, s3bucket] ] ]
                          DomainName: !Join [ "", [ "{s3_bucket_name}.", !FindInMap [ RegionMap, !Ref AWS::Region, s3bucket] ] ]
                          CustomOriginConfig:
                            HTTPPort: 80
                            HTTPSPort: 443
                            OriginReadTimeout: 30
                            OriginKeepaliveTimeout: 5
                            OriginProtocolPolicy: http-only
                            OriginSSLProtocols:
                                - TLSv1.2
                          ConnectionAttempts: 3
                          ConnectionTimeout: 10
                    DefaultCacheBehavior:
                        AllowedMethods:
                            - HEAD
                            - GET
                        CachedMethods:
                            - HEAD
                            - GET
                        CachePolicyId: 658327ea-f89d-4fab-a63d-7e88639e58f6
                        Compress: true
                        SmoothStreaming: false
                        TargetOriginId: !Join [ "", [ "{s3_bucket_name}.", !FindInMap [ RegionMap, !Ref AWS::Region, s3bucket] ] ]
                        ViewerProtocolPolicy: redirect-to-https
                    HttpVersion: http2
                    IPV6Enabled: true"""
    if cdn_viewer_certificate != '':
        cf_template += f"""
                    Aliases:
                        - {cdn_custom_domain_name}
                    ViewerCertificate:
                        AcmCertificateArn: {cdn_viewer_certificate}
                        MinimumProtocolVersion: TLSv1.2_2021
                        SslSupportMethod: sni-only"""
    cf_template += f"""
        STARKApiGateway:
            Type: AWS::Serverless::HttpApi
            Properties:
                Auth:
                    Authorizers:
                        STARKDefaultAuthorizer:
                            AuthorizerPayloadFormatVersion: 2.0
                            EnableSimpleResponses: True
                            FunctionArn: !GetAtt STARKDefaultAuthorizerFunc.Arn
                            FunctionInvokeRole: !GetAtt STARKProjectDefaultAuthorizerInvokeRole.Arn
                            Identity:
                                Headers: 
                                    - cookie
                                ReauthorizeEvery: 300
                    DefaultAuthorizer: STARKDefaultAuthorizer
                CorsConfiguration:
                    AllowOrigins:
                        - !Join [ "", [ "http://{s3_bucket_name}.", !FindInMap [ RegionMap, !Ref AWS::Region, s3endpoint] ] ]
                        - !Join [ "", [ "https://", !GetAtt STARKCloudFront.DomainName ] ]
                        - http://localhost"""
    if cdn_viewer_certificate != '':
        cf_template += f"""
                        - https://{cdn_custom_domain_name}"""
    cf_template += f"""
                    AllowHeaders:
                        - "Content-Type"
                        - "*"
                    AllowMethods:
                        - GET
                        - POST
                        - PUT
                        - DELETE
                    AllowCredentials: True
                    MaxAge: 200
        STARKDynamoDB:
            Type: AWS::DynamoDB::Table
            Properties:
                TableName: {ddb_table_name}
                BillingMode: {ddb_capacity_type}
                TimeToLiveSpecification:
                    AttributeName: TTL
                    Enabled: True
                AttributeDefinitions:
                    -
                        AttributeName: pk
                        AttributeType: S
                    -
                        AttributeName: sk
                        AttributeType: S
                    -
                        AttributeName: STARK-ListView-sk
                        AttributeType: S
                GlobalSecondaryIndexes:
                    -
                        IndexName: STARK-ListView-Index
                        KeySchema:
                            -
                                AttributeName: sk
                                KeyType: HASH
                            -
                                AttributeName: STARK-ListView-sk
                                KeyType: RANGE
                        Projection: 
                            ProjectionType: ALL"""

    if ddb_capacity_type == "PROVISIONED":
        cf_template += f"""
                        ProvisionedThroughput:
                            ReadCapacityUnits: {ddb_rcu_provisioned}
                            WriteCapacityUnits: {ddb_wcu_provisioned}"""

    cf_template += f"""
                KeySchema:
                    -
                        AttributeName: pk
                        KeyType: HASH
                    -
                        AttributeName: sk
                        KeyType: RANGE"""

    if ddb_capacity_type == "PROVISIONED":
        cf_template += f"""
                ProvisionedThroughput:
                    ReadCapacityUnits: {ddb_rcu_provisioned}
                    WriteCapacityUnits: {ddb_wcu_provisioned}"""
    etl_resource_names = []
    for entity in entities:
        entity_logical_name = converter.convert_to_system_name(entity, "cf-resource")
        entity_endpoint_name = converter.convert_to_system_name(entity)
        cf_template += f"""
        STARKBackendApiFor{entity_logical_name}:
            Type: AWS::Serverless::Function
            Properties:
                Events:
                    {entity_logical_name}GetEvent:
                        Type: HttpApi
                        Properties:
                            Path: /{entity_endpoint_name}
                            Method: GET
                            ApiId:
                                Ref: STARKApiGateway
                    {entity_logical_name}PostEvent:
                        Type: HttpApi
                        Properties:
                            Path: /{entity_endpoint_name}
                            Method: POST
                            ApiId:
                                Ref: STARKApiGateway
                    {entity_logical_name}PutEvent:
                        Type: HttpApi
                        Properties:
                            Path: /{entity_endpoint_name}
                            Method: PUT
                            ApiId:
                                Ref: STARKApiGateway
                    {entity_logical_name}DeleteEvent:
                        Type: HttpApi
                        Properties:
                            Path: /{entity_endpoint_name}
                            Method: DELETE
                            ApiId:
                                Ref: STARKApiGateway
                Runtime: python3.9
                Handler: __init__.lambda_handler
                CodeUri: lambda/{entity_endpoint_name}
                Role: !GetAtt STARKProjectDefaultLambdaServiceRole.Arn
                Architectures:
                    - arm64
                MemorySize: 128
                Timeout: 30
                Layers:
                    - !Ref Fpdf2Layer"""
        if analytics_enabled:
            cf_template += f"""
        STARKAnalyticsGlueJobFor{entity_logical_name}:
                Type: AWS::Glue::Job
                Properties: 
                    Command: 
                        Name: glueetl
                        PythonVersion: 3
                        ScriptLocation: lambda/STARK_Analytics/ETL_Scripts/{entity_endpoint_name}.py
                    Description: Test template generated ETL Job
                    ExecutionClass: STANDARD
                    ExecutionProperty: 
                        MaxConcurrentRuns: 1
                    GlueVersion: 3.0
                    MaxRetries: 0
                    Name: STARK_{project_varname}_ETL_script_for_{entity_endpoint_name}
                    NumberOfWorkers: 2
                    Role: !GetAtt STARKAnalyticsGlueJobRole.Arn
                    Timeout: 2880
                    WorkerType: G.1X"""
            etl_resource_names.append(f"STARKAnalyticsGlueJobFor{entity_logical_name}") 
    
    if analytics_enabled:
        if analytics_activated:    
            cf_template += f"""
        STARKAnalyticsETLScheduledTrigger:
            Type: AWS::Glue::Trigger
            Properties:
                Type: SCHEDULED
                Description: DESCRIPTION_SCHEDULED
                Schedule: cron(30 16 * * ? *)
                StartOnCreation: True
                Actions: """
            for resource_name in etl_resource_names:
                cf_template +=f"""
                    - 
                        JobName: !Ref {resource_name}
                        Arguments:
                            "--job-bookmark-option": job-bookmark-enable"""
            cf_template += f"""
                Name: STARK_{project_varname}_ETL_Scheduled_Trigger
            DependsOn:"""
            for resource_name in etl_resource_names:
                cf_template +=f"""
                - {resource_name}"""
                
        cf_template += f"""
        STARKBackendApiForSTARKAnalytics:
            Type: AWS::Serverless::Function
            Properties:
                Events:
                    STARKAnalyticsGetEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_Analytics
                            Method: GET
                            ApiId:
                                Ref: STARKApiGateway
                    STARKAnalyticsPostEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_Analytics
                            Method: POST
                            ApiId:
                                Ref: STARKApiGateway
                    STARKAnalyticsPutEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_Analytics
                            Method: PUT
                            ApiId:
                                Ref: STARKApiGateway
                    STARKAnalyticsDeleteEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_Analytics
                            Method: DELETE
                            ApiId:
                                Ref: STARKApiGateway
                Runtime: python3.9
                Handler: __init__.lambda_handler
                CodeUri: lambda/STARK_Analytics
                Role: !GetAtt STARKProjectAnalyticsLambdaServiceRole.Arn
                Architectures:
                    - arm64
                MemorySize: 128
                Timeout: 60
                Layers:
                    - !Ref Fpdf2Layer""" 
    cf_template += f"""
        GenAIforSTARK:
            Type: AWS::Serverless::Function
            Properties:
                Events:
                    GenAIPostEvent:
                        Type: HttpApi
                        Properties:
                            Path: /GenAI
                            Method: POST
                            ApiId:
                                Ref: STARKApiGateway
                Runtime: python3.10
                Handler: __init__.lambda_handler
                CodeUri: lambda/GenAI
                Policies:
                    - AWSLambdaBasicExecutionRole
                    - AmazonSSMReadOnlyAccess
                    - CloudWatchLogsReadOnlyAccess
                Architectures:
                    - x86_64
                MemorySize: 128
                Timeout: 60
                Layers:
                    - !Ref OpenAILayer
        ObservabilityforSTARK:
            Type: AWS::Serverless::Function
            Properties:
                Events:
                    ObservabilityGetEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_Observability
                            Method: GET
                            ApiId:
                                Ref: STARKApiGateway
                    ObservabilityPostEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_Observability
                            Method: POST
                            ApiId:
                                Ref: STARKApiGateway
                Runtime: python3.9
                Handler: __init__.lambda_handler
                CodeUri: lambda/STARK_Observability
                Policies:
                    - AWSLambdaBasicExecutionRole
                    - CloudWatchLogsReadOnlyAccess
                    - AWSLambda_FullAccess
                    - AmazonS3FullAccess
                Architectures:
                    - arm64
                MemorySize: 128
                Timeout: 60
                Layers:
                    - !Ref RequestsLayer
                    - !Ref OpenAILayer
        STARKBackendApiForSTARKUser:
            Type: AWS::Serverless::Function
            Properties:
                Events:
                    STARKUserGetEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_User
                            Method: GET
                            ApiId:
                                Ref: STARKApiGateway
                    STARKUserPostEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_User
                            Method: POST
                            ApiId:
                                Ref: STARKApiGateway
                    STARKUserPutEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_User
                            Method: PUT
                            ApiId:
                                Ref: STARKApiGateway
                    STARKUserDeleteEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_User
                            Method: DELETE
                            ApiId:
                                Ref: STARKApiGateway
                Runtime: python3.9
                Handler: __init__.lambda_handler
                CodeUri: lambda/STARK_User
                Role: !GetAtt STARKProjectDefaultLambdaServiceRole.Arn
                Architectures:
                    - arm64
                MemorySize: 128
                Timeout: 10
                Layers:
                    - !Ref STARKScryptLayer
                    - !Ref Fpdf2Layer
        STARKBackendApiForSTARKModule:
            Type: AWS::Serverless::Function
            Properties:
                Events:
                    STARKModuleGetEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_Module
                            Method: GET
                            ApiId:
                                Ref: STARKApiGateway
                    STARKModulePostEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_Module
                            Method: POST
                            ApiId:
                                Ref: STARKApiGateway
                    STARKModulePutEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_Module
                            Method: PUT
                            ApiId:
                                Ref: STARKApiGateway
                    STARKModuleDeleteEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_Module
                            Method: DELETE
                            ApiId:
                                Ref: STARKApiGateway
                Runtime: python3.9
                Handler: __init__.lambda_handler
                CodeUri: lambda/STARK_Module
                Role: !GetAtt STARKProjectDefaultLambdaServiceRole.Arn
                Architectures:
                    - arm64
                MemorySize: 128
                Timeout: 5
                Layers:
                    - !Ref Fpdf2Layer
        STARKBackendApiForSTARKUserRoles:
            Type: AWS::Serverless::Function
            Properties:
                Events:
                    STARKUserRolesGetEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_User_Roles
                            Method: GET
                            ApiId:
                                Ref: STARKApiGateway
                    STARKUserRolesPostEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_User_Roles
                            Method: POST
                            ApiId:
                                Ref: STARKApiGateway
                    STARKUserRolesPutEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_User_Roles
                            Method: PUT
                            ApiId:
                                Ref: STARKApiGateway
                    STARKUserRolesDeleteEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_User_Roles
                            Method: DELETE
                            ApiId:
                                Ref: STARKApiGateway
                Runtime: python3.9
                Handler: __init__.lambda_handler
                CodeUri: lambda/STARK_User_Roles
                Role: !GetAtt STARKProjectDefaultLambdaServiceRole.Arn
                Architectures:
                    - arm64
                MemorySize: 128
                Timeout: 5
                Layers:
                    - !Ref STARKScryptLayer
                    - !Ref Fpdf2Layer
        STARKBackendApiForSTARKUserPermissions:
            Type: AWS::Serverless::Function
            Properties:
                Events:
                    STARKUserPermissionsGetEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_User_Permissions
                            Method: GET
                            ApiId:
                                Ref: STARKApiGateway
                    STARKUserPermissionsPostEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_User_Permissions
                            Method: POST
                            ApiId:
                                Ref: STARKApiGateway
                    STARKUserPermissionsPutEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_User_Permissions
                            Method: PUT
                            ApiId:
                                Ref: STARKApiGateway
                    STARKUserPermissionsDeleteEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_User_Permissions
                            Method: DELETE
                            ApiId:
                                Ref: STARKApiGateway
                Runtime: python3.9
                Handler: __init__.lambda_handler
                CodeUri: lambda/STARK_User_Permissions
                Role: !GetAtt STARKProjectDefaultLambdaServiceRole.Arn
                Architectures:
                    - arm64
                MemorySize: 128
                Timeout: 5
                Layers:
                    - !Ref Fpdf2Layer
        STARKBackendApiForSTARKUserSessions:
            Type: AWS::Serverless::Function
            Properties:
                Events:
                    STARKUserSessionsGetEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_User_Sessions
                            Method: GET
                            ApiId:
                                Ref: STARKApiGateway
                    STARKUserSessionsPostEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_User_Sessions
                            Method: POST
                            ApiId:
                                Ref: STARKApiGateway
                    STARKUserSessionsPutEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_User_Sessions
                            Method: PUT
                            ApiId:
                                Ref: STARKApiGateway
                    STARKUserSessionsDeleteEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_User_Sessions
                            Method: DELETE
                            ApiId:
                                Ref: STARKApiGateway
                Runtime: python3.9
                Handler: __init__.lambda_handler
                CodeUri: lambda/STARK_User_Sessions
                Role: !GetAtt STARKProjectDefaultLambdaServiceRole.Arn
                Architectures:
                    - arm64
                MemorySize: 128
                Timeout: 5
                Layers:
                    - !Ref Fpdf2Layer
        STARKBackendApiForSTARKModuleGroups:
            Type: AWS::Serverless::Function
            Properties:
                Events:
                    STARKModuleGroupsGetEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_Module_Groups
                            Method: GET
                            ApiId:
                                Ref: STARKApiGateway
                    STARKModuleGroupsPostEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_Module_Groups
                            Method: POST
                            ApiId:
                                Ref: STARKApiGateway
                    STARKModuleGroupsPutEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_Module_Groups
                            Method: PUT
                            ApiId:
                                Ref: STARKApiGateway
                    STARKModuleGroupsDeleteEvent:
                        Type: HttpApi
                        Properties:
                            Path: /STARK_Module_Groups
                            Method: DELETE
                            ApiId:
                                Ref: STARKApiGateway
                Runtime: python3.9
                Handler: __init__.lambda_handler
                CodeUri: lambda/STARK_Module_Groups
                Role: !GetAtt STARKProjectDefaultLambdaServiceRole.Arn
                Architectures:
                    - arm64
                MemorySize: 128
                Timeout: 5
                Layers:
                    - !Ref Fpdf2Layer
        STARKBackendApiForAuth:
            Type: AWS::Serverless::Function
            Properties:
                Events:
                    AuthPostEvent:
                        Type: HttpApi
                        Properties:
                            Path: /stark_auth
                            Method: POST
                            ApiId:
                                Ref: STARKApiGateway
                Runtime: python3.9
                Handler: __init__.lambda_handler
                CodeUri: lambda/stark_auth
                Role: !GetAtt STARKProjectDefaultLambdaServiceRole.Arn
                Architectures:
                    - arm64
                MemorySize: 128
                Timeout: 5
        STARKBackendApiForLogin:
            Type: AWS::Serverless::Function
            Properties:
                Events:
                    LoginPostEvent:
                        Type: HttpApi
                        Properties:
                            Path: /login
                            Method: POST
                            ApiId:
                                Ref: STARKApiGateway
                            Auth:
                                Authorizer: NONE
                Runtime: python3.9
                Handler: __init__.lambda_handler
                CodeUri: lambda/stark_login
                Role: !GetAtt STARKProjectDefaultLambdaServiceRole.Arn
                Layers:
                    - !Ref STARKScryptLayer
                Architectures:
                    - arm64
                MemorySize: 1792
                Timeout: 5
        STARKBackendApiForLogout:
            Type: AWS::Serverless::Function
            Properties:
                Events:
                    LoginPostEvent:
                        Type: HttpApi
                        Properties:
                            Path: /logout
                            Method: POST
                            ApiId:
                                Ref: STARKApiGateway
                Runtime: python3.9
                Handler: __init__.lambda_handler
                CodeUri: lambda/stark_logout
                Role: !GetAtt STARKProjectDefaultLambdaServiceRole.Arn
                Architectures:
                    - arm64
                MemorySize: 128
                Timeout: 5
        STARKPreLaunch:
            Type: AWS::CloudFormation::CustomResource
            Properties:
                ServiceToken: {prelaunch_service_token}
                UpdateToken: REPLACE-ME-ONLY-FOR-RELAUNCHES
                Project: {project_name}
                DDBTable: {ddb_table_name}
                WebBucket_AccessKeyID: !Ref STARKSystemBucketAccessKey
                WebBucket_SecretAccessKey: !GetAtt STARKSystemBucketAccessKey.SecretAccessKey
                Remarks: Final system pre-launch tasks - things to do after the entirety of the new system's infra and code have been deployed
            DependsOn:
                - STARKApiGateway
                - STARKBackendApiForLogin
                - STARKBucketCleaner
                - STARKDynamoDB
                - STARKProjectDefaultLambdaServiceRole
        STARKOpenAIAPIKey:
            Type: AWS::SSM::Parameter
            Properties: 
                Name: {project_varname}_OPENAI_API_KEY
                Type: String
                Description: Place your OpenAI API Key here
                Value: (Your API Key)
        STARKGenAIFuncName:
            Type: AWS::SSM::Parameter
            Properties: 
                Name: {project_varname}_GENAI_LAMBDA_FUNC
                Type: String
                Description: The STARK GenAI Function for this project
                Value: !Ref GenAIforSTARK
        """

    return textwrap.dedent(cf_template)