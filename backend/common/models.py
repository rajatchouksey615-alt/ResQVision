"""Small cross-domain model primitives."""

import uuid

from django.core.exceptions import ValidationError
from django.db import models


class UUIDPrimaryKeyModel(models.Model):
    """Abstract base for ResQVision-owned records with consistent UUID keys."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("This record is append-only.")

    def delete(self):
        raise ValidationError("This record is append-only.")


class AppendOnlyUUIDModel(UUIDPrimaryKeyModel):
    """UUID record whose normal ORM paths permit insertion but reject mutation."""

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("This record is append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("This record is append-only.")
