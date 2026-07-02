from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import City, CollectionRun, Company, User


class UserRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, user_id: int, username: str | None, full_name: str | None) -> User:
        user = await self.session.get(User, user_id)
        if not user:
            user = User(id=user_id, username=username, full_name=full_name)
            self.session.add(user)
            await self.session.commit()
        return user


class CityRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, name: str) -> City:
        result = await self.session.execute(select(City).where(City.name == name))
        city = result.scalar_one_or_none()
        if not city:
            city = City(name=name)
            self.session.add(city)
            await self.session.commit()
            await self.session.refresh(city)
        return city

    async def get_last_run(self, city_name: str) -> CollectionRun | None:
        result = await self.session.execute(
            select(CollectionRun)
            .join(City)
            .where(City.name == city_name, CollectionRun.status == "done")
            .order_by(CollectionRun.finished_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class RunRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, city_id: int, user_id: int) -> CollectionRun:
        run = CollectionRun(city_id=city_id, user_id=user_id)
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def finish(self, run_id: int, total: int, sheet_url: str) -> None:
        await self.session.execute(
            update(CollectionRun)
            .where(CollectionRun.id == run_id)
            .values(
                status="done",
                total_found=total,
                sheet_url=sheet_url,
                finished_at=datetime.utcnow(),
            )
        )
        await self.session.commit()

    async def fail(self, run_id: int, error: str) -> None:
        await self.session.execute(
            update(CollectionRun)
            .where(CollectionRun.id == run_id)
            .values(status="error", error_message=error, finished_at=datetime.utcnow())
        )
        await self.session.commit()

    async def get(self, run_id: int) -> CollectionRun | None:
        return await self.session.get(CollectionRun, run_id)


class CompanyRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_insert(self, companies: list[dict]) -> int:
        objects = [Company(**c) for c in companies]
        self.session.add_all(objects)
        await self.session.commit()
        return len(objects)

    async def get_by_run(self, run_id: int) -> list[Company]:
        result = await self.session.execute(
            select(Company).where(Company.run_id == run_id).order_by(Company.category, Company.name)
        )
        return list(result.scalars().all())

    async def get_by_city(self, city_name: str) -> list[Company]:
        result = await self.session.execute(
            select(Company)
            .join(CollectionRun)
            .join(City)
            .where(City.name == city_name, CollectionRun.status == "done")
            .order_by(CollectionRun.finished_at.desc(), Company.category, Company.name)
        )
        return list(result.scalars().all())
