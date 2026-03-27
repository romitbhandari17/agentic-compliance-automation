Project Prompts:
As part of the agentic flow,
1. we will have a S3 resource, where a new event will be triggered once a new file is placed, that event will trigger one lambda viz.trigger lambda, which will trigger a Step functions workflow.
2. The step functions would orchestrate two steps as part of a two step process viz. ingestion, compliance.
3. The step funtions state first invokes the ingestion lambda, then the compliance lambda takes the output from ingestion lambda and does the compliance.. Both ingestion and complaince lambda would use bed rock APIs to do the Gen AI stuff..and finally the output of compliance is available in step functions output..
This is the overview of the project, dont make any code changes right now...follow the prompts I provide and only act on those, dont do anything by yourself. As far as possible for all the future prompts, add only the required properties..

2nd and 3rd part:
lets start with 2nd part of the flow for the tfe part, with iam, put the iam role and policy related settings for the ingestion lambda execution role, compliance lambda execution role, and step functions to be able to orchestrate invoking ingestion lambda/print logs followed by complaince lambda…

modules/iam:
In iam, add resources: aws_iam_role with assume role policy, aws_iam_policy_document, aws_iam_role_policy for the two lambdas, and step functions...keep the resources * right now, we will add the specific resources later….

For the ingestion lambda exec role, allow S3 get and put, get and put logs, bedrock apis, textract related properties. For compliance lambda exec role, allow S3 get and put, get and put logs, bedrock apis. For step functions exec role, allow to invoke lambda, and logging. Output the role arns and role names for all services..

Infra/envs/dev:
dev.auto.tfvars would only get env, project, region=‘us-east-1', zip path for the two lambdas...traverse it to main.tf of envs/dev along with var declaration, then to infra root main.tf…under infra/variables.tf. Only these vars are needed in infra/var.tf.

infra/provider.tf:
add the basic stuff for provider.tf with hashicorp/aws.

infra/main.tf:
add module iam, s3, lambda, step functions in infra/main.tf, with vars as needed, like role in lambda coming from iam and so on..

modules/s3:
add resource "aws_s3_bucket" in the s3.tf…add s3 bucket versioning also to the settings..s3.tf…

modules/lambda:
complete the lambda resources now in lambda.tf under modules/lambda, and output appropriate attributes...in outputs.tf..add resource aws_lambda_function for the two lambdas and output the lambda arn and names, use simple variables..add filename coming from main/vars, source code hash generated on the fly with filename, s3 bucket coming from s3 module, function name created in module section, role coming from iam..s3 key not required in lambda..

modules/step-functions:
add step function creation related resource in modules stepfunctions/step-functions.tf and output the name and arn, like this: resource "aws_sfn_state_machine" “this”

infra/step_functions:
step functions will orchestrate invoking ingestion lambda/print logs followed by complaince lambda...create the step functions asl file..put it under src/step_functions folder. reference it under stepfunctions module in infra/main.tf…put this definition in module section of step functions in infra/main.tf also..


Currently we will trigger Step functions manually. For that flow, do we have everything in place..? w.r.t tfe…?

Local user:
local user related setup…

create the dummy zip files for the lambdas.

tfe apply


Setup Python env:
Python3 -m venv .venv
source .venv/bin/activate   # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt  # if you have one
# otherwise at minimum:
pip install boto3 botocore

ingestion lambda:
now, lets develop the code for ingestion lambda, main.py will have the handler function with event as input parameter , and event would be something like "contract_id": "abc-123",     "s3": { "bucket": "my-bucket", "key": "contracts/abc.pdf" }... this should extract text from the document, in such a way that the compliance lambda can apply compliance rules on the output of this lambda..(e.g., GDPR, SOX checks)...output the text extracted which can be used by compliance lambda…add a print and logger stmt in each function...in main.py…

create a quick file to trigger this handler with event in the same folder: {        "contract_id": "",         "s3": { "agentic-compliance-automation-dev-s3-artifacts": "", "key": "contracts/contract.pdf" }       }

try the lambda locally..

compliance lambda:
create a compliance lambda code with handler function which accepts input as ingestion output..the compliance lambda can apply compliance rules on the above..(e.g., GDPR, SOX checks)...using bedrock APIs…and then provide a summary in text about the compliance in the document....make sure to specify region as “us-east-1” for amazon nova lite model…The format of input is like: with  format as: {
"contract_id": "e0da8f55-6300-49d8-8bbc-d93ed0412bb7",
"s3": {
"bucket": "agentic-compliance-automation-dev-s3-artifacts",
"key": "contracts/contract.pdf"
},
"s3_uri": "s3://agentic-compliance-automation-dev-s3-artifacts/contracts/contract.pdf",
"extracted_text": “”}.

and put the request to bedrock model w.r.t amazon nova model with fallback to androphic models…

try the lambda locally..

step functions asl review:
Edit the step functions asl file, based on input to ingestion, output of ingestion, and output of compliance, put the rerty and error handling, all common functionality of step functions in the asl file…

create the zip for the two lambdas, and tfe apply..

lets create a trigger file py under src/scripts, which triggers the step functions in this trigger file, which will in turn trigger ingestion lambda..

Now, trigger the sfn via the trigger file and check if the sfn workflow completes!!

1st part:
invoke sfn lambda:
Now, lets work on the first part of a new lambda getting triggered on a S3 Put event, and this lambda invoking the above step functions state with the right input event object.. Do the changes for modules/iam.tf lambda exec role related, in modules/lambda.tf, in s3.tf for s3 related permissions and in the module section of lambdas in infra/main.tf. Put the mandatory tfe properties only. call this lambda invoke sfn…

create a trigger file under invoke folder/ to invoke this lambda with the event object format like being sent from S3 event…keep the code simple..

Now, trigger the lambda via the trigger file and check if the lambda invokes sfn workflow and it completes!!!







