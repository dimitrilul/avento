from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_alembic_revision_graph_is_connected() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    revisions = ScriptDirectory.from_config(config)

    assert revisions.get_heads() == ["0011"]
    assert revisions.get_revision("0010").down_revision == "0009_google_health"
    assert [revision.revision for revision in revisions.walk_revisions()]
