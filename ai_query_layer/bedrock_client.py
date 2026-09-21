"""
Thin wrapper around Bedrock's invoke_model for Claude.

IMPLEMENTATION NOTE (confirmed in sandbox testing):
Newer Claude models on Bedrock -- including claude-sonnet-4-6 -- require
the inference-profile ARN as the model ID. Calling with just the bare
model id (e.g. "anthropic.claude-sonnet-4-6-v1:0") returns a
ValidationException. config.BEDROCK_MODEL_ARN builds the correct ARN:

    arn:aws:bedrock:<region>:<account_id>:inference-profile/us.anthropic.claude-sonnet-4-6

Every call in this project's AI query layer goes through invoke_claude()
below so this pattern only has to be correct in one place.
"""
import json
import time
import boto3

from config import AWS_REGION, BEDROCK_MODEL_ARN
from ai_query_layer.tokenomics import log_bedrock_call

bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)


def invoke_claude(prompt: str, max_tokens: int = 500, call_type: str = "generic",
                   system: str = None) -> dict:
    """
    Calls Claude via Bedrock using the inference-profile ARN.

    call_type is one of "classification", "sql_generation",
    "contextual_response", or "generic" -- it's passed through to the
    tokenomics logger so cost can be broken out per stage.

    Returns: {"text": str, "input_tokens": int, "output_tokens": int}
    """
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body["system"] = system

    start = time.time()
    response = bedrock.invoke_model(modelId=BEDROCK_MODEL_ARN, body=json.dumps(body))
    latency_ms = round((time.time() - start) * 1000, 1)

    result = json.loads(response["body"].read())
    output = {
        "text": result["content"][0]["text"],
        "input_tokens": result["usage"]["input_tokens"],
        "output_tokens": result["usage"]["output_tokens"],
    }

    log_bedrock_call(
        call_type=call_type,
        input_tokens=output["input_tokens"],
        output_tokens=output["output_tokens"],
        latency_ms=latency_ms,
    )
    return output


if __name__ == "__main__":
    # Sandbox smoke test -- run this standalone before building anything
    # else on top of it, per the assignment's instructions.
    result = invoke_claude("Reply with exactly the word: OK", max_tokens=10)
    print(result)
