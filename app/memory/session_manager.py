from uuid import uuid4


class SessionManager:

    def __init__(self):

        self.active_sessions = set()

    def create_session(self) -> str:

        session_id = str(uuid4())

        self.active_sessions.add(session_id)

        return session_id

    def session_exists(
        self,
        session_id: str
    ) -> bool:

        return session_id in self.active_sessions

    def delete_session(
        self,
        session_id: str
    ):

        self.active_sessions.discard(session_id)


session_manager = SessionManager()