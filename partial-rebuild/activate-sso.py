#!/usr/bin/env python3

##########################################################################################
# Name: Activate Agent System (SSO Version)
# Description: Phase 2 of partial rebuild solution. Quickly configures and activates
# a prepared Alation Agent system. Must be run after prepare-sso.py
# has prepared the standby server.
#
# Author: Alation
# Alation Catalog Version: 2023.3.2
#
# Prerequisites:
# 1. prepare-sso.py must have been run successfully on this server
# 2. Primary agent must be completely offline before running this script
# 3. You must be a Server Admin user in Alation
# 4. You must use SSO authentication and have pre-generated tokens
#
# How to obtain required tokens for SSO users:
# 1. Log into your Alation instance through your browser
# 2. Navigate to your user profile settings
# 3. Generate a Refresh Token and API Access Token
# 4. Update the REFRESH_TOKEN and API_ACCESS_TOKEN variables below
#
# Notice of Usage, Rights, and Alation Responsibility:
# This code is provided as an example and is not intended for use on production Alation
# instances. It should only be used on non-production Alation instances. Alation does
# not provide support for the code, and it is not covered by the Alation subscription
# and its associated support agreement.  Alation is not responsible for any harm
# it may cause, including the unrecoverable corruption of a catalog instance.
##########################################################################################

# ==================================================================================
# IMPORTS AND DEPENDENCIES
# ==================================================================================

# Standard library imports for system operations
import json           # JSON data handling
import logging        # Colored console logging
import subprocess     # Running system commands
import sys            # System-specific parameters
import time           # Sleep and timing functions

# Third-party imports for API and configuration
import requests       # HTTP API client
import toml           # TOML configuration file parsing

# ==================================================================================
# CONFIGURATION VARIABLES
# ==================================================================================
# IMPORTANT: Update these values with your Alation instance details before running
# NOTE: BASE_URL, REFRESH_TOKEN, API_ACCESS_TOKEN should match prepare-sso.py
# agent_id is REQUIRED for activation (not needed during dormant installation)

# Your Alation Cloud Service instance URL (e.g., https://yourcompany.alationcloud.com)
BASE_URL = "<AlationInstanceURL>"

# SSO Authentication Tokens (generate these through the Alation UI)
# These tokens must be obtained manually from your Alation instance:
# 1. Log into your Alation instance through your browser
# 2. Navigate to your user profile settings
# 3. Generate a Refresh Token and API Access Token
REFRESH_TOKEN = "<YourRefreshToken>"
API_ACCESS_TOKEN = "<YourAPIAccessToken>"

# Agent identifier for the agent you want to activate
# This MUST be the same agent_id used in install-dormant-sso.py
agent_id = 1


# ==================================================================================
# LOGGING CONFIGURATION
# ==================================================================================

class ColoredFormatter(logging.Formatter):
    """
    Custom logging formatter that adds color coding to log messages based on their level.
    
    Colors:
    - DEBUG/INFO: Cyan (blue)
    - WARNING: Yellow
    - ERROR: Red
    - CRITICAL: Bold Red
    """
    # ANSI color codes for terminal output
    blue = "\x1b[36m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    
    # Log message format template
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    
    # Color mapping for different log levels
    FORMATS = {
        logging.DEBUG: blue + log_format + reset,
        logging.INFO: blue + log_format + reset,
        logging.WARNING: yellow + log_format + reset,
        logging.ERROR: red + log_format + reset,
        logging.CRITICAL: bold_red + log_format + reset
    }

    def format(self, record):
        """Format log record with appropriate color based on log level."""
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


# Initialize logger with colored output
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Configure console handler with colored formatter
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
handler.setFormatter(ColoredFormatter())
logger.addHandler(handler)


# ==================================================================================
# MAIN EXECUTION LOGIC - AGENT ACTIVATION PHASE
# ==================================================================================

# Use a persistent session for all HTTP requests to maintain authentication
with requests.Session() as session:
    try:
        logger.info("### STARTING AGENT ACTIVATION (WARM STANDBY FAILOVER) ###")
        logger.info("### ⚠️  CRITICAL: Ensure primary agent is completely offline before proceeding! ###")
        logger.info("### This script activates a dormant agent prepared by install-dormant-sso.py ###")
        
        # ======================================================================
        # PRE-ACTIVATION VALIDATION
        # ======================================================================
        
        logger.info("### Performing pre-activation validation... ###")
        # Verify that dormant installation was completed successfully
        # Check for presence of required binaries
        if not subprocess.run(["which", "kratos"], capture_output=True).returncode == 0:
            raise Exception("Kratos binary not found. Did you run install-dormant-sso.py first?")
        
        if not subprocess.run(["which", "hydra"], capture_output=True).returncode == 0:
            raise Exception("Hydra binary not found. Did you run install-dormant-sso.py first?")
            
        if not subprocess.run(["which", "docker"], capture_output=True).returncode == 0:
            raise Exception("Docker not found. Did you run install-dormant-sso.py first?")
        
        # Check that services are not already running (expected for dormant state)
        try:
            result = subprocess.run(["sudo", "systemctl", "is-active", "hydra"], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip() == "active":
                logger.warning("### Hydra service is already active - this may indicate the agent is already running ###")
        except Exception:
            pass  # Service check is informational only
            
        logger.info("### Pre-activation validation complete ###")
        
        # ======================================================================
        # PHASE 1: SSO AUTHENTICATION SETUP
        # ======================================================================
        
        logger.info("### Using SSO authentication tokens for activation... ###")
        # Use pre-generated tokens for SSO authentication
        # These tokens were manually generated through the Alation UI by the user
        refresh_token = REFRESH_TOKEN
        access_token = API_ACCESS_TOKEN
        logger.info("### SSO authentication tokens loaded ###")

        # Configure session to use access token for all subsequent API calls
        session.headers.update({"TOKEN": access_token})

        # ======================================================================
        # PHASE 2: AGENT CONFIGURATION
        # ======================================================================
        
        logger.info("### Retrieving connectivity endpoint... ###")
        # Get the agent connectivity endpoint from Alation
        # This endpoint will be used to configure the agent's proxy settings
        agent_dns = session.get(
            f"{BASE_URL}/integration/v1/agent/endpoint/",
        ).json()["endpoint"]
        logger.info("### Connectivity endpoint retrieved is {} ###".format(agent_dns))

        logger.info("### Updating agent configuration... ###")
        # Read the current Hydra configuration file
        raw = subprocess.check_output(["sudo", "cat", "/etc/hydra/hydra.toml"], encoding="utf8")
        config = toml.loads(raw)
        
        # Update the proxy address with the connectivity endpoint
        config['proxy'] = {'address': agent_dns}
        
        # Write the updated configuration to a temporary file, then move it into place
        # This ensures atomic updates and prevents corruption of the config file
        with open('hydra_updated.toml', 'w') as f:
            toml.dump(config, f)
        subprocess.run(["sudo", "mv", "hydra_updated.toml", "/etc/hydra/hydra.toml"])
        logger.info("### Done updating agent configuration ###")

        # ======================================================================
        # PHASE 3: CERTIFICATE MANAGEMENT
        # ======================================================================
        
        logger.info("### Generating & installing fresh certificate for the Alation Agent... ###")
        # Generate a Certificate Signing Request (CSR) using Kratos
        # This CSR will be sent to Alation for signing to establish secure communication
        csr = subprocess.check_output(['sudo', 'kratos', 'certs', 'gen'], encoding="utf8").strip()
        
        # Send CSR to Alation for signing and receive the signed certificate chain
        agent_certificate = session.post(
            f"{BASE_URL}/integration/v1/agent/{agent_id}/sign_certificate/",
            json={"CSR": csr}
        ).json()["chain"]
        
        # Install the signed certificate using Kratos
        subprocess.run(["sudo", "kratos", "certs", "install"], 
                      input=agent_certificate, universal_newlines=True)
        logger.info("### Done generating & installing fresh certificate ###")

        # ======================================================================
        # PHASE 4: AGENT STARTUP AND CONNECTIVITY
        # ======================================================================
        
        logger.info("### Starting Agent services... ###")
        # Start the Hydra service to apply all configuration changes and activate the agent
        subprocess.run(["sudo", "hydra", "start"], stdout=subprocess.DEVNULL)
        subprocess.run(["sudo", "systemctl", "enable", "hydra"])  # Enable for auto-start on boot
        
        # Verify service started successfully
        try:
            result = subprocess.run(["sudo", "systemctl", "is-active", "hydra"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip() == "active":
                logger.info("### ✅ Hydra service started successfully ###")
            else:
                logger.warning("### ⚠️  Hydra service may not be fully active yet ###")
        except Exception as e:
            logger.warning(f"### Could not verify Hydra service status: {e} ###")
            
        logger.info("### Done starting Agent services ###")

        logger.info("### Waiting for the Agent to connect... ###")
        # Poll the agent status until it shows as connected
        connection_attempts = 0
        max_connection_attempts = 24  # 2 minutes with 5-second intervals
        
        while connection_attempts < max_connection_attempts:
            try:
                # Check the agent connection status via API
                is_connected = session.get(
                    f"{BASE_URL}/integration/v1/agent/{agent_id}/",
                ).json()["is_connected"]
                
                if not is_connected:
                    connection_attempts += 1
                    logger.warning(f"### Agent is not connected yet (attempt {connection_attempts}/{max_connection_attempts})... ###")
                    logger.warning("### Checking again in 5 seconds ###")
                    time.sleep(5)
                    continue
                else:
                    logger.info("### The Agent is now connected! ###")
                    break
            except Exception as e:
                connection_attempts += 1
                logger.warning(f"### Connection check failed (attempt {connection_attempts}/{max_connection_attempts}): {e} ###")
                time.sleep(5)
        else:
            raise Exception(f"Agent failed to connect after {max_connection_attempts} attempts")

        # ======================================================================
        # PHASE 5: AGENT RESYNCHRONIZATION
        # ======================================================================
        
        logger.info("### Resyncing Agent to install latest connectors... ###")
        # Initiate agent resync to reinstall connectors and update metadata
        # This ensures we get the latest connector versions
        res = session.post(
            f"{BASE_URL}/integration/v1/agent/{agent_id}/resync/",
            headers={"TOKEN": access_token},
        )
        job_id = res.json()["job_id"]
        
        logger.info("### Waiting on Agent resync to complete... ###")
        # Monitor the resync job until completion
        sync_attempts = 0
        max_sync_attempts = 60  # 5 minutes with 5-second intervals
        
        while sync_attempts < max_sync_attempts:
            try:
                # Check the status of the resync job
                res = requests.get(
                    f"{BASE_URL}/api/v1/bulk_metadata/job/",
                    params={"id": job_id},
                    headers={"TOKEN": access_token}
                ).json()
                status = res["status"]
                
                if status == "running":
                    sync_attempts += 1
                    logger.info(f"Agent resync in progress (attempt {sync_attempts}/{max_sync_attempts}). Sleeping for 5 seconds...")
                    time.sleep(5)
                    continue
                elif status != "successful":
                    raise Exception("Agent resync job failed {}".format(json.dumps(res)))
                else:
                    logger.info("### Agent resync completed successfully! ###")
                    break
            except Exception as e:
                sync_attempts += 1
                logger.warning(f"### Resync check failed (attempt {sync_attempts}/{max_sync_attempts}): {e} ###")
                time.sleep(5)
        else:
            raise Exception(f"Agent resync failed to complete after {max_sync_attempts} attempts")

        # ======================================================================
        # ACTIVATION COMPLETE
        # ======================================================================
        
        logger.info("### AGENT ACTIVATION COMPLETE! ###")
        logger.info("### Standby agent is now active and fully operational ###")
        logger.info("### Key phases completed: ###")
        logger.info("###   ✅ Pre-activation validation ###")
        logger.info("###   ✅ SSO authentication setup ###")
        logger.info("###   ✅ Connectivity configuration ###") 
        logger.info("###   ✅ Fresh certificate generation and installation ###")
        logger.info("###   ✅ Agent service startup ###")
        logger.info("###   ✅ Agent connection establishment ###")
        logger.info("###   ✅ Connector synchronization (latest versions) ###")
        logger.info("### ###")
        logger.info("### Next steps: ###")
        logger.info("###   1. Verify agent connectivity in Alation UI ###")
        logger.info("###   2. Test data source connections ###")
        logger.info("###   3. Monitor agent performance and logs ###")
        logger.info("### ###")
        logger.info("### Agent failover completed successfully! ###")
        
    except Exception:
        # ======================================================================
        # ERROR HANDLING
        # ======================================================================
        
        logger.exception("### Failed to activate agent ###")
        logger.error("### Agent activation failed - standby remains dormant ###")
        logger.error("### Check logs above for specific error details ###")
        logger.error("### You may need to: ###")
        logger.error("###   1. Verify primary agent is completely offline ###")
        logger.error("###   2. Check network connectivity to Alation ###")
        logger.error("###   3. Validate SSO authentication tokens ###")
        logger.error("###   4. Ensure dormant installation completed successfully ###")
        
    else:
        # ======================================================================
        # SUCCESS COMPLETION
        # ======================================================================
        
        logger.info("### Agent activation completed successfully ###")
        
    finally:
        # ======================================================================
        # CLEANUP - NO TOKEN REVOCATION FOR SSO
        # ======================================================================
        
        logger.info("### SSO tokens not revoked (managed externally) ###")
        # Note: SSO tokens are managed externally and should not be revoked by this script
        # The user is responsible for managing these tokens through the Alation UI
        # No User ID required - tokens remain active for the user to manage manually