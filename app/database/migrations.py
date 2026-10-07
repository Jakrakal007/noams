from alembic import command
from alembic.config import Config
from app.core.config import PROJECT_ROOT, DEMO_DATA


def run_migrations() -> None:
    DEMO_DATA.mkdir(parents=True, exist_ok=True)
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    command.upgrade(config, "head")
