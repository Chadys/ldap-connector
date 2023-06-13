# ldap-connector
Django utility to send or update data to an LDAP service, either ActiveDirectory or OpenLDAP.

The basic configuration will fetch files from a FTP in an expected CSV format to update LDAP state.
The expected files name and mapping are defined in [FileProcessingService](src/applications/ftp_integration/services.py).

This project expects standard ActiveDirectory users or samba OpenLDAP users so the LDAP can be used by an SSO portal.
If you need to adjust the schema/groups/properties, you can edit the [respective LDAP integration classes](src/applications/ftp_integration/ldap.py).

The whole process of fetching user file, parsing them and integrating them in the LDAP is done by calling `./manage.py collect_and_parse_ftp_files`
Processed files will be kept locally in [data](src/data).

This project is configured to use a sqlite db kept in [data](src/data)

## How to run

### Setup
```shell
cd buildrun/docker/ldap-connector
# this file should be updated with your credentials after being copied
cp secrets_sample.env secrets.env

# If you are using ActiveDirectory without LDAPS, 
# you must copy the private SSH key for the AD server in ./ssh_key, name it "id_ad_server"
# and set the SSH_USER variable to the username to use with that key
```
### Run
```shell
cd buildrun/docker/docker-compose/dev-env
docker-compose up -d main
# OR if you want to also start the ldap-admin
docker-compose up -d
```

### Test
```shell
cd buildrun/docker/docker-compose/test-env
docker-compose up test
```
Change command to `pytest -m "not ldap"` if you want to skip integration testing.

### URL
- http://localhost:9090/: ldap-admin

  credentials: cn=admin,dc=domain,dc=com,
  see [docker-compose](buildrun/docker/docker-compose/dev-env/docker-compose.yml) for password

### Configuration

The following environnement variable are available (look into the [settings file](src/configurations/settings.py) for an exhaustive list):
- `FTP_CLEANUP_FILE` Defaults to False. Set to True if you want the files to be deleted from the FTP after being fetched.
- `LDAP_BIND_DN` Admin DN to authenticate as for LDAP operations. Dev LDAP config uses "cn=admin,dc=domain,dc=com".
- `LDAP_BIND_PASSWORD` Admin password to authenticate as for LDAP operations. see [docker-compose](buildrun/docker/docker-compose/dev-env/docker-compose.yml) for dev LDAP password.
- `FTP_URL` Url of the FTP to fetch the files from.
- `FTP_USE_TLS` Defaults to True. Should the FTP connect using TLS or not.
- `LDAP_INTEGRATION_CLASS` Service class to interact with the LDAP. 
  Defaults to `applications.ftp_integration.ldap.OpenLDAPIntegration`, change to `applications.ftp_integration.ldap.ActiveDirectoryIntegration` if you want to connect to an ActiveDirectory instead.
- `SSH_USER` Defaults to "Administrateur". Username used to connect to the LDAP server via SSH.

#### About SSH
On ActiveDirectory, you can only set a password with LDAP command though LDAPS protocol.
If you don't have it configured on your server, you can instead use the powershell `Set-ADAccountPassword` command through SSH.
That's why this utility will require an SSH key to work in a non-LDAPS ActiveDirectory environment.

## How to add a new Python package requirement

Add you requirement to [base-requirements.in](buildrun/docker/ldap-connector/requirements/base-requirements.in)
(or dev-* / prod-* / test-* if your package is only useful in one context).
Then run:

```shell
cd buildrun/docker/docker-compose/dev-env
docker-compose up compile-dep
# Don't forget to rebuild the service to include the new dependency
docker compose up -d --no-recreate --build main
```

**/!\ The compile-dep service will also upgrade all existing packages;
remove all `--upgrade` option in the [docker-compose](buildrun/docker/docker-compose/dev-env/docker-compose.yml) command of compile-dep service to avoid that**.