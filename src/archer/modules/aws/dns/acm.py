from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.dns.route53 import Route53BuildResult
from archer.modules.aws.utils import make_tags

if TYPE_CHECKING:
    from archer.models import AwsResources, InfrastructureConfig


@dataclass
class AcmBuildResult:
    certificates: dict[str, aws.acm.Certificate] = field(default_factory=dict)
    validations: dict[str, aws.acm.CertificateValidation] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class AcmBuilder:
    def __init__(
        self,
        config: InfrastructureConfig,
        route53_result: Route53BuildResult,
    ) -> None:
        self._config = config
        self._route53_result = route53_result

    def build(self) -> AcmBuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        if not resources.acm_certificates:
            return AcmBuildResult()

        result = AcmBuildResult()

        for cert_cfg in resources.acm_certificates:
            cert = aws.acm.Certificate(
                cert_cfg.name,
                domain_name=cert_cfg.domain_name,
                subject_alternative_names=cert_cfg.subject_alternative_names,
                validation_method=cert_cfg.validation_method,
                tags=self._tags(cert_cfg.name, cert_cfg.tags),
                opts=pulumi.ResourceOptions(delete_before_replace=True),
            )
            result.certificates[cert_cfg.name] = cert
            result.outputs[f"{cert_cfg.name}_cert_arn"] = cert.arn

            # Auto DNS validation if a zone_ref is provided
            if cert_cfg.validation_method == "DNS" and cert_cfg.zone_ref:
                zone = self._route53_result.zones.get(cert_cfg.zone_ref)
                if zone:
                    validation_record = aws.route53.Record(
                        f"{cert_cfg.name}-validation-record",
                        zone_id=zone.zone_id,
                        name=cert.domain_validation_options[0].resource_record_name,
                        type=cert.domain_validation_options[0].resource_record_type,
                        records=[cert.domain_validation_options[0].resource_record_value],
                        ttl=60,
                        allow_overwrite=True,
                    )
                    validation = aws.acm.CertificateValidation(
                        f"{cert_cfg.name}-validation",
                        certificate_arn=cert.arn,
                        validation_record_fqdns=[validation_record.fqdn],
                    )
                    result.validations[cert_cfg.name] = validation

        return result

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
