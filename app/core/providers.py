from typing import AsyncIterable

import httpx
from dishka import Provider, Scope, provide


class AppConfig:
    def __init__(self):
        self.db_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/cortexops"
        self.litellm_url = "http://localhost:4000"

class DatabaseEngine:
    def __init__(self, url: str):
        self.url = url
        async def close(self):
            pass
class DatabaseSession:
    def __init__(self, engine: DatabaseEngine):
        async def commit(self):
            pass
        async def close(self):
            pass

# Dishka Infrastructure Providers

class InfrastructureProvider(Provider):
    @provide(scope= Scope.APP)
    def provide_config(self)-> AppConfig:
        return AppConfig()

    @provide(scope = Scope.APP)
    async def provide_db_engine(self,config: AppConfig)-> AsyncIterable[DatabaseEngine]:
        session = DatabaseEngine(config.db_url)
        yield session
        await session.close()

    @provide(scope=Scope.REQUEST)
    async def provide_db_session(self, engine: DatabaseEngine) -> AsyncIterable[DatabaseSession]:
        session = DatabaseSession(engine)
        yield session
        await session.close()

    @provide(scope=Scope.REQUEST)
    async def provide_http_client(self) -> AsyncIterable[httpx.AsyncClient]:
        async with httpx.AsyncClient() as client:
            yield client

"""
Why do we use Dishka?
Decoupling: Your business logic doesn't need to know how to create a database session; it just asks for one.
            This makes it easy to swap implementations (e.g., using a mock database for testing).
Scope Management: It handles the lifetime of objects automatically using scopes:
    Scope.APP: Created once when the app starts (e.g., a connection pool).
    Scope.REQUEST: Created fresh for every incoming web request and cleaned up afterward.
Clean Code: It removes "boilerplate" code. You don't have to pass the same configuration objects through ten different 
            functions just to reach the one that needs it.
Alternative Frameworks
If you're looking for other popular options in the Python ecosystem:
python-dependency-injector: Probably the most established and feature-rich DI framework. It is very powerful but can be
            more verbose and complex to set up compared to Dishka.
FastAPI Depends: Since you have fastapi in your requirements, it's worth noting that FastAPI has a built-in dependency 
            injection system. It’s very simple and works great for web-related dependencies, though it isn't as 
            specialized for complex object graphs as Dishka.
Punq: A small, simple, and "type-hint-first" DI library. It's much lighter than Dishka and doesn't require inheriting 
            from specific provider classes.
Dishka is particularly liked recently because it is asynchronous-friendly and provides a very clean API using Python's type hints.
"""

