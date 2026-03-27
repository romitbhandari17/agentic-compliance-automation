Local user deploy role setup:

Part A — Create the deploy role (Console)

A1) Create the role

AWS Console → IAM
Left menu → Roles
Create role
Trusted entity type: choose AWS account
An AWS account: select This account
Click Next
This creates a role that can be assumed by principals in your own account (we’ll restrict it to romit next).
A2) Attach permissions to the role

On the “Add permissions” step:

Click Create policy (open in a new tab/window so you don’t lose the role wizard)
In Create policy:
Go to JSON tab
Paste the policy below
Next → Name it: TerraformDeployPolicy → Create policy
Back in the role creation tab, refresh the policy list and attach TerraformDeployPolicy
Continue → Name the role TerraformDeployRole → Create role
Policy to attach to the role (baseline)

This is based on what your Terraform is creating: S3 bucket resources, Lambda function, Step Functions state machine, IAM roles/policies + , and CloudWatch Logs. iam:PassRole

Replace and tighten resources later (especially iam:PassRole). For now this is a practical starting point.
{
"Version": "2012-10-17",
"Statement": [
{
"Sid": "StepFunctions",
"Effect": "Allow",
"Action": [
"states:*"
],
"Resource": "*"
},
{
"Sid": "Lambda",
"Effect": "Allow",
"Action": [
"lambda:*"
],
"Resource": "*"
},
{
"Sid": "S3",
"Effect": "Allow",
"Action": [
"s3:*"
],
"Resource": "*"
},
{
"Sid": "IAMForTerraformRolesAndPolicies",
"Effect": "Allow",
"Action": [
"iam:Get*",
"iam:List*",
"iam:CreateRole",
"iam:DeleteRole",
"iam:UpdateRole",
"iam:UpdateAssumeRolePolicy",
"iam:TagRole",
"iam:UntagRole",
"iam:AttachRolePolicy",
"iam:DetachRolePolicy",
"iam:PutRolePolicy",
"iam:DeleteRolePolicy",
"iam:CreatePolicy",
"iam:DeletePolicy",
"iam:CreatePolicyVersion",
"iam:DeletePolicyVersion",
"iam:SetDefaultPolicyVersion",
"iam:TagPolicy",
"iam:UntagPolicy",
"iam:PassRole"
],
"Resource": "*"
},
{
"Sid": "CloudWatchLogsForLambda",
"Effect": "Allow",
"Action": [
"logs:CreateLogGroup",
"logs:CreateLogStream",
"logs:PutLogEvents",
"logs:DescribeLogGroups",
"logs:DescribeLogStreams"
],
"Resource": "*"
},
{
"Sid": "DynamoDB",
"Effect": "Allow",
"Action": [
"dynamodb:*"
],
"Resource": "*"
},
{
"Sid": "BedrockInvokeForIngestionAgent",
"Effect": "Allow",
"Action": [
"bedrock:InvokeModel",
"bedrock:InvokeModelWithResponseStream"
],
"Resource": "*"
},
{
"Sid": "TextractForIngestionAgent",
"Effect": "Allow",
"Action": [
"textract:StartDocumentTextDetection",
"textract:GetDocumentTextDetection"
],
"Resource": "*"
}
]
}

Part B — Allow romit to assume the role

B1) Lock down the role trust policy to romit

IAM → Roles → open TerraformDeployRole
Tab Trust relationships
Click Edit trust policy
Set it to allow only romit:

{
"Version": "2012-10-17",
"Statement": [
{
"Sid": "AllowRomitAssumeRole",
"Effect": "Allow",
"Principal": {
"AWS": "arn:aws:iam::<ACCOUNT_ID>:user/romit"
},
"Action": "sts:AssumeRole"
}
]
}
Save.

B2) Give romit permission to call sts:AssumeRole

IAM → Users → romit
Tab Permissions → Add permissions
Create inline policy (or create a managed policy; inline is fine for this small one)
Go to JSON tab and paste:

{
"Version": "2012-10-17",
"Statement": [
{
"Sid": "AllowAssumeTerraformDeployRole",
"Effect": "Allow",
"Action": "sts:AssumeRole",
"Resource": "arn:aws:iam::<ACCOUNT_ID>:role/TerraformDeployRole"
}
]
}
Create/save the policy.

Part C — Use the role for Terraform (what changes for you)

Two important safety tweaks (do after it works)

Tighten iam:PassRole to only these roles your Terraform creates, e.g.:
arn:aws:iam::<ACCOUNT_ID>:role/agentic-risk-automation-dev-lambda-role
arn:aws:iam::<ACCOUNT_ID>:role/agentic-risk-automation-dev-sfn-role
Consider requiring MFA for role assumption (extra secure).