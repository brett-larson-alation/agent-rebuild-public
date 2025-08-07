# Alation Agent Rebuild Scripts

This repository provides solutions for **reinstalling and configuring Alation Agents** on new systems. Choose between complete rebuild (from scratch) or partial rebuild (two-phase approach) based on your specific needs.

## Repository Overview

The Alation Agent is not built in a highly available (HA) manner, which can create concerns about single points of failure for Alation Cloud customers. These scripts help you quickly set up agents on new servers for various scenarios including disaster recovery, server migration, and testing.

## Choose Your Approach

| Method | Time | Description | Complexity |
|--------|------|-------------|------------|
| **[Complete Rebuild](complete-rebuild/)** | 3-5 minutes | Single script handles everything from download to activation | Low |
| **[Partial Rebuild](partial-rebuild/)** | 3-5 minutes* | Two-phase approach: prepare system once, activate when needed | Medium |

*Requires 3-5 minute preparation phase run once

## Architecture Comparison

### Complete Rebuild (Single Phase)
```
┌─────────────────────────────────────┐
│ ✅ Download, Install, Configure     │  
│ ✅ Certificates, Connect, Sync      │  ── 3-5 minutes
│ ✅ Everything in one execution      │
└─────────────────────────────────────┘
```

### Partial Rebuild (Two Phase)
```
Phase 1: Prepare (Run Once)    Phase 2: Activate (When Needed)
┌─────────────────┐             ┌─────────────────┐
│ ✅ Download     │ ── 3-5 min  │ ✅ Configure    │ ── 3-5 min
│ ✅ Install      │             │ ✅ Certificates │
│ 💤 Dormant      │             │ ✅ Connect      │
└─────────────────┘             └─────────────────┘
```

## Authentication Methods

Both approaches support two authentication methods:

| Authentication | When to Use | Requirements |
|---------------|-------------|--------------|
| **Username/Password** | Direct Alation login | Server Admin credentials |
| **SSO** | SAML, OIDC, etc. | Pre-generated tokens from Alation UI |

## Prerequisites

### System Requirements
- **Alation Cloud Service** instance (on-premise instances don't need agents)
- **Linux Distribution**: Debian/Ubuntu or RHEL/CentOS
- **Python 3.7+**: With `requests` and `toml` libraries
- **Docker**: Must be installed and running (installed as part of Agent setup)
- **Sudo Access**: Required for system-level operations

### Alation Requirements  
- **Server Admin** privileges in Alation
- **Network Access**: Connectivity to Alation instance and data sources
- **Agent ID**: Know which agent you're rebuilding

### Install Dependencies
```bash
pip3 install requests toml
```

## Quick Start

### Option 1: Complete Rebuild
Perfect for fresh installations and one-time recovery:
```bash
cd complete-rebuild/
# Edit configuration in rebuild-core.py or rebuild-sso.py
python3 rebuild-core.py  # or rebuild-sso.py
```

### Option 2: Partial Rebuild  
Ideal for speed-critical scenarios:
```bash
cd partial-rebuild/
# Phase 1: Prepare system (run once)
python3 prepare-core.py  # or prepare-sso.py

# Phase 2: Activate when needed (run during recovery)  
python3 activate-core.py  # or activate-sso.py
```

## Critical Prerequisites

> **IMPORTANT**: Before rebuilding an agent, ensure the existing agent with the same Agent ID is completely shut down. Having multiple agents with the same ID online simultaneously will cause conflicts.

### Agent ID Conflict Prevention
- **Only one agent per Agent ID** can be active at a time
- **Shut down existing agent** before activating replacement
- **Verify agent is offline** before proceeding with rebuild

## Feature Comparison

| Feature | Complete Rebuild | Partial Rebuild |
|---------|------------------|-----------------|
| **Setup Time** | 3-5 minutes | 3-5 minutes* |
| **Preparation** | None required | 3 minutes once |
| **Complexity** | Single script | Two-phase process |

*After initial preparation phase

## Security Features

### Authentication Options
- **Manual Login**: Temporary token generation with automatic revocation
- **SSO**: External token management (tokens not revoked by scripts)

### Security Validation
- **SHA256 checksum verification** for all downloaded packages
- **Certificate-based agent authentication**
- **Secure temporary file handling**
- **Package source validation** from official Alation endpoints

### Optional Authentication Service
Both approaches support optional installation of the Authentication Service for:
- Kerberos authentication
- LDAP integration  
- Complex authentication workflows

## Testing and Validation

### Safe Testing Approach
1. **Test on non-production** Alation instances and datasources first
2. **Document recovery times** for your specific setup

### Validation Steps
After completion, verify:
- Agent connectivity in Alation UI
- Data source connections work
- Docker containers are running
- Service status is healthy

## Troubleshooting

### Common Issues
- **Authentication errors**: Verify credentials and Server Admin privileges
- **Network connectivity**: Check firewall rules
- **Installation failures**: Verify disk space and sudo access
- **Agent conflicts**: Ensure no duplicate Agent IDs are active

### Log Analysis
Both approaches provide detailed colored logging:
- **Blue**: Info and progress messages
- **Yellow**: Warning messages
- **Red**: Error messages

## Directory Structure

```
agent-rebuild/
├── README.md                  # This overview and decision guide
├── CLAUDE.md                  # Development guidance  
├── complete-rebuild/          # Single-phase rebuild (3-5 min)
│   ├── README.md             # Complete rebuild guide
│   ├── rebuild-core.py       # Username/password version
│   └── rebuild-sso.py        # SSO version
└── partial-rebuild/           # Two-phase rebuild (3-5 min activation)
    ├── README.md             # Partial rebuild guide  
    ├── prepare-core.py       # Phase 1: Manual login
    ├── prepare-sso.py        # Phase 1: SSO
    ├── activate-core.py      # Phase 2: Manual login
    └── activate-sso.py       # Phase 2: SSO
```

## Common Use Cases

Both approaches support all scenarios including:
- **Disaster Recovery**: Agent replacement during outages
- **Server Migration**: Moving agents to new infrastructure  
- **Testing & Development**: Setting up temporary or test environments
- **Maintenance**: OS upgrades or system updates
- **Learning**: Understanding agent setup and configuration

## Success Metrics

Track these metrics to validate your chosen approach:
- **Recovery Time Objective (RTO)**: How fast can you rebuild?
- **Recovery Point Objective (RPO)**: How much data/config loss is acceptable?
- **Mean Time to Recovery (MTTR)**: Average time for successful rebuild
- **Success Rate**: Percentage of successful rebuilds

## Additional Resources

- **[Complete Rebuild Guide](complete-rebuild/README.md)**: Comprehensive single-phase approach
- **[Partial Rebuild Guide](partial-rebuild/README.md)**: Fast two-phase approach
- **[Alation Developer Portal](https://developer.alation.com/dev/recipes/agent-re-setup)**: Official documentation
- **[Agent APIs Documentation](https://developer.alation.com/dev/reference/listagents)**: API reference

## Disclaimer

> **Important**: This code is provided as an example and without warranty, and should only be used on **non-production** Alation instances first. Alation does not provide support for this code, and it is not covered by standard support agreements. Users are responsible for testing and validating in their specific environments.
