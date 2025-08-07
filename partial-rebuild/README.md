# Partial Agent Rebuild

This directory contains scripts for **partial agent rebuild** - a two-phase approach that pre-installs agent packages in advance and activates them when needed. 

## Timeline Expectations

- **Preparation Time**: 3-5 minutes (run once)
- **Activation Time**: 3-5 minutes (during recovery)

## Two-Phase Architecture

```
Phase 1: Install Agent       Phase 2: Activate Agent
┌─────────────────┐          ┌──────────────────┐
│ ✅ Packages     │          │ ✅ Configuration │
│ ✅ Dependencies │   ────▶  │ ✅ Certificates  │
│ ✅ Auth Service │          │ ✅ Connectivity  │
│ 💤 Dormant      │          │ ✅ Active        │
└─────────────────┘          └──────────────────┘
```

## Available Scripts

### Phase 1: Install Agent (Run Once)
Install agent packages and dependencies without starting services:

| Authentication | Script | Purpose | agent_id Required? |
|---------------|--------|---------|-------------------|
| **Username/Password** | `prepare-core.py` | Prepare system for manual login | ❌ No |
| **SSO** | `prepare-sso.py` | Prepare system for SSO users | ❌ No |

### Phase 2: Agent Activation (Run When Needed)
Configure connectivity and start services:

| Authentication | Script | Purpose | agent_id Required? |
|---------------|--------|---------|-------------------|
| **Username/Password** | `activate-core.py` | Fast agent activation | ✅ Yes |
| **SSO** | `activate-sso.py` | Fast agent activation | ✅ Yes |

## Quick Start Guide

### Step 1: Provision Target Server
1. **Set up Linux server** 
2. **Install dependencies**:
   ```bash
   # For RHEL/CentOS/Amazon Linux
   sudo dnf update -y
   sudo dnf install -y python3 python3-pip
   
   # For Debian/Ubuntu
   sudo apt-get update
   sudo apt-get install -y python3 python3-pip
   
   pip3 install requests toml
   ```

### Step 2: Prepare System

#### For Manual Login Users
```bash
# Edit configuration in prepare-core.py
python3 prepare-core.py
```

#### For SSO Users
```bash
# Edit configuration in prepare-sso.py  
python3 prepare-sso.py
```

**Expected Outcome**: Agent packages installed, Authentication Service ready (if applicable), Hydra service stopped and confirmed dormant.

### Step 3: Test Preparation (Optional but Recommended)
Verify the preparation completed successfully:
```bash
# Check installed binaries
which kratos hydra
which docker

# Verify Hydra service is stopped (expected)
sudo systemctl status hydra.service  # Should show "inactive (dead)"
sudo docker ps  # Should show no agent containers

# Test Hydra commands are available
sudo hydra --version  # Should show version info
```

### Step 4: Document and Store
1. **Record agent configuration** for activation procedures
2. **Store activation scripts** in accessible location
3. **Update Agent** when updated in primary server

## Agent Activation

### Prerequisites
> **⚠️ IMPORTANT**: Only run activation when you're ready to make this agent active. Ensure any existing agent with the same ID is offline to avoid conflicts.

### Activation Steps
1. **Verify no conflicts** (if replacing an existing agent):
   ```bash
   # Check if another agent with same ID is active
   # Replace with your actual primary server if applicable
   ping primary-agent-server
   ssh user@primary-server "sudo systemctl status hydra.service"
   ```

2. **Run activation script**:
   ```bash
   # For manual login
   python3 activate-core.py
   
   # For SSO  
   python3 activate-sso.py
   ```

3. **Monitor activation**:
   - Watch colored log output for progress
   - Verify agent connectivity in Alation UI
   - Test data source connections

**Expected Timeline**: 3-5 minutes for complete activation.

## What Each Phase Does

### Phase 1: System Preparation
```
✅ Authentication Setup
✅ System Detection  
✅ Agent Package Download & Validation
✅ Agent Package Installation
✅ Authentication Service Installation (if enabled)
✅ Post-Install Validation
✅ Service Stop & Dormant State Verification
❌ Connectivity Configuration (SKIPPED)
❌ Certificate Generation (SKIPPED)
❌ Service Startup (SKIPPED)
❌ Agent Registration (SKIPPED)
❌ Connector Sync (SKIPPED)
```

### Phase 2: Agent Activation  
```
❌ Package Installation (ALREADY DONE)
✅ Pre-Activation Validation
✅ Authentication & Token Setup
✅ Connectivity Configuration
✅ Fresh Certificate Generation
✅ Service Startup & Verification
✅ Agent Registration & Connection
✅ Connector Sync (Latest Versions)
✅ Final Validation
```

## Configuration

### System Preparation Scripts
Preparation scripts require minimal configuration (no agent_id needed):

#### Manual Login Configuration
```python
BASE_URL = "https://yourcompany.alationcloud.com"
USERNAME = "your-admin-username"  
PASSWORD = "your-admin-password"
# agent_id NOT required - preparation is agent-agnostic
INSTALL_AUTH_SERVICE = True  # Set to False if not needed
```

#### SSO Configuration
```python
BASE_URL = "https://yourcompany.alationcloud.com"
REFRESH_TOKEN = "your-refresh-token"
API_ACCESS_TOKEN = "your-api-access-token" 
# agent_id NOT required - preparation is agent-agnostic
INSTALL_AUTH_SERVICE = True  # Set to False if not needed
```

### Agent Activation Scripts
Activation scripts require agent_id (preparation scripts do not):

#### Manual Login Configuration
```python
BASE_URL = "https://yourcompany.alationcloud.com"  # Same as preparation script
USERNAME = "your-admin-username"                   # Same as preparation script
PASSWORD = "your-admin-password"                   # Same as preparation script
agent_id = 1                                       # REQUIRED for activation
```

#### SSO Configuration
```python
BASE_URL = "https://yourcompany.alationcloud.com"  # Same as preparation script
REFRESH_TOKEN = "your-refresh-token"               # Same as preparation script
API_ACCESS_TOKEN = "your-api-access-token"         # Same as preparation script
agent_id = 1                                       # REQUIRED for activation
```

## Testing Your Setup

### Safe Testing Procedure
Test your setup without disrupting production:

1. **Test System Preparation**:
   ```bash
   # Run on clean test server
   python3 prepare-{core|sso}.py
   
   # Verify packages installed but services stopped
   sudo systemctl status hydra.service  # Should show "inactive (dead)"
   # Verify Hydra commands work
   sudo hydra --version
   sudo hydra status  # Should show service is stopped
   ```

2. **Test Activation**:
   ```bash
   # Use test agent ID, not production
   python3 activate-{core|sso}.py
   
   # Verify agent connects and syncs
   ```

3. **Document Recovery Time**:
   - Time the activation process
   - Verify all connectors are working
   - Test data source connections

> **⚠️ Never test activation with production agent ID while another agent is running**

## Maintenance

### Regular Maintenance Tasks
1. **Keep system updated**:
   ```bash
   # Update OS packages as required 
   sudo apt-get update && sudo apt-get upgrade
   # OR
   sudo dnf update
   ```

2. **Verify system readiness** (quarterly):
   ```bash
   # Check disk space
   df -h
   
   # Verify binaries still work
   kratos --version
   hydra --version
   docker --version
   ```

3. **Test activation procedure** (semi-annually):
   - Run full test in isolated environment
   - Update documentation if procedures change
   - Train team members on activation steps

### Agent Version Updates
When Alation releases new agent versions:
1. **Update production agents** using normal procedures
2. **Re-run system preparation** to get latest packages
3. **Test activation** to ensure compatibility

## Troubleshooting

### Common Issues During Preparation

**Package Installation Fails**
- Verify internet connectivity and Alation API access
- Check disk space and permissions
- Ensure authentication credentials are valid

**Docker Issues**
- Verify Docker is installed and running: `sudo docker ps`
- Check user permissions for Docker access
- Ensure no port conflicts
- Confirm Hydra commands work: `sudo hydra --version`

### Common Issues During Activation

**Agent Won't Connect**
- Verify no other agent with same ID is active: `sudo hydra status` on other systems
- Check network connectivity to Alation instance
- Validate agent ID configuration
- Ensure Hydra service started properly: `sudo systemctl status hydra.service`

**Certificate Issues**
- Fresh certificates are generated during activation
- Verify system time is synchronized
- Check Alation API access

**Connector Sync Fails** 
- Monitor sync job progress in logs
- Verify data source network access from target server
- Check for changed data source configurations

### Log Analysis
Both phases provide detailed colored logging:
- **Blue**: Normal progress messages
- **Yellow**: Warnings that don't stop execution  
- **Red**: Errors requiring attention

## API Workflow Details

The partial rebuild approach uses the same Alation Agent APIs as complete rebuild, but splits them across two phases for optimal speed during activation.

### Authentication Methods

#### Manual Login Authentication (`prepare-core.py` & `activate-core.py`)
- **Preparation**: Generates temporary tokens for system setup, then revokes them
- **Activation**: Generates fresh temporary tokens for agent configuration, then revokes them
- **Security**: Each phase uses independent token lifecycle for maximum security

#### SSO Authentication (`prepare-sso.py` & `activate-sso.py`) 
- **Preparation**: Uses pre-generated tokens for system setup
- **Activation**: Uses same pre-generated tokens for agent configuration
- **Management**: Tokens remain active for manual management through Alation UI

### Phase 1: System Preparation API Workflow

**Scripts**: `prepare-core.py`, `prepare-sso.py`

#### Authentication (Manual Login Only)
1. **Generate Refresh Token**: `POST /integration/v1/createRefreshToken/`
2. **Generate Access Token**: `POST /integration/v1/createAPIAccessToken/`

#### System Preparation
3. **Get Installer Info**: `GET /integration/v1/agent/installers/{flavor}/`
   - Retrieves latest version and SHA256 checksum
   - `{flavor}` = `debian` or `rhel` based on system detection

4. **Download Installer**: `GET /integration/v1/agent/installers/{flavor}/latest/`
   - Downloads binary installer package (tar.gz)
   - Validated against SHA256 checksum

#### Authentication Service (Optional)
5. **Get Auth Service Info**: `GET /integration/v1/agent/addons/auth/`
   - Retrieves Authentication Service version and checksum (if `INSTALL_AUTH_SERVICE = True`)

6. **Download Auth Service**: `GET /integration/v1/agent/addons/auth/latest/`
   - Downloads Authentication Service addon package (if enabled)

#### Cleanup
7. **Revoke Tokens**: `POST /integration/v1/revokeAPIAccessTokens/` (manual login only)
   - Automatic security cleanup after preparation

**Phase 1 API Count**: Manual Login = 7 calls, SSO = 4 calls

### Phase 2: Agent Activation API Workflow

**Scripts**: `activate-core.py`, `activate-sso.py`

#### Authentication (Manual Login Only)
1. **Generate Refresh Token**: `POST /integration/v1/createRefreshToken/`
2. **Generate Access Token**: `POST /integration/v1/createAPIAccessToken/`

#### Agent Configuration
3. **Get Connectivity Endpoint**: `GET /integration/v1/agent/endpoint/`
   - Retrieves proxy endpoint for agent connectivity
   - Used to configure `/etc/hydra/hydra.toml`

4. **Sign Certificate**: `POST /integration/v1/agent/{agent_id}/sign_certificate/`
   - Submits Certificate Signing Request (CSR) generated by Kratos
   - Returns signed certificate chain for secure communication

#### Agent Activation
5. **Check Connection**: `GET /integration/v1/agent/{agent_id}/`
   - Polls every 5 seconds until `is_connected = true`
   - Maximum 2 minutes timeout (24 attempts)

6. **Initiate Resync**: `POST /integration/v1/agent/{agent_id}/resync/`
   - Triggers connector installation and metadata refresh
   - Returns `job_id` for monitoring

7. **Monitor Resync**: `GET /api/v1/bulk_metadata/job/?id={job_id}`
   - Polls every 5 seconds until status is `successful` or `failed`
   - Maximum 5 minutes timeout (60 attempts)

#### Cleanup
8. **Revoke Tokens**: `POST /integration/v1/revokeAPIAccessTokens/` (manual login only)
   - Automatic security cleanup after activation

**Phase 2 API Count**: Manual Login = 8 calls, SSO = 5 calls

### Total API Usage Summary

| Authentication | Phase 1 Calls | Phase 2 Calls | Total Calls |
|---------------|---------------|---------------|-------------|
| **Manual Login** | 7 | 8 | 15 |
| **SSO** | 4 | 5 | 9 |


### Base URL Format
All endpoints are relative to your Alation Cloud Service instance:
```
https://your-instance.alationcloud.com
```

## Alternative: Complete Rebuild

The **[complete rebuild approach](../complete-rebuild/)** offers a single-script option that handles everything in one execution.

| Method | Time | Description |
|--------|------|-------------|
| **Partial** | 3-5 min | Two-phase: prepare once, activate when needed |
| **Complete** | 3-5 min | Single script handles everything in one execution |

## Additional Resources

- [Main Repository Guide](../README.md)
- [Complete Rebuild Alternative](../complete-rebuild/README.md)
- [Alation Developer Portal](https://developer.alation.com/dev/recipes/agent-re-setup)