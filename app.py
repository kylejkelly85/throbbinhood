import uvicorn
from fasthtml.common import fast_app
from src.presentation.routes import setup_routes
from src.infrastructure.database import init_db

# Initialize FastHTML Starlette Application
# Lifecycle hook mapped to app startup
app, rt = fast_app(on_startup=[init_db])

# Mount routing setup
setup_routes(app, rt)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False, workers=1)
