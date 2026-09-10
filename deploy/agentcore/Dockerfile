# Amazon Bedrock AgentCore Runtime image.
# Build from the REPO ROOT:
#   docker buildx build --platform linux/arm64 -f deploy/agentcore/Dockerfile -t ninetyninety-agentcore:arm64 --load .
#
# "Platform: Must be linux/arm64" -- AgentCore Runtime requirements summary.
FROM --platform=linux/arm64 python:3.12-slim-bookworm

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# Dependencies first so a code edit does not re-resolve the wheel tree.
COPY deploy/agentcore/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

RUN useradd -r -u 1001 agent
USER agent

# AgentCore reaches /invocations and /ping on 8080; it does not read EXPOSE.
EXPOSE 8080

# No HEALTHCHECK: AgentCore health-checks with GET /ping, and adding one would
# mean putting curl into a slim image for nothing.
CMD ["python", "-m", "ninetyninety.agentcore"]
