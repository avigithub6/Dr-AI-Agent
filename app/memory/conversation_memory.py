from typing import Dict, List

conversation_store: Dict[str, List[dict]] = {}


def create_session(session_id: str):

    if session_id not in conversation_store:

        conversation_store[session_id] = []


def add_message(
    session_id: str,
    role: str,
    message: str
):

    create_session(session_id)

    conversation_store[session_id].append(
        {
            "role": role,
            "content": message
        }
    )


def get_messages(session_id: str, limit: int = 10):

    create_session(session_id)

    return conversation_store[session_id][-limit:]


def clear_session(session_id: str):

    conversation_store.pop(session_id, None)