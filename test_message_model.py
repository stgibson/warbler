"""Message model tests."""

# run these tests like:
#
#    python -m unittest test_message_model.py


import os
from unittest import TestCase

from models import db, User, Message, Follows
from sqlalchemy.exc import IntegrityError

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class MessageModelTestCase(TestCase):
    """Test User model."""

    def setUp(self):
        """Create test client."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        self.client = app.test_client()

    def test_message_model(self):
        """Does basic model work?"""

        # first create a user to create a message
        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )
        
        db.session.add(u)
        db.session.commit()

        msg = Message(
            text="Test message.",
            user_id=u.id
        )

        db.session.add(msg)
        db.session.commit()

        # message should have basic attributes and access to its user
        self.assertEqual(msg.text, "Test message.")
        self.assertEqual(msg.user_id, u.id)
        # should have autocreated a timestamp
        self.assertIsNotNone(msg.timestamp)
        self.assertEqual(msg.user.email, "test@test.com")
        self.assertEqual(msg.user.username, "testuser")
        self.assertEqual(msg.user.password, "HASHED_PASSWORD")

        # user should also have access to messages
        self.assertEqual(u.messages[0].text, "Test message.")

    def test_message_model_fail(self):
        """Does model fail to create a new message with invalid input?"""

        # first create a user to create a message
        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )
        
        db.session.add(u)
        db.session.commit()

        # try to create a message with no text
        msg = Message(user_id=u.id)

        db.session.add(msg)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        # try to create a message with no user id
        msg = Message(text="Test message.")

        db.session.add(msg)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_message_likes(self):
        """Can a user like a message?"""

        u1 = User(
            email="test1@test.com",
            username="testuser1",
            password="HASHED_PASSWORD"
        )

        db.session.add(u1)
        db.session.commit()

        # create another user to create a message
        u2 = User(
            email="test2@test.com",
            username="testuser2",
            password="HASHED_PASSWORD"
        )

        db.session.add(u2)
        db.session.commit()

        # create a message
        msg = Message(
            text="Test message.",
            user_id=u2.id
        )

        db.session.add(msg)
        db.session.commit()

        # u1 shouldn't have any likes yet
        self.assertEqual(len(u1.likes), 0)

        # u1 likes msg
        u1.likes.append(msg)
        db.session.commit()

        # u1 should not like msg
        self.assertEqual(u1.likes[0], msg)