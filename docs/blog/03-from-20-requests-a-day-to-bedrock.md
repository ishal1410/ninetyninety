# Agents for Humans: from 20 requests a day to Amazon Bedrock, and the failover that survived both

First full live run of NinetyNinety, 48 rows in four batches through a Strands graph:

```
48/48 rows classified, 0 unclassified
84 line_guidance tool calls
providers: gemini-3.5-flash x3 batches, then gemini-3.7-flash (3.5 exhausted)
survived: 9 x 429 rate limits, 3 x 503 "high demand"
wall time: ~7.5 minutes, most of it sleeping on advertised retry delays
```

It worked, and it was obviously not something to put in front of a judge.

## The number nobody publishes

Gemini's free tier quota is no longer on the pricing page. Measured on 2026-09-06: **20 requests per day, per model, per project** (the 429 body names the quota: `GenerateRequestsPerDayPerProjectPerModel-FreeTier`). A Strands graph with two parallel agents and a conditional third burns two or three requests per batch. One ledger, one day, one model.

The workaround that got the project through development is in `config.py`: treat each Gemini model id as its own provider, because each id has its own daily cap.

```python
GEMINI_MODEL_IDS = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.6-flash",
                    "gemini-3.7-flash", "gemini-3.5-flash-lite"]

def providers_in_order(env):
    order = []
    if env.get("AWS_ACCESS_KEY_ID"):
        order.append("bedrock")
    if env.get("GOOGLE_API_KEY"):
        order += [f"gemini:{m}" for m in GEMINI_MODEL_IDS]
    ...
```

Roughly 100 requests a day across five ids. Enough to build. Not enough for strangers clicking a hosted demo.

## What failover has to handle

The batch runner wraps every Strands graph execution:

```python
def run_graph(review_graph, task, sleep=time.sleep):
    for attempt in range(3):
        try:
            return review_graph.run(task)
        except Exception as error:
            if not _is_transient(error):   # 429, 500, 502, 503, 504
                raise
            if attempt == 2:
                raise ProviderExhausted(str(error)[:200]) from error
            sleep(_delay_seconds(error))  # the delay the provider asked for, else 20s
```

Three lessons from the live logs, each one a commit:

1. **Read the delay out of the error.** Gemini's 429 body carries a `retryDelay`. Sleeping what it asks for avoids the immediate second 429 that a fixed sleep produced.
2. **5xx is transient too.** The first version only retried 429. A 503 "high demand" killed a run in seven seconds, and my log filter hid the traceback. Now 500 through 504 retry and then fail over.
3. **Anything else must also fail over, not abort.** An adversarial review pass found that a 404 for an unknown model id would escape the loop and throw away every batch already classified. One extra `except` clause.

Failover is per batch, and once a provider is exhausted it stays skipped for the rest of the run. Every batch records which provider answered in the trace the app shows.

## Moving the front of the queue to Bedrock

Strands' native provider is `BedrockModel`, and it needs nothing beyond AWS credentials in the environment:

```python
if provider == "bedrock":
    from strands.models import BedrockModel
    return BedrockModel(region_name=os.environ.get("AWS_REGION", "us-east-1"))
```

No model id argument: the SDK default is a cross-region Claude inference profile. The Gemini rotation stays behind it as failover, so the hosted demo cannot be taken down by one provider having a bad hour.

The account is an AWS Free plan account. It never bills the card; usage draws from the signup credit, and the whole hackathon's demo traffic is a few dollars of it. One snag worth knowing: a brand-new account returns `ThrottlingException: Too many tokens per day` on every Bedrock model until identity verification finishes, which AWS says takes under two hours. That is not a quota, it is a hold.

[BEDROCK RUN NUMBERS: fill in after the live run: batches, seconds per batch, tool calls, referee count]

## Takeaways

- Measure the free tier yourself. The 429 body tells you the real limit and the real delay.
- Retry the transient class, fail over on everything else, and never let one exception discard finished work.
- Put the provider name in the trace. When a judge asks "what answered this batch", the answer is on screen.

Built with Strands Agents for the AWS Agents for Humans hackathon. Repo: https://github.com/ishal1410/ninetyninety
