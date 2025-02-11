import os
import re
import textwrap

from bs4 import BeautifulSoup
from modelcluster.fields import ParentalKey
from modelcluster.tags import ClusterTaggableManager
from taggit.models import Tag, TaggedItemBase
from wagtailcaptcha.models import WagtailCaptchaEmailForm

from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.core.validators import RegexValidator
from django.urls import reverse
from django.db import models
from django.conf import settings
from django.db.models import Case, Count, Q, Value, When
from django.utils.html import mark_safe

from wagtail.admin.mail import send_mail
from wagtail.contrib.forms.models import (
    AbstractEmailForm,
    AbstractFormField,
    AbstractForm,
)
from wagtail.contrib.forms.views import SubmissionsListView
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.search import index

from core import panels
from core.forms import SubmitFormBuilder
from core.utilities import has_recaptcha, validate_only_one_instance


class IndexPage(models.Model):
    """
    Abstract Index Page class. Declare a couple of abstract methods that should be implemented by
    any class implementing this 'interface'.
    """

    def clean(self):
        validate_only_one_instance(self)

    def children(self):
        raise NotImplementedError(
            "Class %s doesn't implement children()" % (self.__class__.__name__)
        )

    def get_context(self, request, *args, **kwargs):
        raise NotImplementedError(
            "Class %s doesn't implement get_context()" % (self.__class__.__name__)
        )

    class Meta:
        abstract = True


class HomePage(Page, IndexPage):
    """
    HomePage class, inheriting from wagtailcore.Page straight away
    """

    subpage_types = [
        "core.CompanyIndex",
        "core.SubmitFormPage",
    ]
    feed_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    search_fields = []

    body = RichTextField(blank=True, features=["bold", "italic", "ol", "ul", "link"])

    @property
    def og_image(self):
        # Returns image and image type of feed_image, if exists
        image = {"image": None, "type": None}
        if self.feed_image:
            image["image"] = self.feed_image
        name, extension = os.path.splitext(image["image"].file.url)
        image["type"] = extension[1:]
        return image

    def children(self):
        return self.get_children().live()

    def get_context(self, request, *args, **kwargs):
        # Get pages
        pages = (
            WagtailSitePage.objects.live()
            .descendant_of(self)
            .order_by("-is_featured", "-latest_revision_created_at")
        )

        # Filter by tag
        tag = request.GET.get("tag")
        if tag:
            pages = pages.filter(tags__slug__iexact=tag)

        # Pagination
        page = request.GET.get("page")
        paginator = Paginator(pages, 12)  # Show 12 pages per page
        try:
            pages = paginator.page(page)
        except PageNotAnInteger:
            pages = paginator.page(1)
        except EmptyPage:
            pages = paginator.page(paginator.num_pages)

        # Update template context
        context = super(HomePage, self).get_context(request, *args, **kwargs)
        context["pages"] = pages
        context["tag"] = tag
        # Only tags used by live pages
        context["tags"] = (
            Tag.objects.filter(
                core_pagetag_items__isnull=False,
                core_pagetag_items__content_object__live=True,
            )
            .annotate(count=Count("core_pagetag_items"))
            .distinct()
            .order_by("-count", "name")
        )

        return context

    class Meta:
        verbose_name = "Home Page"

    content_panels = panels.HOME_PAGE_CONTENT_PANELS
    promote_panels = panels.WAGTAIL_PAGE_PROMOTE_PANELS


class CompanyIndex(Page, IndexPage):
    """
    HomePage class, inheriting from wagtailcore.Page straight away
    """

    parent_types = ["core.HomePage"]
    subpage_types = ["core.WagtailCompanyPage"]
    search_fields = []
    body = RichTextField(
        null=True,
        blank=True,
        features=["bold", "italic", "ol", "ul", "link"],
    )
    show_map = models.BooleanField(
        default=False, help_text="Show map of companies around the world."
    )

    def children(self):
        return self.get_children().live()

    def get_context(self, request, *args, **kwargs):
        # Get pages.
        # Note: `numchild` includes draft/unpublished pages but does not create additional queries.
        pages = (
            WagtailCompanyPage.objects.live()
            .descendant_of(self)
            .distinct()
            .order_by("-numchild", "-latest_revision_created_at")
        )

        # Filter by tag
        tag = request.GET.get("tag")
        if tag:
            pages = pages.filter(tags__name__iexact=tag)

        # Pagination
        page = request.GET.get("page")
        paginator = Paginator(pages, 12)
        try:
            pages = paginator.page(page)
        except PageNotAnInteger:
            pages = paginator.page(1)
        except EmptyPage:
            pages = paginator.page(paginator.num_pages)

        # Update template context
        context = super(CompanyIndex, self).get_context(request, *args, **kwargs)
        context["pages"] = pages
        context["tag"] = tag
        return context

    class Meta:
        verbose_name = "Companies Index Page"

    content_panels = panels.WAGTAIL_COMPANY_INDEX_PAGE_CONTENT_PANELS


class PageTag(TaggedItemBase):
    content_object = ParentalKey("core.WagtailPage", related_name="tagged_items")


# Main core Page model. All main content pages inherit from this class.
class WagtailPage(Page):
    """
    Our main custom Page class. All content pages should inherit from this one.
    """

    parent_types = ["core.HomePage"]
    subpage_types = ["core.WagtailPage"]

    is_creatable = False

    feed_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    body = RichTextField(blank=True, features=["bold", "italic", "ol", "ul", "link"])
    tags = ClusterTaggableManager(through=PageTag, blank=True)
    search_fields = []

    @property
    def parent(self):
        try:
            return self.get_ancestors().reverse()[0]
        except IndexError:
            return None

    @property
    def child(self):
        for related_object in self._meta.get_all_related_objects():
            if not issubclass(related_object.model, self.__class__):
                continue
            try:
                return getattr(self, related_object.get_accessor_name())
            except ObjectDoesNotExist:
                pass

    @property
    def body_text(self):
        return BeautifulSoup(self.body, "html5lib").get_text()

    @property
    def body_excerpt(self):
        """
        Return body text replacing end of lines (. ? ! chars) with a blank space
        """
        return re.sub(r"([\.?!])([a-zA-Z])", r"\1 \2", self.body_text)

    @property
    def og_image(self):
        # Returns image and image type of feed_image or image as fallback, if exists
        image = {"image": None, "type": None}
        if self.feed_image:
            image["image"] = self.feed_image
        name, extension = os.path.splitext(image["image"].file.url)
        image["type"] = extension[1:]
        return image

    class Meta:
        verbose_name = "Content Page"

    content_panels = panels.WAGTAIL_PAGE_CONTENT_PANELS
    promote_panels = panels.WAGTAIL_PAGE_PROMOTE_PANELS


class WagtailCompanyPage(WagtailPage):
    """
    Company page listing a bunch of site pages
    """

    parent_types = ["core.HomePage"]
    subpage_types = ["core.WagtailSitePage"]

    SITES_ORDERING_ALPHABETICAL = "alphabetical"
    SITES_ORDERING_CREATED = "created"
    SITES_ORDERING_PATH = "path"
    SITES_ORDERING = {
        SITES_ORDERING_PATH: {
            "name": "Path (i.e. manual)",
            "ordering": ["-path"],
        },
        SITES_ORDERING_ALPHABETICAL: {
            "name": "Alphabetical",
            "ordering": ["title"],
        },
        SITES_ORDERING_CREATED: {
            "name": "Created",
            "ordering": ["-first_published_at"],
        },
    }
    SITES_ORDERING_CHOICES = [
        (key, opts["name"])
        for key, opts in sorted(SITES_ORDERING.items(), key=lambda k: k[1]["name"])
    ]

    company_url = models.URLField(
        blank=True,
        null=True,
        help_text='The URL of your site, something like "https://www.springload.co.nz"',
    )
    github_url = models.URLField(null=True, blank=True)
    twitter_url = models.URLField(null=True, blank=True)
    location = models.CharField(max_length=128, blank=True, null=True)
    show_map = models.BooleanField(
        default=True, help_text="Show company in the map of companies around the world."
    )
    coords = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        validators=[RegexValidator(r"-?[0-9\.]+,\s?-?[0-9\.]+")],
    )

    logo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    sites_ordering = models.CharField(
        max_length=20,
        blank=False,
        choices=SITES_ORDERING_CHOICES,
        default=SITES_ORDERING_CREATED,
        help_text="The order the sites will be listed on the page",
    )

    search_fields = Page.search_fields + [
        index.SearchField("company_url", boost=1),
        index.SearchField("body_text", boost=1),
    ]

    @property
    def latlong(self):
        if self.coords and "," in self.coords:
            return self.coords.split(",")
        return None

    @property
    def lat(self):
        return self.latlong and self.latlong[0]

    @property
    def lon(self):
        return self.latlong and self.latlong[1]

    @property
    def twitter_handler(self):
        if self.twitter_url:
            return "@%s" % self.twitter_url.strip("/ ").split("/")[-1]
        else:
            return None

    @property
    def github_user(self):
        if self.github_url:
            return self.github_url.strip("/ ").split("/")[-1]
        else:
            return None

    @property
    def children_count(self):
        return self.children().count()

    @property
    def og_image(self):
        # Returns image and image type of logo or feed_image as fallback, if exists
        image = {"image": None, "type": None}
        if self.logo:
            image["image"] = self.logo
        elif self.feed_image:
            image["image"] = self.feed_image
        name, extension = os.path.splitext(image["image"].file.url)
        image["type"] = extension[1:]
        return image

    def children(self):
        user_ordering = self.SITES_ORDERING[self.sites_ordering]["ordering"]
        pages = WagtailSitePage.objects.live().filter(
            Q(path__startswith=self.path) | Q(in_cooperation_with=self)
        )

        # When ordering by `path`, the collaborations would either all be listed first or last
        # depending on whether the collaborator(s) page(s) was created before or after this page.
        # Adding an overwrite here so collaborations always appear last.
        if self.sites_ordering == self.SITES_ORDERING_PATH:
            pages = pages.annotate(
                is_own=Case(
                    When(path__startswith=self.path, then=Value(True)),
                    default_value=Value(False),
                    output_field=models.BooleanField(),
                )
            ).order_by("is_own", *user_ordering)

        # When ordering alphabetically or by creation date,
        # own sites and collaboration sites will be sorted together.
        else:
            pages = pages.order_by(*user_ordering)

        return pages

    def get_context(self, request, *args, **kwargs):
        # Get pages
        pages = self.children()

        # Pagination
        page = request.GET.get("page")
        paginator = Paginator(pages, 12)  # Show 12 pages per page
        try:
            pages = paginator.page(page)
        except PageNotAnInteger:
            pages = paginator.page(1)
        except EmptyPage:
            pages = paginator.page(paginator.num_pages)

        # Update template context
        context = super(WagtailCompanyPage, self).get_context(request, *args, **kwargs)
        context["pages"] = pages
        return context

    @property
    def sites_count(self):
        # Note: It uses `self.numchild` which counts draft/unpublished pages but does not create additional queries.
        return self.get_children_count()

    class Meta:
        verbose_name = "Company Page"

    content_panels = panels.WAGTAIL_COMPANY_PAGE_CONTENT_PANELS
    settings_panels = panels.WAGTAIL_COMPANY_PAGE_SETTINGS_PANELS


class WagtailSitePage(WagtailPage):
    """
    Site page
    """

    parent_types = ["core.WagtailCompanyPage"]
    subpage_types = []
    is_featured = models.BooleanField(
        "Featured",
        default=False,
        blank=False,
        help_text="If enabled, this site will appear on top of the sites list of the homepage.",
    )
    site_screenshot = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=mark_safe(
            "Use a <b>ratio</b> of <i>16:13.28</i> "
            "and a <b>size</b> of at least <i>1200x996 pixels</i> "
            "for an optimal display."
        ),
    )
    site_url = models.URLField(
        blank=True,
        null=True,
        help_text='The URL of your site, something like "https://www.springload.co.nz"',
    )

    in_cooperation_with = models.ForeignKey(
        "core.WagtailCompanyPage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    search_fields = Page.search_fields + [
        index.SearchField("site_url"),
        index.SearchField("body_text"),
    ]

    @property
    def og_image(self):
        # Returns image and image type of feed_image, if exists
        image = {"image": None, "type": None}
        if self.feed_image:
            image["image"] = self.feed_image
        elif self.site_screenshot:
            image["image"] = self.site_screenshot
        name, extension = os.path.splitext(image["image"].file.url)
        image["type"] = extension[1:]
        return image

    def __str__(self):
        if self.site_url:
            return "%s - %s" % (self.title, self.site_url)
        return self.title

    class Meta:
        verbose_name = "Site Page"

    content_panels = panels.WAGTAIL_SITE_PAGE_CONTENT_PANELS
    promote_panels = panels.WAGTAIL_SITE_PAGE_PROMOTE_PANELS


class SubmitFormField(AbstractFormField):
    page = ParentalKey("SubmitFormPage", related_name="form_fields")


class SubmitFormPageSubmissionsListView(SubmissionsListView):
    """
    Will need changes in whatever version of Wagtail changes over to filtersets for this filtering
    """

    def get_filtering(self):
        filtering = super().get_filtering()
        if "pk" in self.request.GET:
            filtering["pk"] = self.request.GET.get("pk")
        return filtering


class SubmitFormPage(WagtailCaptchaEmailForm if has_recaptcha() else AbstractEmailForm):
    """
    Form page, inherits from WagtailCaptchaEmailForm if available, otherwise fallback to AbstractEmailForm
    """

    submissions_list_view_class = SubmitFormPageSubmissionsListView

    def __init__(self, *args, **kwargs):
        super(SubmitFormPage, self).__init__(*args, **kwargs)

        # WagtailCaptcha does not respect cls.form_builder and overwrite with its own.
        # See https://github.com/springload/wagtail-django-recaptcha/issues/7 for more info.
        self.form_builder = SubmitFormBuilder

    parent_types = ["core.HomePage"]
    subpage_types = []

    search_fields = []
    body = RichTextField(
        blank=True, help_text="Edit the content you want to see before the form."
    )
    thank_you_text = RichTextField(
        blank=True,
        help_text="Set the message users will see after submitting the form.",
    )

    class Meta:
        verbose_name = "Form Page"

    def process_form_submission(self, form):
        # Reproduce EmailFormMixin, but passing the submission to send_mail
        submission = AbstractForm.process_form_submission(self, form)
        if self.to_address:
            self.send_mail(form, submission=submission)
        return submission

    def send_mail(self, form, submission=None):
        addresses = [x.strip() for x in self.to_address.split(",")]
        send_mail(
            self.subject,
            self.render_email(form, submission=submission),
            addresses,
            self.from_address,
        )

    def render_email(self, form, submission=None):
        body = super().render_email(form)

        if submission:
            path = reverse(
                "wagtailforms:list_submissions",
                kwargs={"page_id": submission.page_id},
            )
            url = self.get_site().root_url + path
            body += textwrap.dedent(
                """
                <a href="{url}?{filter_query}">Submission {sub_id}</a>
                """.format(
                    url=url,
                    sub_id=submission.id,
                    filter_query="pk=" + str(submission.id),
                )
            )
        return body

    content_panels = panels.SUBMIT_FORM_PAGE_CONTENT_PANELS
