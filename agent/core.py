import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
from agent.prompts import GITPILOT_SYSTEM_PROMPT
from tools.gitlab_tools import (
    list_projects,
    list_issues,
    get_issue_detail,
    list_pipelines,
    get_pipeline_jobs,
    get_project_summary,
    list_merge_requests,
    get_pipeline_failure_diagnosis,
    generate_mr_description,
    generate_sprint_retrospective,
    create_issue_comment,
    update_issue_labels,
    close_issue,
    create_mr_comment,
    create_issue,
    search_issues,
)

load_dotenv()  # Works locally, ignored on Cloud Run

# Works both locally and on Cloud Run
client = genai.Client(
    vertexai=True,
    project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    location=os.environ.get("GOOGLE_CLOUD_REGION", "us-east5")
)

MODEL = "gemini-2.5-flash"

# rest of file stays exactly the same...

# --- Map tool names to actual Python functions ---
TOOL_FUNCTIONS = {
    "list_projects": list_projects,
    "list_issues": list_issues,
    "get_issue_detail": get_issue_detail,
    "list_pipelines": list_pipelines,
    "get_pipeline_jobs": get_pipeline_jobs,
    "get_project_summary": get_project_summary,
    "list_merge_requests": list_merge_requests,
    "get_pipeline_failure_diagnosis": get_pipeline_failure_diagnosis,
    "generate_mr_description": generate_mr_description,
    "generate_sprint_retrospective": generate_sprint_retrospective,
    "create_issue_comment": create_issue_comment,
    "update_issue_labels": update_issue_labels,
    "close_issue": close_issue,
    "create_mr_comment": create_mr_comment,
    "create_issue": create_issue,
    "search_issues": search_issues
}


def run_agent(user_message: str, chat_history: list = None) -> str:
    """
    Run the GitPilot agent with a user message.
    Handles multi-step tool calling loop automatically.

    Args:
        user_message: The user's request
        chat_history: Optional list of previous message dicts
    Returns:
        Final text response from the agent
    """
    # Build conversation history
    history = chat_history or []
    history.append(
        types.Content(
            role="user",
            parts=[types.Part(text=user_message)]
        )
    )

    # Agentic loop
    while True:
        response = client.models.generate_content(
            model=MODEL,
            contents=history,
            config=types.GenerateContentConfig(
                system_instruction=GITPILOT_SYSTEM_PROMPT,
                tools=[list_projects,
                       list_issues,
                       get_issue_detail,
                       list_pipelines,
                       get_pipeline_jobs,
                       get_project_summary,
                       list_merge_requests,
                       get_pipeline_failure_diagnosis,
                       generate_mr_description,
                       generate_sprint_retrospective,
                       create_issue_comment,
                       update_issue_labels,
                       close_issue,
                       create_mr_comment,
                       create_issue,
                       search_issues],
                temperature=0.2
            )
        )

        candidate = response.candidates[0]
        history.append(candidate.content)  # Add assistant response to history

        # Collect any function calls in this response
        function_calls = [
            part.function_call
            for part in candidate.content.parts
            if part.function_call is not None
        ]

        if not function_calls:
            # No tool calls — extract and return final text
            for part in candidate.content.parts:
                if part.text:
                    return part.text
            return "Agent completed but returned no text."

        # Execute each tool and collect results
        tool_response_parts = []
        for fc in function_calls:
            tool_name = fc.name
            tool_args = dict(fc.args) if fc.args else {}

            print(f"🔧 Agent calling tool: {tool_name}({tool_args})")

            try:
                fn = TOOL_FUNCTIONS[tool_name]
                result = fn(**tool_args)
            except Exception as e:
                result = {"error": str(e)}

            tool_response_parts.append(
                types.Part.from_function_response(
                    name=tool_name,
                    response={"result": json.dumps(result, default=str)}
                )
            )

        # Feed tool results back into the conversation
        history.append(
            types.Content(
                role="user",
                parts=tool_response_parts
            )
        )