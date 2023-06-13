import logging

import pytest
from _pytest.logging import LogCaptureFixture
from pytest_mock import MockerFixture

from applications.ftp_integration.services import FTPIntegrationService


class TestFTPIntegrationServiceFile:
    def test_sorted_ftp_files(self, mocker: MockerFixture):
        mocker.patch("applications.ftp_integration.services.import_string")
        service = FTPIntegrationService()
        mock_files = [
            mocker.Mock(is_file=lambda: True, index=3),
            mocker.Mock(is_file=lambda: False),
            mocker.Mock(is_file=lambda: True, index=1),
            mocker.Mock(is_file=lambda: True, index=5),
            mocker.Mock(is_file=lambda: True, index=2),
            mocker.Mock(is_file=lambda: True, index=4),
            mocker.Mock(is_file=lambda: True, index=0),
            mocker.Mock(is_file=lambda: True),
            mocker.Mock(is_file=lambda: True),
        ]
        for file, name in zip(
            mock_files,
            [
                "employee_update2",
                "hiring0",
                "hiring2",
                "position_update1",
                "employee_update1",
                "position_update0",
                "hiring1",
                "AAAA",
                "Hirin",
            ],
        ):
            # name can't be set directly, see https://docs.python.org/3/library/unittest.mock.html#mock-names-and-the-name-attribute
            file.name = name
        folder_path = mocker.Mock(iterdir=lambda: mock_files)
        assert [
            mock_path.index for mock_path in service.sorted_ftp_files(folder_path)
        ] == [0, 1, 2, 3, 4, 5]

    def test_parse_file(self, mocker: MockerFixture, caplog: LogCaptureFixture):
        service = FTPIntegrationService()
        mock_process_creation = mocker.patch.object(service, "process_creation")
        mock_process_employee_update = mocker.patch.object(
            service, "process_employee_update"
        )
        mock_process_position_update = mocker.patch.object(
            service, "process_position_update"
        )
        headers = "Identifiant;Prénom;Nom;Unused1;Date entrée poste;Date de fin;E-mail;Unused2"
        mock_files = [
            mocker.Mock(
                __iter__=lambda _: iter(
                    [headers, "1;a;A;c;d1;d2;e;c", ";a;A;c;d1;d2;e;c"]
                )
            ),
            mocker.Mock(
                __iter__=lambda _: iter(
                    [
                        headers,
                        "1;a;A;c;d1;d2;e;c",
                    ]
                )
            ),
            mocker.Mock(__iter__=lambda _: iter([""])),
            mocker.Mock(
                __iter__=lambda _: iter(
                    [headers, "1;a;A;c;d1;d2;e;c", "2;a;A;c;d1;d2;e;c"]
                )
            ),
            mocker.Mock(__iter__=lambda _: iter([headers])),
        ]
        for file, name in zip(
            mock_files,
            [
                "hiring1",
                "position_update1",
                "hiring2",
                "employee_update1",
                "position_update3",
            ],
        ):
            # name can't be set directly, see https://docs.python.org/3/library/unittest.mock.html#mock-names-and-the-name-attribute
            file.name = name
        with caplog.at_level(logging.WARNING):
            for file in mock_files:
                service.parse_file(file)

        assert not caplog.messages

        common_data = {
            "first_name": "a",
            "last_name": "A",
            "email": "e",
            "date_begin": "d1",
            "date_end": "d2",
        }
        assert mock_process_creation.call_args_list == [
            mocker.call("1", common_data),
            mocker.call("", common_data),
        ]
        assert mock_process_employee_update.call_args_list == [
            mocker.call("1", common_data),
            mocker.call("2", common_data),
        ]
        assert mock_process_position_update.call_args_list == [
            mocker.call(
                "1",
                common_data,
            )
        ]

    def test_parse_file_errors(self, mocker: MockerFixture, caplog: LogCaptureFixture):
        service = FTPIntegrationService()
        mock_process_employee_update = mocker.patch.object(
            service, "process_employee_update"
        )
        mock_process_position_update = mocker.patch.object(
            service, "process_position_update"
        )
        mock_file = mocker.Mock(
            __iter__=lambda _: iter(
                [
                    "Prénom;Nom;Unused1;Date entrée poste;Date de fin;Identifiant;Unused2",
                    "a;A;c;d1;d2;;c",
                    "a;A;c;d1;d2;1;c",
                ]
            )
        )
        with caplog.at_level(logging.ERROR):
            mock_file.name = "BAD_NAME"

            with pytest.raises(ValueError) as e:
                service.parse_file(mock_file)
            assert "BAD_NAME" in e.value.args[0]

            mock_file.name = "employee_update"
            service.parse_file(mock_file)
            # remove necessity for email and date begin function
            service.headers_mapping = {
                "Prénom": "first_name",
                "Nom": "last_name",
                "Identifiant": "user_id",
                "Date de fin": "date_end",
            }
            mock_file.name = "hiring"
            service.parse_file(mock_file)

        assert caplog.messages == [
            'Missing column "E-mail" in file employee_update',
            f"Error 'user_id can't be empty' in file hiring L.1",
            f"Error 'Missing date_begin field' in file hiring L.2",
        ]
        mock_process_employee_update.assert_not_called()
        mock_process_position_update.assert_not_called()
