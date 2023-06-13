from .base import *

LDAP_DOMAIN = env.str("LDAP_DOMAIN", default="dc=domain,dc=com")
USERS_DN = env.str(
    "LDAP_USERS_DN",
    default=f"ou=people,{LDAP_DOMAIN}",
)
BIND_DN = env.str("LDAP_BIND_DN")
BIND_PASSWORD = env.str("LDAP_BIND_PASSWORD")
LDAP_HOST = env.str("LDAP_HOST")
LDAP_URL = f'{env.str("LDAP_PROTOCOL", default="ldaps")}://{LDAP_HOST}'
LDAP_TLS = LDAP_URL.startswith("ldaps")
LDAP_INTEGRATION_CLASS = env.str(
    "LDAP_INTEGRATION_CLASS",
    default="applications.ftp_integration.ldap.OpenLDAPIntegration",
)
SSH_USER = env.str("SSH_USER", default="Administrateur")
