# Changelog

All notable changes to archer are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

______________________________________________________________________

## [Unreleased]

### Planned

- Azure resource expansion (NSGs, Storage Accounts, AKS, App Service, CosmosDB)
- GCP resource expansion (Cloud SQL, GKE, Cloud Storage, Cloud Run)
- `archer import` — import existing cloud resources into state
- Aurora / Aurora Serverless v2 support
- Drift detection summary in `archer refresh`

______________________________________________________________________

## [0.2.0] - 2026-03-04

### Added

- **Standalone security groups** — top-level `security_groups:` YAML block; groups can be referenced by name from `ec2`, `rds`, `alb`, `elasticache` via `security_group_refs`
- **Global tags** — top-level `tags:` block in the YAML; merged into every resource tag dictionary (resource-level tags take precedence)
- **ElastiCache** — Redis (ReplicationGroup) and Memcached (Cluster) with subnet groups and encryption support
- **Secrets Manager** — create secrets with values sourced from env vars at deploy time via `env_var`
- **CloudWatch** — Log Groups (with configurable retention) and Metric Alarms
- **`archer validate`** — validate the YAML config without connecting to any cloud API
- **`archer output`** — print the current stack outputs without running any operation
- **`--stack` / `-s` flag** — override the stack name from the CLI for all commands (no YAML duplication for dev/staging/prod)

### Changed

- `make_tags` now accepts `global_tags` parameter; all 18 builders pass the parent config's tags through
- `SecurityGroupBuilder` now provisions all named SGs from `security_groups:` and exposes them via `sg_map` for cross-resource referencing
- Builder dependency chain extended: ElastiCache (step 19) → Secrets Manager (step 20) → CloudWatch (step 21)

______________________________________________________________________

## [0.1.0] - 2026-03-04

### Added

- Initial release — AWS-first implementation
- CLI commands: `up`, `preview`, `destroy`, `refresh`
- AWS resource support:
  - Networking: VPC, Subnets, Internet Gateway, NAT Gateways, Transit Gateway, VPC Endpoints, Security Groups, Route Tables
  - Compute: EC2, Auto Scaling Groups (with Launch Templates), EKS, ECS Fargate
  - Database: RDS (PostgreSQL, MySQL, MariaDB, Oracle, SQL Server)
  - Storage: S3, EFS
  - Load Balancing: ALB (with HTTP→HTTPS redirect), NLB
  - DNS / TLS: Route53 Hosted Zones + Records, ACM Certificates (auto DNS validation)
  - Security: IAM Roles + Policies, KMS Keys
- Pydantic v2 model validation with cross-field CIDR containment checks
- Local filesystem and Pulumi Cloud state backends
- Real-time preview output via loguru streaming
- Rich terminal presentation (panels, tables, spinners)
- Azure stub: Resource Group, VNet, Subnets, Linux VMs
- GCP stub: VPC Network, Subnetworks, Compute Instances
