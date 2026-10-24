from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create (or reset) the demo users used by the Postman collection."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="DogsAreGreat!2026")

    def handle(self, *args, **options):
        User = get_user_model()
        for username in ("demo", "other"):
            user, created = User.objects.get_or_create(
                username=username, defaults={"email": f"{username}@example.com"}
            )
            user.set_password(options["password"])
            user.is_active = True
            user.save()
            verb = "Created" if created else "Reset"
            self.stdout.write(self.style.SUCCESS(f"{verb} user '{username}'"))
        self.stdout.write(f"Password for both: {options['password']}")
