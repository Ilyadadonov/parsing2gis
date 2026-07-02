from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, DateTime, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(128))
    full_name: Mapped[str | None] = mapped_column(String(256))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    runs: Mapped[list["CollectionRun"]] = relationship(back_populates="user")


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    twogis_region_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    runs: Mapped[list["CollectionRun"]] = relationship(back_populates="city")


class CollectionRun(Base):
    __tablename__ = "collection_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    total_found: Mapped[int] = mapped_column(Integer, default=0)
    sheet_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    city: Mapped["City"] = relationship(back_populates="runs")
    user: Mapped["User"] = relationship(back_populates="runs")
    companies: Mapped[list["Company"]] = relationship(back_populates="run")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("collection_runs.id"))
    org_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(512))
    city: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(256))
    twogis_url: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(Text)
    socials: Mapped[str | None] = mapped_column(Text)
    branch_count: Mapped[int] = mapped_column(Integer, default=1)
    yclients: Mapped[str] = mapped_column(String(32), default="не определено")
    rating: Mapped[float | None] = mapped_column(Float)
    collected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    run: Mapped["CollectionRun"] = relationship(back_populates="companies")

    __table_args__ = (
        UniqueConstraint("run_id", "org_id", name="uq_company_run_org"),
    )
