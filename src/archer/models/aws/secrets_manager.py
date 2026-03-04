"""
models/aws/secrets_manager.py — AWS Secrets Manager models.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SecretsManagerSecretConfig(BaseModel):
    """
    AWS Secrets Manager secret.

    The secret value is never stored in YAML.  Provide it at deploy time via
    one of two mechanisms (mutually exclusive — env_var takes precedence):

      env_var       — archer reads os.environ[env_var] and stores it as the secret value.
      secret_string — a literal value; only use for non-sensitive placeholders or
                      values that are already encoded (e.g. a JSON template string).

    If neither is provided, the secret is created without an initial version;
    you can populate it manually or via another tool.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    description: str | None = None

    # Secret value source — only one should be set
    env_var: str | None = None  # name of env var to read at deploy time
    secret_string: str | None = None  # literal value (use sparingly)

    # Encryption
    kms_key_id: str | None = None  # defaults to the AWS-managed key if omitted

    # Recovery
    recovery_window_days: int = 30  # 0 = force-delete immediately (use in dev only)

    tags: dict[str, str] = Field(default_factory=dict)
