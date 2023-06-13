from django.db import models


class UserOperation(models.Model):
    class TypeChoices(models.TextChoices):
        CREATION = "C"
        DELETION = "D"

    user_id = models.CharField(max_length=20)
    last_name = models.CharField(max_length=50)
    first_name = models.CharField(max_length=50)
    email = models.EmailField()
    date_for_change = models.DateField()
    type_operation = models.CharField(max_length=1, choices=TypeChoices.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "type_operation"],
                name="%(app_label)s_%(class)s_unique_operation_for_user",
            ),
        ]
