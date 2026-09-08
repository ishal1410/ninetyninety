# Agents for Humans: I built on a 20-request-a-day free tier and shipped on a five-model rotation

First full live run of NinetyNinety, 48 rows in four batches through a Strands graph, on a free-tier model:

```
48/48 rows classified, 0 unclassified
84 line_guidance tool calls
survived: 9 x 429 rate limits, 3 x 503 "high demand"
wall time: ~7.5 minutes, most of it sleeping on advertised retry delays
```

It worked, and the reason it barely worked is a number nobody publishes.

## The number

Google's Gemini free tier no longer lists its quota on the pricing page. Measured on 2026-09-06 from the body of the 429: **20 requests per day, per model id, per project.** The graph has two blind entry agents and a conditional Referee, so a batch of 12 rows costs two or three requests, and a five-batch ledger costs up to fifteen. One ledger a day, if nothing retries. That is not a demo, it is a coin flip.

## The AWS detour

This is an AWS hackathon, so on 2026-09-07 I wired Amazon Bedrock through Strands' native `BedrockModel` (commit 734fd75), then made it the only provider and deleted the Gemini code (e7cf258). Clean story, one box in the diagram.

Every call came back `ThrottlingException: Too many tokens per day`, on every model, in every region, with zero usage. `get_foundation_model_availability` said AUTHORIZED and AVAILABLE. Service Quotas explained it: on a new Free-plan account the default tokens-per-day quota shows in the billions, the applied value is 0, and the field is marked "Not adjustable". re:Post threads from other new accounts say Support wants at least one billing cycle of history before it seeds the quota. That is not a verification hold that clears in a few hours. It is policy, and the deadline was a week away.

So on 2026-09-08 Bedrock went too (161026f). The README still says it is a one-line swap, `BedrockModel` for `GeminiModel`, and that is true. But a demo has to run, and the only provider that would run for zero dollars was the one with the 20-a-day cap.

## Making 20 a day enough

The cap is per model id. Google serves several flash models, and each one has its own 20. `config.py` is now short:

```python
DEFAULT_MODEL_IDS = "gemini-3.8-flash,gemini-3.5-flash,gemini-3.6-flash,gemini-3.7-flash,gemini-3.5-flash-lite"

def build_model(model_id: str | None = None):
    from strands.models.gemini import GeminiModel
    return GeminiModel(client_args={"api_key": os.environ["GOOGLE_API_KEY"]},
                       model_id=model_id or model_ids()[0])
```

The batch runner does the rest. Each batch runs on the first model id that is not retired. A 429 or a 5xx sleeps for the delay the error body advertises (20 seconds if it names none), and the third failure in a row raises `ProviderExhausted`, which retires that model id for the rest of the run and hands the batch to the next one:

```python
def run_graph(review_graph, task, sleep=time.sleep):
    for attempt in range(3):
        try:
            return review_graph.run(task)
        except Exception as error:
            if not _is_transient(error):
                raise
            if attempt == 2:
                raise ProviderExhausted(str(error)[:200]) from error
            sleep(_delay_seconds(error))
```

A non-transient failure (a 404 model id, a malformed structured answer) costs that batch on that model only; the model stays available for the next batch. A batch no model can answer is recorded as unclassified with the error text and the run continues, so nothing already classified is lost. The provider that answered each batch is written into the trace the app shows.

Three lessons from the logs, each one a commit: read the retry delay out of the 429 body instead of sleeping a fixed number; treat 5xx as transient too, since a 503 killed a run in seven seconds; and match status codes as standalone tokens, because `"500 " in str(error)` also matched a validation error echoing a $500 row.

## The run that shipped

2026-09-08, the 54-row demo ledger, five batches:

- batches 1 to 3 answered by gemini-3.5-flash, batch 4 by gemini-3.6-flash, batch 5 by gemini-3.5-flash-lite
- 92 `line_guidance` tool calls
- 2 Preparer and Reviewer disagreements, so the Referee ran on 1 batch
- 576.6 seconds wall time, 0 rows unclassified

Three model ids for one ledger. The rotation is not a clever architecture. It is the shape of the quota.

## Takeaways

- Measure the free tier yourself. The 429 body carries the real limit and the real delay.
- A new AWS Free-plan account is not a Bedrock account yet. Check Service Quotas for the applied value, not the default, before you plan around it.
- Keep the provider swap to one line and the retry logic provider-agnostic. Both changed twice in two days and the graph never noticed.

Built with Strands Agents for the AWS Agents for Humans hackathon. Repo: https://github.com/ishal1410/ninetyninety
