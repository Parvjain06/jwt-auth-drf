from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from accounts.demo import make_expired_access_token


class Command(BaseCommand):
    help = (
        "Print a correctly signed access token that has already expired, so the "
        "expired-token case can be demonstrated in Postman without waiting 5 minutes."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo")
        parser.add_argument("--minutes-ago", type=int, default=1,
                            help="How many minutes ago the token expired.")

    def handle(self, *args, **options):
        try:
            user = get_user_model().objects.get(username=options["username"])
        except get_user_model().DoesNotExist as exc:
            raise CommandError(f"No user named {options['username']!r}. Run create_demo_user first.") from exc
        self.stdout.write(str(make_expired_access_token(user, options["minutes_ago"])))
