# archer

**Infrastructure as Code from a single YAML file.** archer is an open-source CLI that lets you
provision and manage cloud infrastructure on AWS, Azure, and GCP without writing Pulumi programs,
Terraform HCL, or CloudFormation templates. Describe your stack in YAML — archer handles the rest.

> **Keywords:** infrastructure as code, IaC, YAML infrastructure, AWS provisioning,
> cloud deployment automation, Pulumi wrapper, declarative infrastructure, self-hosted IaC,
> deploy AWS from YAML, infrastructure automation CLI

[![CI](https://github.com/troll-warlord/archer/actions/workflows/ci.yml/badge.svg)](https://github.com/troll-warlord/archer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)

______________________________________________________________________

## Cloud support

| Cloud | Status | Resources |
|---|---|---|
| **AWS** | ✅ Full support | VPC, Subnets, IGW, NAT GW, TGW, VPC Endpoints, Security Groups, EC2, ASG, EKS, ECS Fargate, RDS, ElastiCache (Redis/Memcached), S3, EFS, ALB, NLB, Route53, ACM, IAM, KMS, Secrets Manager, CloudWatch |
| Azure | 🚧 Basic stub | Resource Group, VNet, Subnets, Linux VMs |
| GCP | 🚧 Basic stub | VPC Network, Subnetworks, Compute Instances |

Azure and GCP will be expanded in future releases.

______________________________________________________________________

## Table of contents

- [How it works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick start](#quick-start)
- [CLI reference](#cli-reference)
- [YAML schema](#yaml-schema)
- [Examples](#examples)
- [Project structure](#project-structure)
- [Architecture decisions](#architecture-decisions)
- [Extending archer](#extending-archer)
- [Development](#development)
- [Contributing](#contributing)

______________________________________________________________________

## How it works

archer wraps the [Pulumi Automation API](https://www.pulumi.com/docs/using-pulumi/automation-api/).
You describe your infrastructure in YAML. archer translates it into Pulumi resources and runs
`up`, `preview`, `destroy`, or `refresh` — no Pulumi programs to write, no `Pulumi.yaml` to manage.

```
infrastructure.yaml  →  archer preview  →  Pulumi Automation API  →  AWS / Azure / GCP
```

| Property | Detail |
|---|---|
| State backend | Local filesystem (default) or Pulumi Cloud |
| Credential source | Standard SDK env-var / credential-file chain |
| Config validation | Pydantic v2 with cross-field CIDR checks |
| Logging | loguru, verbosity controlled by `--verbose` |
| Presentation | rich (tables, spinners, panels) — CLI layer only |

______________________________________________________________________

## Architecture decisions

### Provider registry instead of if/elif

```python
# providers/__init__.py
PROVIDER_REGISTRY: dict[str, type[BaseProvider]] = {
    "aws":   AWSProvider,
    "azure": AzureProvider,
    "gcp":   GCPProvider,
}
```

Adding a new provider is a single line here. The engine does
`PROVIDER_REGISTRY[config.provider]` and calls `build_resources()` +
`get_outputs()` — that's the entire interface contract.

### Opt-in resource provisioning

Every builder checks `if not resources.<field>: return empty_result()` as its
first line. Resources you don't declare in YAML are never created. A minimal config
with only a VPC and subnets will not touch NAT Gateways, EC2, RDS, or anything else.

### Cross-field CIDR validation with @model_validator

Cross-field checks (e.g. "does subnet CIDR fit inside the VPC CIDR?") use
`@model_validator(mode="after")` which runs after all fields are parsed:

```python
@model_validator(mode="after")
def validate_subnet_cidrs_fit_vpc(self) -> "InfrastructureConfig":
    vpc_network = ipaddress.ip_network(self.resources.vpc.cidr_block)
    for subnet in self.resources.subnets:
        subnet_network = ipaddress.ip_network(subnet.cidr_block)
        if not subnet_network.subnet_of(vpc_network):
            raise ValueError(f"Subnet {subnet.name} CIDR {subnet.cidr_block} is outside VPC {vpc_network}")
    return self
```

### Secrets stay out of YAML

YAML files are typically committed to version control. Passwords and tokens are
referenced by env-var name only:

```yaml
rds:
  - password_env_var: DB_PASSWORD   # ← env var name, not the value
```

archer reads `os.environ["DB_PASSWORD"]` at deploy time.

### Builder dependency order (AWS)

Each builder receives only the outputs it depends on:

```
KMS → IAM → VPC → Subnets → SecurityGroups
→ NatGateway → TransitGateway → VpcEndpoints
→ S3 → EFS → ALB/NLB → Route53 → ACM
→ EC2 → ASG → EKS → ECS → RDS
```

______________________________________________________________________

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | ≥ 3.11 | Runtime |
| [uv](https://docs.astral.sh/uv/) | latest | Dependency management + virtual env |
| [Pulumi CLI](https://www.pulumi.com/docs/install/) | ≥ 3.110 | Required by the Automation API |
| AWS credentials | — | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` (or `~/.aws/credentials`) — required only when deploying to AWS |

Install Pulumi:

```bash
# macOS / Linux
curl -fsSL https://get.pulumi.com | sh

# Windows (winget)
winget install pulumi

# Homebrew
brew install pulumi/tap/pulumi
```

______________________________________________________________________

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/archer.git
cd archer

# 2. Create a virtual environment and install dependencies with uv
uv venv
uv pip install -e ".[dev]"

# 3. Verify the CLI is available
archer --version
```

______________________________________________________________________

## Quick start

### 1. Set credentials

```bash
# AWS
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# RDS password (never put this in the YAML)
export DB_PASSWORD="MyStr0ng!Password"
```

### 2. Preview the changes

```bash
archer preview --config infrastructure.yaml
```

### 3. Deploy

```bash
archer up --config infrastructure.yaml
```

### 4. Inspect outputs

archer prints all Pulumi stack outputs (VPC ID, EC2 IPs, RDS endpoint, etc.)
in a table after every successful `up`.

### 5. Tear down

```bash
archer destroy --config infrastructure.yaml
# add --yes to skip the confirmation prompt
archer destroy --config infrastructure.yaml --yes
```

______________________________________________________________________

## CLI reference

```
Usage: archer [OPTIONS] COMMAND [ARGS]...

  archer — Infrastructure-as-Code wrapper around Pulumi.

Options:
  --version        Show version and exit.
  -v, --verbose    Enable DEBUG-level log output.
  --help           Show this message and exit.

Commands:
  up        Deploy or update infrastructure (pulumi up).
  preview   Preview infrastructure changes without deploying (pulumi preview).
  destroy   Destroy all infrastructure resources (pulumi destroy).
  refresh   Reconcile local stack state with the real cloud state (pulumi refresh).
  validate  Validate the configuration file without connecting to any cloud API.
  output    Print the current stack outputs without running any operation.
```

Each command accepts `--config / -c PATH` (default: `infrastructure.yaml`) and `--stack / -s NAME` (overrides the stack name):

```bash
archer up       --config infra/production.yaml
archer preview  -c infra/staging.yaml -v
archer destroy  --config infra/dev.yaml --yes
archer refresh  -c infra/dev.yaml
archer validate -c infra/prod.yaml
archer output   -c infra/prod.yaml --stack prod
# same YAML, three stacks:
archer up -c infra/app.yaml --stack dev
archer up -c infra/app.yaml --stack staging
archer up -c infra/app.yaml --stack prod
```

______________________________________________________________________

## YAML schema

```yaml
# ── Top-level ──────────────────────────────────────────────────────────────
project: <string>          # Pulumi project name
stack:   <string>          # Stack name (default: dev)  ← override with --stack
provider: aws | azure | gcp
region:  <string>          # Provider-specific region/location

# Global tags — applied to every resource; resource-level tags override these
tags:
  team: platform
  env: prod
  cost-center: eng-42

# ── Backend (optional) ─────────────────────────────────────────────────────
backend:
  type: local | cloud      # default: local
  path: .archer-state      # only for type: local
  url: <string>            # only for type: cloud (omit to use Pulumi Cloud)

# ── AWS resources ──────────────────────────────────────────────────────────
resources:
  vpc:
    name: <string>
    cidr_block: <CIDR>     # e.g. 10.0.0.0/16
    enable_dns_hostnames: true
    enable_dns_support: true

  subnets:
    - name: <string>
      cidr_block: <CIDR>   # must be contained within vpc.cidr_block
      availability_zone: <string>   # e.g. us-east-1a
      type: public | private

  # Named security groups — reference from ec2/rds/alb/elasticache via security_group_refs
  security_groups:
    - name: app-sg
      description: "App tier"
      ingress_rules:
        - protocol: tcp
          from_port: 8080
          to_port: 8080
          cidr_blocks: ["10.0.0.0/8"]
      # egress_rules: [] ← defaults to allow-all when omitted

  ec2:
    - name: <string>
      instance_type: <string>       # validated against allowed set
      ami: <string>                 # AMI ID for the target region
      subnet_ref: <subnet.name>     # must reference a declared subnet
      assign_public_ip: true | false
      key_name: <string>            # optional EC2 key pair name
      tags: {}                      # optional extra tags

  rds:
    - name: <string>
      engine: postgres | mysql | mariadb | …
      engine_version: <string>
      instance_class: db.t3.micro | …   # validated against allowed set
      allocated_storage: <int>          # minimum 20
      db_name: <string>
      username: <string>
      password_env_var: DB_PASSWORD     # env var name (not the value!)
      subnet_refs: [<subnet.name>, …]   # must reference declared subnets
      multi_az: false
      publicly_accessible: false
      tags: {}

  elasticache:
    - name: app-redis
      engine: redis           # redis | memcached
      node_type: cache.t3.micro
      num_cache_nodes: 1
      subnet_refs: [app-1, app-2]
      security_group_refs: [app-sg]
      transit_encryption: true
      at_rest_encryption: true

  secrets:
    - name: db-password
      env_var: DB_PASSWORD    # value read from os.environ[DB_PASSWORD] at deploy time
    - name: api-key
      env_var: THIRD_PARTY_API_KEY

  log_groups:
    - name: /app/production
      retention_days: 30

  cloudwatch_alarms:
    - name: high-cpu
      metric_name: CPUUtilization
      namespace: AWS/EC2
      threshold: 80
      comparison_operator: GreaterThanOrEqualToThreshold
      alarm_actions: [arn:aws:sns:us-east-1:123:alerts]
```

### Validation rules enforced at parse time

| Rule | How |
|---|---|
| Provider must be `aws`, `azure`, or `gcp` | `field_validator` |
| Every subnet CIDR must fit inside the VPC CIDR | `@model_validator` + `ipaddress.subnet_of()` |
| Subnet names must be unique | `@model_validator` |
| `ec2[].subnet_ref` must reference a declared subnet | `@model_validator` |
| `rds[].subnet_refs` must all reference declared subnets | `@model_validator` |
| `allocated_storage` ≥ 20 GiB | `field_validator` |
| Region, instance type, engine | Validated by the cloud provider at preview/deploy time |

______________________________________________________________________

## Extending archer

### Add a new AWS resource type

1. **Model** — add a Pydantic model in `src/archer/models/aws/<service>.py` (named after the AWS service namespace, e.g. `waf.py`)
1. **Register** — add it as a field on `AwsResources` in `src/archer/models/aws/__init__.py`
1. **Builder** — create `src/archer/modules/aws/<service>.py` with an early-return guard
1. **Wire** — call the builder from `AWSProvider.build_resources()` in the correct dependency position
1. **Test** — add a unit test in `tests/unit/test_builders.py`

See [CONTRIBUTING.md](CONTRIBUTING.md) for a complete worked example.

### Add a new cloud provider

1. **Create `src/archer/providers/<name>.py`** — implement `BaseProvider`
1. **Add models** to `src/archer/models/<name>.py`
1. **Register** in `providers/__init__.py`:
   ```python
   from archer.providers.digitalocean import DigitalOceanProvider

   PROVIDER_REGISTRY: dict[str, type[BaseProvider]] = {
       "aws":          AWSProvider,
       "azure":        AzureProvider,
       "gcp":          GCPProvider,
       "digitalocean": DigitalOceanProvider,   # ← one line
   }
   ```
1. No changes needed in `engine.py` or `cli.py`.

______________________________________________________________________

## Project structure

| Path | Purpose |
|---|---|
| `src/archer/cli.py` | Click commands + rich presentation (no Pulumi imports) |
| `src/archer/engine.py` | Pulumi Automation API wrapper |
| `src/archer/models/base.py` | Shared models: `BackendConfig`, `OperationResult`, `ResourceChange` |
| `src/archer/models/<cloud>/` | One file per service namespace (e.g. `models/aws/ec2.py`, `models/aws/rds.py`). Adding a new service = add one file here. |
| `src/archer/modules/<cloud>/` | One builder file per service — mirrors `models/<cloud>/`. Each builder has an early-return guard so unused services add zero cost. |
| `src/archer/providers/` | Thin orchestration layer. `aws.py` calls builders in dependency order; `azure.py` / `gcp.py` delegate to their respective module packages. |
| `examples/` | Ready-to-run YAML configurations |
| `tests/unit/` | Pydantic validator tests + builder early-return tests |

______________________________________________________________________

## Examples

Ready-to-use YAML files are in the [`examples/`](examples/) directory:

| File | What it deploys |
|---|---|
| [`aws-minimal.yaml`](examples/aws-minimal.yaml) | VPC + 2 subnets + 1 EC2 bastion |
| [`aws-3tier.yaml`](examples/aws-3tier.yaml) | ALB + ASG (web/app tiers) + RDS PostgreSQL |
| [`aws-eks.yaml`](examples/aws-eks.yaml) | EKS cluster with managed node group |

______________________________________________________________________

## Roadmap

| Item | Status |
|---|---|
| AWS — core service coverage | ✅ 0.1.0 |
| Standalone security groups + global tags | ✅ 0.2.0 |
| ElastiCache, Secrets Manager, CloudWatch | ✅ 0.2.0 |
| `archer validate` + `--stack` flag + `archer output` | ✅ 0.2.0 |
| Lambda + IAM execution role | 🔜 planned |
| API Gateway (HTTP API + REST API) | 🔜 planned |
| SNS topics + SQS queues | 🔜 planned |
| DynamoDB tables | 🔜 planned |
| CloudFront distributions | 🔜 planned |
| Aurora / Aurora Serverless v2 | 🔜 planned |
| Variable substitution in YAML (`${env}`, `${region}`) | 🔜 planned |
| Azure — full parity with AWS | 🔜 planned |
| GCP — full parity with AWS | 🔜 planned |
| `archer import` — bring existing resources under management | 💡 idea |
| Stack references — pass outputs from one config as inputs to another | 💡 idea |
| Drift detection (`archer diff`) | 💡 idea |

______________________________________________________________________

## Development

```bash
# Install with dev extras
uv pip install -e ".[dev]"

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Type check
pyright src/

# Run tests
pytest

# Tests with coverage
pytest --cov=src/archer --cov-report=term-missing
```

All linting rules are in `pyproject.toml` under `[tool.ruff]`. Line length is **180** characters, target Python 3.11+.

______________________________________________________________________

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

______________________________________________________________________

## License

[MIT](LICENSE)
