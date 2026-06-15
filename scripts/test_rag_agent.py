import json
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from app.config import load_settings
from app.agent import build_tools, _run_tool
import anthropic

settings = load_settings()

client = anthropic.Anthropic(
    api_key=settings.anthropic_api_key,
    base_url=settings.anthropic_base_url,
)

tools = build_tools()

# Prompt the agent to find out about authentication
messages = [
    {
        "role": "user",
        "content": "Can you use your search_knowledge_base tool to tell me where authentication is implemented?"
    }
]

print("Sending request to LLM...")
response = client.messages.create(
    model=settings.anthropic_model,
    max_tokens=1000,
    tools=tools,
    messages=messages
)

for block in response.content:
    if getattr(block, "type", None) == "tool_use":
        print(f"\nTool invoked: {block.name}")
        print(f"Input: {block.input}")
        
        # Execute tool
        tool_result = _run_tool(settings, block.name, block.input)
        print(f"\nTool Output:\n{json.dumps(tool_result, indent=2)}")
        
        messages.append({"role": "assistant", "content": [block.model_dump()]})
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(tool_result)
                }
            ]
        })
        
        print("\nSending tool result back to LLM...")
        final_response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1000,
            tools=tools,
            messages=messages
        )
        print(f"\nFinal LLM Response:\n{final_response.content[0].text}")

