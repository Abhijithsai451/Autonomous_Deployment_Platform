from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await app.state.dishka_container.close()

def create_app():
    app = FastAPI(title= "")
