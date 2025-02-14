# -*- coding: utf-8 -*-

from django.core.management import BaseCommand

from wagtail.contrib.redirects.models import Redirect
from wagtail.models import Page


class Command(BaseCommand):
    """
    Create redirect for given page and it's descendants (have to be live)

    Usage:
    Run this command after you've changed the slug of the page

    ./manage.py create_redirect --page_slug=current-slug --page_old_slug=old-slug \
                --include_descendants --permanent --dry_run

        use --dry_run to see what would happen
        use --include_descendants to include whole page subtree
              (that changed due to parent page slug change)
        use --permanent to create 301 redirect (302 otherwise)

    Example usage: create redirects for developer's pages after developer's name changed
    ./manage.py create_redirect --page_slug=neon-jungle --page_old_slug=takeflight \
                --include_descendants --permanent
    """

    dry_run = True
    permanent = False

    def add_arguments(self, parser):
        parser.add_argument(
            "--page_slug",
            action="store",
            dest="page_slug",
            type=str,
            help="Find page by it's current slug",
            required=True,
        )
        parser.add_argument(
            "--page_old_slug",
            action="store",
            dest="page_old_slug",
            type=str,
            help="Old page slug for redirect",
            required=True,
        )
        parser.add_argument(
            "--include_descendants",
            action="store_true",
            dest="include_descendants",
            default=False,
            help="Create redirects for page descendants (live pages only)",
        )
        parser.add_argument(
            "--dry_run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Run command to show what would happen, but don't create any redirects",
        )
        parser.add_argument(
            "--permanent",
            action="store_true",
            dest="permanent",
            default=False,
            help="Create 301 permanent redirects",
        )

    def handle(self, *args, **options):
        page_slug = options["page_slug"]
        old_slug = options["page_old_slug"]
        include_descendants = options["include_descendants"]
        self.dry_run = options["dry_run"]
        self.permanent = options["permanent"]
        try:
            page = Page.objects.get(slug=page_slug, live=True)
        except Page.DoesNotExist:
            self.stderr.write("Can't find live page for slug {}".format(page_slug))
        else:
            self.create_page_redirect(page, page_slug, old_slug)

            if include_descendants:
                for page in page.get_descendants().live():
                    self.create_page_redirect(page, page_slug, old_slug)

    def create_page_redirect(self, page, page_slug, old_slug):
        """
        Construct old page path for given old slug and create redirect for that path.
        :param page: string current page path
        :param page_slug: string current page slug
                          it will be be parent page slug for descendant page
        :param old_slug: string old page slug
                         it will be be parent page slug for descendant page
        :return: None
        """
        site_id, root, page_path = page.get_url_parts()
        old_path = self.get_old_path(page_path, page_slug, old_slug)
        if old_path == page_path:
            self.stderr.write(
                "Error: old path {!r} has to be different to current path {!r}. "
                "Skipping redirect creation".format(old_path, page_path)
            )
        else:
            old_path = Redirect.normalise_path(old_path)
            try:
                Redirect.objects.get(old_path=old_path, site_id=site_id)
            except Redirect.DoesNotExist:
                if self.dry_run:
                    self.stdout.write(
                        "Redirect for {!r} path needs to be created.".format(old_path)
                    )
                else:
                    Redirect.objects.create(
                        old_path=old_path,
                        site_id=site_id,
                        is_permanent=self.permanent,
                        redirect_page=page,
                    )
                    self.stdout.write(
                        "Redirect for {!r} path created.".format(old_path)
                    )
            else:
                self.stdout.write(
                    "Redirect for {!r} path exists already. Skipping".format(old_path)
                )

    def get_old_path(self, page_path, slug, old_slug):
        """
        Construct old page path for given old slug
        :param page_path: string current page path
        :param slug: string current page slug
        :param old_slug: string old page slug
        :return: string
        """
        # search full "/slug/" phrase to ensure we replace correct slug only
        # to cover cases like /developers/springload/springload-2018/
        return page_path.replace("/{}/".format(slug), "/{}/".format(old_slug))
