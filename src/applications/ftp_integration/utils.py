import logging
import subprocess
from ftplib import FTP_TLS

from django.conf import settings

logger = logging.getLogger(__name__)


def launch_ssh_command(cmd: str, key_file_name) -> None:
    cmd = f"ssh {settings.SSH_USER}@{settings.LDAP_HOST} -o StrictHostKeyChecking=no -i /.ssh/{key_file_name} '{cmd}' "
    logger.debug(f"run command: {cmd}")
    try:
        result: subprocess.CompletedProcess = subprocess.run(
            cmd, capture_output=True, check=True, shell=True
        )
    except subprocess.CalledProcessError as e:
        logger.exception(e.stderr)
        raise e
    else:
        logger.debug(f"command result: {result.returncode} {result.stdout}")
        logger.info(f"command error result: {result.returncode} {result.stderr}")


class SessionReuseFTP_TLS(FTP_TLS):
    """
    Explicit FTPS, with shared TLS session
    Using solution taken from https://stackoverflow.com/a/43301750/7438175
    """

    def ntransfercmd(self, cmd, rest=None):
        # skip FTP_TLS implementation
        conn, size = super(FTP_TLS, self).ntransfercmd(cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(
                conn, server_hostname=self.host, session=self.sock.session
            )  # passing the session is the fix
        return conn, size
