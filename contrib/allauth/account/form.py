# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from captcha.fields import ReCaptchaField
from django import forms

from core.utilities import has_recaptcha


class BaseSignUpForm(forms.Form):
    field_order = ['email', 'username', 'password1', 'password2', 'captcha']

    if has_recaptcha():
        captcha = ReCaptchaField(label='')

    def signup(self, request, user):
        """
        Invoked at signup time to complete the signup of the user.
        """
        pass
