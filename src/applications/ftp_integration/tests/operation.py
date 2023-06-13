import logging
from datetime import date, timedelta

import ldap
import pytest
from _pytest.logging import LogCaptureFixture
from pytest_mock import MockerFixture

from applications.ftp_integration.models import UserOperation
from applications.ftp_integration.services import FTPIntegrationService


class TestFTPIntegrationServiceOperation:
    def test_process_creation(self, db):
        service = FTPIntegrationService()
        user_id = "01@domain.com"
        with pytest.raises(AssertionError):
            service.process_creation("", {})
        with pytest.raises(ValueError):
            service.process_creation(user_id, {})

        service.process_creation(user_id, {"date_begin": "01/01/1970"})
        assert (
            UserOperation.objects.filter(
                type_operation=UserOperation.TypeChoices.CREATION
            ).count()
            == 1
        )
        assert not UserOperation.objects.filter(
            type_operation=UserOperation.TypeChoices.DELETION
        ).exists()

        service.process_creation(user_id, {"date_begin": "01/01/1970"})
        assert (
            UserOperation.objects.filter(
                type_operation=UserOperation.TypeChoices.CREATION
            ).count()
            == 1
        )
        assert not UserOperation.objects.filter(
            type_operation=UserOperation.TypeChoices.DELETION
        ).exists()

        service.process_creation(
            user_id, {"date_begin": "01/01/1970", "date_end": "01/01/1970"}
        )
        assert (
            UserOperation.objects.filter(
                type_operation=UserOperation.TypeChoices.CREATION
            ).count()
            == 1
        )
        assert (
            UserOperation.objects.filter(
                type_operation=UserOperation.TypeChoices.DELETION
            ).count()
            == 1
        )

    def test_process_employee_update(self, db, mocker: MockerFixture):
        service = FTPIntegrationService()
        user_id = "01@domain.com"
        with pytest.raises(AssertionError):
            service.process_employee_update("", {})
        mocker.patch.object(service.ldap_integration, "update_ldap_user")
        service.process_employee_update(user_id, {})
        assert not UserOperation.objects.exists()

        mocker.patch.object(
            service.ldap_integration,
            "update_ldap_user",
            side_effect=ldap.NO_SUCH_OBJECT,
        )
        service.process_employee_update(user_id, {"date_begin": "01/01/1970"})
        assert (
            UserOperation.objects.filter(
                type_operation=UserOperation.TypeChoices.CREATION
            ).count()
            == 1
        )
        assert not UserOperation.objects.filter(
            type_operation=UserOperation.TypeChoices.DELETION
        ).exists()

        service.process_employee_update(user_id, {"date_begin": "01/01/1970"})
        assert (
            UserOperation.objects.filter(
                type_operation=UserOperation.TypeChoices.CREATION
            ).count()
            == 1
        )
        assert not UserOperation.objects.filter(
            type_operation=UserOperation.TypeChoices.DELETION
        ).exists()

    def test_process_position_update(self, db):
        service = FTPIntegrationService()
        user_id = "01@domain.com"
        with pytest.raises(AssertionError):
            service.process_position_update("", {})

        service.process_position_update(user_id, {})
        assert not UserOperation.objects.filter(
            type_operation=UserOperation.TypeChoices.CREATION
        ).exists()
        assert not UserOperation.objects.filter(
            type_operation=UserOperation.TypeChoices.DELETION
        ).exists()

        service.process_position_update(user_id, {"date_begin": "01/01/1970"})
        assert not UserOperation.objects.filter(
            type_operation=UserOperation.TypeChoices.CREATION
        ).exists()
        assert not UserOperation.objects.filter(
            type_operation=UserOperation.TypeChoices.DELETION
        ).exists()

        service.process_position_update(
            user_id, {"date_begin": "01/01/1970", "date_end": "01/01/1970"}
        )
        assert not UserOperation.objects.filter(
            type_operation=UserOperation.TypeChoices.CREATION
        ).exists()
        assert (
            UserOperation.objects.filter(
                type_operation=UserOperation.TypeChoices.DELETION
            ).count()
            == 1
        )

        UserOperation.objects.create(
            type_operation=UserOperation.TypeChoices.CREATION,
            user_id=user_id,
            date_for_change=date.today(),
        )
        service.process_position_update(
            user_id, {"date_begin": "01/01/1970", "date_end": "01/01/1970"}
        )
        create_operation = UserOperation.objects.filter(
            type_operation=UserOperation.TypeChoices.CREATION
        ).get()
        assert create_operation.date_for_change == date(1970, 1, 1)
        assert (
            UserOperation.objects.filter(
                type_operation=UserOperation.TypeChoices.DELETION
            ).count()
            == 1
        )

    def test_process_db_operation(
        self, db, mocker: MockerFixture, caplog: LogCaptureFixture
    ):
        service = FTPIntegrationService()
        mocker.patch.object(
            service,
            "ldap_integration",
        )
        mock_create_ldap_user = mocker.patch.object(
            service.ldap_integration,
            "create_ldap_user",
            side_effect=ValueError,
        )
        mock_delete_ldap_user = mocker.patch.object(
            service.ldap_integration,
            "delete_ldap_user",
            side_effect=ldap.NO_SUCH_OBJECT,
        )
        today = date.today()
        for index in range(-2, 3):
            UserOperation.objects.create(
                type_operation=UserOperation.TypeChoices.CREATION,
                user_id=f"0{index}@domain.com",
                date_for_change=today + timedelta(days=index),
            )
            UserOperation.objects.create(
                type_operation=UserOperation.TypeChoices.DELETION,
                user_id=f"0{index}@domain.com",
                date_for_change=today + timedelta(days=index),
            )

        with caplog.at_level(logging.WARNING):
            service.process_db_operation()

        common_kwargs = dict(
            first_name="",
            last_name="",
            email="",
        )
        mock_create_ldap_user.assert_has_calls(
            [
                mocker.call(user_id="0-2@domain.com", **common_kwargs),
                mocker.call(user_id="0-1@domain.com", **common_kwargs),
                mocker.call(user_id="00@domain.com", **common_kwargs),
                mocker.call(user_id="01@domain.com", **common_kwargs),
            ],
            any_order=True,
        )
        assert len(mock_create_ldap_user.call_args_list) == 4
        mock_delete_ldap_user.assert_has_calls(
            [
                mocker.call(user_id="0-2@domain.com"),
                mocker.call(user_id="0-1@domain.com"),
            ],
            any_order=True,
        )
        assert len(mock_delete_ldap_user.call_args_list) == 2

        assert len(caplog.messages) == 6
        assert (
            len(
                [record for record in caplog.records if record.levelno == logging.ERROR]
            )
            == 4
        )
        assert (
            len(
                [
                    record
                    for record in caplog.records
                    if record.levelno == logging.WARNING
                ]
            )
            == 2
        )
        assert (
            UserOperation.objects.filter(
                type_operation=UserOperation.TypeChoices.CREATION
            ).count()
            == 1
        )
        assert (
            UserOperation.objects.filter(
                type_operation=UserOperation.TypeChoices.DELETION
            ).count()
            == 3
        )
