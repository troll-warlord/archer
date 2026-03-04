# Security policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x | ✅ |

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security issues by emailing the maintainers directly. Include:

- A clear description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes (optional)

We aim to acknowledge reports within 48 hours and provide a fix or mitigation
plan within 14 days.

## Scope

- Credential handling — archer never writes credentials to disk or logs
- YAML injection — malicious YAML that could escape Pydantic validation
- Dependency vulnerabilities — report against specific transitive deps

## Out of scope

- Vulnerabilities in Pulumi itself — report those to https://github.com/pulumi/pulumi
- AWS/Azure/GCP service vulnerabilities — report those to the respective cloud provider
