# agentic-compliance-automation

Project skeleton for the agentic compliance automation project.

Directory layout created:

├── infra/
│   ├── envs/
│   │   ├── dev/
│   │   ├── staging/
│   │   └── prod/
│   ├── modules/
│   │   ├── s3/
│   │   ├── iam/
│   │   ├── dynamodb/
│   │   ├── lambda/
│   │   └── step-functions/
│   └── main.tf
│
├── agents/
│   ├── ingestion/
│   │   ├── handler.py
│   │   └── prompt.txt
│   ├── risk_analysis/
│   ├── compliance/
│   ├── summary/
│   └── approval/
│
├── step_functions/
│   └── contract_review.asl.json
│
├── shared/
│   ├── bedrock_client.py
│   ├── schema_validation.py
│   └── logging.py
│
├── ci/
│   └── github-actions.yml
│
└── README.md

This is a starter scaffold; populate modules and agents with working code as you go.

