from __future__ import annotations

import csv
import logging
from datetime import date, datetime, timedelta
from ftplib import FTP
from pathlib import Path
from typing import Generator, TextIO

import ldap
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django.utils.module_loading import import_string

from applications.ftp_integration.ldap import BaseLDAPIntegration
from applications.ftp_integration.models import UserOperation
from applications.ftp_integration.utils import SessionReuseFTP_TLS

logger = logging.getLogger(__name__)


class FTPIntegrationService:
    file_type_name = (
        "hiring",
        "employee_update",
        "position_update",
    )
    export_folder = "export"
    headers_mapping = {
        "Prénom": "first_name",
        "Nom": "last_name",
        "E-mail": "email",
        "Identifiant": "user_id",
        "Date entrée poste": "date_begin",
        "Date de fin": "date_end",
    }
    date_format = "%d/%m/%Y"

    def __init__(self) -> None:
        super().__init__()
        self.ldap_integration: BaseLDAPIntegration = import_string(
            settings.LDAP_INTEGRATION_CLASS
        )()

    def retrieve_person_files(self):
        ftp_class = SessionReuseFTP_TLS if settings.FTP_USE_TLS else FTP
        settings.FTP_FOLDER.mkdir(parents=True, exist_ok=True)

        with ftp_class(**settings.FTP_CONNEXION) as ftp:
            if settings.FTP_USE_TLS:
                ftp.prot_p()
            for file_path in ftp.nlst(self.export_folder):
                # folder prefix or not in the path depends on the FTP server implementation
                if not file_path.startswith(f"{self.export_folder}/"):
                    file_path = f"{self.export_folder}/{file_path}"
                file_path = Path(file_path)
                if not file_path.name.startswith(self.file_type_name):
                    continue
                output_file_path = settings.FTP_FOLDER / file_path.name
                with output_file_path.open(mode="wb") as output_file:
                    ftp.retrbinary(f"RETR {file_path}", output_file.write)
                if settings.FTP_CLEANUP_FILE:
                    ftp.delete(str(file_path))
                logger.info(
                    f"processed file {file_path.name} from FTP {settings.FTP_CONNEXION['host']}"
                )

    def process_creation(self, user_id: str, data: dict):
        assert user_id, "user_id can't be empty"
        date_begin = data.pop("date_begin", None)
        date_end = data.pop("date_end", None)
        if not date_begin:
            raise ValueError("Missing date_begin field")
        UserOperation.objects.update_or_create(
            type_operation=UserOperation.TypeChoices.CREATION,
            user_id=user_id,
            defaults=dict(
                date_for_change=datetime.strptime(date_begin, self.date_format), **data
            ),
        )
        self._update_date_end(user_id, date_end)

    def process_employee_update(self, user_id: str, data: dict):
        assert user_id, "user_id can't be empty"
        employee_data = {
            key: data[key]
            for key in {"first_name", "last_name", "email"}
            if key in data
        }
        try:
            self.ldap_integration.update_ldap_user(user_id, **employee_data)
        except ldap.NO_SUCH_OBJECT:
            # try to update existing creation query
            object_number = UserOperation.objects.filter(
                type_operation=UserOperation.TypeChoices.CREATION, user_id=user_id
            ).update(**employee_data)
            if object_number == 0:
                # No operation scheduled, treat the line as a creation instead
                self.process_creation(user_id, data)

    def process_position_update(self, user_id: str, data: dict):
        assert user_id, "user_id can't be empty"
        # update only begin and end date for now, no management of job change
        date_begin = data.pop("date_begin", None)
        date_end = data.pop("date_end", None)
        if date_begin:
            # We don't care if it does not exist, that means the user was already created
            UserOperation.objects.filter(
                type_operation=UserOperation.TypeChoices.CREATION, user_id=user_id
            ).update(date_for_change=datetime.strptime(date_begin, self.date_format))
        self._update_date_end(user_id, date_end)

    def _update_date_end(self, user_id: str, date_end: str):
        if date_end:
            UserOperation.objects.update_or_create(
                type_operation=UserOperation.TypeChoices.DELETION,
                user_id=user_id,
                defaults=dict(
                    date_for_change=datetime.strptime(date_end, self.date_format),
                ),
            )

    def parse_file(self, file: TextIO):
        logger.debug(f" Parsing file : {file.name}")

        match Path(file.name).name[0]:
            case "h":  # Hiring
                process_function = self.process_creation
            case "e":  # Employee
                process_function = self.process_employee_update
            case "p":  # Position
                process_function = self.process_position_update
            case _:
                raise ValueError(f"File {file.name} is not handled")

        reader = csv.DictReader(
            file,
            strict=True,
            delimiter=";",
        )
        for index, line in enumerate(reader):
            try:
                data = {
                    data_key: line[line_header]
                    for line_header, data_key in self.headers_mapping.items()
                }
            except KeyError as e:
                logger.error(f'Missing column "{e.args[0]}" in file {file.name}')
                break
            user_id = data.pop("user_id")
            try:
                process_function(user_id, data)
            except (ValueError, AssertionError) as e:
                logger.exception(f"Error '{e}' in file {file.name} L.{index+1}")
                continue

    def sorted_ftp_files(self, folder_path: Path) -> Generator[Path, None, None]:
        # assign ordering from first letter of file name
        file_ordering = {"h": 0, "e": 1, "p": 1}
        # iterate so that user creation comes first
        for file_path in sorted(
            folder_path.iterdir(),
            key=lambda path: f"{file_ordering.get(path.name[0], -1)}{path.name}",
        ):
            if not file_path.is_file() or not file_path.name.startswith(
                self.file_type_name
            ):
                continue
            yield file_path

    def process_person_files(self):
        with self.ldap_integration:
            for file_path in self.sorted_ftp_files(
                settings.FTP_FOLDER,
            ):
                with file_path.open("r", encoding="utf-8-sig") as f:
                    self.parse_file(f)
                processed_folder = Path(
                    timezone.now().strftime(str(settings.FTP_PROCESSED_FOLDER))
                )
                processed_folder.mkdir(parents=True, exist_ok=True)
                file_path.rename(processed_folder / file_path.name)

    def process_db_operation(self):
        today = date.today()

        # would be good to use select_for_update to lock the rows, but it does not exist on sqlite
        # it is of no matter because all operations are launched sequentially
        # so we don't really care about concurrency
        creation_filter = Q(
            type_operation=UserOperation.TypeChoices.CREATION,
            date_for_change__lte=today + timedelta(days=1),
        )
        deletion_filter = Q(
            type_operation=UserOperation.TypeChoices.DELETION,
            date_for_change__lte=today - timedelta(days=1),
        )

        with self.ldap_integration:
            for operation in UserOperation.objects.filter(creation_filter):
                # employee arrive tomorrow or before, create them
                employee_data = dict(
                    user_id=operation.user_id,
                    first_name=operation.first_name,
                    last_name=operation.last_name,
                    email=operation.email,
                )
                try:
                    self.ldap_integration.create_ldap_user(**employee_data)
                except ValueError as e:
                    logger.exception(
                        f"Error '{e}' in user {operation.user_id} creation operation"
                    )
                    continue
                except ldap.ALREADY_EXISTS:
                    logger.warning(
                        f"Creation operation scheduled for already existing user {operation.user_id}"
                    )
                    self.ldap_integration.update_ldap_user(**employee_data)

            for operation in UserOperation.objects.filter(deletion_filter):
                # employee left yesterday or before, delete them
                try:
                    self.ldap_integration.delete_ldap_user(
                        user_id=operation.user_id,
                    )
                except ldap.NO_SUCH_OBJECT:
                    logger.warning(
                        f"Trying to delete nonexistent user {operation.user_id}"
                    )
                    continue
        UserOperation.objects.filter(creation_filter | deletion_filter).delete()
