# Alation Agent Re-Setup Scripts

This repository contains Python scripts to automate the installation and configuration of Alation Agents on new servers. These scripts use the Alation Agent APIs to download, install, and configure an Alation Agent, connect it to Alation Cloud, and reinstall its connectors.

## 📋 Overview

This process allows you to quickly replicate an Agent's setup to a new server, providing flexibility for maintenance, scaling, or disaster recovery scenarios.

## ⚠️ Critical Prerequisites

> **Before beginning the agent rebuild process on the new server, the original agent server must be shut down or taken offline.** Having both the old and new agent online simultaneously will prevent proper connector installation and configuration transfer.

### Key Considerations
- The Agent itself is stateless - all configurations are maintained within Alation
- **Agent ID Conflict**: Only one agent per Agent ID can be active at a time
- The original agent must be offline before setting up the replacement

## 🚀 Two-Script Approach

This repository provides **two separate scripts** to reduce complexity:

### Choose Your Script:

| Authentication Method | Script to Use | Configuration Required |
|----------------------|---------------|----------------------|
| **Username/Password** | `agent-rebuild-core.py` | BASE_URL, USERNAME, PASSWORD, agent_id |
| **SSO (SAML, OIDC, etc.)** | `agent-rebuild-sso.py` | BASE_URL, REFRESH_TOKEN, API_ACCESS_TOKEN, agent_id |

## 📁 Script Selection Guide

### Use `agent-rebuild-core.py` if:
- You use username/password authentication
- You log into Alation directly (not through SSO)
- You can provide Server Admin credentials

### Use `agent-rebuild-sso.py` if:
- You use SSO authentication (SAML, OIDC, etc.)
- You cannot provide username/password directly
- You can generate tokens through the Alation UI

## 🔧 Prerequisites

### System Requirements
- **Alation Cloud Service Instance** (on-premise instances don't need agents)
- **Server Admin access** in Alation
- **Linux server** that can access all required data sources
- **Python 3.7+** with `requests` and `toml` libraries
- **Network access** to the same data sources as the original agent

### Authentication Requirements
- **For Manual Login**: Server Admin username and password
- **For SSO Users**: Pre-generated refresh token and API access token from Alation UI

## 📝 Setup Instructions

### 1. Gather Information

You'll need:
- Your Alation instance URL (e.g., `https://yourBaseUrl.alationcloud.com`)
- Authentication credentials (username/password OR SSO tokens)
- The Alation-assigned Agent ID (found in the agent's URL in Alation UI)

### 2. Prepare the New Server

#### 2.1. Connect to the Linux Server
```bash
# SSH or use Systems Manager Session Manager
ssh user@your-new-server.com
```

#### 2.2. Update System and Install Python
```bash
# For RHEL/CentOS/Amazon Linux
sudo dnf update -y
sudo dnf install -y python3 python3-pip

# For Debian/Ubuntu
sudo apt-get update
sudo apt-get install -y python3 python3-pip
```

#### 2.3. Install Required Python Libraries
```bash
pip3 install requests toml
```

#### 2.4. Verify Installation
```bash
python3 -c "import requests, toml; print('Python libraries installed successfully')"
```

> 💡 **Note**: Docker installation is not required as a prerequisite. The Alation Agent installation process will automatically install and configure Docker.

### 3. Configure Your Script

#### For Manual Login Users (`agent-rebuild-core.py`)

1. **Download the script** to your new server
2. **Edit the configuration** section:
```python
BASE_URL = "https://yourBaseUrl.alationcloud.com"
USERNAME = "your-admin-username"
PASSWORD = "your-admin-password"
agent_id = 1  # Your agent identifier
```

#### For SSO Users (`agent-rebuild-sso.py`)

1. **Generate tokens** from Alation UI:
   - Log into your Alation instance through your browser
   - Navigate to your user profile settings
   - Generate a Refresh Token and API Access Token

2. **Download the script** to your new server
3. **Edit the configuration** section:
```python
BASE_URL = "https://yourBaseUrl.alationcloud.com"
REFRESH_TOKEN = "your-refresh-token-here"
API_ACCESS_TOKEN = "your-api-access-token-here"
agent_id = 1  # Your agent identifier
```

### 4. Execute the Script

#### 4.1. Make the Script Executable
```bash
chmod +x agent-rebuild-core.py
# OR
chmod +x agent-rebuild-sso.py
```

#### 4.2. Run the Script
```bash
python3 agent-rebuild-core.py
# OR
python3 agent-rebuild-sso.py
```

**Execution Time**: Approximately 2-3 minutes. The script provides detailed colored logging throughout the process.

## 📊 What the Scripts Do

### API Workflow (Both Scripts)
The scripts use these Alation APIs in sequence:

1. **Authentication** (differs between scripts)
   - Manual: `POST /integration/v1/createRefreshToken/` → `POST /integration/v1/createAPIAccessToken/`
   - SSO: Uses pre-generated tokens

2. **Agent Installation**
   - `GET /integration/v1/agent/installers/{flavor}/` - Get installer info
   - `GET /integration/v1/agent/installers/{flavor}/latest/` - Download installer
   - Install packages using system package manager

3. **Agent Configuration**
   - `GET /integration/v1/agent/endpoint/` - Get connectivity endpoint
   - Update agent configuration files
   - `POST /integration/v1/agent/{agent_id}/sign_certificate/` - Generate certificates

4. **Service Installation**
   - `GET /integration/v1/agent/addons/auth/` - Get auth service info
   - `GET /integration/v1/agent/addons/auth/latest/` - Download auth service
   - Install authentication service

5. **Agent Activation**
   - `GET /integration/v1/agent/{agent_id}/` - Check connection status
   - `POST /integration/v1/agent/{agent_id}/resync/` - Resync connectors
   - `GET /api/v1/bulk_metadata/job/` - Monitor resync progress

6. **Cleanup**
   - Manual: `POST /integration/v1/revokeAPIAccessTokens/` - Revoke tokens
   - SSO: No token revocation (managed externally)

### Security Features
- **SHA256 checksum validation** for all downloaded packages
- **Temporary file handling** with secure cleanup
- **Certificate-based authentication** for agent communication
- **Automatic token revocation** (manual login only)
- **Package cleanup** on installation failure

## ✅ Validation Steps

### 5.1. Check Docker Containers
```bash
sudo docker ps
```

Expected output should show containers for:
- `agent` - Main agent container
- `proxy` - Reverse proxy
- `application_gateway` - Application gateway
- `auth` - Authentication service
- `connector_*` - One container per connector

### 5.2. Test Connection in Alation
1. Open Alation → **Data Sources**
2. Select a data source that uses the agent
3. Click **ellipses** (⋮) → **Settings**
4. Click **General Settings** → **Test Connection**

> 💡 **Tip**: Test multiple data sources to ensure all connectors are working properly.

## 🧹 Cleanup

After validating the new agent, secure your credentials:

### Option 1: Secure File Deletion
```bash
# Overwrite file with random data
sudo shred -vfz -n 3 agent-rebuild-*.py
# Remove the file
rm agent-rebuild-*.py
```

### Option 2: Simple Deletion
```bash
rm agent-rebuild-*.py
```

### Option 3: Remove Credentials Only
```bash
# Edit the file to replace credentials with placeholders
nano agent-rebuild-*.py

# Replace actual values with:
BASE_URL = "<AlationInstanceURL>"
USERNAME = "<AlationServerAdminUserName>"
PASSWORD = "<AlationServerAdminPassword>"
# OR for SSO
REFRESH_TOKEN = "<YourRefreshToken>"
API_ACCESS_TOKEN = "<YourAPIAccessToken>"
```

## 📚 Additional Resources

- [Alation Developer Portal](https://developer.alation.com/dev/recipes/agent-re-setup)
- [Agent APIs Documentation](https://developer.alation.com/dev/reference/listagents)

## ⚖️ Disclaimer

> **Important**: This code is provided as an example and is not intended for use on production Alation instances without thorough review and testing. Alation does not provide support for this code, and it is not covered by the Alation subscription and its associated support agreement. Alation is not responsible for any harm it may cause, including the unrecoverable corruption of a catalog instance.
