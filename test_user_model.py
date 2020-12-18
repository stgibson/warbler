"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


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


class UserModelTestCase(TestCase):
    """Test User model."""

    def setUp(self):
        """Create test client."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        self.client = app.test_client()

    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages, no followers, no followings, & no likes
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)
        self.assertEqual(len(u.following), 0)
        self.assertEqual(len(u.likes), 0)

        # User should have inputted fields
        self.assertEqual(u.email, "test@test.com")
        self.assertEqual(u.username, "testuser")
        self.assertEqual(u.password, "HASHED_PASSWORD")

        # __repr__() should return description of User
        self.assertEqual(u.__repr__(), \
            f"<User #{u.id}: testuser, test@test.com>")

        # User should have default attributes for images URLs
        self.assertEqual(u.image_url, "/static/images/default-pic.png")
        self.assertEqual(u.header_image_url, "/static/images/warbler-hero.jpg")

        # test adding optional attributes
        u.image_url = "http://test-url.png"
        u.header_image_url = "http://test-header-url.png"
        u.bio = "This is a test bio for testuser"
        u.location = "Test City, TS"

        db.session.add(u)
        db.session.commit()

        self.assertEqual(u.image_url, "http://test-url.png")
        self.assertEqual(u.header_image_url, "http://test-header-url.png")
        self.assertEqual(u.bio, "This is a test bio for testuser")
        self.assertEqual(u.location, "Test City, TS")

        # verify can create user with initial image_url
        u_with_image = User(
            email="test_with_image@test.com",
            username="testuserwithimage",
            password="HASHED_PASSWORD",
            image_url="http://test-url.png"
        )

        db.session.add(u_with_image)
        db.session.commit()
    
        # User should have inputted fields
        self.assertEqual(u_with_image.email, "test_with_image@test.com")
        self.assertEqual(u_with_image.username, "testuserwithimage")
        self.assertEqual(u_with_image.password, "HASHED_PASSWORD")
        self.assertEqual(u_with_image.image_url, "http://test-url.png")

    def test_user_model_fail(self):
        """Does model fail to create a user with invalid input?"""

        # first create a user successfully to test for validating uniqueness
        u1 = User(
            email="test1@test.com",
            username="testuser1",
            password="HASHED_PASSWORD"
        )

        db.session.add(u1)
        db.session.commit()

        # attempt to create user with same email
        u2 = User(
            email="test1@test.com",
            username="testuser2",
            password="HASHED_PASSWORD"
        )

        db.session.add(u2)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        # attempt to create user with same username
        u2 = User(
            email="test2@test.com",
            username="testuser1",
            password="HASHED_PASSWORD"
        )

        db.session.add(u2)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        # attempt to create user with no email
        u2 = User(
            username="testuser2",
            password="HASHED_PASSWORD"
        )

        db.session.add(u2)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        # attempt to create user with no username
        u2 = User(
            email="test2@test.com",
            password="HASHED_PASSWORD"
        )

        db.session.add(u2)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        # attempt to create user with no hashed password
        u2 = User(
            email="test2@test.com",
            username="testuser1"
        )
        
        db.session.add(u2)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_user_model_is_following(self):
        """Does is_following detect whether or not u1 is following u2?"""

        u1 = User(
            email="test1@test.com",
            username="testuser1",
            password="HASHED_PASSWORD"
        )
        
        db.session.add(u1)
        db.session.commit()

        u2 = User(
            email="test2@test.com",
            username="testuser2",
            password="HASHED_PASSWORD"
        )

        db.session.add(u2)
        db.session.commit()

        # is_following should detect that u1 is not following u2
        self.assertFalse(u1.is_following(u2))
        
        u1.following.append(u2)
        db.session.commit()

        # is_following should detect that u1 is following u2
        self.assertTrue(u1.is_following(u2))

    def test_user_model_is_followed_by(self):
        """Does is_followed_by detect whether or not u1 is followed by u2?"""

        u1 = User(
            email="test1@test.com",
            username="testuser1",
            password="HASHED_PASSWORD"
        )
        
        db.session.add(u1)
        db.session.commit()

        u2 = User(
            email="test2@test.com",
            username="testuser2",
            password="HASHED_PASSWORD"
        )

        db.session.add(u2)
        db.session.commit()

        # is_followed_by should detect that u1 is not followed by u2
        self.assertFalse(u1.is_followed_by(u2))

        u2.following.append(u1)
        db.session.commit()

        # is_followed_by should detect that u1 is followed by u2
        self.assertTrue(u1.is_followed_by(u2))

    def test_user_model_authenticate(self):
        """
            Does authenticate return a user only when given a valid username
            and password?
        """

        # try to sign up a 

        u = User.signup(
            username="testuser",
            email="test@test.com",
            password="testpassword",
            image_url="http://test-url.png"
        )
        db.session.commit()

        # user should have correct attributes
        self.assertEqual(u.username, "testuser")
        self.assertEqual(u.email, "test@test.com")
        self.assertEqual(u.image_url, "http://test-url.png")
        # test that password was hashed
        self.assertNotEqual(u.password, "testpassword")

        # try logging in with invalid username
        self.assertFalse(User.authenticate(username="user", \
            password="testpassword"))

        # try logging in with invalid password
        self.assertFalse(User.authenticate(username="testuser", \
            password="password"))

        # try logging in with valid username and password
        self.assertTrue(User.authenticate(username="testuser", \
            password="testpassword"))