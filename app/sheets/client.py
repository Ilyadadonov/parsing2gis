import asyncio
import logging
from datetime import date
from functools import partial

import gspread
from google.oauth2.service_account import Credentials

from app.config import settings
from app.db.models import Company

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "Название", "Город", "Категория", "Ссылка на 2ГИС",
    "Сайт", "Соцсети", "Кол-во филиалов", "YCLIENTS", "Рейтинг", "Дата сбора",
]


def _build_row(company):
    return [
        company.name, company.city, company.category,
        company.twogis_url or "", company.website or "", company.socials or "",
        company.branch_count, company.yclients, company.rating or "",
        company.collected_at.strftime("%Y-%m-%d") if company.collected_at else "",
    ]


class SheetsClient:
    def __init__(self):
        creds = Credentials.from_service_account_info(settings.google_credentials, scopes=SCOPES)
        self._gc = gspread.authorize(creds)
        self._spreadsheet_id = settings.google_spreadsheet_id

    def _write_sheet_sync(self, city, companies):
        sheet_title = f"{city} {date.today().isoformat()}"
        spreadsheet = self._gc.open_by_key(self._spreadsheet_id)
        try:
            ws = spreadsheet.add_worksheet(title=sheet_title, rows=len(companies)+10, cols=len(HEADERS))
        except gspread.exceptions.APIError as e:
            if "already exists" in str(e):
                ws = spreadsheet.worksheet(sheet_title)
                ws.clear()
            else:
                raise
        rows = [HEADERS] + [_build_row(c) for c in companies]
        ws.update("A1", rows)
        ws.format("A1:J1", {"textFormat": {"bold": True}})
        sheet_url = f"https://docs.google.com/spreadsheets/d/{self._spreadsheet_id}/edit#gid={ws.id}"
        logger.info("Sheet written: %s", sheet_url)
        return sheet_url

    async def write_sheet(self, city, companies):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(self._write_sheet_sync, city, companies))
