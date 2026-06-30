from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


class DatabaseManager:
    def __init__(self, config: AppConfig):
        self.engine = create_async_engine(
            config.db_url,
            pool_size = 20,
            max_overflow = 10,
            echo = False # Set to True for debugging.
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    async def close(self):
        await self.engine.dispose()


