#STARK Code Generator component.
#Produces the customized dynamic content for a STARK system
#This creates the SAM template.yml file to create the end-user's system infra

#Python Standard Library
import base64
import json
import os
import textwrap
from uuid import uuid4

#Extra modules
import yaml
import boto3

#Private modules
import convert_friendly_to_system as converter


def create(data):

    cloud_resources = data['cloud_resources']
    repo_name       = data['repo_name']
    cloud_provider  = cloud_resources["Cloud Provider"]

    #Get environment type - this will allow us to take different branches depending on whether we are LOCAL or PROD (or any other future valid value)
    ENV_TYPE = os.environ['STARK_ENVIRONMENT_TYPE']
    if ENV_TYPE == "PROD":
        default_response_headers = { "Content-Type": "application/json" }
        s3  = boto3.client('s3')

        codegen_bucket_name  = os.environ['CODEGEN_BUCKET_NAME']
        response = s3.get_object(
            Bucket=codegen_bucket_name,
            Key=f'STARKConfiguration/STARK_config.yml'
        )
        config = yaml.safe_load(response['Body'].read().decode('utf-8')) 
        cleaner_service_token    = config['Cleaner_ARN']  
        cg_static_service_token  = config['CGStatic_ARN']
        cg_dynamic_service_token = config['CGDynamic_ARN']
        cicd_bucket_name         = config['CICD_Bucket_Name']

    else:
        #We only have to do this because `SAM local start-api` doesn't follow CORS info from template.yml, which is bullshit
        default_response_headers = {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        }
        codegen_bucket_name      = "codegen-fake-local-bucket"
        cleaner_service_token    = "CleanerService-FakeLocalToken"
        cg_static_service_token  = "CGStaticService-FakeLocalToken"
        cg_dynamic_service_token = "CGDynamicService-FakeLocalToken"
        codegen_bucket_name      = "codegen-fake-local-bucket"
        cicd_bucket_name         = "cicd-fake-local-bucket"


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
    s3_bucket_name    = cloud_resources["S3 webserve"]["Bucket Name"].lower()
    s3_error_document = cloud_resources["S3 webserve"]["Error Document"]
    s3_index_document = cloud_resources["S3 webserve"]["Index Document"]

    #DynamoDB-related data
    ddb_table_name            = cloud_resources["DynamoDB"]['Table Name']
    ddb_capacity_type         = cloud_resources["DynamoDB"]['Capacity Type'].upper()
    ddb_surge_protection      = cloud_resources["DynamoDB"]['Surge Protection']
    ddb_surge_protection_fifo = cloud_resources["DynamoDB"]['Surge Protection FIFO']
    ddb_rcu_provisioned       = cloud_resources["DynamoDB"].get("RCU", 0)
    ddb_wcu_provisioned       = cloud_resources["DynamoDB"].get("WCU", 0)
    ddb_auto_scaling          = cloud_resources["DynamoDB"].get("Auto Scaling", '')

    #FIXME: Should this transformation be here or in the Parser?
    #Let this remain here now, but probably should be the job of the parser in the future.
    if ddb_capacity_type != "PROVISIONED":
        ddb_capacity_type = "PAY_PER_REQUEST"

    #Some default values not yet from the Parser, but should be added to Parser later
    s3_versioning     = "Enabled"
    s3_access_control = "PublicRead"

    #Update Token - this token forces CloudFormation to update the resources that do dynamic code generation,
    #               as well as forced re-deployment of Lambdas (by using this as a deployment package path/folder)
    update_token = str(uuid4())

    #Initialize our template
    #This is where we can use triple-quoted f-strings + textwrap.dedent(), instead of manually placing tabs and nl, unreadable!
    #The forward slash ( \ ) is so that we don't have an empty blank line at the top of our resulting file.
    cf_template = f"""\
    AWSTemplateFormatVersion: '2010-09-09'
    Transform: AWS::Serverless-2016-10-31
    Description: Bootstrapper
    Parameters:
        UserCodeGenBucketNameParameter:
            Type: String
            Description: Name for user bucket that will hold static files and deployment packages created by STARK
    Resources:
        STARKSystemBucket:
            Type: AWS::S3::Bucket
            Properties:
                BucketName: {s3_bucket_name}
                VersioningConfiguration:
                    Status: {s3_versioning}
                WebsiteConfiguration:
                    ErrorDocument: {s3_error_document}
                    IndexDocument: {s3_index_document}
                PublicAccessBlockConfiguration:
                    BlockPublicAcls: false
                OwnershipControls:
                    Rules:
                        - ObjectOwnership: ObjectWriter
        STARKBucketCleaner:
            Type: AWS::CloudFormation::CustomResource
            Properties:
                ServiceToken: {cleaner_service_token}
                UpdateToken: {update_token}
                Bucket:
                    Ref: STARKSystemBucket
                Remarks: This will empty the STARKSystemBucket for DELETE STACK operations
        STARKApiGateway:
            Type: AWS::Serverless::HttpApi
            Properties:
                CorsConfiguration:
                    AllowOrigins:
                        - !Join [ "", [ "http://{s3_bucket_name}.s3-website-", !Ref AWS::Region, ".amazonaws.com"] ]
                    AllowHeaders:
                        - "*"
                    AllowMethods:
                        - "*"
                    MaxAge: 200
                    AllowCredentials: False
        STARKCGStatic:
            Type: AWS::CloudFormation::CustomResource
            Properties:
                ServiceToken: {cg_static_service_token}
                UpdateToken: {update_token}
                Project: {project_name}
                Bucket: !Ref STARKSystemBucket
                ApiGatewayId: !Ref STARKApiGateway
                RepoName: {repo_name}
                Remarks: This will create the customized STARK HTML/CSS/JS files into the STARKSystemBucket, based on the supplied entities
            DependsOn:
                -   STARKSystemBucket
                -   STARKApiGateway
                -   STARKCGDynamic
        STARKCGDynamic:
            Type: AWS::CloudFormation::CustomResource
            Properties:
                ServiceToken: {cg_dynamic_service_token}
                UpdateToken: {update_token}
                Project: {project_name}
                DDBTable: {ddb_table_name}
                CICDBucket: {cicd_bucket_name}
                Bucket: !Ref STARKSystemBucket
                RepoName: {repo_name}
                Remarks: This will create the customized STARK lambda functions, based on the supplied entities
        STARKDynamoDB:
            Type: AWS::DynamoDB::Table
            Properties:
                TableName: {ddb_table_name}
                BillingMode: {ddb_capacity_type}
                AttributeDefinitions:
                    -
                        AttributeName: pk
                        AttributeType: S
                    -
                        AttributeName: sk
                        AttributeType: S
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
        
    if cloud_provider != "AWS":    
        cf_template +=f"""
        STARKProjectCodeBuildServiceRole:
            Type: AWS::IAM::Role
            Properties:
                AssumeRolePolicyDocument:
                    Version: '2012-10-17'
                    Statement: 
                        - 
                            Effect: Allow
                            Principal:
                                Service: 
                                    - 'codebuild.amazonaws.com'
                            Action: 'sts:AssumeRole'
                ManagedPolicyArns:
                    - 'arn:aws:iam::aws:policy/AmazonS3FullAccess'
                    - 'arn:aws:iam::aws:policy/AWSLambda_FullAccess'
                Policies:
                    - 
                        PolicyName: PolicyForSTARKProjectCodeBuildServiceRole
                        PolicyDocument:
                            Version: "2012-10-17"
                            Statement:
                                - 
                                    Effect: Allow
                                    Action:
                                        - 'logs:CreateLogGroup'
                                        - 'logs:CreateLogStream'  
                                        - 'logs:PutLogEvents'
                                        - 's3:PutObject'
                                        - 's3:GetObject'
                                        - 's3:GetObjectVersion'
                                        - 's3:GetBucketAcl'
                                        - 's3:GetBucketLocation'
                                        - 'codebuild:CreateReportGroup'
                                        - 'codebuild:CreateReport'
                                        - 'codebuild:UpdateReport'
                                        - 'codebuild:BatchPutTestCases'
                                    Resource: '*'
        STARKProjectCodePipelineServiceRole:
            Type: AWS::IAM::Role
            Properties:
                AssumeRolePolicyDocument:
                    Version: '2012-10-17'
                    Statement:
                        - 
                            Effect: Allow
                            Principal:
                                Service: 
                                    - 'codepipeline.amazonaws.com'
                            Action: 'sts:AssumeRole'
                Policies:
                    - 
                        PolicyName: PolicyForSTARKProjectCodePipelineServiceRole
                        PolicyDocument:
                            Version: '2012-10-17'
                            Statement:
                                - 
                                    Sid: VisualEditor0
                                    Effect: Allow
                                    Action:
                                        - 'opsworks:DescribeStacks'
                                        - 'rds:*'
                                        - 'devicefarm:GetRun'
                                        - 'cloudformation:CreateChangeSet'
                                        - 'autoscaling:*'
                                        - 'codebuild:BatchGetBuilds'
                                        - 'devicefarm:ScheduleRun'
                                        - 'servicecatalog:ListProvisioningArtifacts'
                                        - 'devicefarm:ListDevicePools'
                                        - 'cloudformation:UpdateStack'
                                        - 'servicecatalog:DescribeProvisioningArtifact'
                                        - 'cloudformation:DescribeChangeSet'
                                        - 'cloudformation:ExecuteChangeSet'
                                        - 'devicefarm:ListProjects'
                                        - 'sns:*'
                                        - 'lambda:ListFunctions'
                                        - 'lambda:InvokeFunction'
                                        - 'codedeploy:RegisterApplicationRevision'
                                        - 'opsworks:DescribeDeployments'
                                        - 'devicefarm:CreateUpload'
                                        - 'cloudformation:*'
                                        - 'cloudformation:DescribeStacks'
                                        - 'codecommit:GetUploadArchiveStatus'
                                        - 'cloudwatch:*'
                                        - 'cloudformation:DeleteStack'
                                        - 'opsworks:DescribeInstances'
                                        - 'ecs:*'
                                        - 'ecr:DescribeImages'
                                        - 'ec2:*'
                                        - 'codebuild:StartBuild'
                                        - 'cloudformation:ValidateTemplate'
                                        - 'opsworks:DescribeApps'
                                        - 'opsworks:UpdateStack'
                                        - 'codedeploy:CreateDeployment'
                                        - 'codedeploy:GetApplicationRevision'
                                        - 'codedeploy:GetDeploymentConfig'
                                        - 'sqs:*'
                                        - 'servicecatalog:CreateProvisioningArtifact'
                                        - 'cloudformation:DeleteChangeSet'
                                        - 'codecommit:GetCommit'
                                        - 'servicecatalog:DeleteProvisioningArtifact'
                                        - 'codedeploy:GetApplication'
                                        - 'cloudformation:SetStackPolicy'
                                        - 'codecommit:UploadArchive'
                                        - 's3:*'
                                        - 'elasticloadbalancing:*'
                                        - 'codecommit:CancelUploadArchive'
                                        - 'devicefarm:GetUpload'
                                        - 'elasticbeanstalk:*'
                                        - 'opsworks:UpdateApp'
                                        - 'opsworks:CreateDeployment'
                                        - 'cloudformation:CreateStack'
                                        - 'ssm:*'
                                        - 'codecommit:GetBranch'
                                        - 'servicecatalog:UpdateProduct'
                                        - 'codedeploy:GetDeployment'
                                        - 'opsworks:DescribeCommands'
                                    Resource: '*'
                                - 
                                    Sid: VisualEditor1
                                    Effect: Allow
                                    Action: 'iam:PassRole'
                                    Resource: '*'
                                    Condition:
                                        StringEqualsIfExists:
                                            iam:PassedToService:
                                            - 'cloudformation.amazonaws.com'
                                            - 'elasticbeanstalk.amazonaws.com'
                                            - 'ec2.amazonaws.com'
                                            - 'ecs-tasks.amazonaws.com'
                                -
                                    Sid: VisualEditor2
                                    Effect: Allow
                                    Action: 'codestar-connections:UseConnection'
                                    Resource: '*'
        STARKProjectRepo:
            Type: AWS::CodeCommit::Repository
            Properties:
                RepositoryName: STARK_{project_varname}
                RepositoryDescription: Default Git repo for the STARK project "{project_name}"
        STARKProjectBuildProject:
            Type: AWS::CodeBuild::Project
            Properties:
                Name: STARK_{project_varname}_build
                Artifacts:
                    Type: CODEPIPELINE  
                Description: Default Build Project for the STARK project "{project_name}" CI/CD Pipeline
                Environment:
                    ComputeType: BUILD_GENERAL1_SMALL
                    Image: "aws/codebuild/standard:4.0"
                    Type: LINUX_CONTAINER
                    EnvironmentVariables:
                        - Name: CODEGEN_BUCKET_NAME
                          Value: !Ref UserCodeGenBucketNameParameter
                ServiceRole: !GetAtt STARKProjectCodeBuildServiceRole.Arn
                Source:
                    Type: CODEPIPELINE
        STARKProjectCICDPipeline:
            Type: AWS::CodePipeline::Pipeline
            Properties:
                Name: STARK_{project_varname}_pipeline
                ArtifactStore: 
                    Type: S3
                    Location: {cicd_bucket_name}
                RoleArn: !GetAtt STARKProjectCodePipelineServiceRole.Arn
                Stages:
                    -
                        Name: Source
                        Actions:
                            -
                                Name: SourceAction
                                RunOrder: 1
                                ActionTypeId:
                                    Category: Source
                                    Owner: AWS
                                    Provider: CodeCommit
                                    Version: '1'
                                Configuration:
                                    RepositoryName: !GetAtt STARKProjectRepo.Name
                                    PollForSourceChanges: 'true'
                                    BranchName: master
                                InputArtifacts: []
                                OutputArtifacts:
                                    - Name: SourceArtifact
                    -
                        Name: Build
                        Actions:
                            -
                                Name: BuildAction
                                RunOrder: 2
                                ActionTypeId:
                                    Category: Build
                                    Owner: AWS
                                    Provider: CodeBuild
                                    Version: '1'
                                Configuration:
                                    ProjectName: !Ref STARKProjectBuildProject
                                InputArtifacts:
                                    - Name: SourceArtifact
                                OutputArtifacts: []
        
        """

    return textwrap.dedent(cf_template)