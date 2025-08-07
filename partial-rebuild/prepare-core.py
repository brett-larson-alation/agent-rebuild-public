#!/usr/bin/env python3

##########################################################################################
# Name: Prepare Agent System (Manual Login Version)
# Description: Phase 1 of partial rebuild solution. Installs Alation Agent packages
# and dependencies but leaves services dormant. Use activate-core.py to complete
# the activation during agent setup.
#
# Author: Alation
# Alation Catalog Version: 2023.3.2
#
# Catalog requirements:
# 1. You must have an Alation Cloud Service instance of Alation (on-premise instances have no need for the Agent).
# 2. You must be a Server Admin user in Alation to run this script.
# 3. You must use username/password authentication (NOT SSO).
#
# For SSO users: Use prepare-sso.py instead of this script.
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
import glob           # File pattern matching
import hashlib        # SHA256 checksum validation
import json           # JSON data handling
import logging        # Colored console logging
import shutil         # System utility functions
import subprocess     # Running system commands
import sys            # System-specific parameters
import tempfile       # Secure temporary file handling
import time           # Sleep and timing functions

# Third-party imports for API and configuration
import requests       # HTTP API client
import toml           # TOML configuration file parsing

# ==================================================================================
# CONFIGURATION VARIABLES
# ==================================================================================
# IMPORTANT: Update these values with your Alation instance details before running

# Your Alation Cloud Service instance URL (e.g., https://yourcompany.alationcloud.com)
BASE_URL = "<AlationInstanceURL>"

# Server Admin credentials for username/password authentication
# These will be used to generate temporary API tokens
USERNAME = "<AlationServerAdminUserName>"
PASSWORD = "<AlationServerAdminPassword>"

# NOTE: agent_id is NOT required for dormant installation
# The agent_id is only needed during activation (activate-core.py)
# since dormant installation doesn't connect to or configure specific agents

# Authentication Service installation (optional)
# Set to True if your data sources require advanced authentication methods
# Set to False for basic installations or if not needed
INSTALL_AUTH_SERVICE = False


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
# SYSTEM UTILITY FUNCTIONS
# ==================================================================================

def post_install_checks():
    """
    Performs post-installation validation to ensure the Alation Agent and its 
    dependencies have been installed correctly on the system.
    
    Checks:
    - Kratos and Hydra binaries are available in PATH
    - Docker is installed and accessible
    - Docker daemon is running
    
    Raises:
        SystemExit: If any required component is missing or not functioning
    """
    # Check if Alation Agent binaries are installed and accessible
    if not shutil.which("kratos") or not shutil.which("hydra"):
        logger.error("The Alation Agent does not appear to have been installed correctly")
        sys.exit(1)
    
    # Verify Docker is installed
    if not shutil.which("docker"):
        logger.error("Docker was not found in the current path")
        sys.exit(1)
    
    # Test if Docker daemon is running by attempting to get stats
    if subprocess.call(["sudo", "docker", "stats", "--no-stream"], stdout=subprocess.DEVNULL) != 0:
        logger.error("The Docker daemon does not appear to be running")
        sys.exit(1)


def linux_flavor():
    """
    Determines the flavor of the current Linux distribution by checking for
    the presence of specific package managers.
    
    Returns:
        str: 'debian' for Debian-based distros, 'rhel' for Red Hat-based distros
        
    Raises:
        Exception: If the Linux distribution is not recognized
    """
    # Check for Debian-based distributions (Ubuntu, Debian, etc.)
    if shutil.which("apt-get"):
        return "debian"
    # Check for Red Hat-based distributions (RHEL, CentOS, Fedora, etc.)
    elif shutil.which("yum"):
        return "rhel"
    
    # Unsupported distribution
    raise Exception("Unrecognized Linux distribution flavor")


def linux_flavor_pkg_ext():
    """
    Determines the expected file extension for packages on the current Linux distribution.
    
    Returns:
        str: 'deb' for Debian-based distros, 'rpm' for Red Hat-based distros
    """
    if linux_flavor() == "debian":
        return "deb"  # Debian package format
    return "rpm"       # Red Hat package format


def linux_flavor_pkg_manager():
    """
    Determines the package manager command for the current Linux distribution.
    
    Returns:
        str: 'apt-get' for Debian-based distros, 'yum' for Red Hat-based distros
    """
    if linux_flavor() == "debian":
        return "apt-get"  # Debian package manager
    return "yum"          # Red Hat package manager


# ==================================================================================
# MAIN EXECUTION LOGIC - DORMANT INSTALLATION PHASE
# ==================================================================================

# Use a persistent session for all HTTP requests to maintain authentication
with requests.Session() as session:
    # Initialize variables to None so they're accessible in the finally block
    refresh_token = None
    user_id = None
    
    try:
        logger.info("### STARTING DORMANT AGENT INSTALLATION (WARM STANDBY PREPARATION) ###")
        logger.info("### This script installs packages but leaves services dormant ###")
        logger.info("### Use activate-agent-core.py to complete activation during failover ###")
        
        # ======================================================================
        # PHASE 1: AUTHENTICATION AND TOKEN GENERATION
        # ======================================================================
        
        logger.info("### Generating refresh token... ###")
        # Create a refresh token using Server Admin credentials
        # This is the first step in the authentication process for manual login users
        response = session.post(
            f"{BASE_URL}/integration/v1/createRefreshToken/",
            json={"username": USERNAME, "password": PASSWORD, "name": "agent-dormant"}
        )
        
        # Check if the API request was successful (200 OK or 201 Created)
        if response.status_code not in [200, 201]:
            logger.error(f"### Failed to create refresh token. HTTP Status: {response.status_code} ###")
            logger.error(f"### Response text: {response.text} ###")
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")
        
        res = response.json()
        
        # Check if the response contains the expected keys
        if "refresh_token" not in res or "user_id" not in res:
            logger.error(f"### API response missing expected keys. Response: {res} ###")
            raise Exception(f"Invalid API response structure: {res}")
        
        refresh_token = res["refresh_token"]
        user_id = res["user_id"]
        logger.info("### Done generating refresh token ###")

        logger.info("### Generating access token... ###")
        # Convert refresh token to API access token for subsequent requests
        # This token will be used for all API calls throughout the script
        access_token = session.post(
            f"{BASE_URL}/integration/v1/createAPIAccessToken/",
            json={"refresh_token": refresh_token, "user_id": user_id}
        ).json()["api_access_token"]
        logger.info("### Done generating access token ###")

        # Configure session to use access token for all subsequent API calls
        # This eliminates the need to pass the token in each individual request
        session.headers.update({"TOKEN": access_token})

        # ======================================================================
        # PHASE 2: SYSTEM DETECTION AND INSTALLER PREPARATION
        # ======================================================================
        
        # Detect the Linux distribution to determine the correct installer package
        flavor = linux_flavor()
        
        logger.info("### Retrieving latest Alation Agent installer version and checksum... ###")
        # Get information about the latest agent installer for this Linux flavor
        # This includes both version information and security checksum for validation
        installers = session.get(
            f"{BASE_URL}/integration/v1/agent/installers/{flavor}/"
        ).json()
        latest_installer_version = installers["latest"]["version"]
        latest_installer_checksum = installers["latest"]["checksum"]
        logger.info("### Done retrieving latest Alation Agent installer version and checksum ###")

        # ======================================================================
        # PHASE 3: AGENT INSTALLER DOWNLOAD AND VALIDATION
        # ======================================================================
        
        logger.info(f"### Downloading latest Alation Agent version {latest_installer_version}... ###")
        # Use a temporary file to securely download and validate the installer
        with tempfile.NamedTemporaryFile(mode="w+b", prefix="alation-agent-", suffix=".tar.gz") as tmp_file:
            # Download the latest agent installer package
            res = session.get(
                f"{BASE_URL}/integration/v1/agent/installers/{flavor}/latest/",
            )
            res.raise_for_status()  # Raise exception for HTTP errors
            tmp_file.write(res.content)
            tmp_file.seek(0)  # Reset file pointer for reading
            logger.info("### Done downloading latest Alation Agent ###")

            logger.info("### Validating integrity of downloaded Alation Agent installer... ###")
            # Compute SHA256 checksum of downloaded file for security validation
            sha256_checksum = hashlib.sha256(tmp_file.read()).hexdigest()
            
            # Compare computed checksum with expected checksum from Alation
            if latest_installer_checksum != sha256_checksum:
                raise Exception("The SHA256 checksum of the downloaded installer is "
                                "not equal to the precomputed checksum from Alation")
            logger.info("### Done validating integrity of downloaded Alation Agent installer ###")

            # ======================================================================
            # PHASE 4: AGENT INSTALLATION
            # ======================================================================
            
            logger.info(f"### Installing the latest Alation Agent version {latest_installer_version}... ###")
            
            # Get system-specific package information
            flavor_pkg_ext = linux_flavor_pkg_ext()        # .deb or .rpm
            flavor_pkg_manager = linux_flavor_pkg_manager() # apt-get or yum
            
            # Extract and install agent packages in a temporary directory
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Extract the downloaded tar.gz file
                subprocess.run(["sudo", "tar", "-xzf", tmp_file.name, "-C", tmp_dir], 
                             stdout=subprocess.DEVNULL)
                
                # Locate the extracted package files
                alation_container_service_archive = \
                    glob.glob(f"{tmp_dir}/ocf-agent/alation-container-service*.{flavor_pkg_ext}")[0]
                ocf_agent_archive = glob.glob(f"{tmp_dir}/ocf-agent/ocf-agent*.{flavor_pkg_ext}")[0]
                
                # Install both packages using the system package manager
                subprocess.run(
                    ["sudo", flavor_pkg_manager, "install", "-y", 
                     alation_container_service_archive, ocf_agent_archive],
                    stdout=subprocess.DEVNULL)
            logger.info("### Done installing latest Alation Agent ###")

        # Verify that the installation completed successfully
        logger.info("### Performing post-install checks...")
        post_install_checks()
        logger.info("### Done performing post-install checks ###")

        # ======================================================================
        # PHASE 5: AUTHENTICATION SERVICE INSTALLATION (OPTIONAL)
        # ======================================================================
        
        if INSTALL_AUTH_SERVICE:
            logger.info("### Installing Authentication Service (optional component)... ###")
            logger.info("### Retrieving the latest version of the Authentication Service and its checksum... ###")
            # Get information about the latest Authentication Service addon
            # This service is required for proper agent authentication with various data sources
            available_auth_service_versions = session.get(
                f"{BASE_URL}/integration/v1/agent/addons/auth/"
            ).json()
            latest_auth_service_version = available_auth_service_versions["latest"]["version"]
            latest_auth_service_checksum = available_auth_service_versions["latest"]["checksum"]
            logger.info("### Done retrieving the latest version of the Authentication Service and its checksum ###")

            logger.info(f"### Downloading latest Authentication Service version {latest_auth_service_version}... ###")
            # Use a temporary file to securely download the Authentication Service
            with tempfile.NamedTemporaryFile(mode="w+b", prefix="authentication-service-", suffix=".tar.gz") as tmp_file:
                # Download the latest Authentication Service addon
                res = session.get(
                    f"{BASE_URL}/integration/v1/agent/addons/auth/latest/",
                )
                res.raise_for_status()  # Raise exception for HTTP errors
                tmp_file.write(res.content)
                tmp_file.seek(0)  # Reset file pointer for reading
                logger.info("### Done downloading latest Authentication Service ###")

                logger.info("### Validating integrity of downloaded Authentication Service... ###")
                # Compute SHA256 checksum for security validation
                sha256_checksum = hashlib.sha256(tmp_file.read()).hexdigest()
                
                # Verify the checksum matches the expected value from Alation
                if latest_auth_service_checksum != sha256_checksum:
                    raise Exception("The SHA256 checksum of the downloaded Authentication Service is "
                                    "not equal to the precomputed checksum from Alation")
                logger.info("### Done validating integrity of downloaded Authentication Service ###")

                logger.info(f"### Installing the latest Authentication Service version {latest_auth_service_version}... ###")
                # Install the Authentication Service addon using Kratos
                subprocess.run(["sudo", "kratos", "addons", "install", "auth", tmp_file.name])
                logger.info("### Done installing latest Authentication Service ###")
        else:
            logger.info("### Skipping Authentication Service installation (disabled in configuration) ###")

        # ======================================================================
        # PHASE 6: ENSURE SERVICES REMAIN DORMANT
        # ======================================================================
        
        logger.info("### Ensuring agent services remain stopped (dormant state)... ###")
        
        # Check if Hydra service is running and stop it if needed
        try:
            result = subprocess.run(["sudo", "systemctl", "is-active", "hydra"], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip() == "active":
                logger.info("### Hydra service is running - stopping it to maintain dormant state ###")
                subprocess.run(["sudo", "hydra", "stop"], stdout=subprocess.DEVNULL)
                logger.info("### Hydra service stopped successfully ###")
            else:
                logger.info("### Hydra service is already stopped (dormant state confirmed) ###")
        except Exception as e:
            logger.warning(f"### Could not check/stop Hydra service: {e} ###")
            logger.info("### Attempting to stop Hydra service anyway ###")
            subprocess.run(["sudo", "hydra", "stop"], stdout=subprocess.DEVNULL)
        
        # Final verification of dormant state
        logger.info("### Verifying final dormant state... ###")
        try:
            result = subprocess.run(["sudo", "systemctl", "status", "hydra"], 
                                  capture_output=True, text=True)
            if "inactive" in result.stdout or "failed" in result.stdout:
                logger.info("### ✅ Hydra service confirmed in dormant state ###")
            else:
                logger.warning("### ⚠️  Hydra service may still be active - check manually ###")
        except Exception:
            logger.info("### Service status check completed ###")
            
        logger.info("### Done ensuring services remain dormant ###")

        # ======================================================================
        # DORMANT INSTALLATION COMPLETE
        # ======================================================================
        
        logger.info("### DORMANT AGENT INSTALLATION COMPLETE ###")
        logger.info("### Agent packages are installed but services remain dormant ###")
        logger.info("### Key phases completed: ###")
        logger.info("###   ✅ Authentication and token generation ###")
        logger.info("###   ✅ Agent package download and validation ###") 
        logger.info("###   ✅ Agent package installation ###")
        logger.info("###   ✅ Authentication Service installation (if enabled) ###")
        logger.info("###   ✅ Post-installation validation ###")
        logger.info("### ###")
        logger.info("### Phases skipped (for activation): ###")
        logger.info("###   ⏭️  Connectivity configuration ###")
        logger.info("###   ⏭️  Certificate generation ###")
        logger.info("###   ⏭️  Service startup ###")
        logger.info("###   ⏭️  Agent registration ###")
        logger.info("###   ⏭️  Connector synchronization ###")
        logger.info("### ###")
        logger.info("### To activate this standby agent during failover: ###")
        logger.info("###   1. Ensure primary agent is completely offline ###")
        logger.info("###   2. Run: python3 activate-agent-core.py ###")
        logger.info("###   3. Expected activation time: 3-5 minutes ###")
        logger.info("### ###")
        logger.info("### Standby agent is ready for emergency activation! ###")
        
    except Exception:
        # ======================================================================
        # ERROR HANDLING AND CLEANUP
        # ======================================================================
        
        logger.exception("### Failed to install dormant agent ###")
        logger.warning("### Removing any installed packages... ###")
        
        # Clean up any packages that may have been installed before the failure
        # This ensures the system is returned to its original state
        subprocess.run(["sudo", linux_flavor_pkg_manager(), "remove", "-y", "alation-container-service*"],
                       stdout=subprocess.DEVNULL)
        subprocess.run(["sudo", linux_flavor_pkg_manager(), "remove", "-y", "alation-hydra*"],
                       stdout=subprocess.DEVNULL)
        logger.warning("### Done removing any installed packages ###")
        
    else:
        # ======================================================================
        # SUCCESS COMPLETION
        # ======================================================================
        
        logger.info("### Dormant agent installation completed successfully ###")
        
    finally:
        # ======================================================================
        # CLEANUP AND TOKEN REVOCATION
        # ======================================================================
        
        # Only attempt to revoke tokens if they were successfully created
        if refresh_token and user_id:
            logger.info("### Revoking access token... ###")
            # Always revoke the access token for security, regardless of success or failure
            # This ensures no tokens remain active after the script completes
            try:
                res = session.post(
                    f"{BASE_URL}/integration/v1/revokeAPIAccessTokens/",
                    json={"refresh_token": refresh_token, "user_id": user_id}
                ).json()
                logger.info("### Done revoking access token ###")
            except Exception as e:
                logger.warning(f"### Failed to revoke access token: {e} ###")
        else:
            logger.info("### No tokens to revoke ###")