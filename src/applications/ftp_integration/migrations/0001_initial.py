# Generated by Django 4.1.5 on 2023-01-19 15:24

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="UserOperation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("user_id", models.CharField(max_length=20)),
                ("last_name", models.CharField(max_length=50)),
                ("first_name", models.CharField(max_length=50)),
                ("email", models.EmailField(max_length=254)),
                ("date_for_change", models.DateField()),
                (
                    "type_operation",
                    models.CharField(
                        choices=[("C", "Creation"), ("D", "Deletion")], max_length=1
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="useroperation",
            constraint=models.UniqueConstraint(
                fields=("user_id", "type_operation"),
                name="ftp_integration_useroperation_unique_operation_for_user",
            ),
        ),
    ]
