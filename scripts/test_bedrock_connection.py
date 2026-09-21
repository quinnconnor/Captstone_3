"""
Standalone smoke test: confirms the Bedrock/Claude inference-profile ARN
pattern works before any routing or SQL-generation logic is built on top
of it. Per the assignment: "Run this function once, standalone, with a
simple test prompt. Confirm you get a real response before building the
rest of the query layer on top of it."

Run with: python scripts/test_bedrock_connection.py
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_query_layer.bedrock_client import invoke_claude
from config import BEDROCK_MODEL_ARN


def main():
    print(f"Testing Bedrock connectivity using inference-profile ARN:\n  {BEDROCK_MODEL_ARN}\n")
    result = invoke_claude("Reply with exactly the word: OK", max_tokens=10, call_type="smoke_test")
    print("Response:", result["text"])
    print("Input tokens:", result["input_tokens"], "| Output tokens:", result["output_tokens"])

    if "OK" in result["text"].upper():
        print("\n✅ Bedrock/Claude connection confirmed working via inference-profile ARN.")
    else:
        print("\n⚠️  Got a response, but not the expected content. Inspect above.")


if __name__ == "__main__":
    main()
