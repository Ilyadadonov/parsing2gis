import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from app.db import async_session
from app.db.repository import CompanyRepo
from app.sheets import SheetsClient
from app.utils import normalize_city

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("export"))
async def cmd_export(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /export <город>\nНапример: /export Тюмень")
        return
    city = normalize_city(args[1])
    await message.answer(f"Выгружаю сохранённую базу по <b>{city}</b>... ⏳", parse_mode="HTML")
    async with async_session() as session:
        companies = await CompanyRepo(session).get_by_city(city)
    if not companies:
        await message.answer(f"База по городу <b>{city}</b> не найдена.\nСначала выполните сбор — просто напишите название города.", parse_mode="HTML")
        return
    try:
        sheet_url = await SheetsClient().write_sheet(city, companies)
        await message.answer(f"✅ Готово! Выгружено {len(companies)} компаний по {city}.\nОткрыть таблицу → {sheet_url}")
    except Exception as exc:
        logger.exception("Export failed: %s", exc)
        await message.answer(f"❌ Ошибка при выгрузке: <code>{exc}</code>", parse_mode="HTML")
