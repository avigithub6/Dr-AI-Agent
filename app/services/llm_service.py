from app.agents.medical_agent import generate_response as run_medical_agent


def generate_response(messages: list[dict[str, str]]) -> str:
    """Generate a response by running the LangGraph medical workflow."""
    return run_medical_agent(messages)