import asyncio
import logging
from dataclasses import dataclass
from typing import AsyncIterator

import aiohttp
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://catalog.api.2gis.com/3.0/items"
PAGE_SIZE = 10

CATEGORIES = [
    "Массажный салон",
    "Студия йоги",
    "Студия стретчинга",
    "Ногтевая студия",
    "Тренажерный зал",
    "Студия пилатеса",
    "Косметология",
    "Барбершоп",
    "Бассейн",
    "Эпиляция",
    "Салон красоты",
    "Студия функционального тренинга",
    "Танцевальная студия",
    "Баня",
]

YCLIENTS_CATEGORIES = {
    "Ногтевая студия",
    "Косметология",
    "Барбершоп",
    "Эпиляция",
    "Массажный салон",
    "Салон красоты",
}

YCLIENTS_MARKERS = ("yclients", "yclients.ru", "n.yc.kz")

MIN_RATING = 4.5

CITY_COORDS: dict[str, str] = {
    "Москва": "37.618423,55.751244",
    "Санкт-Петербург": "30.315635,59.938951",
    "Екатеринбург": "60.605514,56.838011",
    "Новосибирск": "82.920430,55.030199",
    "Казань": "49.106408,55.796127",
    "Нижний Новгород": "44.002047,56.329882",
    "Челябинск": "61.402554,55.159897",
    "Самара": "50.197937,53.195538",
    "Уфа": "55.971652,54.735152",
    "Ростов-на-Дону": "39.700798,47.222078",
    "Омск": "73.368212,54.989342",
    "Красноярск": "92.852572,56.010569",
    "Воронеж": "39.200289,51.660781",
    "Пермь": "56.229431,58.010455",
    "Волгоград": "44.516939,48.707103",
    "Тюмень": "68.970664,57.152985",
    "Краснодар": "38.975313,45.035470",
}

CITY_RADIUS = 40000


@dataclass
class CompanyData:
    org_id: str
    name: str
    city: str
    category: str
    twogis_url: str | None
    website: str | None
    socials: str | None
    branch_count: int
    yclients: str
    rating: float | None


class TwoGisClient:
    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()

    @retry(
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def _get(self, params: dict) -> dict:
        assert self._session is not None
        params["key"] = settings.twogis_api_key
        async with self._session.get(BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 429:
                retry_after = int(resp.headers.get("Retry-After", "5"))
                logger.warning("Rate limited by 2GIS, waiting %s seconds", retry_after)
                await asyncio.sleep(retry_after)
                raise aiohttp.ClientResponseError(resp.request_info, resp.history, status=429)
            if resp.status >= 500:
                raise aiohttp.ClientResponseError(resp.request_info, resp.history, status=resp.status)
            resp.raise_for_status()
            return await resp.json()

    async def _iter_pages(self, city: str, category: str) -> AsyncIterator[dict]:
        coords = CITY_COORDS.get(city)
        if coords is None:
            logger.warning("No coordinates for city '%s', skipping", city)
            return
        page = 1
        while True:
            params = {
                "q": category,
                "location": coords,
                "radius": CITY_RADIUS,
                "fields": "items.reviews,items.contact_groups,items.photos,items.branch_count,items.url",
                "page_size": PAGE_SIZE,
                "page": page,
                "locale": "ru_RU",
            }
            data = await self._get(params)
            result = data.get("result", {})
            items = result.get("items", [])
            if not items:
                break
            for item in items:
                yield item
            total = result.get("total", 0)
            if page * PAGE_SIZE >= total:
                break
            page += 1
            await asyncio.sleep(0.3)

    def _extract_contacts(self, item: dict) -> tuple[str | None, str | None]:
        website_parts: list[str] = []
        social_parts: list[str] = []
        for group in item.get("contact_groups", []):
            for contact in group.get("contacts", []):
                ctype = contact.get("type", "")
                value = contact.get("value", "") or contact.get("url", "")
                if not value:
                    continue
                if ctype in ("website", "url"):
                    website_parts.append(value)
                elif ctype in ("vk", "instagram", "facebook", "telegram", "youtube", "tiktok", "ok"):
                    social_parts.append(value)
        return (", ".join(website_parts) or None, ", ".join(social_parts) or None)

    def _check_yclients(self, item: dict) -> str:
        all_text = ""
        for group in item.get("contact_groups", []):
            for contact in group.get("contacts", []):
                all_text += " ".join(str(v) for v in contact.values()).lower()
        for marker in YCLIENTS_MARKERS:
            if marker in all_text:
                return "да"
        return "нет" if all_text else "не определено"

    def _passes_filters(self, item: dict) -> bool:
        reviews = item.get("reviews", {})
        rating = reviews.get("rating_statistical") or reviews.get("general_rating") or reviews.get("rating")
        if rating is not None and float(rating) < MIN_RATING:
            return False
        return True

    async def collect_city(self, city: str) -> list[CompanyData]:
        seen_ids: set[str] = set()
        results: list[CompanyData] = []

        for category in CATEGORIES:
            logger.info("Collecting category '%s' for city '%s'", category, city)
            try:
                async for item in self._iter_pages(city, category):
                    org_id = item.get("id", "")
                    if org_id in seen_ids:
                        continue
                    if not self._passes_filters(item):
                        continue
                    seen_ids.add(org_id)

                    website, socials = self._extract_contacts(item)
                    need_yclients = any(cat in category for cat in YCLIENTS_CATEGORIES)
                    yclients = self._check_yclients(item) if need_yclients else "не определено"

                    reviews_data = item.get("reviews", {})
                    rating_raw = reviews_data.get("rating_statistical") or reviews_data.get("general_rating") or reviews_data.get("rating")
                    results.append(
                        CompanyData(
                            org_id=str(org_id),
                            name=item.get("name", ""),
                            city=city,
                            category=category,
                            twogis_url=item.get("url") or f"https://2gis.ru/firm/{org_id}",
                            website=website,
                            socials=socials,
                            branch_count=int(item.get("branch_count") or 1),
                            yclients=yclients,
                            rating=float(rating_raw) if rating_raw else None,
                        )
                    )
            except Exception as exc:
                logger.error("Error collecting category '%s': %s", category, exc)
                raise

        return results
