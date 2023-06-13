from __future__ import annotations

import logging

from django.core.management.base import BaseCommand

from applications.ftp_integration.services import FTPIntegrationService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Parse files newly sent from ftp, then process pending DB operation for the day"

    def handle(self, *args, **options):
        service = FTPIntegrationService()
        service.retrieve_person_files()
        service.process_person_files()
        service.process_db_operation()
