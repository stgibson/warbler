"""User View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, connect_db, User, Message

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

app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False


class UserViewTestCase(TestCase):
    """Test views for users."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()
        
        self.password = "testuser"

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password=self.password,
                                    image_url=None)

        db.session.commit()

        # add default images and base url for testing
        self.image_url = "/static/images/default-pic.png"
        self.header_image_url = "/static/images/warbler-hero.jpg"
        self.base_url = "http://localhost"

    def test_signup(self):
        """
            Can you create an account? Will you fail to create an account with
            existing username or email?
        """

        with self.client as c:
            username1 = "testuser1"
            email1 = "test1@test.com"
            data = {
                "username": username1,
                "email": email1,
                "password": self.password,
                "image_url": ""
            }
            # try to create an account
            resp = c.post("/signup", data=data, follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(f"@{username1}", html)
            self.assertIn(self.header_image_url, html)
            self.assertIn(self.image_url, html)

            username2 = "testuser2"
            email2 = "test2@test.com"

            # try to create an account with a taken username
            data = {
                "username": username1,
                "email": email2,
                "password": self.password,
                "image_url": ""
            }
            resp = c.post("/signup", data=data)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Username or email already taken", html)
            # input should still be in form
            self.assertIn(username1, html)
            self.assertIn(email2, html)

            # try to create an account with a taken email
            data = {
                "username": username2,
                "email": email1,
                "password": self.password,
                "image_url": ""
            }
            resp = c.post("/signup", data=data)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Username or email already taken", html)

    def test_login(self):
        """
            Can you login with valid credentials? Will you fail to login with
            invalid credentials?
        """

        with self.client as c:
            # try to login with valid credentials
            data = {
                "username": self.testuser.username,
                "password": self.password
            }
            resp = c.post("/login", data=data, follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(f"Hello, {self.testuser.username}!", html)
            self.assertIn(f"@{self.testuser.username}", html)

            # try to login with invalid username
            wrong_username = "wrong"
            data = { "username": wrong_username, "password": self.password }
            resp = c.post("/login", data=data)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Invalid credentials.", html)
            self.assertIn(wrong_username, html)

            # try to login with invalid password
            wrong_password = "wrong_password"
            data = {
                "username": self.testuser.username,
                "password": wrong_password
            }
            resp = c.post("/login", data=data)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Invalid credentials.", html)
            self.assertIn(self.testuser.username, html)

    def test_logout(self):
        """
            Can you logout when you are logged in, and if you are already
            logged out, does it take you the the home page?
        """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # try to logout while logged in
            resp = c.get("logout")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, f"{self.base_url}/")
            with c.session_transaction() as sess:
                self.assertIsNone(sess.get(CURR_USER_KEY, None))

            # try to logout without being logged in
            resp = c.get("logout")
            
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, f"{self.base_url}/")
            with c.session_transaction() as sess:
                self.assertIsNone(sess.get(CURR_USER_KEY, None))

    def test_list_users(self):
        """
            Can you see a listing of users regardless of whether or not you are
            logged in?
        """

        # first create some more test users
        num_of_test_users = 3
        test_usernames = ("diffuser", "testuser1", "testuser2")
        test_emails = ("diff@test.com", "test1@test.com", "test2@test.com")
        test_bios = ("Test user 1", "Test user 2", "Test user 3")
        test_users = [User(username=user[0], email=user[1], \
            password="HASHED_PASSWORD", bio=user[2]) for user in \
            zip(test_usernames, test_emails, test_bios)]
        db.session.add_all(test_users)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # test going to user list page while logged in
            resp = c.get("/users")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            # should have all test users, including currently logged in user
            self.assertIn(f"@{self.testuser.username}", html)
            for i in range(num_of_test_users):
                self.assertIn(f"@{test_usernames[i]}", html)
                self.assertIn(test_bios[i], html)
            # should be follow buttons
            self.assertIn("Follow", html)

            # test searching for users
            resp = c.get("/users?q=diff")
            html = resp.get_data(as_text=True)
            
            self.assertEqual(resp.status_code, 200)
            # check for the user that should show up
            self.assertIn(f"@{test_usernames[0]}", html)
            self.assertIn(test_bios[0], html)
            # check that other users don't show up
            self.assertNotIn(f"@{self.testuser.username}", html)
            for i in range(1, num_of_test_users):
                self.assertNotIn(f"@{test_usernames[i]}", html)
                self.assertNotIn(test_bios[i], html)
            # should still be a follow button
            self.assertIn("Follow", html)

            # test searching for a user that doesn't exist
            resp = c.get("/users?q=none")
            html = resp.get_data(as_text=True)
            
            self.assertEqual(resp.status_code, 200)
            # check that other users don't show up
            self.assertNotIn(f"@{self.testuser.username}", html)
            for i in range(num_of_test_users):
                self.assertNotIn(f"@{test_usernames[i]}", html)
                self.assertNotIn(test_bios[i], html)

            # test page while logged out
            with c.session_transaction() as sess:
                del sess[CURR_USER_KEY]

            resp = c.get("/users")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(f"@{self.testuser.username}", html)
            for i in range(num_of_test_users):
                self.assertIn(f"@{test_usernames[i]}", html)
                self.assertIn(test_bios[i], html)
            # should not be any follow buttons
            self.assertNotIn("Follow", html)

    def test_users_show(self):
        """
            Can you see a user's profile regardless of whether or not you are
            logged in?
        """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # create another user's account
            username = "otheruser"
            email = "other@test.com"
            password = "password"
            bio = "I am another user"
            location = "San Francisco"
            other_user = User(username=username, email=email, password=password, \
                bio=bio, location=location)
            db.session.add(other_user)
            db.session.commit()

            # try to go to user's page while logged in
            resp = c.get(f"/users/{other_user.id}")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(f"@{username}", html)
            self.assertIn(bio, html)
            self.assertIn(location, html)

            # try to go to user's page while logged out
            with c.session_transaction() as sess:
                del sess[CURR_USER_KEY]

            resp = c.get(f"/users/{other_user.id}")
            self.assertIn(f"@{username}", html)
            self.assertIn(bio, html)
            self.assertIn(location, html)

    def test_users_following(self):
        """
            Only when you're logged in, can you see the following page for any
            user?
        """

        with self.client as c:
            # try to go to other user's following page while logged in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # create another user's account
            username = "otheruser"
            email = "other@test.com"
            password = "password"
            other_user = User(username=username, email=email, \
                password=password)
            db.session.add(other_user)
            db.session.commit()
            # have other user follow current user
            other_user.following.append(self.testuser)
            db.session.commit()

            resp = c.get(f"/users/{other_user.id}/following")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(f"@{username}", html)
            self.assertIn(f"@{self.testuser.username}", html)

            # try to go to other user's following page while logged out
            with c.session_transaction() as sess:
                del sess[CURR_USER_KEY]

            resp = c.get(f"/users/{other_user.id}/following")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, f"{self.base_url}/")

    def test_users_followers(self):
        """
            Only when you're logged in, can you see the followers page for any
            user?
        """

        with self.client as c:
            # try to go to other user's followers page while logged in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # create another user's account
            username = "otheruser"
            email = "other@test.com"
            password = "password"
            other_user = User(username=username, email=email, \
                password=password)
            db.session.add(other_user)
            db.session.commit()
            # follow other user
            other_user.followers.append(self.testuser)
            db.session.commit()

            resp = c.get(f"/users/{other_user.id}/followers")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(f"@{username}", html)
            self.assertIn(f"@{self.testuser.username}", html)

            # try to go to other user's followers page while logged out
            with c.session_transaction() as sess:
                del sess[CURR_USER_KEY]

            resp = c.get(f"/users/{other_user.id}/followers")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, f"{self.base_url}/")

    def test_add_follow(self):
        """Only when you're logged in, can you follow any user?"""

        with self.client as c:
            # try to follow other user while logged in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            # create another user's account
            username = "otheruser"
            email = "other@test.com"
            password = "password"
            other_user = User(username=username, email=email, \
                password=password)
            db.session.add(other_user)
            db.session.commit()
            other_user_id = other_user.id

            resp = c.post(f"/users/follow/{other_user_id}", \
                follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(f"@{self.testuser.username}", html)
            self.assertIn(f"@{username}", html)
            self.assertIn("Unfollow", html)

            # try to follow other user while logged out
            with c.session_transaction() as sess:
                del sess[CURR_USER_KEY]

            resp = c.post(f"/users/follow/{other_user_id}")
            
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, f"{self.base_url}/")

    def test_stop_following(self):
        """Only when you're logged in, can you unfollow a user?"""

        with self.client as c:
            # try to unfollow other user while logged in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            # create another user's account
            username = "otheruser"
            email = "other@test.com"
            password = "password"
            other_user = User(username=username, email=email, \
                password=password)
            db.session.add(other_user)
            db.session.commit()
            other_user_id = other_user.id

            # follow other user
            other_user.followers.append(self.testuser)
            db.session.commit()

            resp = c.post(f"/users/stop-following/{other_user_id}", \
                follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(f"@{self.testuser.username}", html)
            self.assertNotIn(f"@{username}", html)

            # try to unfollow other user while logged out
            with c.session_transaction() as sess:
                del sess[CURR_USER_KEY]

            resp = c.post(f"/users/stop-following/{other_user_id}")
            
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, f"{self.base_url}/")

    def test_show_likes(self):
        """Only when you're logged in, can you see any user's likes page?"""

        with self.client as c:
            # try to see other user's likes page while logged in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # create another user's account to like a message
            username = "otheruser"
            email = "other@test.com"
            password = "password"
            other_user = User(username=username, email=email, \
                password=password)
            db.session.add(other_user)
            db.session.commit()
            other_user_id = other_user.id

            # currently-logged-in user creates a message for other user to like
            text = "Test message."
            message = Message(text=text, user_id=self.testuser.id)
            db.session.add(message)
            db.session.commit()

            # other user likes this message
            other_user.likes.append(message)
            db.session.commit()

            resp = c.get(f"/users/{other_user_id}/likes")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(f"@{username}", html)
            self.assertIn(f"@{self.testuser.username}", html)
            self.assertIn(text, html)

            # try to see other user's likes page while logged out
            with c.session_transaction() as sess:
                del sess[CURR_USER_KEY]

            resp = c.get(f"/users/{other_user_id}/likes")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, f"{self.base_url}/")

    def test_add_like(self):
        """Only when you're logged in, can you like a message?"""

        with self.client as c:
            # try to like a message while logged in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # create another user's account to create a message
            username = "otheruser"
            email = "other@test.com"
            password = "password"
            other_user = User(username=username, email=email, \
                password=password)
            db.session.add(other_user)
            db.session.commit()
            other_user_id = other_user.id

            # other user creates a message to be liked
            text = "Test message."
            message = Message(text=text, user_id=other_user_id)
            db.session.add(message)
            db.session.commit()
            message_id = message.id

            resp = c.post(f"/users/add_like/{message_id}")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, f"{self.base_url}/")
            with c.session_transaction() as sess:
                testuser = User.query.get(sess[CURR_USER_KEY])
                self.assertEqual(testuser.likes[0].text, text)

            # try to like a message while logged out
            with c.session_transaction() as sess:
                del sess[CURR_USER_KEY]

            resp = c.post(f"/users/add_like/{message_id}", \
                follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized.", html)

    def test_remove_like(self):
        """Only when you're logged in, can you unlike a message?"""

        with self.client as c:
            # try to unlike a message while logged in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # create another user's account to create a message
            username = "otheruser"
            email = "other@test.com"
            password = "password"
            other_user = User(username=username, email=email, \
                password=password)
            db.session.add(other_user)
            db.session.commit()
            other_user_id = other_user.id

            # other user creates a message
            text = "Test message."
            message = Message(text=text, user_id=other_user_id)
            db.session.add(message)
            db.session.commit()
            message_id = message.id

            # current user likes message
            with c.session_transaction() as sess:
                testuser = User.query.get(sess[CURR_USER_KEY])
                testuser.likes.append(message)
                db.session.commit()

            resp = c.post(f"/users/remove_like/{message_id}")
            
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, f"{self.base_url}/")
            with c.session_transaction() as sess:
                testuser = User.query.get(sess[CURR_USER_KEY])
                self.assertEqual(len(testuser.likes), 0)

            # try to unlike a message while logged out
            with c.session_transaction() as sess:
                del sess[CURR_USER_KEY]

            resp = c.post(f"/users/remove_like/{message_id}", \
                follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized.", html)

    def test_profile(self):
        """
            Can you edit your profile with correct credentials only, only when
            you're logged in?
        """

        with self.client as c:
            # try to edit profile with correct credentials while logged in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            new_username = "newtestuser"
            new_email = "newtest@test.com"
            new_image_url = "http://new_image.png"
            new_header_image_url = "http://new_header_image.png"
            bio = "I am now a new user."
            data = {
                "username": new_username,
                "email": new_email,
                "image_url": new_image_url,
                "header_image_url": new_header_image_url,
                "bio": bio,
                "password": self.password
            }
            resp = c.post("/users/profile", data=data, follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(f"@{new_username}", html)
            self.assertIn(bio, html)
            self.assertIn(new_image_url, html)
            self.assertIn(new_header_image_url, html)

            # try to edit profile with incorrect credentials while logged in
            another_username = "anothertestuser"
            another_email = "anothertest@test.com"
            another_image_url = "http://another_image.png"
            another_header_image_url = "http://another_header_image.png"
            another_bio = "I am different once again."
            wrong_password = "wrong"
            data = {
                "username": another_username,
                "email": another_email,
                "image_url": another_image_url,
                "header_image_url": another_header_image_url,
                "bio": another_bio,
                "password": wrong_password
            }
            resp = c.post("/users/profile", data=data, follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Invalid password.", html)

            # try to edit profile while logged out
            with c.session_transaction() as sess:
                del sess[CURR_USER_KEY]

            data = {
                "username": another_username,
                "email": another_email,
                "image_url": another_image_url,
                "header_image_url": another_header_image_url,
                "bio": another_bio,
                "password": self.password
            }
            resp = c.post("/users/profile", data=data, follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized.", html)

    def test_delete_user(self):
        """Only when you're logged in, can you delete your account?"""

        with self.client as c:
            # try to delete account while logged in
            testuser_id = self.testuser.id
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post("/users/delete")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, f"{self.base_url}/signup")
            with c.session_transaction() as sess:
                self.assertIsNone(sess.get(CURR_USER_KEY, None))
            self.assertIsNone( \
                User.query.filter_by(id=testuser_id).one_or_none())
            
            # try to delete account while logged out (already logged out)
            resp = c.post("/users/delete", follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized.", html)

    def test_homepage(self):
        """Can you go to the homepage?"""

        with self.client as c:
            # try to go to the homepage while logged in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.get("/")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(f"@{self.testuser.username}", html)

            # try to go to the homepage while logged out
            with c.session_transaction() as sess:
                del sess[CURR_USER_KEY]

            resp = c.get("/")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            # verify on a page with a button to sign up
            self.assertIn("Sign up", html)