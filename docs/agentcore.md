# Amazon Bedrock AgentCore Runtime deployment

The hackathon's Technological Implementation criterion says "a live demo and/or Amazon
Bedrock AgentCore deployment will strengthen this score". This is the runbook for the
AgentCore half. Everything up to step 2 is already built and verified locally; steps 3
onward create billable AWS resources and are yours to run.

**Blocked on one human step.** The IAM user `ninetyninety-demo` (account `726053620023`)
cannot call `bedrock-agentcore:CreateAgentRuntime`, and cannot grant itself the
permission either (`iam:AttachUserPolicy` is denied). Someone with admin on the account
has to do step 3.1. Until then nothing else in this file can run.

## What is deployed

`src/ninetyninety/agentcore.py` — the Strands graph (Preparer + Reviewer concurrent,
Referee on disagreement) behind the HTTP contract AgentCore requires. One invocation
classifies **one batch of ledger rows** and returns an assembled Form 990-EZ Part I
draft. It is deliberately not the whole ledger run: AgentCore caps a synchronous request
at 15 minutes, and a full ledger's wall-clock is set by Gemini free-tier backoff, which
no code here controls. Big ledgers stay on the Streamlit app and `cli.py`.

The container calls **Gemini**, not Bedrock. The execution role therefore does not need
`bedrock:InvokeModel`, but the runtime does need outbound internet
(`networkMode: PUBLIC`) to reach `generativelanguage.googleapis.com`.

## The contract this image implements

Source: [HTTP protocol contract](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-http-protocol-contract.html)
and [Get started without the AgentCore CLI](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/getting-started-custom.html),
both read 2026-09-09.

| Requirement | Value | Where |
|---|---|---|
| Host / port | `0.0.0.0:8080` | `agentcore.PORT`, `EXPOSE 8080` |
| Platform | `linux/arm64` (mandatory) | `FROM --platform=linux/arm64` |
| Health | `GET /ping` -> `200 {"status": "Healthy"}` | `Handler.do_GET` |
| Invoke | `POST /invocations`, JSON in / JSON out | `Handler.do_POST` |
| Registry | image must live in ECR, max 2 GB | image is 370 MB |
| Request timeout | 15 minutes, not adjustable | why `AGENTCORE_MAX_ROWS` defaults to 12 |
| Max payload | 100 MB request and response | not a constraint here |
| Idle session | 15 min default, `idleRuntimeSessionTimeout` | set it to 60 s, see costs |
| Max session | 8 h, `maxLifetime` | set it to 900 s |
| Session id header | `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id`, 33+ chars | the SDK sends it |

Request and response bodies are **not** fixed by AWS — AgentCore passes the payload
through untouched. Ours:

```json
POST /invocations
{"input": {"ledger_csv": "date,description,amount\n2025-01-08,ONLINE DONATION,1250.00\n",
           "max_rows": 12}}
```
```json
200 {"output": {"lines": {...}, "totals": {"line9": …, "line17": …, "line18": …},
                "disagreements": [], "low_confidence": [], "unclassified": [],
                "unreviewed": [], "ungrounded": [], "trace": [...], "skipped": []}}
```

`400` for a bad request (not JSON, no `ledger_csv`, a CSV with no `description`/`amount`
column, more rows than the cap). `500` with the reason for a failed draft — AgentCore
surfaces that to the caller as `RuntimeClientError` (424) and the reason lands in
CloudWatch.

`/ping` returns `Healthy`, never `HealthyBusy`, and never sets `time_of_last_update`.
That is deliberate: a `time_of_last_update` that advances on every ping means the idle
session timeout never fires, and the session runs to `maxLifetime` burning credits.

## 1. Build and verify locally (no AWS, no spend)

From the repo root:

```bash
docker buildx create --use                       # once
docker buildx build --platform linux/arm64 \
  -f deploy/agentcore/Dockerfile \
  -t ninetyninety-agentcore:arm64 --load .

docker run -d --name nn-ac --platform linux/arm64 -p 8080:8080 \
  -e GOOGLE_API_KEY="$GOOGLE_API_KEY" ninetyninety-agentcore:arm64

curl -s http://127.0.0.1:8080/ping
# {"status": "Healthy"}

curl -s -X POST http://127.0.0.1:8080/invocations -H 'Content-Type: application/json' \
  -d '{"input":{"ledger_csv":"date,description,amount\n2025-01-08,ONLINE DONATION STRIPE PAYOUT,1250.00\n2025-02-05,ELGIN PROPERTIES LLC FEB RENT,(1450.00)\n"}}'

docker rm -f nn-ac
```

Use `127.0.0.1`, not `localhost`: on Windows `localhost` resolves to `::1` first and the
connection fails silently with curl exit 000.

On an x86 machine this runs under QEMU emulation, which Docker Desktop provides. It is
slow to build and fine to run.

## 2. Prerequisites for the AWS steps

```bash
aws --version                 # v2
aws sts get-caller-identity   # expect arn:aws:iam::726053620023:user/ninetyninety-demo
export AWS_REGION=us-east-1
export ACCOUNT=726053620023
export REPO=bedrock-agentcore-ninetyninety
export AGENT=ninetyninety            # must match [a-zA-Z][a-zA-Z0-9_]{0,47}
```

`us-east-1` and `us-west-2` carry the highest AgentCore session quotas. Pick one and use
it everywhere — the ECR repo, the role and the runtime must be in the same Region.

## 3. The human steps

### 3.1 Grant the IAM permission (ADMIN ONLY — this is the blocker)

`ninetyninety-demo` currently gets:

```
AccessDeniedException: User: arn:aws:iam::726053620023:user/ninetyninety-demo is not
authorized to perform: bedrock-agentcore:CreateAgentRuntime on resource:
arn:aws:bedrock-agentcore:us-east-1:726053620023:runtime/*
```

That is a missing identity policy, not a quota (a quota block returns
`ServiceQuotaExceededException`). Signed in as the **account root user or an admin**:

Console → IAM → Users → `ninetyninety-demo` → **Add permissions** → **Attach policies
directly** → tick **`BedrockAgentCoreFullAccess`** → **Next** → **Add permissions**.

Also needed, because steps 3.3 and 3.4 create a role and pass it:

Console → IAM → Users → `ninetyninety-demo` → **Add permissions** → **Create inline
policy** → JSON → paste, name it `NinetyNinetyAgentCoreSetup`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RoleForAgentCore",
      "Effect": "Allow",
      "Action": ["iam:CreateRole", "iam:GetRole", "iam:PutRolePolicy",
                 "iam:DeleteRole", "iam:DeleteRolePolicy", "iam:TagRole"],
      "Resource": ["arn:aws:iam::726053620023:role/*BedrockAgentCore*"]
    },
    {
      "Sid": "PassRoleToAgentCore",
      "Effect": "Allow",
      "Action": ["iam:PassRole"],
      "Resource": ["arn:aws:iam::726053620023:role/*BedrockAgentCore*"],
      "Condition": {"StringEquals": {"iam:PassedToService": "bedrock-agentcore.amazonaws.com"}}
    },
    {
      "Sid": "EcrForAgentCore",
      "Effect": "Allow",
      "Action": ["ecr:CreateRepository", "ecr:DescribeRepositories", "ecr:DescribeImages",
                 "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload",
                 "ecr:PutImage", "ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage",
                 "ecr:GetDownloadUrlForLayer", "ecr:ListImages", "ecr:DeleteRepository"],
      "Resource": ["arn:aws:ecr:us-east-1:726053620023:repository/bedrock-agentcore-*"]
    },
    {
      "Sid": "EcrLogin",
      "Effect": "Allow",
      "Action": ["ecr:GetAuthorizationToken"],
      "Resource": "*"
    }
  ]
}
```

Confirm the grant landed before going on:

```bash
aws bedrock-agentcore-control list-agent-runtimes --region $AWS_REGION
# an empty list is success; AccessDeniedException means the policy has not attached yet
```

### 3.2 Create the ECR repository and push the image

```bash
aws ecr create-repository --repository-name $REPO --region $AWS_REGION

aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin $ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com

docker buildx build --platform linux/arm64 \
  -f deploy/agentcore/Dockerfile \
  -t $ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO:latest --push .

aws ecr describe-images --repository-name $REPO --region $AWS_REGION \
  --query 'imageDetails[0].{pushed:imagePushedAt,mb:imageSizeInBytes}'
```

The repo name must start with `bedrock-agentcore-` if you want the inline policy above
to cover it.

### 3.3 Create the execution role

```bash
cat > /tmp/trust.json <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AssumeRolePolicy",
    "Effect": "Allow",
    "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": {"aws:SourceAccount": "726053620023"},
      "ArnLike": {"aws:SourceArn": "arn:aws:bedrock-agentcore:us-east-1:726053620023:*"}
    }
  }]
}
JSON

aws iam create-role --role-name NinetyNinetyBedrockAgentCoreRole \
  --assume-role-policy-document file:///tmp/trust.json
```

Permissions. This is AWS's documented runtime execution policy with the
`bedrock:InvokeModel` statement removed — the graph runs on Gemini, so granting Bedrock
model access would be permission this agent never uses:

```bash
cat > /tmp/exec.json <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [
    {"Sid": "ECRImageAccess", "Effect": "Allow",
     "Action": ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
     "Resource": ["arn:aws:ecr:us-east-1:726053620023:repository/bedrock-agentcore-*"]},
    {"Sid": "ECRTokenAccess", "Effect": "Allow",
     "Action": ["ecr:GetAuthorizationToken"], "Resource": "*"},
    {"Effect": "Allow",
     "Action": ["logs:DescribeLogStreams", "logs:CreateLogGroup"],
     "Resource": ["arn:aws:logs:us-east-1:726053620023:log-group:/aws/bedrock-agentcore/runtimes/*"]},
    {"Effect": "Allow",
     "Action": ["logs:PutResourcePolicy"],
     "Resource": ["arn:aws:logs:us-east-1:726053620023:log-group:/aws/bedrock-agentcore/runtimes/ninetyninety-*"]},
    {"Effect": "Allow", "Action": ["logs:DescribeLogGroups"],
     "Resource": ["arn:aws:logs:us-east-1:726053620023:log-group:*"]},
    {"Effect": "Allow",
     "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
     "Resource": ["arn:aws:logs:us-east-1:726053620023:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"]},
    {"Effect": "Allow",
     "Action": ["xray:PutTraceSegments", "xray:PutTelemetryRecords",
                "xray:GetSamplingRules", "xray:GetSamplingTargets"],
     "Resource": ["*"]},
    {"Effect": "Allow", "Action": "cloudwatch:PutMetricData", "Resource": "*",
     "Condition": {"StringEquals": {"cloudwatch:namespace": "bedrock-agentcore"}}},
    {"Sid": "GetAgentAccessToken", "Effect": "Allow",
     "Action": ["bedrock-agentcore:GetWorkloadAccessToken",
                "bedrock-agentcore:GetWorkloadAccessTokenForJWT"],
     "Resource": [
       "arn:aws:bedrock-agentcore:us-east-1:726053620023:workload-identity-directory/default",
       "arn:aws:bedrock-agentcore:us-east-1:726053620023:workload-identity-directory/default/workload-identity/ninetyninety-*"
     ]}
  ]
}
JSON

aws iam put-role-policy --role-name NinetyNinetyBedrockAgentCoreRole \
  --policy-name NinetyNinetyAgentCoreExecution \
  --policy-document file:///tmp/exec.json
```

### 3.4 Create the agent runtime

`GOOGLE_API_KEY` goes in as an environment variable. Note honestly what that means:
anyone who can call `GetAgentRuntime` on this account can read it back. For a hackathon
demo on a throwaway free-tier Gemini key that is an acceptable trade; the production
answer is AWS Secrets Manager plus a `secretsmanager:GetSecretValue` grant on the
execution role.

```python
# deploy_agentcore.py -- run from the repo root, GOOGLE_API_KEY in your shell or .env
import os, boto3
from dotenv import load_dotenv
load_dotenv()

ACCOUNT, REGION = "726053620023", "us-east-1"
client = boto3.client("bedrock-agentcore-control", region_name=REGION)

response = client.create_agent_runtime(
    agentRuntimeName="ninetyninety",
    description="NinetyNinety: Strands graph drafting IRS Form 990-EZ Part I from a ledger",
    agentRuntimeArtifact={"containerConfiguration": {
        "containerUri": f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/bedrock-agentcore-ninetyninety:latest"}},
    networkConfiguration={"networkMode": "PUBLIC"},   # needed to reach Gemini
    protocolConfiguration={"serverProtocol": "HTTP"},
    roleArn=f"arn:aws:iam::{ACCOUNT}:role/NinetyNinetyBedrockAgentCoreRole",
    environmentVariables={
        "GOOGLE_API_KEY": os.environ["GOOGLE_API_KEY"],
        "AGENTCORE_MAX_ROWS": "12",
    },
    lifecycleConfiguration={
        "idleRuntimeSessionTimeout": 60,   # seconds. The default is 900; 60 caps idle spend.
        "maxLifetime": 900,                # seconds. Hard ceiling on a runaway session.
    },
)
print(response["agentRuntimeArn"], response["status"])
```

`status` comes back `CREATING`. Poll until `READY`:

```bash
aws bedrock-agentcore-control get-agent-runtime --region $AWS_REGION \
  --agent-runtime-id <id-from-the-arn> --query status
```

`CREATE_FAILED` almost always means the image is not ARM64, or the execution role cannot
pull from ECR. Check `/aws/bedrock-agentcore/runtimes/` in CloudWatch Logs.

### 3.5 Verify

```python
# invoke_agentcore.py
import boto3, json, uuid
client = boto3.client("bedrock-agentcore", region_name="us-east-1")
csv = ("date,description,amount\n"
       "2025-01-08,ONLINE DONATION STRIPE PAYOUT BATCH 4471,1250.00\n"
       "2025-02-05,ELGIN PROPERTIES LLC FEB RENT,(1450.00)\n"
       "2025-02-04,VENMO J MARTINEZ SAT WORKSHOP INSTRUCTION,(600.00)\n")

response = client.invoke_agent_runtime(
    agentRuntimeArn="arn:aws:bedrock-agentcore:us-east-1:726053620023:runtime/ninetyninety-XXXXXXXXXX",
    runtimeSessionId=str(uuid.uuid4()) + str(uuid.uuid4()),   # must be 33+ characters
    payload=json.dumps({"input": {"ledger_csv": csv}}),
    qualifier="DEFAULT",
)
out = json.loads(response["response"].read())["output"]
print(out["totals"])          # {'line9': 1250, 'line17': 2050, 'line18': -800}
print(out["trace"][0])        # the Strands node order, tool calls and provider
```

That `trace` entry is the screenshot worth taking: it names the graph nodes that ran, how
many `line_guidance` tool calls each made, and whether the Referee was reached.

Then end the session immediately rather than waiting for the idle timeout:

```python
client.stop_runtime_session(
    agentRuntimeArn="arn:aws:bedrock-agentcore:us-east-1:726053620023:runtime/ninetyninety-XXXXXXXXXX",
    runtimeSessionId="<the same session id>", qualifier="DEFAULT")
```

## 4. Tear down (do this the day judging ends)

An idle AgentCore runtime with no live sessions scales to zero and costs nothing, so the
urgent item is sessions, not the runtime. In order:

```bash
# 1. any live session (see 3.5) -- stop_runtime_session

# 2. the runtime itself
aws bedrock-agentcore-control delete-agent-runtime --region $AWS_REGION \
  --agent-runtime-id <id>

# 3. the image (ECR storage is the only charge that accrues with nothing running)
aws ecr delete-repository --repository-name $REPO --region $AWS_REGION --force

# 4. the role
aws iam delete-role-policy --role-name NinetyNinetyBedrockAgentCoreRole \
  --policy-name NinetyNinetyAgentCoreExecution
aws iam delete-role --role-name NinetyNinetyBedrockAgentCoreRole

# 5. confirm
aws bedrock-agentcore-control list-agent-runtimes --region $AWS_REGION
aws ecr describe-repositories --region $AWS_REGION
```

CloudWatch log groups under `/aws/bedrock-agentcore/runtimes/` survive the delete. They
are a few KB; delete them from the console if you want a clean account.

## 5. What this costs against the $50 credit

Published rates ([AgentCore pricing](https://aws.amazon.com/bedrock/agentcore/pricing/),
read 2026-09-09): **$0.0895 per vCPU-hour** and **$0.00945 per GB-hour**, metered on
actual consumption from microVM boot to session termination. CPU during I/O wait is free
— which is most of our wall-clock, since the container sits waiting on Gemini.

Assume the pessimistic case anyway: 1 vCPU and 2 GB billed for the entire session
wall-clock.

| | Rate |
|---|---|
| 1 vCPU + 2 GB | `0.0895 + 2 × 0.00945` = **$0.1084 / hour** = $0.0000301 / second |

Measured locally, one 3-row invocation takes **13.3 s**.

| Scenario | Session seconds | Cost |
|---|---|---|
| One invocation, session stopped straight after | ~15 | **$0.0005** |
| One invocation, `idleRuntimeSessionTimeout: 60` | ~75 | **$0.002** |
| One invocation, AWS default 900 s idle timeout | ~915 | **$0.028** |
| 50 judge invocations at 60 s idle | ~3,750 | **$0.11** |
| 50 judge invocations at the 900 s default | ~45,750 | **$1.38** |

Plus ECR storage: the image is 370 MB uncompressed, roughly 130 MB stored, at $0.10 per
GB-month → **about $0.013 a month**. CloudWatch logs for a handful of runs are cents.

**Realistic total for the judging window: under $2 of the $50.** The credits expire
2026-10-31, so the budget is not the constraint. The two ways to actually burn money are
both guarded against above: setting `time_of_last_update` on `/ping` so sessions never
idle out (the entrypoint does not set it), and leaving the ECR repo behind forever (step
4.3).

The Gemini free tier is the real scarce resource, not AWS. Each invocation is roughly 6-8
requests against one model id's 20-per-day cap; `AGENTCORE_MAX_ROWS=12` keeps one
invocation to a single batch.
