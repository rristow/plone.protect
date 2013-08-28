import unittest2 as unittest

from plone.testing.z2 import Browser
from plone.protect.testing import PROTECT_FUNCTIONAL_TESTING

from plone.protect import createToken
from plone.protect.authenticator import AuthenticatorView
from plone.keyring.interfaces import IKeyManager
from zope.component import getUtility
from plone.app.testing import logout
from plone.app.testing import login
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import TEST_USER_PASSWORD


class AutoCSRFProtectTests(unittest.TestCase):
    layer = PROTECT_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.browser = Browser(self.layer['app'])
        self.request = self.layer['request']
        login(self.portal, TEST_USER_NAME)
        self.open('login_form')
        self.browser.getControl(name='__ac_name').value = TEST_USER_NAME
        self.browser.getControl(
            name='__ac_password').value = TEST_USER_PASSWORD
        self.browser.getControl(name='submit').click()

    def open(self, path):
        self.browser.open(self.portal.absolute_url() + '/' + path)

    def test_adds_csrf_protection_input(self):
        self.open('test-unprotected')
        self.assertTrue('name="_authenticator"' in self.browser.contents)

    def test_authentication_works_automatically(self):
        self.open('test-unprotected')
        self.browser.getControl('submit1').click()

    def test_authentication_works_for_other_form(self):
        self.open('test-unprotected')
        self.browser.getControl('submit2').click()

    def test_works_for_get_form_yet(self):
        self.open('test-unprotected')
        self.browser.getControl('submit3').click()

    def test_forbidden_raised_if_auth_failure(self):
        self.open('test-unprotected')
        self.browser.getForm('one').\
            getControl(name="_authenticator").value = 'foobar'
        try:
            self.browser.getControl('submit1').click()
        except Exception, ex:
            self.assertEquals(ex.getcode(), 403)

    def test_CSRF_header(self):
        self.request.environ['HTTP_X_CSRF_TOKEN'] = createToken()
        view = AuthenticatorView(None, self.request)
        self.assertEqual(view.verify(), True)

    def test_incorrect_CSRF_header(self):
        self.request.environ['HTTP_X_CSRF_TOKEN'] = 'foobar'
        view = AuthenticatorView(None, self.request)
        self.assertEqual(view.verify(), False)

    def test_only_add_auth_when_user_logged_in(self):
        logout()
        self.open('logout')
        self.open('test-unprotected')
        try:
            self.browser.getForm('one').getControl(name="_authenticator")
            self.assertEqual('anonymous should not be protected', '')
        except LookupError:
            pass

    def test_keyrings_get_rotated_on_requests(self):
        manager = getUtility(IKeyManager)
        ring = manager['_forms']
        keys = ring.data
        self.assertEqual(ring.last_rotation, 0)
        self.open('test-unprotected')
        self.assertNotEqual(keys, ring.data)
        self.assertNotEqual(ring.last_rotation, 0)
