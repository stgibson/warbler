"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)

        db.session.commit()

        self.base_url = "http://localhost"

    def test_messages_add(self):
        """Can user add a message only when logged in?"""

        with self.client as c:
            # try adding message while logged in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post("/messages/new", data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msg = Message.query.one()
            self.assertEqual(msg.text, "Hello")

            # try adding message while logged out
            with c.session_transaction() as sess:
                del sess[CURR_USER_KEY]

            resp = c.post("/messages/new", data={"text": "Howdy"})

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, f"{self.base_url}/")

            # should still only be 1 message
            messages = Message.query.all()
            self.assertEqual(len(messages), 1)

    def test_messages_show(self):
        """
            Can user see other user's messages regardless of whether or not
            user is logged in?
        """

        with self.client as c:
            testuser_id = self.testuser.id
            testuser_username = self.testuser.username
            # try to see someone elses message while logged in
            with c.session_transaction() as sess:
                    sess[CURR_USER_KEY] = testuser_id

            # create another user, who creates a message
            username = "otheruser"
            email = "other@test.com"
            password = "otheruser"
            othertestuser = User.signup(username=username,
                                        email=email,
                                        password=password,
                                        image_url=None)
            db.session.commit()
            othertestuser_id = othertestuser.id

            text = "Hello from other"
            msg = Message(text=text, user_id=othertestuser_id)
            db.session.add(msg)
            db.session.commit()
            msg_id = msg.id

            resp = c.get(f"/messages/{msg_id}")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(f"@{username}", html)
            self.assertIn(text, html)
            self.assertIn("Follow", html)

            # try to see someone elses message while logged out
            with c.session_transaction() as sess:
                del sess[CURR_USER_KEY]

            resp = c.get(f"/messages/{msg_id}")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(f"@{username}", html)
            self.assertIn(text, html)
            self.assertNotIn("Follow", html)

            # try to see own message while logged in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = testuser_id

            # first user creates own message
            text = "Hello from self"
            msg = Message(text=text, user_id=testuser_id)
            db.session.add(msg)
            db.session.commit()
            msg_id = msg.id

            resp = c.get(f"/messages/{msg_id}")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(testuser_username, html)
            self.assertIn(text, html)
            self.assertIn("Delete", html)

    def test_messages_destroy(self):
        """Can user delete own a message only when logged in?"""
        with self.client as c:
            testuser_id = self.testuser.id
            # try to delete own message while logged in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = testuser_id

            msg = Message(text="Hello", user_id=testuser_id)
            db.session.add(msg)
            db.session.commit()
            msg_id = msg.id

            resp = c.post(f"/messages/{msg_id}/delete")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(len(Message.query.all()), 0)

            # try to delete a message while logged out
            msg = Message(text="Hello", user_id=testuser_id)
            db.session.add(msg)
            db.session.commit()
            msg_id = msg.id
            with c.session_transaction() as sess:
                del sess[CURR_USER_KEY]

            resp = c.post(f"/messages/{msg_id}/delete")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, f"{self.base_url}/")
            self.assertEqual(len(Message.query.all()), 1)

            # try to delete another user's message while logged in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = testuser_id

            username = "otheruser"
            email = "other@test.com"
            password = "otheruser"
            othertestuser = User.signup(username=username,
                                        email=email,
                                        password=password,
                                        image_url=None)
            db.session.commit()
            othertestuser_id = othertestuser.id

            text = "Hello from other"
            msg = Message(text=text, user_id=othertestuser_id)
            db.session.add(msg)
            db.session.commit()
            msg_id = msg.id

            resp = c.post(f"/messages/{msg_id}/delete")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, f"{self.base_url}/")
            self.assertEqual(len(Message.query.all()), 2)