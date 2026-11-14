"""Custom human account model selected before the first migration."""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower, Trim

from apps.accounts.managers import UserManager
from common.models import UUIDPrimaryKeyModel


class User(UUIDPrimaryKeyModel, AbstractUser):
    username = None
    email = models.EmailField(max_length=254)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        db_table = "accounts_user"
        constraints = [
            models.UniqueConstraint(fields=["email"], name="uq_user_email"),
            models.CheckConstraint(
                condition=Q(email=Lower(Trim("email"))) & ~Q(email=""),
                name="ck_user_email_canonical",
            ),
        ]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.email
