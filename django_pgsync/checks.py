"""Django system checks: surface configuration mistakes at startup."""

from django.core import checks

from .conf import DEFAULT_MODE, KNOWN_PGSYNC_SETTINGS, MODES, RESERVED_KEYS


@checks.register()
def check_pgsync_settings(app_configs, **kwargs):
    from django.conf import settings

    errors = []
    pgsync = getattr(settings, "PGSYNC", {})
    if not isinstance(pgsync, dict):
        return [
            checks.Error(
                f"The PGSYNC setting must be a dict, got {type(pgsync).__name__}.",
                id="django_pgsync.E001",
            )
        ]
    mode = pgsync.get("MODE", DEFAULT_MODE)
    if mode not in MODES:
        errors.append(
            checks.Error(
                f"Invalid PGSYNC['MODE'] {mode!r}.",
                hint=f"Expected one of {MODES}.",
                id="django_pgsync.E002",
            )
        )
    for key in pgsync:
        if not isinstance(key, str) or not key.isupper():
            errors.append(
                checks.Warning(
                    f"PGSYNC key {key!r} is not an uppercase string; "
                    f"PGSync environment settings are uppercase.",
                    id="django_pgsync.W001",
                )
            )
        elif key not in RESERVED_KEYS and key not in KNOWN_PGSYNC_SETTINGS:
            errors.append(
                checks.Warning(
                    f"PGSYNC key {key!r} is not a recognized PGSync "
                    f"setting — possible typo. It will still be exported "
                    f"to the environment.",
                    hint=(
                        "Known settings are listed in "
                        "django_pgsync.conf.KNOWN_PGSYNC_SETTINGS."
                    ),
                    id="django_pgsync.W002",
                )
            )
    return errors


@checks.register()
def check_index_schemas(app_configs, **kwargs):
    """Every registered PGSyncIndex must produce a valid schema document.

    Catches broken definitions (unknown fields, uninferrable
    relationships) at startup instead of at sync time. Uses model
    metadata only; no database connection is made.
    """
    from .indexes import registry
    from .schema import SchemaGenerationError, build_document

    errors = []
    for index_cls in registry:
        try:
            build_document(index_cls)
        except SchemaGenerationError as exc:
            errors.append(
                checks.Error(
                    f"PGSyncIndex {index_cls.__name__!r} "
                    f"(index {index_cls.get_index_name()!r}) cannot "
                    f"generate a schema: {exc}",
                    id="django_pgsync.E003",
                )
            )
    return errors
