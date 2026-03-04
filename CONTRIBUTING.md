# Contributing to archer

Thank you for your interest in contributing! This document covers everything you
need to get started.

______________________________________________________________________

## Table of contents

- [Development setup](#development-setup)
- [Project layout](#project-layout)
- [Adding a new AWS resource](#adding-a-new-aws-resource)
- [Adding a new cloud provider](#adding-a-new-cloud-provider)
- [Running tests](#running-tests)
- [Linting and formatting](#linting-and-formatting)
- [Submitting a pull request](#submitting-a-pull-request)
- [Commit style](#commit-style)

______________________________________________________________________

## Development setup

```bash
# 1. Fork + clone
git clone https://github.com/<your-fork>/archer.git
cd archer

# 2. Create a virtual environment and install all dependencies
uv venv
uv pip install -e ".[dev]"

# 3. Verify everything works
archer --version
pytest
```

> **Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/) are required.**
> The [Pulumi CLI](https://www.pulumi.com/docs/install/) must also be on your PATH.

______________________________________________________________________

## Project layout

| Layer | Path | Convention |
|---|---|---|
| **CLI** | `src/archer/cli.py` | Click commands + rich presentation only — no Pulumi imports |
| **Engine** | `src/archer/engine.py` | Pulumi Automation API wrapper |
| **Models** | `src/archer/models/base.py` | Shared config + result models |
| | `src/archer/models/<cloud>/` | One file per service namespace (e.g. `aws/ec2.py`, `aws/rds.py`). File name = AWS/Azure/GCP service name. |
| **Builders** | `src/archer/modules/<cloud>/` | One builder file per service — mirrors `models/<cloud>/`. Every builder has an early-return guard. |
| **Providers** | `src/archer/providers/` | Thin orchestration layer. `aws.py` calls builders in dependency order; cloud providers delegate to their module package. |
| **Tests** | `tests/unit/` | `test_models.py` (validators) + `test_builders.py` (early-return guards) |

______________________________________________________________________

## Adding a new AWS resource

Example: adding an SQS queue.

### 1. Add a Pydantic model

Create `src/archer/models/aws/sqs.py` (named after the AWS service namespace):

```python
from pydantic import BaseModel, ConfigDict, Field

class SqsQueueConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    fifo: bool = False
    visibility_timeout_seconds: int = 30
    message_retention_seconds: int = 345600  # 4 days
    tags: dict[str, str] = Field(default_factory=dict)
```

### 2. Register it in `AwsResources`

In `src/archer/models/aws/__init__.py`:

```python
from archer.models.aws.sqs import SqsQueueConfig

class AwsResources(BaseModel):
    ...
    sqs: list[SqsQueueConfig] = Field(default_factory=list)
```

### 3. Write a builder

Create `src/archer/modules/aws/sqs.py`:

```python
from dataclasses import dataclass, field
from typing import Any
import pulumi
import pulumi_aws as aws
from archer.modules.aws.subnets import SubnetBuildResult

@dataclass
class SqsBuildResult:
    queues: dict[str, aws.sqs.Queue] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)

class SqsBuilder:
    def __init__(self, config, subnet_result: SubnetBuildResult) -> None:
        self._config = config
        self._subnet_result = subnet_result

    def build(self) -> SqsBuildResult:
        resources = self._config.resources
        if not resources.sqs:          # ← early-return guard is mandatory
            return SqsBuildResult()
        result = SqsBuildResult()
        for q_cfg in resources.sqs:
            queue = aws.sqs.Queue(
                q_cfg.name,
                fifo_queue=q_cfg.fifo,
                visibility_timeout_seconds=q_cfg.visibility_timeout_seconds,
                message_retention_seconds=q_cfg.message_retention_seconds,
            )
            result.queues[q_cfg.name] = queue
            result.outputs[f"{q_cfg.name}_queue_url"] = queue.url
        return result
```

### 4. Wire into `AWSProvider`

In `src/archer/providers/aws.py`, call it at the right point in the dependency
chain and merge the outputs:

```python
from archer.modules.aws.sqs import SqsBuilder

# inside build_resources():
sqs_result = SqsBuilder(self.config, subnet_result).build()
self._output_map.update(sqs_result.outputs)
```

### 5. Add tests

In `tests/unit/test_builders.py`, add at minimum:

- An empty-list early-return test
- A smoke test that verifies the builder creates the expected Pulumi resources

______________________________________________________________________

## Adding a new cloud provider

1. Create `src/archer/providers/<name>.py` — implement `BaseProvider`.
1. Add Pydantic models to `src/archer/models/<name>.py`.
1. Add a `<Name>Resources` container and export from `src/archer/models/__init__.py`.
1. Register in `src/archer/providers/__init__.py`:
   ```python
   PROVIDER_REGISTRY["digitalocean"] = DigitalOceanProvider
   ```
1. Wire into `cli.py`'s `_load_config` resources-block dispatch.

______________________________________________________________________

## Running tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src/archer --cov-report=term-missing

# A specific file
pytest tests/unit/test_models.py -v
```

______________________________________________________________________

## Linting and formatting

```bash
# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Type check
pyright src/
```

CI will fail if any of these report errors.

______________________________________________________________________

## Submitting a pull request

1. Create a branch: `git checkout -b feat/elasticache-support`
1. Keep PRs focused — one feature or fix per PR
1. Add or update tests for your change
1. Ensure `ruff check`, `ruff format --check`, and `pytest` all pass locally
1. Fill in the PR description template

______________________________________________________________________

## Commit style

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(aws): add ElastiCache builder
fix(engine): handle None detailedDiff in Pulumi events
docs: update README with ElastiCache example
chore: bump pulumi-aws to 6.40.0
test: add unit tests for RDS builder early-return guard
```
