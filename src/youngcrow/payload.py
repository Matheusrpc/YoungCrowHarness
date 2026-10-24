"""The scripts and requirements `youngcrow init` copies into a project."""
from importlib.resources import files
from pathlib import Path

PAYLOAD: tuple[str, ...] = (
    *(f'scripts/{name}.py' for name in (
        'vault', 'document_store', 'documents', 'docling_worker', 'source_fetch',
        'source_prompt', 'memory', 'graphify_worker', 'capabilities', 'integrations',
        'personalize', 'adoption', 'adoption_fs')),
    'scripts/adoption_acl.ps1',
    *(f'requirements/{name}.txt' for name in ('docling', 'docling-media', 'graphify')),
)

# Vault indexes `init` creates when they are missing. They stay single-sourced in the repository's
# own vault/ and are not part of PAYLOAD: they land in the project's vault/, not in .youngcrow/.
VAULT_TEMPLATES: tuple[str, ...] = (
    'vault/index.md', 'vault/integrations/index.md', 'vault/capabilities/index.md',
)


def payload_root() -> Path:
    """Folder holding `scripts/`, `requirements/` and `vault/`: packaged, else the repository root."""
    packaged = Path(str(files('youngcrow') / 'payload'))
    return packaged if packaged.is_dir() else Path(__file__).resolve().parents[2]
