import unittest

from app.auth.demo import DEMO_USER_ID
from app.auth.demo import DemoIdentityProvider
from app.core.errors import ValidationAppError


class DemoIdentityProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_current_user_returns_stable_demo_user(self) -> None:
        provider = DemoIdentityProvider()

        user = await provider.current_user()

        self.assertEqual(user.uid, DEMO_USER_ID)
        self.assertEqual(user.auth_mode, "demo")

    async def test_rejects_empty_demo_uid(self) -> None:
        with self.assertRaises(ValidationAppError):
            DemoIdentityProvider(uid=" ")


if __name__ == "__main__":
    unittest.main()
