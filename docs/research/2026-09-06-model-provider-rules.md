# Agents for Humans: does the model provider affect eligibility or scoring?

Verified 2026-09-06 against primary sources only (Official Rules fetched raw via curl and grepped; FAQ, updates, forum, past galleries and winner pages fetched). Builds on the 2026-09-05 Agents for Humans verification note (kept outside the repo).

## TL;DR

1. **No model provider is required or forbidden.** Only Strands Agents SDK is mandatory; the Manager ruled a project built "with Strands Agents and a different model host" stays eligible.
2. **The five criteria never mention Bedrock, Nova, Claude or any model.** "AWS" appears once, in criterion 1: "A live demo and/or AWS AgentCore deployment will strengthen this score" — a deployment booster, not a model booster.
3. **A WAF-spoofing gateway breaches rule text.** §4 "Third Party Integrations" requires being "authorized to use them in accordance with any terms and conditions"; §11 allows disqualification for conduct "inappropriate ... or a violation of any applicable law."
4. **All six 2025 AWS AI Agent Global Hackathon winners used Bedrock (Nova Pro, Claude 3.5 Sonnet, Nova Sonic) — but that contest *required* a Bedrock/SageMaker-hosted LLM**, so it proves nothing about judge preference here.
5. **Recommendation: Claude on Bedrock via the new AWS Free-plan account; Gemini free as fallback; never agentrouter.**

## 1. Required or forbidden provider?

**Rules §4, Project Requirements** (https://agentsforhumans.devpost.com/rules):
> "Build a new AI agent with Strands Agents that does real work for real people. ..."
> "Deploying with Amazon Bedrock AgentCore is a smart architectural choice and will strengthen your Technical Implementation score, but it's not required."

No clause in the full rules names any model, LLM, or provider as required or prohibited. Entry steps: "Sign up for an AWS Account." / "Install the Strands Agents SDK".

**FAQ** (https://agentsforhumans.devpost.com/details/faqs):
> "Q: Do I need to use AWS AgentCore? A: No. AgentCore is encouraged and will strengthen your Technical Implementation score, but it's not required. Build with Strands Agents as your foundation and deploy however works for you."

No FAQ entry mentions Claude, OpenAI, Gemini, Ollama or provider choice. The diagram FAQ says "AWS services used: Bedrock, Lambda, S3, DynamoDB, AgentCore, etc. — whatever's in your stack" (descriptive).

**Updates** (https://agentsforhumans.devpost.com/updates): 5 posts, none names a required model. 46174: "Name Strands Agents explicitly — it's one of the first things reviewed."

**Organizer rulings** (Shawni Devpost, Manager):
- https://agentsforhumans.devpost.com/forum_topics/44925 — "Your submission stays eligible if you build AidRadar with Strands Agents and do not deploy it on AgentCore."
- https://agentsforhumans.devpost.com/forum_topics/44937 — to a user whose every Bedrock model (incl. Nova) returned "ValidationException: Operation not allowed": "Devpost cannot unblock Bedrock model access. ... You are not blocked from submitting. ... Your project stays eligible if you build it with Strands Agents and a different model host."

Strands docs (https://strandsagents.com/docs/user-guide/quickstart/overview/): "Any model provider works. ... an AWS account is only required if you keep the default." OpenRouter and Google are listed providers.

**Answer: nothing required, nothing forbidden.**

## 2. Do the criteria reward AWS/Bedrock?

Rules §6, verbatim from raw HTML; "equally weighted", no percentages:

1. "**Technical Implementation** How thoroughly and skillfully does the project use Strands Agents? Does the code reflect genuine effort and a working, non-trivial implementation? A live demo and/or AWS AgentCore deployment will strengthen this score."
2. "**Design** Does the project deliver a complete, coherent product experience — not just a technical proof of concept?"
3. "**Potential Impact** Does the project make a credible, specific case for solving a real problem for a real audience — and does the solution actually address that problem based on what's demonstrated?"
4. "**Creativity & Originality** Is this a creative, non-obvious use of Strands Agents — and does the team demonstrate genuine understanding of the problem space they're working in?"
5. "**Presentation** Does the video clearly demonstrate the project working end-to-end? Does the pitch communicate what problem is solved, who it's for, and why it matters? Is the overall presentation easy to follow"

Occurrences: "AWS" once (crit. 1, "AWS AgentCore deployment"); "AgentCore" once (same sentence); "Bedrock" zero (main page restates it as "Amazon Bedrock AgentCore deployment"; rules control per §11); "Strands Agents" in crits 1 and 4. No model or provider word anywhere. Tiebreak = "first applicable criterion" = Technical Implementation. Bonus 0.6 for builder.aws posts on "implementing AWS for this hackathon" is provider-agnostic. AgentCore is "Paid plan exclusive" on a Free-plan account (https://aws.amazon.com/free/), so the reachable crit. 1 booster is the **live demo**.

## 3. Clauses a WAF-spoofing gateway could breach

**§4 Third Party Integrations:**
> "If a Project integrates any third-party SDK, APIs and/or data, Entrant must be authorized to use them in accordance with any terms and conditions or licensing requirements of the tool."

Forging client-identity headers to get past an upstream WAF is, by construction, not use "in accordance with any terms and conditions". This sits in Project Requirements, so it is an eligibility defect.

**§4 Intellectual Property:** Submission must "not violate the intellectual property rights or other rights including but not limited to copyright, trademark, patent, **contract**, and/or privacy rights, of any other person or entity."

**§11 General Conditions:**
> "Sponsor and Administrator reserve the right in their sole discretion to disqualify any individual or Entrant if it finds to be actually or presenting the appearance of tampering with the entry process or the operation of the Hackathon or to be acting in violation of these Official Rules or in a manner that is inappropriate, unsportsmanlike, not in the best interests of this Hackathon, or a violation of any applicable law or regulation."

**§9:** "You will be bound by and comply with these Official Rules and the decisions of the Sponsor, Administrator, and/or the Hackathon Judges which are binding and final"; entrants "release, indemnify, defend and hold harmless the Promotion Entities". **§14** incorporates the Devpost ToS (https://info.devpost.com/terms).

"Unauthorized", "disparage", "reputational" do not appear (only "Unauthorized copying" of Sponsor IP). The operative hooks are §4 Third Party Integrations, §4 "contract" rights, §11. The repo must be public, so the spoofing code is visible to 12 AWS-employee judges.

## 4. Past winners' providers

AWS AI Agent Global Hackathon, Sep–Oct 2025, 613 projects (https://aws-agent-hackathon.devpost.com/project-gallery; winners post /updates/38140):

| Prize | Project | Model / provider (project page) |
|---|---|---|
| 1st | EcoLafaek (https://devpost.com/software/ecolafaek) | "Amazon Bedrock Nova-Pro v1.0 (`amazon.nova-pro-v1:0`) as reasoning LLM"; AgentCore |
| 2nd | AegisAgent (https://devpost.com/software/aegisagent-an-insurance-claim-app-fully-developed-by-kiro) | "AWS Bedrock models"; "BedRock Nova Pro"; "Sonnet 4.5" via Kiro |
| 3rd | Province (https://devpost.com/software/province) | "Claude 3.5 Sonnet v2 for all AI operations" on Bedrock; Strands; AgentCore |
| Best AgentCore | Fraud triage (https://devpost.com/software/ai-driven-multi-agent-fraud-alert-triage-system) | "Claude 3.5 Sonnet on Amazon Bedrock" |
| Best Bedrock App | Oratio (https://devpost.com/software/oratio-merd5o) | "Nova Sonic"; "BedrockAgentCore & Strands Agents" |
| Best Strands SDK | AgentShell (https://devpost.com/software/agent-shell) | "Amazon Bedrock Nova (Micro/Pro)"; AgentCore |

**Caveat:** that contest's rules (https://aws-agent-hackathon.devpost.com/rules) mandated a "Large Language Model (LLM) hosted out of AWS Bedrock or Amazon SageMaker AI." with Technical Execution at 50%. 6/6 Bedrock was the rule, not a preference. Agents for Humans has no such clause.

Other 2026 AWS agent hackathons: Football For Good (https://berlin-agents-of-football.devpost.com/, "Must utilize Strands Agent SDK and deploy on AWS Infrastructure (preferably Amazon Bedrock AgentCore)") and CockroachDB × AWS (https://cockroachdb-ai.devpost.com/) — both "Winners announced soon", galleries unpublished. The Devpost hackathon-search page fetch failed (domain block); list built from WebSearch over devpost.com plus direct fetches.

## Recommendation for NinetyNinety

1. **Claude Sonnet on Bedrock via the new AWS Free-plan account — preferred.** Rule-neutral, but every past winner ran on Bedrock, judges are 12 AWS employees, the FAQ diagram spec expects "AWS services used: Bedrock ...", and the 0.6 bonus is about "implementing AWS". Bedrock is "Available on both plans", paid from the $100 sign-up credit: zero cash. Verify model access on day 1 — account-wide blocks are real (forum 44937) and AWS Support is slow.
2. **Gemini free — fully eligible fallback.** Covered verbatim by ruling 44937 ("a different model host"). Loses only a halo no criterion scores.
3. **OpenRouter paid Claude — eligible, but breaks the zero-budget rule** and buys nothing the rubric rewards beyond Bedrock-Claude.
4. **agentrouter.org — do not use.** Breaches §4 Third Party Integrations and the §4 "contract" warranty, invites §11 disqualification, in a public repo. Eligibility risk, zero scoring upside.

The rubric never sees the provider. Points live in Strands depth (crit. 1, 4), a live demo link (crit. 1 booster and tiebreak axis), a complete product (crit. 2) and the video (crit. 5). Keep the model behind Strands' one-line provider swap so it can change without touching the agent.
