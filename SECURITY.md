# Security Policy

## Supported versions

Security fixes are provided for the latest released version.

| Version | Supported |
| --- | --- |
| Latest | Yes |
| Older releases | Best effort |

## Reporting a vulnerability

Please report security issues privately by emailing:

**ravikiran.pagidi@gmail.com**

Include:

- affected version or commit
- reproduction steps
- impact
- any suggested mitigation

Please do not open a public issue for suspected vulnerabilities until the issue has been reviewed.

## Scope

This library generates synthetic data and writes files through pandas or Spark. It does not manage cloud credentials, configure storage permissions, or transform sensitive production data into privacy-preserving synthetic data.

If a vulnerability depends on a cloud runtime, Spark connector, notebook platform, or storage permission model, include those environment details in the report.
