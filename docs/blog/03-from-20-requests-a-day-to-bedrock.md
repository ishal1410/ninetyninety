# Agents for Humans: I built on a 20-request-a-day free tier, then threw it away for Amazon Bedrock

First full live run of NinetyNinety, 48 rows in four batches through a Strands graph, on a free-tier model:

```
48/48 rows classified, 0 unclassified
84 line_guidance tool calls
survived: 9 x 429 rate limits, 3 x 503 "high demand"
wall time: ~7.5 minutes, most of it sleeping on advertised retry delays
```

It worked. It was also obviously not something to put in front of a judge, and the reason is a number nobody publishes.

## The number

The free tier I started on (a well-known non-AWS model API) no longer lists its quota on the pricing page. Measured on 2026-09-06 from the 429 body: **20 requests per day, per model, per project.** A Strands graph with two parallel agents and a conditional third burns two or three requests per batch. One ledger a day. I spent an evening rotating across five model ids to get to a hundred requests a day, and the config file grew a provider list, a failover ladder, and three sets of tests.

That is the wrong direction for a hackathon. Judges score one clear story, and mine was becoming "a classifier with an elaborate way of coping with quota".

## One flow

The rewrite that landed on 2026-09-07 is the whole of `config.py`:

```python
def build_model():
    if not bedrock_configured(os.environ):
        raise RuntimeError("Amazon Bedrock is not configured. Set AWS_ACCESS_KEY_ID and "
                           "AWS_SECRET_ACCESS_KEY (and AWS_REGION, default us-east-1) in .env.")
    from strands.models import BedrockModel
    kwargs = {"region_name": os.environ.get("AWS_REGION", "us-east-1")}
    if os.environ.get("BEDROCK_MODEL_ID"):
        kwargs["model_id"] = os.environ["BEDROCK_MODEL_ID"]
    return BedrockModel(**kwargs)
```

Strands' native provider. No model id argument means the SDK's default cross-region Claude inference profile. The environment variables are the standard AWS ones, which is also exactly what Streamlit Community Cloud secrets and any AWS runtime already understand. Gemini, OpenRouter, the rotation, the ladder: deleted. Test count went down and the architecture diagram got one box simpler.

## What stayed: backoff that reads the error

Retrying is still worth having, because Bedrock throttles too, and a brand-new account starts with a hold. The batch runner wraps every graph execution:

```python
def run_graph(review_graph, task, sleep=time.sleep):
    for attempt in range(3):
        try:
            return review_graph.run(task)
        except Exception as error:
            if not _is_transient(error):    # throttling, 429, 5xx
                raise
            if attempt == 2:
                raise ProviderExhausted(str(error)[:200]) from error
            sleep(_delay_seconds(error))    # the delay the service asks for, else 20s
```

Three things the live logs taught me, each one a commit:

1. **Read the delay out of the error.** A 429 body carries a retry delay. Sleeping what it asks for avoids the immediate second 429 that a fixed sleep produced.
2. **5xx is transient too.** The first version only retried 429. A 503 killed a run in seven seconds and my log filter hid the traceback.
3. **Match status codes, not substrings.** `"500 " in str(error)` also matched a validation error echoing a $500 row. Now a code has to stand alone, and exception classes named `Throttl…` count as transient (that is what Strands raises for Bedrock, `ModelThrottledException`).

A batch that still fails after three attempts is recorded as unclassified with the error text, and the run continues. Nothing already classified is ever lost.

## The Free plan snag

The AWS account is a Free plan account: it never bills the card, usage draws from the signup credit, and the whole hackathon's demo traffic is a few dollars of it. One thing worth knowing: for the first hours after signup every Bedrock model returns `ThrottlingException: Too many tokens per day`, on every model, with zero usage. That is the identity-verification hold, not a quota. It clears on its own.

[BEDROCK RUN NUMBERS: fill in after the live run: batches, seconds per batch, tool calls, referee count]

## Takeaways

- Measure the free tier yourself. The 429 body tells you the real limit and the real delay.
- For a judged project, one provider and one story beat a clever failover ladder. Delete the ladder.
- Retry the transient class, surface everything else, and never let one exception discard finished work.

Built with Strands Agents on Amazon Bedrock for the AWS Agents for Humans hackathon. Repo: https://github.com/ishal1410/ninetyninety
