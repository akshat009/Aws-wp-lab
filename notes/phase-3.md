# Phase 3 — Deploy Pipeline (GitHub Actions CI/CD)

> **Definition of Done:** Push to GitHub ➔ Actions green ➔ file automatically updated on the server. Failing test ➔ deploy job never runs (Quality Gate).

---

<details>
<summary><h3>🧠 Conceptual Foundations, Architecture & Trade-offs (Click to Expand)</h3></summary>

## What it does

Builds a fully automated, test-gated CI/CD deployment pipeline using GitHub Actions that tests WordPress plugin code (linting with PHPCS and unit tests with PHPUnit) and securely deploys passing code to the production EC2 instance over SSH without downtime using atomic releases and symlinks.

---

## Why choose it (Over Alternatives)

- **GitHub Actions CI/CD over Manual SFTP/SSH:** Manual SFTP or logging into EC2 to edit files (`nano`) is error-prone, untracked, has no rollback trail, and risks pushing broken code directly to live visitors.
- **Automated Gated Deploy (`needs: test`) over Direct Server Git Pull:** Running `git pull` directly on the server doesn't run automated tests before deploying. If a commit contains a syntax error or a failing test, `git pull` immediately breaks the production site. Gated CI/CD ensures that broken code never reaches the server.
- **Dedicated `ed25519` Deploy Key over Reusing Admin Key Pair:** Isolates CI/CD access. If the GitHub repository or runner is ever compromised, revoking the deploy key from `~/.ssh/authorized_keys` cuts off deployment without locking the administrator out of the EC2 instance.
- **Atomic Symlink Deployment over Direct In-place rsync:** Direct `rsync` into the active `/var/www/html/` directory creates a race condition where visitors accessing the site while files are being copied receive partial files, causing 500 errors or white screens of death (WSOD). Symlink swapping (`ln -sfn`) switches the active code instantly in 0.001 seconds.

---

## Trade-offs

- **Security Surface in GitHub Secrets:** Storing an SSH private key in GitHub Secrets grants GitHub runners remote shell access to the EC2 server. If the GitHub repository admin access is lost or compromised, attackers have shell access unless restricted.
- **Build Time & Actions Minutes:** Running Composer installs, PHPCS, and PHPUnit on every commit takes runner minutes (though well within the free 2,000 GitHub Actions minutes/month).
- **Disk Usage for Releases:** Storing timestamped releases (`/var/www/releases/`) consumes EBS disk space over time. We mitigate this with an automated release cleanup command retaining only the last 5 releases (`ls -1dt | tail -n +6 | xargs rm -rf`).

---

## Architecture Diagram

```text
[Developer Local Machine]
      │
      │  git push origin main
      ▼
[GitHub Repository]
      │
      │  Triggers .github/workflows/deploy.yml
      ▼
[GitHub Actions Runner (Ubuntu Latest)]
      │
      ├── 1. CI Job (Test Gate)
      │      ├── Setup PHP 8.3 / Composer
      │      ├── Run PHP CodeSniffer (phpcs)
      │      └── Run PHPUnit Tests (phpunit)
      │
      │   ❌ Test Fails? ➔ STOP! Deploy job NEVER runs.
      │   ✅ Test Passes? ➔ Proceed to CD Job (`needs: test`)
      │
      └── 2. CD Job (Atomic Deploy)
             ├── Read Secrets (SSH_PRIVATE_KEY, SSH_HOST, SSH_USER)
             ├── SSH Handshake with EC2 (ap-south-1)
             ├── rsync code to new release folder: /var/www/releases/<timestamp>/
             └── Atomic Switch: ln -sfn /var/www/releases/<timestamp> /var/www/html/wp-content/plugins/<plugin>
```

</details>

---

<details>
<summary><h3>⚙️ Step-by-Step Execution (Click to Expand)</h3></summary>

## Step-by-Step Execution

### Step 1: Connect to EC2 and Generate Dedicated Deploy Key Pair

#### How to connect to EC2 (Trade-offs: Instance Connect vs Local SSH Key)

| Feature | Option A: EC2 Instance Connect (Browser) | Option B: Local SSH Key (`.pem` file) |
|---|---|---|
| **Mechanism** | AWS console temporarily pushes a 60-second one-time public key to the EC2 metadata service via IAM. | Authenticates directly via asymmetric cryptography using your local `.pem` private key. |
| **Advantage** | **Zero local setup.** No key files to find, no Windows permission issues (`chmod 400`), and connects regardless of your laptop's changing ISP IP. | **Standard developer workflow.** Native terminal experience, scriptable, supports `scp`/`rsync`, multi-tab sessions, and SSH tunnels. |
| **Trade-off / Limitation** | Tied to the AWS web console; cannot be used directly for local automated tooling or CI/CD runner pipelines. | The `.pem` key file must be guarded securely; losing it risks server lockout. If your home IP changes, Security Group rules must be updated. |

##### Practical Connection Steps:

- **Option A (AWS Console Browser):**
  1. Open AWS Console ➔ EC2 ➔ Instances ➔ Select `wp-lab` (checkbox checked).
  2. The **"Connect"** button appears right above the instance table (between the blue circular refresh icon and the "Instance state" button).
  3. Click **Connect** ➔ Under the **EC2 Instance Connect** tab, click the bottom **Connect** button.
  4. A browser-based web terminal opens immediately.

![EC2 Instance Running and Connect Button](images/p3-ec2-running-connect.png)
_AWS Console EC2 Dashboard: `wp-lab` instance in 'Running' state with the top 'Connect' action button highlighted._

![EC2 Instance Connect Screen](images/p3-ec2-connect-modal.png)
_Connect to Linux instance wizard: EC2 Instance Connect selected with user `ubuntu` and Elastic IP `43.205.26.235`._

![EC2 Browser Terminal Connected](images/p3-ec2-browser-terminal-connected.png)
_EC2 Instance Connect terminal successfully connected: Notice 'Last login ... from 122.163.147.100', confirming our old ISP IP!_




- **Option B (Local Terminal via `.pem` Key):**
  Key location: `C:\Users\HP\Desktop\aws-key\wp-lab-key.pem`
  ```powershell
  cd C:\Users\HP\Desktop\aws-key
  ssh -i wp-lab-key.pem ubuntu@lab.asaxenadev.com
  # Or via Elastic IP:
  # ssh -i wp-lab-key.pem ubuntu@43.205.26.235
  ```

![EC2 Connect Error: Failed to connect to your instance](images/ec2-connect-failed-error.png)
_Error: 'Failed to connect to your instance - Error establishing SSH connection' caused by missing EC2 Instance Connect CIDR and dynamic ISP IP change._

##### ⚠️ Gotchas & Real-World Troubleshooting: Why did SSH fail?

1. **Dynamic ISP Public IP Changes Break Port 22:**
   - **The Error:** `WARNING: TCP connect to (43.205.26.235 : 22) failed / Ping TimedOut`.
   - **Root Cause:** In Phase 1 & 2, the Security Group SSH rule was set to `My IP`. Home Wi-Fi/Fiber connections (Jio, Airtel) have dynamic public IPs that change periodically or after router reboot. When the client IP changes (e.g. to `223.178.237.6`), the AWS stateful firewall silently drops Port 22 traffic.
   - **The Fix:** Go to **Security Groups ➔ Inbound rules ➔ Edit rules** ➔ Re-select **"My IP"** on Port 22 (AWS auto-fills your new `/32` IP).

![Security Groups Table](images/ec2-security-groups-list.png)
_AWS EC2 Security Groups console: Identifying `launch-wizard-4` attached to our WordPress instance._

![Security Group Old Inbound Rules](images/sg-old-ip-inbound-rules.png)
_Security Group Inbound rules: Notice Port 22 (SSH) is locked to old stale IP `122.163.147.100/32`, completely blocking our current connection._

![Edit Inbound Rules Form](images/sg-edit-inbound-rules-form.png)
_Edit Inbound rules editor: Updating SSH Port 22 source to current IP and whitelisting EC2 Instance Connect CIDR._

![Updated Inbound Rules Configured](images/sg-updated-inbound-rules-form.png)
_Inbound rules successfully configured: Port 22 allowed for both current IP `223.178.237.6/32` and EC2 Instance Connect CIDR `13.233.177.0/29`._





2. **EC2 Instance Connect (Browser) Requires AWS CIDR Whitelisting:**
   - **The Error:** `Error establishing SSH connection to your instance. Try again later.` in browser modal.
   - **Root Cause:** When using browser-based EC2 Instance Connect, the SSH connection does **not** originate from your personal laptop. It originates from **AWS's managed service IP block**. Because Port 22 was strictly locked to personal `My IP`, AWS's own service connection was dropped by the Security Group!
   - **The Fix:** Add an inbound rule for Port 22 with the regional AWS EC2 Instance Connect IP CIDR:
     - For Region `ap-south-1` (Mumbai): `13.233.177.0/29`.
     - Official AWS IP range prefix: AWS publishes these in `https://ip-ranges.amazonaws.com/ip-ranges.json` under service `EC2_INSTANCE_CONNECT`.

3. **Interview Question: "If we had connected directly from the desktop terminal via `.pem` key instead of the browser, would it have worked without touching the Security Group?"**
   - **Answer: NO, it would have failed identically!**
   - **Why?** Both your browser session and your desktop terminal (`PowerShell` / `ssh -i wp-lab-key.pem`) share the exact same outbound network router and Wi-Fi interface. When your home Wi-Fi/Fiber ISP dynamically refreshed your public IP to `223.178.237.6`, any packet sent from your laptop—whether generated by an SSH command in PowerShell or by a browser request—carried that new source IP.
   - The stateful AWS Security Group was still configured with the stale IP (`122.163.147.100/32`). Our direct terminal test proved this:
     ```powershell
     WARNING: TCP connect to (43.205.26.235 : 22) failed
     TcpTestSucceeded : False
     ```
   - **Difference between the two methods:**
     - Connecting from **Desktop Terminal** required whitelisting **"My IP"** (`223.178.237.6/32`).
     - Connecting from **EC2 Instance Connect (Browser)** required whitelisting AWS's regional CIDR (`13.233.177.0/29`).
   - **Real-World Production Insight (How companies handle this):**
     In enterprise environments, engineers do not manually re-whitelist their home IPs in Security Groups daily. Production architectures solve this via:
     1. **Corporate VPN / Dedicated Bastion Hosts:** Route all developer traffic through a fixed, static egress IP.
     2. **AWS Systems Manager (SSM) Session Manager (Phase 6):** Completely closes Port 22 to the public internet, channeling interactive shell sessions securely over AWS IAM and encrypted HTTPS endpoints without requiring any public IP whitelisting!

---

#### Generating the Dedicated Deploy Key on EC2

Rather than storing our primary personal `.pem` key inside GitHub Secrets, we generate a dedicated, unprivileged keypair specifically for GitHub Actions.


```bash
# 1. Generate an ed25519 keypair without a passphrase (-N "") for non-interactive automation
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy -N ""

# 2. Append the public key to authorized_keys so EC2 allows login with this key
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys

# 3. Enforce strict permissions (OpenSSH drops connections if permissions are too open)
chmod 600 ~/.ssh/authorized_keys && chmod 600 ~/.ssh/github_deploy

# 4. View the private key to copy into GitHub Secrets
cat ~/.ssh/github_deploy
```

##### Verified Terminal Execution Log:
```text
ubuntu@ip-172-31-1-148:~$ ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy -N ""
Generating public/private ed25519 key pair.
Your identification has been saved in /home/ubuntu/.ssh/github_deploy
Your public key has been saved in /home/ubuntu/.ssh/github_deploy.pub
The key fingerprint is:
SHA256:cw4boQNng04QaIatOCKLwARpKGLFQxksZ0eLk2/Fqe8 github-actions-deploy
+--[ED25519 256]--+
|=+B=+.           |
|BB.Oooo .        |
|@.++*.++.        |
|B. oo+oo .       |
|=o  .+o S .      |
|o   . .. B       |
|       .. .      |
|      .          |
|       E         |
+----[SHA256]-----+
ubuntu@ip-172-31-1-148:~$ cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
ubuntu@ip-172-31-1-148:~$ chmod 600 ~/.ssh/authorized_keys && chmod 600 ~/.ssh/github_deploy
ubuntu@ip-172-31-1-148:~$ cat ~/.ssh/github_deploy
-----BEGIN OPENSSH PRIVATE KEY-----
[REDACTED_FOR_SECURITY - Pasted directly into GitHub Actions Repository Secrets]
-----END OPENSSH PRIVATE KEY-----
```

> **Security Rule:** As per AWS security best practices, the private key output is strictly never committed to source control or exposed in public notes. It is transmitted directly into encrypted GitHub Repository Secrets.

![Deploy Key Terminal Generation](images/p3-deploy-key-terminal.png)
_EC2 terminal: Ed25519 deploy key generation, authorized_keys configuration, and chmod 600 strict permission assignment._

---

### Step 2: Configure GitHub Repository Secrets

Under **GitHub Repo ➔ Settings ➔ Secrets and variables ➔ Actions ➔ New repository secret**:

| Secret Name | Value | Purpose |
|---|---|---|
| `SSH_PRIVATE_KEY` | Content of `~/.ssh/github_deploy` | Allows GitHub Runner to authenticate with EC2 via SSH |
| `SSH_HOST` | `lab.asaxenadev.com` | Domain name pointing to our Elastic IP |
| `SSH_USER` | `ubuntu` | Default SSH user for AWS Ubuntu AMIs |

---

### Step 3: WordPress Plugin, Test Suite & CI/CD Pipeline Setup

We created a dedicated WordPress plugin repository ([akshat009/aws-wp-plugin](https://github.com/akshat009/aws-wp-plugin)) to isolate plugin lifecycle management from WordPress core.

#### 1. Custom WordPress Plugin Code (`aws-wp-plugin.php`):
```php
<?php
/**
 * Plugin Name: AWS WP Lab Plugin
 * Plugin URI: https://lab.asaxenadev.com
 * Description: Automated CI/CD WordPress Plugin deployed to AWS EC2 via GitHub Actions.
 * Version: 1.0.0
 * Author: Akshat Saxena
 * License: GPL2
 */

namespace AwsWpLab;

if (!defined('ABSPATH')) {
    define('ABSPATH', dirname(__FILE__) . '/');
}

class AwsWpLabPlugin
{
    public static function getVersion(): string
    {
        return '1.0.0';
    }

    public static function getStatus(): string
    {
        return 'Active - Deployed via GitHub Actions';
    }
}
```

#### 2. Composer & Testing Configuration (`composer.json`):
```json
{
    "name": "akshat009/aws-wp-plugin",
    "description": "WordPress plugin for testing AWS CI/CD pipeline",
    "type": "wordpress-plugin",
    "license": "GPL-2.0-or-later",
    "require": {
        "php": ">=8.1"
    },
    "require-dev": {
        "phpunit/phpunit": "^10.0 || ^11.0",
        "squizlabs/php_codesniffer": "^3.8"
    },
    "autoload": {
        "classmap": [
            "aws-wp-plugin.php"
        ]
    },
    "scripts": {
        "phpcs": "phpcs --standard=PSR12 --ignore=vendor .",
        "phpunit": "phpunit tests"
    }
}
```

#### 3. Unit Tests (`tests/PluginTest.php`):
```php
<?php

namespace AwsWpLab\Tests;

use AwsWpLab\AwsWpLabPlugin;
use PHPUnit\Framework\TestCase;

final class PluginTest extends TestCase
{
    public function testPluginVersionReturnsString(): void
    {
        $this->assertSame('1.0.0', AwsWpLabPlugin::getVersion());
    }

    public function testPluginStatusIsActive(): void
    {
        $this->assertStringContainsString('Active', AwsWpLabPlugin::getStatus());
    }
}
```

#### 4. GitHub Actions CI/CD Pipeline (`.github/workflows/deploy.yml`):
```yaml
name: Deploy

on:
  push:
    branches: [main]

concurrency:
  group: deploy-production
  cancel-in-progress: false

jobs:
  test:
    name: CI - Code Quality & Unit Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: shivammathur/setup-php@v2
        with:
          php-version: '8.3'
          tools: composer

      - run: composer install --no-interaction --prefer-dist
      - run: composer run phpcs
      - run: composer run phpunit

  deploy:
    name: CD - Deploy to EC2
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.SSH_PRIVATE_KEY }}" > ~/.ssh/id_ed25519
          chmod 600 ~/.ssh/id_ed25519
          ssh-keyscan -H ${{ secrets.SSH_HOST }} >> ~/.ssh/known_hosts

      - name: Deploy plugin
        run: |
          rsync -avz --delete \
            --exclude='.git*' \
            --exclude='node_modules' \
            --exclude='tests' \
            --exclude='.github' \
            ./ ${{ secrets.SSH_USER }}@${{ secrets.SSH_HOST }}:/var/www/html/wp-content/plugins/aws-wp-plugin/
```

#### Deep-Dive: Architectural Breakdown of the Workflow:
- **`concurrency: group: deploy-production, cancel-in-progress: false`**:
  - Prevents race conditions. If two commits are pushed in rapid succession, the second job waits for the first deploy to complete rather than terminating it mid-transfer (which could leave corrupted files).
- **Quality Gate (`needs: test`)**:
  - The `deploy` job explicitly declares `needs: test`. If `composer run phpcs` or `composer run phpunit` exits with an error code, GitHub Actions halts execution immediately. Broken code NEVER touches the production server.
- **`ssh-keyscan -H ${{ secrets.SSH_HOST }} >> ~/.ssh/known_hosts`**:
  - Seeds the EC2 server's public host key into the runner's `known_hosts` file. Without this, SSH prompts `Are you sure you want to continue connecting (yes/no)?`, which causes headless non-interactive CI jobs to hang and timeout.

---

### Step 4: Pipeline Execution, Quality Gate Verification & Real-World Debugging

#### 1. Real-World Breakage 1: Coding Standard Failure (Quality Gate in Action)
- **What Happened:** On the initial commit (`03fd2bb`), code was pushed using non-PSR-12 formatting (WordPress bracket spacing, snake_case methods).
- **The Result:** PHP CodeSniffer failed with 12 errors.
- **The Quality Gate Proved:** Because `test` failed, the dependent `deploy` job with `needs: test` was **automatically SKIPPED**:
  ```text
  name   status    conclusion
  ----   ------    ----------
  test   completed failure
  deploy completed skipped
  ```
- **Interview Takeaway:** This definitively proves the CI/CD Quality Gate. A developer can push broken code, but automated tests guarantee it will never reach or damage the live production site.
- **The Fix:** Refactored `aws-wp-plugin.php` and `tests/PluginTest.php` with proper PHP 8 namespaces (`AwsWpLab`), strict PSR-12 formatting, and camelCase methods (`getVersion()`, `getStatus()`). Both tests passed with 100% assertions.

![GitHub Actions Quality Gate Test Failed and Deploy Skipped](images/actions-deploy-ssh-fail.png)
_GitHub Actions: The 'test' job succeeded, triggering the 'deploy' job, which failed at 'Set up SSH'._

#### 2. Real-World Breakage 2: Multiline SSH Private Key Bash Expansion
- **What Happened:** In commit `21c83fe`, `test` turned green! But `deploy` failed at `Set up SSH`:
  ```text
  Set up SSH: Error: Process completed with exit code 1.
  ```
- **Root Cause:** In GitHub Actions, writing `echo "${{ secrets.SSH_PRIVATE_KEY }}" > ~/.ssh/id_ed25519` directly inside an inline `run: |` block expands the raw multiline Base64 string directly into the shell script. Bash interprets subsequent lines of the key as distinct shell commands (e.g. `b3BlbnNzaC...: command not found`), crashing the runner.
- **The Fix:** Multiline secrets must be exported via the GitHub Actions `env:` block and safely written to disk using `printf '%s\n' "$SSH_PRIVATE_KEY" > ~/.ssh/id_ed25519`.

#### 3. Real-World Breakage 3: `ssh-keyscan` Connection Dropped by EC2 Security Group
- **What Happened:** In commit `7a257c3`, `Set up SSH` failed again with exit code 1 on line 5:
  ```bash
  ssh-keyscan -H "$SSH_HOST" >> ~/.ssh/known_hosts
  shell: /usr/bin/bash -e {0}
  Error: Process completed with exit code 1.
  ```

![GitHub Actions ssh-keyscan failure log](images/p3-actions-ssh-keyscan-fail.png)
_GitHub Actions log: `ssh-keyscan` failure caused by AWS Security Group dropping public GitHub runner traffic._

- **Root Cause:**
  GitHub Actions runners execute on dynamically allocated Microsoft Azure / GitHub cloud infrastructure. Because our EC2 Security Group locked Port 22 exclusively to our home laptop's IP (`223.178.237.6/32`), the AWS stateful firewall silently dropped GitHub Actions Runner's connection request to Port 22. Because bash executes with `-e` (exit immediately on non-zero return), the entire deployment halted.
- **The Fix:**
  Update EC2 Security Group (`launch-wizard-4`) Inbound rules for Port 22 (SSH) from `My IP` to **`Anywhere-IPv4` (`0.0.0.0/0`)**.

![Security Group Port 22 Anywhere Inbound Rule](images/sg-ssh-anywhere-rule.png)
_Security Group Inbound rules updated: Port 22 set to Anywhere-IPv4 (`0.0.0.0/0`), allowing GitHub Actions runners to perform SSH handshakes._

- **Interview Deep-Dive: "Is opening Port 22 to `0.0.0.0/0` acceptable practice? What is the trade-off?"**
  - **The Trade-off:**
    - **Advantage:** Enables CI/CD runners with constantly rotating dynamic IP pools to deploy without maintaining massive, brittle IP CIDR lists.
    - **Security Mitigation:** Passwords are completely disabled on AWS Ubuntu AMIs (`PasswordAuthentication no`). The server strictly accepts cryptographic authentication via the `ed25519` keypair. Brute-force dictionary attacks are impossible.
    - **Downside:** Internet bots and port scanners will probe Port 22, filling `/var/log/auth.log` with failed connection noise.
    - **Phase 6 Hardening Plan:** In Phase 6 ("Harden it"), we close Port 22 completely to the public internet by migrating deployments to **AWS Systems Manager (SSM) Session Manager** or using a self-hosted GitHub runner deployed inside the private VPC!

#### 4. Real-World Breakage 4: `rsync: mkdir failed: Permission denied (13)` (Linux Permissions & Daemon Ownership)
- **What Happened:** SSH connected successfully (green checkmark), but the `Deploy plugin` step crashed on line 10:
  ```text
  rsync: [Receiver] mkdir "/var/www/html/wp-content/plugins/aws-wp-plugin" failed: Permission denied (13)
  rsync error: error in file IO (code 11) at main.c(680) [Receiver=3.4.1]
  Error: Process completed with exit code 11.
  ```

![GitHub Actions rsync Permission Denied Failure](images/p3-actions-rsync-permission-denied.png)
_GitHub Actions log: `rsync` fails with Permission denied (13) because user `ubuntu` lacks write permissions in `/var/www/html/wp-content/plugins/`._

- **Root Cause (The Linux Permissions Dilemma):**
  - GitHub Actions runner authenticates via SSH as user **`ubuntu`**.
  - In Phase 1, WordPress core was configured with strict security ownership: `www-data:www-data` (the Nginx/PHP-FPM web server daemon) with directory permissions `755` (`rwxr-xr-x`).
  - `755` permissions translate to:
    - **Owner (`www-data`):** Read, Write, Execute (`rwx`)
    - **Group (`www-data`):** Read, Execute (`r-x` — NO WRITE)
    - **Others (all other accounts, including `ubuntu`):** Read, Execute (`r-x` — NO WRITE)
  - When the `ubuntu` user attempted to create directory `/var/www/html/wp-content/plugins/aws-wp-plugin`, the Linux kernel enforced POSIX access control and dropped the syscall with `EACCES (Permission denied 13)`.

- **The Bad Fix vs The Clean Fix (Interview Trade-Off):**
  - **The Bad Fix (Insecure Hack):** `sudo chmod -R 777 /var/www/html`.
    - *Why it's a critical flaw:* Setting `777` makes files world-writable. Any vulnerability in an installed plugin or PHP upload vulnerability allows an attacker or any rogue process to overwrite arbitrary PHP files across the entire web server.
  - **The Clean Fix (Group Delegation & Scoped Ownership):**
    Pre-provision the target plugin directory with owner `ubuntu`, group `www-data`, and mode `775` (`rwxrwxr-x`), and add `ubuntu` to the `www-data` group:
    ```bash
    # 1. Pre-create target plugin directory
    sudo mkdir -p /var/www/html/wp-content/plugins/aws-wp-plugin

    # 2. Assign deployment user as owner and web server as group
    sudo chown -R ubuntu:www-data /var/www/html/wp-content/plugins/aws-wp-plugin

    # 3. Grant write permissions to both owner and group (775)
    sudo chmod -R 775 /var/www/html/wp-content/plugins/aws-wp-plugin

    # 4. Add ubuntu user to www-data group for unified collaboration
    sudo usermod -aG www-data ubuntu
    ```

![EC2 Target Directory Permissions Fixed](images/p3-ec2-permissions-fixed.png)
_EC2 Ubuntu terminal: Successfully configured plugin directory with `ubuntu:www-data` and `775` permissions._

### Step 5: Verified Green Pipeline & Production Server Verification

After addressing all 4 real-world breakages (lint formatting, bash multiline key expansion, security group ingress, and Linux daemon directory permissions), the GitHub Actions pipeline ran with 100% green status!

#### 1. Green CI/CD Pipeline Execution:
- **`test` job:** Succeeded in 9 seconds (Composer, PSR-12 CodeSniffer, PHPUnit).
- **`deploy` job:** Succeeded in 11 seconds (SSH handshake, host-key verification, rsync transfer).

![GitHub Actions Pipeline Succeeded Green](images/p3-actions-pipeline-green.png)
_GitHub Actions: Full CI/CD pipeline green - code tested, quality-checked, and deployed to EC2 production._

#### 2. Verification on Production EC2 Server:
Inspecting `/var/www/html/wp-content/plugins/aws-wp-plugin` confirmed that all code was transferred, permissions were preserved, and exclusions (`.git`, `tests/`, `.github/`) were respected:

```bash
ubuntu@ip-172-31-1-148:~$ ls -la /var/www/html/wp-content/plugins/aws-wp-plugin
total 20
drwxr-xr-x 2 ubuntu www-data 4096 Oct 27 08:26 .
drwxr-xr-x 4 www-data www-data 4096 Oct 27 08:23 ..
-rw-r--r-- 1 ubuntu ubuntu     15 Oct 27 08:26 README.md
-rw-r--r-- 1 ubuntu ubuntu    773 Oct 27 08:26 aws-wp-plugin.php
-rw-r--r-- 1 ubuntu ubuntu    552 Oct 27 08:26 composer.json

ubuntu@ip-172-31-1-148:~$ cat /var/www/html/wp-content/plugins/aws-wp-plugin/aws-wp-plugin.php
<?php
/**
 * Plugin Name: AWS WP Lab Plugin
 * Plugin URI: https://lab.asaxenadev.com
 * Description: Automated CI/CD WordPress Plugin deployed to AWS EC2 via GitHub Actions.
 * Version: 1.0.0
 * Author: Akshat Saxena
 * License: GPL2
 */
...
```

![EC2 Server Files Verified](images/p3-ec2-files-verified.png)
_EC2 terminal verification: The plugin files exist in `/var/www/html/wp-content/plugins/aws-wp-plugin/`, with exact code match._

---

### Step 6: Proving the Gate Works (Deliberate Test Failure & Gate Verification)

The core requirement of Phase 3's "Definition of Done" is:
> *"Failing test ➔ deploy job never runs."*

To prove that the pipeline guards the production server against faulty code, we executed a deliberate failure drill:

#### 1. Deliberate Bug Injection (`PluginTest.php`):
We altered the expected plugin version assertion from `1.0.0` to `9.9.9`:

```diff
     public function testPluginVersionReturnsString(): void
     {
-        $this->assertSame('1.0.0', AwsWpLabPlugin::getVersion());
+        // INTENTIONALLY BROKEN: Testing CI/CD Gate
+        $this->assertSame('9.9.9', AwsWpLabPlugin::getVersion());
     }
```

#### 2. Commit & Push to GitHub:
Commit `8715d6a`: `test: break unit test assertion to verify CI quality gate` was pushed to branch `main`.

#### 3. GitHub Actions Execution Outcome:
- **`test` job:** Failed immediately on step `Run composer run phpunit` with PHPUnit assertion error:
  ```text
  Failed asserting that two strings are identical.
  --- Expected
  +++ Actual
  @@ @@
  -'9.9.9'
  +'1.0.0'
  ```
- **`deploy` job:** Because `deploy` declared `needs: test`, GitHub Actions marked `deploy` as **`SKIPPED`**:
  ```text
  name   status    conclusion
  ----   ------    ----------
  test   completed failure   ❌
  deploy completed skipped   🚫 (Never triggered)
  ```
- **Production Server State:** Verified on EC2 that `/var/www/html/wp-content/plugins/aws-wp-plugin/aws-wp-plugin.php` remained intact and completely unaffected.

---

### Step 7: Atomic Symlink Zero-Downtime Deployment (The Production Upgrade)

#### Why In-Place rsync is dangerous:
Copying files directly into an active production directory creates a **race condition**:
- If a plugin has multiple PHP files or large assets, `rsync` transfers files one by one.
- If a visitor or automated cron job requests the site during the 5–10 seconds of transfer, PHP may attempt to execute code referencing classes or files not yet copied, resulting in **500 Internal Server Errors** or **Fatal Class Not Found** exceptions.

#### The Architecture of Atomic Symlink Releases:
```text
/var/www/
├── releases/
│   ├── 20261027140001/    (Old release)
│   ├── 20261027140510/    (Current active release) ◄────┐
│   └── 20261027141020/    (Incoming release being uploaded)
│
└── html/
    └── wp-content/
        └── plugins/
            └── aws-wp-plugin ──[SYMLINK]───┘ (Swapped in 0.001s via ln -sfn)
```

1. **Staged Transfer:** Code is uploaded to an isolated timestamp directory: `/var/www/releases/<timestamp>/`.
2. **Instant Atomic Switch:** `ln -sfn /var/www/releases/<timestamp> /var/www/html/wp-content/plugins/aws-wp-plugin`.
   - The Linux kernel changes the symbolic link pointer in **a single inode operation (~1 millisecond)**. Zero visitors experience partial files.
3. **Instant 1-Second Rollback:** If a bug slips through to production, rolling back is simply re-pointing the symlink to the previous timestamp directory—no git checkout, rebuilding, or re-downloading required!
4. **Automated Disk Retention:** Releases directory keeps only the 5 most recent releases (`ls -1dt | tail -n +6 | xargs rm -rf`), preventing disk exhaustion.

---

### Step 8: Production Verification of Atomic Symlink Releases

On the live EC2 instance, running `ls -la` confirms that `/var/www/html/wp-content/plugins/aws-wp-plugin` is no longer a static physical directory, but a live symbolic link pointing directly to the latest timestamped release:

```bash
ubuntu@ip-172-31-1-148:~$ ls -la /var/www/html/wp-content/plugins/
total 20
drwxrwxr-x 3 www-data www-data 4096 Oct 27 08:45 .
drwxr-xr-x 5 www-data www-data 4096 Oct 27 07:47 ..
drwxr-xr-x 5 www-data www-data 4096 Oct 16 09:14 akismet
lrwxrwxrwx 1 ubuntu   ubuntu     32 Oct 27 08:45 aws-wp-plugin -> /var/www/releases/20261027084519
-rw-r--r-- 1 www-data www-data 2669 Oct 16 09:14 hello.php
-rw-r--r-- 1 www-data www-data   28 Oct 16 09:14 index.php

ubuntu@ip-172-31-1-148:~$ ls -la /var/www/releases/
total 16
drwxrwxr-x 4 ubuntu www-data 4096 Oct 27 08:45 .
drwxr-xr-x 4 root   root     4096 Oct 27 08:38 ..
drwxr-xr-x 2 ubuntu ubuntu   4096 Oct 27 08:40 20261027084053
drwxr-xr-x 2 ubuntu ubuntu   4096 Oct 27 08:45 20261027084519
```

![EC2 Atomic Symlink Verified](images/p3-atomic-symlink-verified.png)
_EC2 terminal verification: `aws-wp-plugin` successfully linked as a symlink (`lrwxrwxrwx`) pointing to timestamped release `20261027084519`._

#### How Rollback Works in Practice:
If release `20261027084519` had a catastrophic bug in production, rollback takes exactly 1 millisecond with zero build/download lag:
```bash
ln -sfn /var/www/releases/20261027084053 /var/www/html/wp-content/plugins/aws-wp-plugin
```
WordPress immediately points back to the stable release!

</details>

---

<details>
<summary><h3>💡 What Surprised Me (The Gotchas & Real-World Breakages) (Click to Expand)</h3></summary>

## What Surprised Me (The Gotchas & Real-World Breakages)

1. **The Dynamic Home ISP IP Trap:**
   - Security Group inbound rules were tied to `My IP` in Phase 1 & 2. As soon as the ISP router reconnected, the IP changed from `122.163.147.100` to `223.178.237.6`. Port 22 SSH packets were silently dropped by AWS's stateful firewall, causing connection timeouts for both local terminal and EC2 Instance Connect.
2. **EC2 Instance Connect is Not Direct From Browser:**
   - Many developers assume browser-based SSH connects directly from their browser tab. In reality, it initiates from AWS's managed service IP block (`13.233.177.0/29` in Mumbai). Locking Port 22 to `My IP` breaks browser connect until the regional AWS CIDR is explicitly whitelisted.
3. **Multiline Secrets in Bash Inline Scripts Crash the Runner:**
   - Interpolating multiline secrets directly (`echo "${{ secrets.SSH_PRIVATE_KEY }}"`) causes Bash to execute lines of the Base64 key as shell commands (`b3BlbnNzaC...: command not found`). Exporting secrets to environment variables (`env:`) and using `printf '%s\n'` is mandatory.
4. **`ssh-keyscan` Fails if Port 22 isn't Reachable by GitHub:**
   - GitHub Actions runners run in cloud data centers with dynamic IPs. If Port 22 is firewalled by `My IP`, `ssh-keyscan` fails with exit code 1. Port 22 must be open to `0.0.0.0/0` (secured strictly by Ed25519 asymmetric cryptography) or routed via AWS SSM (Phase 6).
5. **The Linux Daemon Ownership Dilemma (`www-data` vs `ubuntu`):**
   - Direct rsync / symlink creation fails with `Permission denied (13)` because web servers use `www-data` with `755` permissions, blocking user `ubuntu`. The clean fix is adding `ubuntu` to `www-data` (`usermod -aG www-data ubuntu`) and granting group write permissions (`chmod 775`), never resorting to insecure `chmod 777`.

</details>

---

<details>
<summary><h3>💰 Cost & Resource Management (Click to Expand)</h3></summary>

## Cost & Resource Management

- **GitHub Actions Runner Minutes:** Free (public/private repos receive 2,000 free minutes/month; our 5 runs consumed ~2.5 minutes total).
- **EC2 Instance (`wp-lab`):** Free Tier (`t3.micro` 750 hours/month).
- **Elastic IP:** $0.00 while attached to the running instance.
- **EBS Disk Storage:** Timestamp releases consume minimal disk (~1.5 KB per release). Our automated retention command retains only the last 5 releases, keeping disk overhead under 20 KB.

</details>

---

<details>
<summary><h3>💰 Commands & Config Actually Run (With Line-by-Line Explanations) (Click to Expand)</h3></summary>

## Commands & Config Actually Run (With Line-by-Line Explanations)

Here is every single command executed in Phase 3, broken down with an exact English explanation directly beneath each line to explain what it does and why it was required.

---

### Part 1: EC2 SSH & Deploy Key Commands

#### 1. Generate Dedicated Key Pair:
```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy -N ""
```
> **What it does:** Generates a new, high-security asymmetric cryptographic keypair using the modern Edwards-curve algorithm (`ed25519`).
> - `-t ed25519`: Specifies the key algorithm (faster, shorter, and more secure than legacy RSA).
> - `-C "github-actions-deploy"`: Adds a comment label to the key so you can identify its purpose later inside `authorized_keys`.
> - `-f ~/.ssh/github_deploy`: Saves the private key to `~/.ssh/github_deploy` and the public key to `~/.ssh/github_deploy.pub`.
> - `-N ""`: Sets an empty passphrase so GitHub Actions automation can authenticate headlessly without human input.

---

#### 2. Authorize Public Key for SSH Login:
```bash
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
```
> **What it does:** Reads the contents of your newly generated public key (`cat`) and appends (`>>`) it to the end of the `authorized_keys` file.
> - When an incoming SSH client (GitHub Actions) presents the matching private key, OpenSSH checks this list to grant access to the `ubuntu` user account.

---

#### 3. Secure File Permissions:
```bash
chmod 600 ~/.ssh/authorized_keys && chmod 600 ~/.ssh/github_deploy
```
> **What it does:** Restricts file permissions so that ONLY the owner (`ubuntu`) can read and write these files (`rw-------` / `600`).
> - OpenSSH strictly rejects keys and refuses SSH handshakes if `authorized_keys` or private keys are readable by other users or groups on the system (POSIX permission check).

---

#### 4. Print Private Key for GitHub Secrets:
```bash
cat ~/.ssh/github_deploy
```
> **What it does:** Outputs the full private key (including the `-----BEGIN OPENSSH PRIVATE KEY-----` header and `-----END OPENSSH PRIVATE KEY-----` footer) to the terminal screen so you can copy and paste it into GitHub Repository Secrets (`SSH_PRIVATE_KEY`).

---

### Part 2: Linux Directory Permissions & Daemon Configuration

#### 5. Create Releases Storage Directory:
```bash
sudo mkdir -p /var/www/releases
```
> **What it does:** Creates the parent directory for staging timestamped releases.
> - `-p` (parents): Creates any missing parent directories and avoids throwing an error if the directory already exists.

---

#### 6. Assign Ownership to Deploy User & Web Daemon:
```bash
sudo chown -R ubuntu:www-data /var/www/releases
```
> **What it does:** Recursively (`-R`) changes the owner to `ubuntu` (the SSH deployment user) and the group to `www-data` (the Nginx/PHP-FPM web server user).
> - Allows GitHub Actions to upload files as `ubuntu` while allowing PHP to execute and read them as `www-data`.

---

#### 7. Set Collaborative Group Permissions (775):
```bash
sudo chmod -R 775 /var/www/releases
```
> **What it does:** Sets permissions recursively to `rwxrwxr-x` (`775`).
> - Owner (`ubuntu`): Read, Write, Execute (`rwx` = 7).
> - Group (`www-data`): Read, Write, Execute (`rwx` = 7).
> - Others: Read and Execute only (`r-x` = 5).
> - Guarantees both GitHub deploy scripts and Nginx have full read/write access without opening insecure `777` world-writable permissions.

---

#### 8. Enable Group Write on WordPress Plugins Directory:
```bash
sudo chmod 775 /var/www/html/wp-content/plugins
```
> **What it does:** Grants group write permissions on the parent `plugins/` directory.
> - In Linux, creating, renaming, or deleting a symlink requires write permission (`w`) on the **parent directory** containing the link, not just the file itself.

---

#### 9. Add Deploy User to Web Group:
```bash
sudo usermod -aG www-data ubuntu
```
> **What it does:** Appends (`-a`) the `ubuntu` user into the secondary group (`-G`) named `www-data`.
> - Enables `ubuntu` to inherit all group permissions granted to `www-data` across the WordPress directory tree.

---

#### 10. Remove Old Static Directory to Allow Symlinking:
```bash
sudo rm -rf /var/www/html/wp-content/plugins/aws-wp-plugin
```
> **What it does:** Recursively (`-r`) and forcefully (`-f`) removes the old static folder created by direct rsync.
> - Linux will not create a clean symlink if a physical folder with the same name already occupies that path.

---

### Part 3: GitHub Actions Pipeline Runner Commands

#### 11. Write Private Key via `printf`:
```bash
printf '%s\n' "$SSH_PRIVATE_KEY" > ~/.ssh/id_ed25519
```
> **What it does:** Safely writes the multiline private key from an environment variable into the runner's OpenSSH private key file.
> - Using `printf '%s\n'` prevents Bash from interpreting Base64 key lines as shell commands (which caused Breakage 2).

---

#### 12. Pre-Scan Host Fingerprint:
```bash
ssh-keyscan -H "$SSH_HOST" >> ~/.ssh/known_hosts
```
> **What it does:** Queries the EC2 server (`lab.asaxenadev.com`) on Port 22 and retrieves its public host key fingerprint, appending it to the runner's `~/.ssh/known_hosts`.
> - Without this step, SSH would pause with an interactive prompt: *"The authenticity of host... can't be established. Are you sure you want to continue connecting (yes/no)?"*, which freezes and times out headless CI/CD runners.

---

#### 13. Staged Rsync Upload to Timestamped Release:
```bash
REL=$(date +%Y%m%d%H%M%S)
rsync -avz --delete \
  --exclude='.git*' \
  --exclude='node_modules' \
  --exclude='tests' \
  --exclude='.github' \
  ./ "$SSH_USER@$SSH_HOST":/var/www/releases/$REL/
```
> **What it does:**
> - `REL=$(date +%Y%m%d%H%M%S)`: Generates a unique 14-digit timestamp (e.g. `20261027140510`) for the new release folder.
> - `rsync -avz`: Synchronizes files with archive mode (`-a`, preserves timestamps/permissions), verbose output (`-v`), and compression during transit (`-z`).
> - `--exclude`: Prevents development artifacts (Git history, unit tests, GitHub workflow files) from being copied to production.
> - Files are uploaded into an isolated staging folder (`/var/www/releases/$REL/`), meaning live site visitors never experience partial or broken files.

---

#### 14. Instant Atomic Pointer Swap & Retention Cleanup:
```bash
ssh "$SSH_USER@$SSH_HOST" "
  ln -sfn /var/www/releases/$REL /var/www/html/wp-content/plugins/aws-wp-plugin && \
  (ls -1dt /var/www/releases/* 2>/dev/null | tail -n +6 | xargs -r rm -rf)
"
```
> **What it does:**
> - `ln -sfn`: Creates an atomic symbolic link.
>   - `-s`: Symbolic link (points path to target).
>   - `-f`: Force (unlinks and replaces existing link target).
>   - `-n`: No-dereference (treats the destination symlink as a file rather than traversing into it).
>   - **Atomic Inode Flip:** The Linux kernel redirects the symlink in **~1 millisecond (0.001s)**. Visitors instantly see the new code with zero downtime.
> - `ls -1dt /var/www/releases/*`: Lists all releases sorted by modification time (`-t`), newest first, in single column format (`-1`).
> - `tail -n +6`: Filters the list to select everything starting from the 6th release onwards (ignoring the 5 most recent).
> - `xargs -r rm -rf`: Deletes the older releases. If there are fewer than 6 releases, `-r` prevents `rm` from running unnecessarily, keeping EBS disk clean automatically.

</details>

---

<details>
<summary><h3>📦 Incident Management & Disaster Recovery (What to do when things go wrong?) (Click to Expand)</h3></summary>

## Incident Management & Disaster Recovery (What to do when things go wrong?)

In production operations, there are two distinct failure scenarios every DevOps and WordPress engineer must handle:

```text
                                  ┌───────────────────────────┐
                                  │   Code Pushed to GitHub   │
                                  └─────────────┬─────────────┘
                                                │
                                  ┌─────────────▼─────────────┐
                                  │      CI Tests Run         │
                                  └──────┬─────────────┬──────┘
                                         │             │
                                  ❌ Test Fails    ✅ Test Passes
                                         │             │
                               ┌─────────▼─────────┐   │
                               │   Scenario 1:     │   │
                               │ Deploy Blocked    │   │
                               │ (Prod 100% Safe)  │   │
                               └───────────────────┘   │
                                                       │
                                            ┌──────────▼──────────┐
                                            │  Deployed to Prod   │
                                            └──────────┬──────────┘
                                                       │
                                            ┌──────────▼──────────┐
                                            │     Scenario 2:     │
                                            │ Uncaught Bug Breaks │
                                            │  Live Production!   │
                                            └──────────┬──────────┘
                                                       │
                                            ┌──────────▼──────────┐
                                            │ Emergency Rollback  │
                                            │ (1-Sec Symlink Swap)│
                                            └─────────────────────┘
```

---

### Scenario 1: What happens if a Test Fails in CI? (Pre-Production Gate)

#### 1. What actually happens:
- The CI Runner detects a non-zero exit code from `composer run phpcs` or `composer run phpunit`.
- The `deploy` job with `needs: test` is **automatically cancelled/skipped**.
- **The live production server is 100% safe and untouched.** Visitors experience zero impact.

#### 2. What the developer must do:
1. **Inspect Failure Logs:** Click on the red step in the GitHub Actions tab (e.g. PHPUnit assertion failure or PHPCS line number).
2. **Reproduce Locally:** Run the exact test locally on your laptop:
   ```bash
   composer run phpcs
   composer run phpunit
   ```
3. **Fix and Re-Verify:** Fix the bug, verify the test passes locally with 100% assertions.
4. **Push a New Commit:**
   ```bash
   git commit -am "fix: correct test assertion / resolve syntax issue"
   git push origin main
   ```
   The pipeline will run again, pass green, and automatically deploy to EC2.

---

### Scenario 2: What happens if an uncaught bug slips through and BREAKS Production? (Disaster Recovery)

Even with comprehensive unit tests, an unhandled edge-case (e.g., third-party API timeout, database schema mismatch, or unhandled null pointer) might pass CI tests but cause **500 Internal Server Errors** or a White Screen of Death (WSOD) on live production traffic.

When production breaks, you have two choices: **Fix-Forward** or **Instant Rollback**. In production, **always Rollback first, investigate later!**

#### 1. Immediate Emergency Rollback (Takes Exactly 1 Second!):
Because we configured **Atomic Symlink Releases**, you do NOT need to wait 5 minutes for a new GitHub Actions build or git revert. You can instantly restore the live site in 1 millisecond directly from the EC2 terminal:

```bash
# Step A: View your stored releases (sorted newest first)
ls -1dt /var/www/releases/*
# Output:
# /var/www/releases/20261027084519  <-- Broken release
# /var/www/releases/20261027084053  <-- Previous STABLE release

# Step B: Atomically swap the symlink back to the stable release!
ln -sfn /var/www/releases/20261027084053 /var/www/html/wp-content/plugins/aws-wp-plugin
```

> **Why this saves the business:**
> The `ln -sfn` command performs a single atomic inode pointer update in **0.001 seconds**. In 1 second, production is completely restored to the previous working state without any downtime or re-downloading!

#### 2. Automated 1-Click Rollback via GitHub Actions (`.github/workflows/rollback.yml`):
To enable team members without direct EC2 terminal access to instantly recover from an incident, we implemented a dedicated `workflow_dispatch` pipeline:
- **How to trigger:**
  1. Open GitHub Repository ➔ **Actions** tab.
  2. Select **"Rollback Production"** from the left sidebar.
  3. Click **"Run workflow"** button.
     - *(Optional)* Specify a target release timestamp (e.g. `20261027084053`), or leave it empty to automatically roll back to the immediately preceding stable release (`ls -1dt | sed -n '2p'`).
  4. GitHub Actions connects over SSH, atomically updates the symlink pointer, reloads PHP-FPM to flush OPCache, and verifies the active release within seconds!

```yaml
# .github/workflows/rollback.yml snippet
on:
  workflow_dispatch:
    inputs:
      target_release:
        description: 'Specific release timestamp to roll back to (Leave blank for previous release)'
        required: false

jobs:
  rollback:
    name: CD - Instant 1-Click Rollback
    runs-on: ubuntu-latest
    steps:
      - name: Set up SSH
        ...
      - name: Execute Instant Atomic Rollback
        run: |
          ssh "$SSH_USER@$SSH_HOST" "
            TARGET=\$(ls -1dt /var/www/releases/* | sed -n '2p')
            ln -sfn \"\$TARGET\" /var/www/html/wp-content/plugins/aws-wp-plugin
            sudo systemctl reload php8.3-fpm 2>/dev/null || true
          "
```

#### 3. Clean Up Git History (Revert Commit):
Once production is safe, revert the faulty commit in Git so that other developers don't pull or deploy the broken code:
```bash
git revert <broken-commit-hash>
git push origin main
```

#### 4. Post-Mortem & Preventative Regression Test:
- Ask: *"Why did our test suite fail to catch this bug?"*
- Write a new unit test in `tests/PluginTest.php` that explicitly reproduces the bug condition.
- Verify the new test fails against the broken code and passes against the fix.
- This guarantees the exact same bug can **never** pass CI again in the future!

---

### Non-PHP Production Failure Scenarios & Cloud Incident Response

In real-world cloud architectures, **over 60% of production outages are NOT caused by PHP syntax or code logic bugs**. They are caused by infrastructure, caching desynchronization, cloud resource throttling, database drift, network firewalls, or external upstream dependencies. 

Here is the master reference matrix of non-PHP production failure categories, root causes, symptoms, and battle-tested DevOps recovery steps:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      Major Non-PHP Production Outage Categories                        │
├──────────────────────────┬──────────────────────────┬──────────────────────────────────┤
│ Category                 │ Root Cause               │ Emergency Mitigation             │
├──────────────────────────┼──────────────────────────┼──────────────────────────────────┤
│ 1. Database              │ Schema out-of-sync       │ Expand-Contract Migrations       │
│ 2. Third-Party API       │ External Timeouts (504)  │ Strict Timeouts & Circuit Breaker│
│ 3. Memory (OOM)          │ Kernel OOM Killer        │ Swap Space & FPM Pool Tuning     │
│ 4. Disk Saturation       │ Logs / Old Releases      │ Automated Retention & Alarms     │
│ 5. Network / SSL         │ Expired Let's Encrypt    │ Dry-run Verification & Canaries  │
│ 6. FastCGI Socket        │ PHP-FPM Down (502)       │ Systemd Auto-Restart Watchdog    │
│ 7. Cache / Symlink Trap  │ OPCache / Realpath Stale │ opcache_reset() & FPM Reload     │
│ 8. AWS CPU Throttling    │ T3 Credit Depletion (0)  │ T3 Unlimited / Instance Resize   │
│ 9. EBS I/O Starvation    │ Burst Balance at 0%      │ gp3 Provisioned IOPS Upgrade     │
│ 10. WordPress Lock       │ .maintenance File Stuck  │ rm /var/www/html/.maintenance    │
│ 11. CI Upstream Outage   │ GitHub API 403 / Packagist│ COMPOSER_AUTH & Runner Caching  │
│ 12. SSH Fingerprint      │ Host Key Changed Warning │ ssh-keygen -R <host>             │
│ 13. Nginx Buffer Overflow│ upstream sent too big hdr│ fastcgi_buffers 16 16k Tuning    │
└──────────────────────────┴──────────────────────────┴──────────────────────────────────┘
```

---

#### 1. Database Schema Out-of-Sync (MySQL / Database Layer)
- **The Outage:** A new deployment goes live with code expecting a new table (`wp_orders_custom`) or column (`order_tracking_id`). The code deploys before the database migration finishes or after an unattended migration failed.
- **The Symptom:** PHP code has zero syntax errors, but database queries fail with `Table 'wordpress.wp_orders_custom' doesn't exist` or `Unknown column`. The live site throws fatal database errors.
- **Why Symlink Rollback isn't enough:** Symlink rollback reverts code, but **cannot undo database schema changes or data writes** already committed to MySQL.
- **Production Solution (The Expand-Contract Pattern):**
  - **Phase 1 (Deploy 1):** Add the new table/column to MySQL in a backward-compatible way (columns must be nullable or have defaults).
  - **Phase 2 (Deploy 2):** Deploy code that reads and writes to both old and new schema.
  - **Phase 3 (Deploy 3):** Drop the deprecated old columns only after the new code has run stably for 48 hours.

---

#### 2. Third-Party API Timeouts Exhausting Web Server Workers (504 Gateway Timeout)
- **The Outage:** Your WordPress site integrates with an external service (Stripe payment gateway, Mailchimp, CRM webhook, or AWS SES). That third-party service suffers an outage or severe latency (taking 30–60 seconds to respond).
- **The Symptom:** PHP processes wait synchronously for HTTP responses. Every incoming visitor locks a PHP-FPM worker thread. Within 1 minute, all `max_children` (e.g. 5–10 processes on `t3.micro`) are exhausted. **The entire site crashes with `504 Gateway Time-out`**, even on simple pages (like the Homepage or About Us) that don't even use that API!
- **Production Solution:**
  - **Strict HTTP Timeouts:** Never allow `wp_remote_get()` or cURL to wait indefinitely; cap timeouts at 2 to 3 seconds:
    ```php
    wp_remote_get( 'https://api.example.com', array( 'timeout' => 3 ) );
    ```
  - **Asynchronous Decoupling (Background Jobs):** Offload non-critical external calls to background queues (AWS SQS or Action Scheduler / WP-Cron) rather than blocking the user's synchronous web request.
  - **Circuit Breaker Pattern:** If an API fails 5 times consecutively, stop calling it for 5 minutes and immediately return a cached or fallback response.

---

#### 3. Linux Kernel Out-Of-Memory (OOM) Killer (Infrastructure Layer)
- **The Outage:** A traffic spike, uncached bot crawl, or memory-intensive query exceeds physical instance RAM (e.g., 1 GB on `t3.micro`).
- **The Symptom:** Linux Kernel executes the **OOM Killer** to prevent an operating system crash. It identifies the highest-memory consuming process (usually `mysqld` or `php-fpm`) and abruptly kills it (`SIGKILL -9`). The site instantly crashes with `Error establishing a database connection` or `502 Bad Gateway`.
- **How to Diagnose:** Check Linux kernel messages:
  ```bash
  sudo dmesg -T | grep -i oom
  # Output: Out of memory: Killed process 1245 (mysqld)
  ```
- **Production Solution:**
  - **Linux Swap Space (Phase 1 Fix):** Ensure a 2 GB `/swapfile` exists so memory spills to disk rather than killing critical system daemons.
  - **Tune PHP-FPM Pools:** In `/etc/php/8.3/fpm/pool.d/www.conf` (or 8.5), set `pm.max_children = 5` on 1 GB instances so PHP cannot over-allocate physical RAM.
  - **Cloud Scaling (Phase 4 & 9):** Decouple MySQL to AWS RDS (Phase 4) and place EC2 behind an Auto Scaling Group with an Application Load Balancer (Phase 9).

---

#### 4. Disk Storage Saturation (EBS Volume 100% Full)
- **The Outage:** An unchecked log file (`/var/log/nginx/error.log` or `wp-content/debug.log`) or accumulated releases fill up the 8 GB / 20 GB EBS volume.
- **The Symptom:** `df -h` shows `100%` use on `/`.
  - Nginx cannot buffer client POST request bodies (`No space left on device`).
  - MySQL crashes because it cannot create temporary tables or write to the InnoDB binary redo log.
  - Users cannot log in; sessions cannot be written to `/var/lib/php/sessions`.
- **Production Solution:**
  - **Automated Release Pruning:** Our CI/CD pipeline command automatically enforces storage cleanup:
    ```bash
    ls -1dt /var/www/releases/* | tail -n +6 | xargs rm -rf
    ```
  - **Linux Logrotate:** Configure `/etc/logrotate.d/nginx` and `logrotate` for WordPress to compress and delete logs older than 7 days.
  - **CloudWatch Disk Alarms (Phase 7):** Trigger automated SNS alerts when disk usage exceeds 80%.

---

#### 5. SSL/TLS Certificate Expiration & DNS Failures
- **The Outage:** Let's Encrypt certificates expire every 90 days. If the Certbot systemd timer (`certbot.timer`) fails or gets disabled, the certificate expires.
- **The Symptom:** Visitors get a full-screen red warning: `NET::ERR_CERT_DATE_INVALID` ("Your connection is not private"). Traffic drops to zero immediately.
- **Production Solution:**
  - **Verify Automated Timers:** Ensure the systemd background timer is active:
    ```bash
    sudo systemctl status certbot.timer
    ```
  - **Dry-run Renewal Test:**
    ```bash
    sudo certbot renew --dry-run
    ```
  - **CloudWatch Synthetic Canaries:** Automated AWS probes that ping `https://lab.asaxenadev.com` daily and alarm when the certificate is within 14 days of expiration.

---

#### 6. Web Server & FastCGI Socket Desynchronization (502 Bad Gateway)
- **The Outage:** PHP-FPM crashes, updates to a new version (e.g. PHP 8.4 to 8.5), or the Unix socket file (`/run/php/php8.3-fpm.sock`) is removed or has invalid permissions.
- **The Symptom:** Nginx cannot forward PHP requests to the upstream FastCGI daemon, returning `502 Bad Gateway` to all visitors.
- **Production Solution:**
  - **Verify Daemon & Socket:**
    ```bash
    sudo systemctl status php8.3-fpm
    ls -la /run/php/
    ```
  - **Systemd Watchdog Auto-Restart:** Ensure `/lib/systemd/system/php8.3-fpm.service` has `Restart=always` so crashed processes resurrect within 1 second.
  - **Safe Config Reloads:** Never restart Nginx without testing config syntax first:
    ```bash
    sudo nginx -t && sudo systemctl reload nginx
    ```

---

#### 7. PHP OPCache & Realpath Cache Desynchronization (The Atomic Symlink Trap)
- **The Outage:** After deploying a new release via atomic symlink swap (`ln -sfn`), visitors still see old bugs or receive `Fatal error: Class not found` even though the symlink on disk points to the new release folder.
- **The Cause (The Symlink Trap):**
  - PHP's **OPCache** compiles PHP scripts into bytecode stored in shared RAM.
  - Furthermore, PHP maintains a **`realpath_cache`** to avoid repeated filesystem lookups.
  - If `opcache.revalidate_path = 0`, PHP resolves the symlink once to `/var/www/releases/20261027084053/` and continues serving the cached bytecode from the *old* path, ignoring the fact that the symlink now points to `20261027084519`!
  - If some files resolve to the new release while others resolve to the old release, PHP crashes with missing class or function redeclaration errors.
- **Production Solution:**
  - **Post-Deploy PHP-FPM Reload:** Add a reload command directly to the deploy pipeline after swapping the symlink:
    ```bash
    sudo systemctl reload php8.3-fpm
    ```
    *(A reload gracefully flushes worker caches without terminating in-flight requests).*
  - **OPCache Config Tuning:** In `/etc/php/8.3/fpm/php.ini`:
    ```ini
    opcache.revalidate_path = 1
    opcache.validate_timestamps = 1
    opcache.revalidate_freq = 2
    ```

---

#### 8. AWS EC2 T3 CPU Credit Balance Exhaustion (CPU Throttling)
- **The Outage:** `t3.micro` is a burstable instance type. AWS grants baseline CPU performance (10% CPU for `t3.micro`). During normal activity, the instance accumulates CPU Credits. Under continuous load (traffic surge, bot attack, or unindexed database queries), the CPU runs at 100% and burns all credits.
- **The Symptom:**
  - Once CPU Credit Balance drops to 0, AWS strictly throttles instance CPU down to baseline 10%.
  - Server response time jumps from 150ms to 25+ seconds.
  - Incoming requests queue up until Nginx and PHP-FPM timeouts trigger HTTP 504 and SSH sessions lag out completely.
- **How to Diagnose:**
  - In AWS Console ➔ EC2 ➔ Monitoring ➔ Look at metric **`CPUCreditBalance`** dropping to zero and **`CPUUtilization`** flatlining at 10%.
- **Production Solution:**
  - **Enable T3 Unlimited:** Allows the instance to burst above baseline even with 0 credits (charged at ~$0.05 per vCPU-hour):
    ```bash
    aws ec2 modify-instance-credit-specification \
      --instance-id i-0454e55a303f5f9ae \
      --cpu-credits unlimited
    ```
  - **Scale Up Instance Type:** Upgrade to non-burstable `c6i.large` or larger `t3.small` / `t3.medium`.

---

#### 9. AWS EBS Burst Balance / IOPS Starvation
- **The Outage:** On General Purpose SSD (gp2) EBS volumes smaller than 1 TB, IOPS burst up to 3,000 using a burst bucket. Heavy disk activity (MySQL table scans, extensive plugin logging, or large file uploads) depletes the burst bucket.
- **The Symptom:**
  - When EBS `BurstBalance` reaches 0%, disk IOPS drop to baseline (for an 8 GB volume: only 3 × 8 = **24 IOPS!**).
  - Linux `iowait` climbs to 80–95%.
  - MySQL hangs waiting to write to disk. The site appears completely frozen, and SSH commands take 10 seconds to respond.
- **How to Diagnose:**
  ```bash
  # Check I/O wait and disk utilization in real time:
  iostat -xz 1
  ```
  Check CloudWatch metric `BurstBalance` under EC2 EBS metrics.
- **Production Solution:**
  - **Migrate gp2 to gp3:** gp3 volumes provide baseline **3,000 IOPS and 125 MB/s throughput** out of the box, regardless of storage volume size, with zero burst bucket limitations.
  - **Offload Media to S3 (Phase 5):** Eliminate local disk writes by storing WordPress uploads directly in AWS S3.

---

#### 10. WordPress Stuck in Maintenance Mode (`.maintenance` Lock File)
- **The Outage:** During automatic background updates or interrupted deployment scripts, WordPress creates a temporary file named `.maintenance` in the root web directory (`/var/www/html/.maintenance`).
- **The Symptom:** Every page on the website displays:
  > *"Briefly unavailable for scheduled maintenance. Check back in a minute."*
  Even after deployment finishes, the message persists indefinitely.
- **The Cause:** If a process crashed, timed out, or had insufficient permissions to delete `.maintenance` after updating, the file remains locked.
- **Production Solution:**
  ```bash
  # Check if lock file exists:
  ls -la /var/www/html/.maintenance
  # Instantly remove lock:
  sudo rm -f /var/www/html/.maintenance
  ```
  - **Preventative CI/CD Rule:** In deployment scripts, add a safeguard check to ensure `.maintenance` is never packaged or left lingering.

---

#### 11. CI/CD Pipeline Failure: GitHub API 403 Rate Limits & Packagist Upstream Outages
- **The Outage:** GitHub Actions fails on step `composer install`, aborting the pipeline before tests or deployment can even run.
- **The Symptom:**
  ```text
  Could not fetch https://api.github.com/repos/...
  403 API rate limit exceeded for 142.250.x.x
  ```
- **The Cause:**
  - Public GitHub Actions runners share public IP ranges. Unauthenticated GitHub API calls are capped at 60 requests per hour per IP.
  - When runner IP addresses exceed this rate limit, Composer fails to download dependencies.
- **Production Solution:**
  - **GitHub Token Injection:** Pass GitHub's default token to Composer in `deploy.yml`:
    ```yaml
    - name: Configure Composer GitHub Token
      run: composer config --global github-oauth.github.com ${{ secrets.GITHUB_TOKEN }}
    ```
    *(Increases API rate limit from 60 to 5,000 requests/hour).*
  - **Enable Dependency Caching:** Cache `vendor/` directory using `actions/cache@v4` so Composer doesn't fetch packages on every single run.

---

#### 12. SSH Host Key Verification Failure (`REMOTE HOST IDENTIFICATION HAS CHANGED!`)
- **The Outage:** A deployment that worked yesterday suddenly crashes on step `ssh` or `rsync` with:
  ```text
  @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
  @    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @
  @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
  IT IS POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!
  Host key verification failed.
  ```
- **The Cause:**
  - The EC2 instance was rebuilt, re-launched, or an Elastic IP was re-assigned to a new server.
  - The server's SSH host key fingerprint generated in `/etc/ssh/ssh_host_*` is different from the fingerprint previously saved in the client's `~/.ssh/known_hosts`. OpenSSH halts to protect against Man-in-the-Middle (MITM) attacks.
- **Production Solution:**
  - Remove the stale host key from `known_hosts`:
    ```bash
    ssh-keygen -R lab.asaxenadev.com
    # Or for IP:
    ssh-keygen -R 43.205.26.235
    ```
  - In CI/CD pipelines, always use `ssh-keyscan -H "$SSH_HOST" >> ~/.ssh/known_hosts` to seed the current key dynamically.

---

#### 13. Nginx FastCGI Buffer Overflow (HTTP 502 with `upstream sent too big header`)
- **The Outage:** Visitors attempting to log into WordPress admin or checkout via WooCommerce receive an instant `502 Bad Gateway`. Public static pages work fine.
- **The Symptom:**
  - Nginx error log shows:
    ```text
    upstream sent too big header while reading response header from upstream
    ```
- **The Cause:**
  - WordPress plugins (security suites, e-commerce, or complex session cookies) generate HTTP response headers (e.g. large `Set-Cookie` headers) that exceed Nginx's default FastCGI buffer size (4 KB or 8 KB).
  - Nginx considers the response invalid and terminates the connection with HTTP 502.
- **Production Solution:**
  - In Nginx virtual host configuration (`/etc/nginx/sites-available/wordpress`):
    ```nginx
    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php8.3-fpm.sock;

        # FastCGI Buffer Tuning for WordPress:
        fastcgi_buffer_size 32k;
        fastcgi_buffers 16 16k;
        fastcgi_busy_buffers_size 64k;
        fastcgi_temp_file_write_size 64k;
    }
    ```
  - Reload Nginx: `sudo nginx -t && sudo systemctl reload nginx`.

</details>

---

<details>
<summary><h3>🎯 Interview Questions & Answers (Phase 3 Prep) (Click to Expand)</h3></summary>

## Interview Questions & Answers (Phase 3 Prep)

### Q1: What is a CI/CD Pipeline, and why is it called a "pipeline"?
- **Answer:**
  - **Definition:** A pipeline is an automated sequence of stages (steps) that code must pass through from the moment a developer commits it until it is running on production servers.
  - **The "Pipe" Analogy:** Just like water enters one end of a pipe, gets filtered/treated inside, and emerges clean at the other end:
    - **Input:** Developer pushes raw code (`git push origin main`).
    - **Inside the pipe:** Automated quality checks, linting, dependency installation, and unit tests execute in a temporary sandbox.
    - **Output:** Verified, tested, and production-ready code is deployed without manual human intervention.
  - **Why not manual?** Without a pipeline, developers must manually SFTP files or SSH into production servers. Manual deployments are slow, error-prone, untracked, lack an audit trail, and risk pushing untested or syntax-broken code directly to live visitors.

---

### Q2: How is CI different from CD? (Continuous Integration vs Continuous Deployment)
- **Answer:**
  - **CI (Continuous Integration):**
    - **Focus:** Code quality, validation, and early bug detection.
    - **Environment:** Runs in an isolated, temporary GitHub Actions runner (Ubuntu VM).
    - **Actions in Phase 3:** `composer install`, `composer run phpcs` (PSR-12 linter), and `composer run phpunit` (unit tests).
    - **Server Access:** Requires **NO** access to production servers or SSH private keys.
    - **Outcome:** Passes (green) or fails (red). If it fails, the pipeline halts immediately.
  - **CD (Continuous Deployment):**
    - **Focus:** Releasing and provisioning passing code to production infrastructure.
    - **Environment:** Connects directly to the live server (AWS EC2 instance).
    - **Actions in Phase 3:** Reads SSH secrets, performs SSH handshake, stages files in `/var/www/releases/<timestamp>/`, and executes atomic symlink swap (`ln -sfn`).
    - **Server Access:** Requires SSH credentials and network access to Port 22.
    - **Dependency:** Strictly declared with `needs: test`. If CI fails, CD is **skipped automatically**.

---

### Q3: What is the difference between Continuous Delivery and Continuous Deployment?
- **Answer:**
  - **Continuous Delivery:** The pipeline automatically builds and tests the code, leaving it in a deployable state. However, releasing to production requires **manual human approval** (clicking a "Deploy" button or staging environment sign-off).
  - **Continuous Deployment (What we built in Phase 3):** Fully automated with zero human intervention. As soon as CI tests pass green on the `main` branch, the code is deployed directly to production.

---

### Q4: Why should the CD deploy job declare `needs: test`?
- **Answer:**
  - `needs: test` creates an automated **Quality Gate**. In distributed CI/CD systems, jobs run in parallel by default to save time. Without `needs: test`, deployment would begin before tests finish, potentially deploying buggy or syntax-broken code to production. With `needs: test`, any failure in tests immediately aborts execution and **skips** deployment, keeping production 100% stable.

---

### Q5: What does a concurrency group prevent in deployment pipelines?
- **Answer:**
  - A concurrency group (`group: deploy-production, cancel-in-progress: false`) guarantees that only **one deployment runs at any given moment**. If multiple developers push commits in quick succession, the jobs queue up rather than executing concurrently. Setting `cancel-in-progress: false` ensures an active deployment finishes transferring its release before the next deploy begins, preventing race conditions, file corruption, or half-swapped symlinks.

---

### Q6: Why is an atomic symlink deployment superior to direct in-place rsync?
- **Answer:**
  - Direct in-place `rsync` copies files file-by-file into the live document root. If visitors access the application during transfer, PHP executes half-transferred files, triggering **500 fatal errors** or white screens of death (WSOD).
  - Atomic symlink deployment stages code into `/var/www/releases/<timestamp>/`. Once all files are transferred and verified, `ln -sfn` performs an atomic pointer flip in **0.001 seconds (single inode operation)**. Visitors experience zero downtime. Furthermore, rolling back from a broken release is instantaneous—simply repoint the symlink to the previous release folder.

---

### Q7: Why is `chmod 777` an unacceptable solution for web server permission issues?
- **Answer:**
  - `777` makes directories and files readable, writable, and executable by *any* user and process on the operating system. If an attacker exploits a WordPress plugin vulnerability or file-upload bug, they gain uninhibited ability to overwrite executable PHP files, inject web shells, or deface the site. The secure approach delegates permissions via specific Linux groups (`usermod -aG www-data ubuntu` with `775`), adhering to the **Principle of Least Privilege**.

---

### Q8: Why do we generate a dedicated `ed25519` deploy key instead of reusing our personal EC2 `.pem` key?
- **Answer:**
  - **Principle of Least Privilege & Blast Radius Isolation:**
    - If the GitHub repository is ever compromised or an unauthorized collaborator gains repository access, they only have the deploy key.
    - Revoking the deploy key from `~/.ssh/authorized_keys` cuts off GitHub Actions access immediately without locking the administrator out of the EC2 instance.
    - If you shared your primary `.pem` admin key, revoking it would require replacing host keys and could permanently lock administrators out of the server.

---

### Q9: What happens when a CI test fails in the pipeline?
- **Answer:**
  - **1. CD Job is Immediately Aborted:** Because CD explicitly specifies `needs: test`, GitHub Actions marks the deploy step as **`SKIPPED`**. The runner never connects to the production server.
  - **2. Production Server Remains 100% Intact:** Faulty code never touches the EC2 filesystem. Live visitors continue experiencing the stable existing release with zero downtime.
  - **3. Merge is Blocked & Developer is Notified:** A red cross (❌) appears on the commit. GitHub dispatches an alert email containing the exact failure logs, affected file, and line number so the developer can reproduce and resolve it locally.

---

### Q10: Should a branch ever be merged if CI fails? (The "Never Merge on Red" Rule and Branch Protection)
- **Answer:**
  - **The Golden Rule:** **"Never Merge on Red."** A branch must never be merged into the primary branch (`main` or `master`) while CI checks are failing.
  - **Why merging on red is dangerous:**
    1. **Corrupts the Shared Baseline (`main`):** Once broken code enters `main`, every other developer who pulls code inherits the broken build, halting team productivity.
    2. **Triggers Cascading Outages:** Production and staging environments often auto-deploy from `main`. Merging broken code can cause immediate production downtime.
  - **Enforcement via GitHub Branch Protection Rules:**
    - Professional engineering teams do not rely on developer discipline alone.
    - Under **Repo Settings ➔ Branches ➔ Branch Protection Rules**, administrators configure **"Require status checks to pass before merging"** and bind it to the CI test workflow.
    - Until all tests run green, GitHub programmatically **disables and greys out the "Merge" button**, preventing anyone from merging failing code.

---

### Q11: Where do Git hooks (like Husky) fit into the software delivery lifecycle, and how do they differ from CI?
- **Answer:**
  - **Execution Location & Lifecycle:**
    - **Husky (Git Hooks):** Executes **locally on the developer's laptop** before code is committed (`pre-commit`) or before it leaves the machine (`pre-push`).
    - **CI (GitHub Actions):** Executes in the **cloud** on an isolated virtual machine after code is pushed to GitHub.
  - **The "Shift Left" Paradigm:**
    - Catching a syntax or formatting error on a local machine takes **under 1 second**. Catching it in CI takes **1 to 3 minutes** (waiting for runner provisioning, Docker setup, and Composer installs).
    - Husky provides instant feedback at zero cost in runner minutes.
  - **Why Husky Cannot Replace CI:**
    - **Husky can be bypassed locally:** A developer can run `git commit --no-verify` or `git commit -n` to skip hooks, or clone without running `npm install`.
    - **CI is an unbypassable gatekeeper:** CI runs in the cloud, completely controlled by repository policy. Developers cannot bypass cloud status checks.

---

### Q12: Do we run the exact same checks in Husky as we do in CI? What is the trade-off in execution speed vs test coverage?
- **Answer:**
  - **No, their scopes are deliberately different:**
    - **Husky is optimized for Speed (< 3 seconds):**
      - Runs lightweight linters on *staged files only* (using tools like `lint-staged`).
      - Runs quick formatting checks (`phpcs`) and fast unit tests.
      - *Trade-off:* If a local hook takes 30–60 seconds on every commit, developer experience degrades, and developers will routinely bypass the hook.
    - **CI is optimized for Exhaustive Coverage (2 to 5 minutes):**
      - Runs full test suites across the entire codebase.
      - Runs **Matrix Testing** across multiple PHP versions simultaneously (e.g. PHP 7.4, 8.0, 8.1, 8.2, 8.3).
      - Spins up Docker services (e.g., MySQL 8.0 or Redis containers) for deep integration and database transaction tests.
      - Runs static analysis (PHPStan Level 8) and security vulnerability audits (`composer audit`, Snyk).
  - **Summary:** Husky is the local first line of defense for developer productivity; CI is the comprehensive, non-negotiable security and stability gate for production readiness.

</details>
