import logging
import re
import unicodedata

import ldap
from django.conf import settings
from ldap.ldapobject import ReconnectLDAPObject
from ldap.modlist import addModlist, modifyModlist

from applications.ftp_integration.utils import launch_ssh_command

logger = logging.getLogger(__name__)


class BaseLDAPIntegration:
    user_id_attribute = None

    def __init__(self):
        self.connection: ldap.ldapobject.LDAPObject = None

    def assert_connection(self):
        assert (
            self.connection is not None
        ), "methods of class {class_name} must be called using a context manager".format(
            class_name=self.__class__.__name__
        )

    def __enter__(self):
        logger.debug("initialize")
        self.connection = ReconnectLDAPObject(
            settings.LDAP_URL,
            bytes_mode=False,
            trace_level=2
            if settings.LOGLEVEL == "DEBUG"
            else 1
            if settings.LOGLEVEL == "INFO"
            else 0,
        )
        self.connection.set_option(ldap.OPT_REFERRALS, ldap.OPT_OFF)
        self.connection.set_option(
            ldap.OPT_X_TLS_REQUIRE_CERT,
            ldap.OPT_X_TLS_NEVER,
        )
        self.connection.set_option(
            ldap.OPT_X_TLS_NEWCTX,
            0,
        )

        logger.debug(f"simple_bind_s {settings.BIND_DN}")
        self.connection.simple_bind_s(
            who=settings.BIND_DN,
            cred=settings.BIND_PASSWORD,
        )
        return self

    def __exit__(self, *args):
        self.connection.unbind_s()

    def normalize(self, value: str):
        value = str(value)
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
        return re.sub(r"[^\w]", "", value.lower())

    def get_base_attributes(
        self,
        first_name: str,
        last_name: str,
        email: str,
    ) -> dict:
        last_name = last_name.upper()
        displayName = f"{first_name} {last_name}".encode()
        first_name = first_name.encode()
        last_name = last_name.encode()
        email = email.encode()

        values = dict(
            givenName=[first_name],
            sn=[last_name],
            displayName=[displayName],
            mail=[email] if email else [],
        )
        return values

    def create_ldap_user(
        self,
        user_id: str,
        first_name: str,
        last_name: str,
        email: str,
    ) -> (str, str):
        raise NotImplementedError()

    def update_ldap_user(
        self,
        user_id: str,
        first_name: str,
        last_name: str,
        email: str,
    ) -> (str, bool):
        self.assert_connection()
        updated = False
        results = self.connection.search_s(
            settings.USERS_DN,
            ldap.SCOPE_SUBTREE,
            f"({self.user_id_attribute}={user_id})",
            [],
        )

        if results is not None and len(results) > 0:
            dn, old_values = results[0]
        else:
            raise ldap.NO_SUCH_OBJECT(f"User {user_id} not found")

        values = self.get_base_attributes(first_name, last_name, email)
        modlist = modifyModlist(old_values, values, ignore_oldexistent=True)

        if modlist:
            logger.debug(f"modify_s {dn} {modlist}")
            self.connection.modify_s(dn, modlist)
            updated = True
        return dn, updated

    def delete_ldap_user(
        self,
        user_id: str,
    ) -> str:
        self.assert_connection()
        results = self.connection.search_s(
            settings.USERS_DN,
            ldap.SCOPE_SUBTREE,
            f"({self.user_id_attribute}={user_id})",
            [],
        )

        if results is not None and len(results) > 0:
            dn, old_values = results[0]
        else:
            raise ldap.NO_SUCH_OBJECT(f"User {user_id} not found")

        self.connection.delete_s(dn)
        return dn


class ActiveDirectoryIntegration(BaseLDAPIntegration):
    user_id_attribute = "userPrincipalName"

    def _set_password(self, dn: str, pwd: str):
        if settings.LDAP_TLS:
            # Will not work without SSL
            # prerequisite for password: https://nawilson.com/2010/08/26/ldap-password-changes-in-active-directory/
            formatted_pwd = f'"{pwd}"'.encode("utf-16-le")
            # replace is needed: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-adts/6e803168-f140-4d23-b2d3-c3a8ab5917d2
            modlist = [(ldap.MOD_REPLACE, "unicodePwd", [formatted_pwd])]
            logger.debug(f"modify_s {dn} {modlist}")
            self.connection.modify_s(dn, modlist)
        else:
            launch_ssh_command(
                f'Set-ADAccountPassword -Identity "{dn}" -Reset -NewPassword (ConvertTo-SecureString -AsPlainText "{pwd}" -Force)',
                "id_ad_server",
            )

    def _activate_user(self, dn: str):
        # activate user, see https://github.com/go-ldap/ldap/issues/106#issuecomment-342698860
        results = self.connection.search_s(
            settings.USERS_DN,
            ldap.SCOPE_SUBTREE,
            f"(distinguishedName={dn})",
            [],
        )
        dn, old_values = results[0]
        values = {
            # 512 is for NORMAL_ACCOUNT, see https://learn.microsoft.com/en-us/troubleshoot/windows-server/identity/useraccountcontrol-manipulate-account-properties
            "userAccountControl": [b"512"],
            # see https://learn.microsoft.com/en-us/windows/win32/adschema/a-pwdlastset
            "pwdLastSet": [b"0"],
        }
        modlist = modifyModlist(old_values, values, ignore_oldexistent=True)
        if modlist:
            logger.debug(f"modify_s {dn} {modlist}")
            self.connection.modify_s(dn, modlist)

    def create_ldap_user(
        self,
        user_id: str,
        first_name: str,
        last_name: str,
        email: str,
    ) -> (str, str):
        self.assert_connection()
        pwd = user_id
        user_id = user_id.encode()
        username = self.normalize(f"{first_name[0]}{last_name}").encode()
        cn = f"{first_name} {last_name.upper()}"
        homonym_suffix = 1

        values = dict(
            **self.get_base_attributes(first_name, last_name, email),
            **{self.user_id_attribute: user_id},
            sAMAccountName=username,
            objectClass=[b"top", b"user", b"person", b"organizationalPerson"],
            objectCategory=f"CN=Person,CN=Schema,CN=Configuration,{settings.LDAP_DOMAIN}".encode(),
            instanceType=b"4",
        )
        dn = f"CN={cn},{settings.USERS_DN}"

        modlist = addModlist(values)
        logger.debug(f"add_s {dn} {modlist}")
        while True:
            try:
                self.connection.add_s(dn, modlist)
            except ldap.ALREADY_EXISTS:
                # sAMAccountName is already used by someone with the same username
                values["sAMAccountName"] = username + str(homonym_suffix).encode()
                modlist = addModlist(values)
                # reset DN in case it was changed by previous loop, to try a creation without any DN suffix
                dn = f"CN={cn},{settings.USERS_DN}"
            else:
                break
            try:
                self.connection.add_s(dn, modlist)
            except ldap.ALREADY_EXISTS:
                # DN is already used by someone with the same complete name
                # (or there is another conflict on username, but it will be taken care of by next loop
                dn = f"CN={cn}{homonym_suffix},{settings.USERS_DN}"
            else:
                break
            homonym_suffix += 1
        self._set_password(dn, pwd)
        self._activate_user(dn)

        return dn, pwd


class OpenLDAPIntegration(BaseLDAPIntegration):
    user_id_attribute = "uid"

    def create_ldap_user(
        self,
        user_id: str,
        first_name: str,
        last_name: str,
        email: str,
    ) -> (str, str):
        self.assert_connection()
        pwd = user_id
        home_directory = f"/home/users/users/{user_id}".encode()
        uid_number = self.get_uid_number(user_id)
        samba_id = f"S-1-5-21-1-{uid_number}".encode()
        uid_number = str(uid_number).encode()

        values = dict(
            **self.get_base_attributes(first_name, last_name, email),
            uid=user_id.encode(),
            objectClass=[b"top", b"posixAccount", b"sambaSamAccount", b"inetOrgPerson"],
            gidnumber=b"500",
            uidNumber=uid_number,
            sambasid=samba_id,
            homedirectory=home_directory,
            sambaacctflags=b"[U]",
        )
        dn = f"CN={user_id},{settings.USERS_DN}"

        modlist = addModlist(values)
        logger.debug(f"add_s {dn} {modlist}")
        self.connection.add_s(dn, modlist)
        self.connection.passwd_s(dn, None, pwd)

        return dn, pwd

    def get_uid_number(self, user_id: str):
        match = re.match(r"C(\d+)", user_id)
        if match is None:
            raise ValueError(f"user_id {user_id} does not follow the correct format")
        return 1000 + int(match[1])
