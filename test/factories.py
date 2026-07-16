class MockUser:
    """Lightweight user double for dependency-overriding get_current_user."""

    def __init__(
        self,
        id: int = 1,
        username: str = "testuser",
        email: str = "test@example.com",
        oidc_user: bool = False,
        admin: bool = True,
        deleted: bool = False,
        first_name: str = "Test",
        last_name: str = "User",
    ):
        self.id = id
        self.username = username
        self.email = email
        self.oidc_user = oidc_user
        self.admin = admin
        self.deleted = deleted
        self.first_name = first_name
        self.last_name = last_name
