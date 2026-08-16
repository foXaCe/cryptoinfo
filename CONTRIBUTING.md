# Contributing

Merci de votre intérêt pour Cryptoinfo !

## Bug reports

Utilisez le [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml).

## Feature requests

Utilisez le [feature request template](.github/ISSUE_TEMPLATE/feature_request.yml).

## Pull requests

1. Créez une branche dédiée : `git checkout -b feat/ma-feature`
2. Installez les hooks de validation : `prek install`
3. Écrivez le code et les tests : `pytest tests/`
4. Lint : `ruff check . && ruff format --check .`
5. Type check : `mypy custom_components/cryptoinfo`
6. Committez en conventional commits : `feat: …`
7. Poussez la branche et ouvrez une PR vers `main`

## Setup local

Installez les dépendances de développement depuis `pyproject.toml` :

```bash
pip install -e ".[dev]"
pipx install prek   # ou brew install j178/prek/prek
prek install
```

(prek est un drop-in Rust de pre-commit, beaucoup plus rapide. Si vous préférez la version Python : `pipx install pre-commit`.)

## Gestion des dépendances

Ce repo utilise **Renovate** (et non Dependabot). Les PR de mise à jour sont ouvertes
par le bot `@renovate[bot]`. Voir le [dashboard Renovate](../../issues?q=is:issue+author:app/renovate).
