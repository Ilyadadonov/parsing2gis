import asyncio
import logging
import time
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from app.api.twogis import TwoGisClient
from app.bot.keyboards import confirm_city_keyboard, existing_city_keyboard
from app.db import async_session
from app.db.repository import CityRepo, CompanyRepo, RunRepo
from app.sheets import SheetsClient
from app.utils import normalize_city

logger = logging.getLogger(__name__)
router = Router()
PROGRESS_INTERVAL = 120


async def _run_collection(city, run_id, chat_id, bot):
    start = time.monotonic()
    progress_task = asyncio.create_task(_progress_notifier(bot, chat_id, start))
    try:
        async with TwoGisClient() as client:
            companies = await client.collect_city(city)
        async with async_session() as session:
            company_dicts = [
                {"run_id": run_id, "org_id": c.org_id, "name": c.name, "city": c.city,
                 "category": c.category, "twogis_url": c.twogis_url, "website": c.website,
                 "socials": c.socials, "branch_count": c.branch_count, "yclients": c.yclients,
                 "rating": c.rating}
                for c in companies
            ]
            count = await CompanyRepo(session).bulk_insert(company_dicts)
            saved = await CompanyRepo(session).get_by_run(run_id)
            sheet_url = await SheetsClient().write_sheet(city, saved)
            await RunRepo(session).finish(run_id, count, sheet_url)
        progress_task.cancel()
        await bot.send_message(chat_id, f"✅ Готово! По {city} найдено {count} компаний.\nОткрыть таблицу → {sheet_url}")
    except Exception as exc:
        progress_task.cancel()
        logger.exception("Collection failed: %s", exc)
        async with async_session() as session:
            await RunRepo(session).fail(run_id, str(exc))
        await bot.send_message(chat_id, f"❌ Ошибка при сборе данных по {city}:\n<code>{exc}</code>\n\nПопробуйте ещё раз — /start", parse_mode="HTML")


async def _progress_notifier(bot, chat_id, start):
    await asyncio.sleep(PROGRESS_INTERVAL)
    elapsed = int(time.monotonic() - start)
    await bot.send_message(chat_id, f"⏳ Всё ещё собираю, скоро будет готово... (прошло {elapsed // 60} мин)")


async def _start_collection(city, user_id, chat_id, bot):
    async with async_session() as session:
        city_obj = await CityRepo(session).get_or_create(city)
        run = await RunRepo(session).create(city_id=city_obj.id, user_id=user_id)
    asyncio.create_task(_run_collection(city, run.id, chat_id, bot))


@router.message(F.text & ~F.text.startswith("/"))
async def message_city(message: Message):
    city = normalize_city(message.text)
    await message.answer(f"Вы хотите собрать базу по городу <b>{city}</b>?", parse_mode="HTML", reply_markup=confirm_city_keyboard(city))


@router.callback_query(F.data.startswith("city:"))
async def cb_city_selected(call: CallbackQuery):
    city = call.data.split(":", 1)[1]
    await call.message.edit_text(f"Вы хотите собрать базу по городу <b>{city}</b>?", parse_mode="HTML", reply_markup=confirm_city_keyboard(city))


@router.callback_query(F.data.startswith("confirm:"))
async def cb_confirm(call: CallbackQuery):
    city = call.data.split(":", 1)[1]
    async with async_session() as session:
        last_run = await CityRepo(session).get_last_run(city)
    if last_run:
        d = last_run.finished_at.strftime("%Y-%m-%d") if last_run.finished_at else "неизвестно"
        await call.message.edit_text(f"База по городу <b>{city}</b> уже есть (собрана {d}).\nОбновить или открыть существующую?", parse_mode="HTML", reply_markup=existing_city_keyboard(city))
        return
    await call.message.edit_text(f"Принято! Начинаю собирать базу по <b>{city}</b>.\nЭто займёт несколько минут — напишу, как только будет готово ⏳", parse_mode="HTML")
    await _start_collection(city, call.from_user.id, call.message.chat.id, call.bot)


@router.callback_query(F.data == "cancel")
async def cb_cancel(call: CallbackQuery):
    await call.message.edit_text("Отменено. Введите название города или /start.")


@router.callback_query(F.data.startswith("update:"))
async def cb_update(call: CallbackQuery):
    city = call.data.split(":", 1)[1]
    await call.message.edit_text(f"Запускаю обновление базы по <b>{city}</b>.\nСтарый лист останется в таблице как архив. ⏳", parse_mode="HTML")
    await _start_collection(city, call.from_user.id, call.message.chat.id, call.bot)


@router.callback_query(F.data.startswith("open:"))
async def cb_open(call: CallbackQuery):
    city = call.data.split(":", 1)[1]
    async with async_session() as session:
        last_run = await CityRepo(session).get_last_run(city)
    if last_run and last_run.sheet_url:
        await call.message.edit_text(f"Открыть существующую таблицу по <b>{city}</b> →\n{last_run.sheet_url}", parse_mode="HTML")
    else:
        await call.message.edit_text("Ссылка на таблицу не найдена. Попробуйте обновить базу.")
