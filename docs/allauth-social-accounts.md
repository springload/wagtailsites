# Django allauth integration

Follow [django-allauth installation](http://django-allauth.readthedocs.io/en/latest/installation.html) instructions

## django-allauth and Wagtail
- [x] Don't use `django.contrib.sites.middleware.CurrentSiteMiddleware`
    - It clash with Wagtail `wagtail.wagtailcore.middleware.SiteMiddleware`
    - make sure django sites and wagtail site are in sync.
- [x] redirect django admin login page to allauth login page (in urls.py)
- [x] redirect wagtail admin login page to allauth login page (in urls.py)
- [x] configure allauth login page as default `LOGIN_URL` and `WAGTAIL_FRONTEND_LOGIN_URL`
- [x] template styling

# Social accounts configuration

- Specific configuration for each social account provider
- User is identified by unique email (different to django default behaviour)
- Verified email is required

## Google

Based on [django-allauth documentation](http://django-allauth.readthedocs.io/en/latest/providers.html#google)

### Installation
- [x] `'allauth.socialaccount.providers.google'` in `INSTALLED_APPS`

### Configuration in Google developer console
- [x] [Create a new project](https://console.developers.google.com/projectcreate)
- [ ] Fill the details for [OAuth consent screen](https://console.developers.google.com/apis/credentials/consent)
    - [ ] at least the **Product name shown to users** - `Made With Wagtail`
- [ ] [Go to credentials page](https://console.developers.google.com/apis/credentials), verify your new project selected
(in top header), then click `Create credentials` button, choose `OAuth client ID`
    - [ ] **Application type** - `Web application`
    - [ ] **Authorised redirect URIs** - `https://madewithwagtail.org//accounts/google/login/callback/`
- [ ] copy over `Client ID` and `Client Secret`

### Configuration in django-allauth admin
- [ ] In Django admin > Social Accounts > Social Applications create a new Social application. Keep in mind there are 2 different admin panel _Django_ admin (`/django-admin`) and _Wagtail_ admin (`/admin`).
    - [ ] **Provider** - `Google`
    - [ ] **Name** - `Google`
    - [ ] **Client id** - `Client ID` from Google developer console
    - [ ] **Secret key** - `Client Secret` from Google developer console
    - [ ] **Key** - leave empty
    - [ ] **Sites** choose - `madewithwagtail.org` (might be different locally e.g. `example.com`)


A new users may sign up with their Google account on [Sign Up page](https://madewithwagtail.org/accounts/signup/)

An existing users have to sign in by their credentials ([Sign In page](https://madewithwagtail.org/accounts/login/))
and allow sign in by Google on [Account Connections page](https://madewithwagtail.org/accounts/social/connections/)
first.
