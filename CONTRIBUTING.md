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

```
src/archer/
├── cli.py              ← Click commands + rich presentation (no Pulumi imports)
├── engine.py           ← Pulumi Automation API wrapper
├── models/
│   ├── __init__.py     ← InfrastructureConfig + re-exports
│   ├── base.py         ← BackendConfig, OperationResult, ResourceChange
│   ├── aws/
│   │   ├── compute.py  ← EC2, ASG, EKS, ECS models
│   │   ├── database.py ← RDS model
│   │   ├── dns.py      ← Route53, ACM models
│   │   ├── loadbalancing.py
│   │   ├── networking.py ← VPC, Subnet, NAT GW, TGW, VPC Endpoint models
│   │   ├── security.py   ← IAM, KMS models
│   │   └── storage.py    ← S3, EFS models
│   ├── azure.py
│   └── gcp.py
├── modules/aws/        ← One builder class per service domain
│   ├── compute/        ← Ec2Builder, AsgBuilder, EksBuilder, EcsBuilder
│   ├── database/       ← RdsBuilder
│   ├── dns/            ← Route53Builder, AcmBuilder
│   ├── loadbalancing/  ← AlbBuilder
│   ├── networking/     ← VpcBuilder, SubnetBuilder, NatGatewayBuilder, …
│   ├── security/       ← IamBuilder, KmsBuilder
│   └── storage/        ← S3Builder, EfsBuilder
└── providers/
    ├── __init__.py     ← PROVIDER_REGISTRY
    ├── base.py         ← BaseProvider ABC
    ├── aws.py          ← AWSProvider (orchestrates all builders)
    ├── azure.py        ← AzureProvider
    └── gcp.py          ← GCPProvider
```

______________________________________________________________________

## Adding a new AWS resource

Example: adding ElastiCache.

### 1. Add a Pydantic model

Create `src/archer/models/aws/cache.py`:

```python
from pydantic import BaseModel, ConfigDict, Field

class ElasticacheConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    node_type: str = "cache.t3.micro"
    num_cache_nodes: int = 1
    engine: str = "redis"
    subnet_refs: list[str] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)
```

### 2. Register it in `AwsResources`

In `src/archer/models/aws/__init__.py`:

```python
from archer.models.aws.cache import ElasticacheConfig

class AwsResources(BaseModel):
    ...
    elasticache: list[ElasticacheConfig] = Field(default_factory=list)
```

### 3. Write a builder

Create `src/archer/modules/aws/cache/elasticache.py`:

```python
from dataclasses import dataclass, field
import pulumi, pulumi_aws as aws
from archer.modules.aws.networking.subnets import SubnetBuildResult

@dataclass
class ElasticacheBuildResult:
    clusters: dict[str, aws.elasticache.Cluster] = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)

class ElasticacheBuilder:
    def __init__(self, config, subnet_result: SubnetBuildResult) -> None:
        self._config = config
        self._subnet_result = subnet_result

    def build(self) -> ElasticacheBuildResult:
        resources = self._config.resources
        if not resources.elasticache:          # ← early-return guard is mandatory
            return ElasticacheBuildResult()
        ...
```

### 4. Wire into `AWSProvider`

In `src/archer/providers/aws.py`, call it at the right point in the dependency
chain and merge the outputs:

```python
cache_result = ElasticacheBuilder(self.config, subnet_result).build()
self._output_map.update(cache_result.outputs)
```

### 5. Add tests

Add `tests/unit/test_elasticache_builder.py` with at minimum:

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
