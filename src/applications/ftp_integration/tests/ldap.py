import logging
from typing import Callable

import ldap
import pytest
from django.conf import settings
from django.utils.module_loading import import_string

from applications.ftp_integration.ldap import (
    ActiveDirectoryIntegration,
    BaseLDAPIntegration,
    OpenLDAPIntegration,
)

logger = logging.getLogger(__name__)


class TestBaseLDAPIntegration:
    def user_management_scenario(
        self,
        ldap_integration_class: type[BaseLDAPIntegration],
        check_bind_func: Callable[[BaseLDAPIntegration, str, str], None],
    ):
        configured_ldap_integration_class: type[BaseLDAPIntegration] = import_string(
            settings.LDAP_INTEGRATION_CLASS
        )
        if not issubclass(ldap_integration_class, configured_ldap_integration_class):
            return
        with configured_ldap_integration_class() as ldap_integration:
            user_id_to_delete = []
            data = {
                "first_name": "Foo",
                "last_name": "BAR",
                "email": "fbar@domain.com",
                "user_id": "C12345@domain.com",
            }
            dn, pwd = ldap_integration.create_ldap_user(**data)
            user_id_to_delete.append(data["user_id"])

            logger.debug(f"simple_bind_s {dn}")
            check_bind_func(ldap_integration, dn, pwd)
            ldap_integration.connection.simple_bind_s(
                who=settings.BIND_DN,
                cred=settings.BIND_PASSWORD,
            )

            data["user_id"] = "C5555@domain.com"
            dn, pwd = ldap_integration.create_ldap_user(**data)
            user_id_to_delete.append(data["user_id"])
            data["first_name"] = "Faa"
            data["user_id"] = "C6666@domain.com"
            dn, pwd = ldap_integration.create_ldap_user(**data)
            user_id_to_delete.append(data["user_id"])
            data["user_id"] = "C7777@domain.com"
            dn, pwd = ldap_integration.create_ldap_user(**data)
            user_id_to_delete.append(data["user_id"])

            old_dn, updated = ldap_integration.update_ldap_user(**data)
            assert not updated
            data["email"] = "fbar@domain.ovh"
            data["first_name"] = "Foo2"
            data["last_name"] = "BAR2"
            new_dn, updated = ldap_integration.update_ldap_user(**data)
            assert updated
            assert old_dn == new_dn
            for user_id in user_id_to_delete:
                ldap_integration.delete_ldap_user(user_id)

    @pytest.mark.ldap
    def test_active_directory_integration(self):
        def check_bind_func(ldap_integration: BaseLDAPIntegration, dn: str, pwd: str):
            try:
                # check newly created user can't connect because of pwdLastSet
                ldap_integration.connection.simple_bind_s(
                    who=dn,
                    cred=pwd,
                )
            except ldap.INVALID_CREDENTIALS:
                pass
            else:
                raise Exception(
                    f"could connect with newly created user {dn} when we shouldn't"
                )

        self.user_management_scenario(ActiveDirectoryIntegration, check_bind_func)

    @pytest.mark.ldap
    def test_open_ldap_integration(self):
        def check_bind_func(ldap_integration: BaseLDAPIntegration, dn: str, pwd: str):
            # newly created user should be able to connect directly
            ldap_integration.connection.simple_bind_s(
                who=dn,
                cred=pwd,
            )

        self.user_management_scenario(OpenLDAPIntegration, check_bind_func)

    def test_open_ldap_get_uid_number(self):
        ldap_integration = OpenLDAPIntegration()
        assert ldap_integration.get_uid_number("C00005@domain.com") == 1005
        assert ldap_integration.get_uid_number("C342@domain.com") == 1342
        with pytest.raises(ValueError):
            ldap_integration.get_uid_number("342@domain.com")
