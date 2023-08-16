#This receives parsed data from the STARK Parser, then turns that into the
#appropriate CloudFormation template to actually create the STARK-powered system

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



#Get environment type - this will allow us to take different branches depending on whether we are LOCAL or PROD (or any other future valid value)
ENV_TYPE = os.environ['STARK_ENVIRONMENT_TYPE']
if ENV_TYPE == "PROD":
    default_response_headers = { "Content-Type": "application/json" }
    s3  = boto3.client('s3')

    #Get resource ids from STARK configuration document
    codegen_bucket_name  = os.environ['CODEGEN_BUCKET_NAME']
    response = s3.get_object(
        Bucket=codegen_bucket_name,
        Key=f'STARKConfiguration/STARK_config.yml'
    )
    config = yaml.safe_load(response['Body'].read().decode('utf-8')) 
    bootstrapper_service_token = config['Bootstrapper_ARN']
    cleaner_service_token      = config['Cleaner_ARN']
    cg_static_service_token    = config['CGStatic_ARN']
    cg_dynamic_service_token   = config['CGDynamic_ARN']
    cicd_bucket_name           = config['CICD_Bucket_Name']

else:
    #We only have to do this because `SAM local start-api` doesn't follow CORS info from template.yml, which is bullshit
    default_response_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
    }

    bootstrapper_service_token = "BootstrapperService-FakeLocalToken"
    cleaner_service_token      = "CleanerService-FakeLocalToken"
    cg_static_service_token    = "CGStaticService-FakeLocalToken"
    cg_dynamic_service_token   = "CGDynamicService-FakeLocalToken"
    codegen_bucket_name        = "codegen-fake-local-bucket"
    cicd_bucket_name           = "cicd-fake-local-bucket"


def lambda_handler(event, context):

    cloud_resources = event
    print(cloud_resources)
    #Get Provider
    cloud_provider = cloud_resources["Cloud Provider"]

    #Get Project Name
    #FIXME: Project Name is used here as unique identifier. For now it's a user-supplied string, which is unreliable
    #       as a unique identifier. Make this a GUID for prod use.
    #       We do still need a user-supplied project name for display purposes (header of each HTML page, login screen, etc), though.
    project_name      = cloud_resources["Project Name"]
    project_varname   = converter.convert_to_system_name(project_name)
    project_stackname = converter.convert_to_system_name(project_name, 'cf-stack')

    if ENV_TYPE == "PROD":
        #So that cloud_resources can be used by our CodeGen components (which are lambda-backed custom resources in this resulting CF/SAM template),
        #   we need to dump cloud_resources into the shared repository for STARK components.
        response = s3.put_object(
            Body=yaml.dump(cloud_resources, sort_keys=False, encoding='utf-8'),
            Bucket=codegen_bucket_name,
            Key=f'codegen_dynamic/{project_varname}/{project_varname}.yaml',
            Metadata={
                'STARK_Description': 'Cloud resources for this project, as determined by the STARK Parser'
            }
        )

    ###############################################################################################################
    #Load and sanitize data here, for whatever IaC rules that govern them (e.g., S3 Bucket names must be lowercase)

    #DynamoDB-related data
    ddb_table_name = cloud_resources["DynamoDB"]['Table Name']

    #Update Token - this token forces CloudFormation to update the resources that do dynamic code generation,
    #               as well as forced re-deployment of Lambdas (by using this as a deployment package path/folder)
    update_token = str(uuid4())

    #Initialize our template
    #This is where we can use triple-quoted f-strings + textwrap.dedent(), instead of manually placing tabs and nl, unreadable!
    #The forward slash ( \ ) is so that we don't have an empty blank line at the top of our resulting file.
    cf_template = f"""\
    AWSTemplateFormatVersion: '2010-09-09'
    Transform: AWS::Serverless-2016-10-31
    Description: STARK-generated CI/CD Pipeline for Project [{project_name}]
    Resources:
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
                    - 'arn:aws:iam::aws:policy/AWSCodeCommitFullAccess'
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
        STARKProjectCodePipelineDeployServiceRole:
            Type: AWS::IAM::Role
            Properties:
                AssumeRolePolicyDocument:
                    Version: '2012-10-17'
                    Statement: 
                        - 
                            Effect: Allow
                            Principal:
                                Service: 
                                    - 'cloudformation.amazonaws.com'
                            Action: 'sts:AssumeRole'
                ManagedPolicyArns:
                    - 'arn:aws:iam::aws:policy/AdministratorAccess'
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
                          Value: {codegen_bucket_name}
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
                                    - Name: SourceArtifact"""
    if cloud_provider == "AWS":    
        cf_template +=f"""
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
                                OutputArtifacts:
                                    - Name: BuildArtifact
                    -
                        Name: Deploy
                        Actions:
                            -
                                Name: ChangeSetReplace
                                RunOrder: 3
                                ActionTypeId:
                                    Category: Deploy
                                    Owner: AWS
                                    Provider: CloudFormation
                                    Version: '1'
                                Configuration:
                                    ActionMode: CHANGE_SET_REPLACE
                                    StackName: STARK-project-{project_stackname}
                                    Capabilities: CAPABILITY_IAM,CAPABILITY_NAMED_IAM,CAPABILITY_AUTO_EXPAND
                                    ChangeSetName: STARK-project-{project_stackname}-changeset
                                    TemplatePath: "BuildArtifact::outputtemplate.yml"
                                    TemplateConfiguration: "BuildArtifact::template_configuration.json"
                                    RoleArn: !GetAtt STARKProjectCodePipelineDeployServiceRole.Arn
                                InputArtifacts:
                                    - Name: BuildArtifact
                                OutputArtifacts: []
                            -
                                Name: ExecuteChangeSet
                                RunOrder: 4
                                ActionTypeId:
                                    Category: Deploy
                                    Owner: AWS
                                    Provider: CloudFormation
                                    Version: '1'
                                Configuration:
                                    ActionMode: CHANGE_SET_EXECUTE
                                    StackName: STARK-project-{project_stackname}
                                    Capabilities: CAPABILITY_IAM,CAPABILITY_NAMED_IAM,CAPABILITY_AUTO_EXPAND
                                    ChangeSetName: STARK-project-{project_stackname}-changeset
                                InputArtifacts:
                                    - Name: BuildArtifact
                                OutputArtifacts: []"""
    else:    
        cf_template +=f"""
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
    cf_template +=f"""
        STARKBootstrapper:
            Type: AWS::CloudFormation::CustomResource
            Properties:
                ServiceToken: {bootstrapper_service_token}
                UpdateToken: {update_token}
                Project: {project_name}
                DDBTable: {ddb_table_name}
                CICDBucket: {cicd_bucket_name}
                RepoName: !GetAtt STARKProjectRepo.Name
                Remarks: Bootstraps the new system to allow the newly-created pipeline to trigger code generation"""


    if ENV_TYPE == "PROD":
        response = s3.put_object(
            Body=textwrap.dedent(cf_template).encode(),
            Bucket=codegen_bucket_name,
            Key=f'codegen_dynamic/{project_varname}/STARK_SAM_{project_varname}.yaml',
            Metadata={
                'STARK_Description': 'Writer output for CloudFormation'
            }
        )

    else:
        print(textwrap.dedent(cf_template))


    return {
        "isBase64Encoded": False,
        "statusCode": 200,
        "body": json.dumps("Success"),
        "headers": default_response_headers
    }
