# Phase 10 — Infrastructure as Code (Terraform / OpenTofu Automation)

> **Definition of Done:** Running `terraform destroy` tears down the entire AWS infrastructure, and subsequent `terraform apply` brings the complete, production-ready WordPress site back to life.

---

<details>
<summary><h3>🧠 Conceptual Foundations, Architecture & Trade-offs</h3></summary>

## What it does

Translates every manual AWS Console click, dropdown selection, security group rule, and server bootstrap command performed across Phases 1 through 9 into version-controlled, declarative code files (`main.tf`, `variables.tf`, `outputs.tf`). A single command (`terraform apply`) creates the entire WordPress cloud stack, and another single command (`terraform destroy`) tears everything down without leaving stray billing resources.

---

## Why choose it (Over AWS Console, CloudFormation & Configuration Management)

- **Declarative State Management vs Imperative Scripts:**
  - *Imperative (Bash / Python Boto3):* You specify *HOW* to build step-by-step (`if VPC not exists: create VPC`). If it fails halfway, retrying crashes because partial resources exist.
  - *Declarative (Terraform HCL):* You declare *WHAT* the desired end-state should be (`1 VPC, 1 EC2, 1 Security Group`). Terraform automatically calculates the difference ("delta"), builds a dependency graph, and applies only necessary changes (**Idempotency**).
- **The 3 Core Pillars of Terraform:**
  1. **Desired State (Code):** The `.tf` blueprints stored in Git.
  2. **Current Known State (`terraform.tfstate`):** The single source of truth mapping declared HCL resources to physical AWS IDs (`i-0af3a3266517a12c6`).
  3. **Actual State (Real World):** The real servers and networks physically running in AWS datacenters.
- **Why Terraform Over CloudFormation & Ansible:**
  - *CloudFormation:* Locked into AWS with verbose JSON/YAML. Terraform is cloud-agnostic (manages AWS, Cloudflare, GitHub, Datadog simultaneously).
  - *Ansible / Chef:* Excellent for *inside* the OS configuration management. Terraform is purpose-built for *underlying cloud infrastructure* provisioning.

---

## Trade-offs

- **State File Security Risk:**
  `terraform.tfstate` contains every resource attribute in plain JSON text — including database passwords and private keys. It must never be committed to Git; it must reside in an encrypted Amazon S3 bucket.
- **Concurrency & Race Conditions:**
  If two engineers run `terraform apply` simultaneously without state locking (DynamoDB), race conditions will corrupt the state file.
- **Blast Radius & Accidental Destruction:**
  Because Terraform destroys infrastructure with a single command, an unverified `terraform destroy` or modifying an immutable attribute can wipe out a live production database.

---

## Architecture Diagram

```text
               [Developer / CI/CD Runner]
                           │
                           │ terraform plan / apply
                           ▼
               [Terraform Engine (Core)]
                           │
        ┌──────────────────┴──────────────────┐
        │                                     │ Reads & Locks
        ▼                                     ▼
[Terraform AWS Provider]           [Remote Backend (S3 + DynamoDB)]
        │                          ├── terraform.tfstate (S3 Bucket)
        │ AWS API Calls            └── LockID (DynamoDB Table)
        ▼
[AWS Cloud (ap-south-1 Mumbai)]
├── aws_vpc & aws_subnet
├── aws_security_group
├── aws_iam_role & aws_iam_policy
├── aws_s3_bucket
├── aws_db_instance (RDS)
└── aws_lb & aws_autoscaling_group
```

---

## The 2 Approaches: Way 1 (Local Prototyping) vs Way 2 (Enterprise GitOps with OIDC)

```text
[Way 1: Local Prototyping]
Developer Workstation (PowerShell) ──(Temporary Access Keys)──► AWS Mumbai (EC2 + SG)
├── State: Local Disk (terraform.tfstate)
└── Trade-off: 2-minute instant feedback | High secret leak risk, zero team locking

[Way 2: Enterprise GitOps with OIDC]
Developer Workstation ──(git push PR)──► GitHub Actions Runner
                                                │
                                                │ OIDC Token (Zero Static Secrets!)
                                                ▼
                                       AWS IAM Role (AssumeRole)
                                                │
                          ┌─────────────────────┴─────────────────────┐
                          ▼                                           ▼
            Remote S3 Bucket + DynamoDB Lock               AWS Infrastructure
```

| Dimension | Way 1: Lab / Local Prototyping | Way 2: Industry Enterprise GitOps | Architectural Trade-off (Interview Answer) |
| :--- | :--- | :--- | :--- |
| **Execution Engine** | Developer ka Local Laptop (PowerShell) | GitHub Actions Hosted Cloud Runner | Production mein single developer machine par dependency khatam ho jati hai. |
| **Authentication** | Static Access Key & Secret Key | AWS IAM OIDC (Zero Static Keys) | Static key leak ka risk zero ho jata hai; temporary 15-minute STS session milta hai. |
| **State Storage** | Local Disk (`terraform.tfstate`) | Remote S3 Bucket + DynamoDB State Lock | Concurrent apply conflict aur state corruption se 100% safety. |
| **Setup Time** | < 2 Minutes | 1–2 Ghante | Enterprise security and compliance require upfront operational configuration. |
| **Best Purpose** | Learning, Testing, Quick Local POCs | Production, Real Companies, Team Collaboration | Pehle local test karo, verify hone ke baad GitOps mein commit karo. |

---

## The 2 Workspaces Architecture: `bootstrap/` (Vault) vs `infra/` (Active Production)

```text
Project Root (Aws-wp-lab/)
│
├── bootstrap/  (Stage 1: Foundational Vault — Run Once & Done)
│   ├── main.tf ──────────► Provisions S3 State Bucket + DynamoDB Lock Table
│   └── terraform.tfstate ──► Local State (Bootstrap lifecycle stays local)
│
└── infra/      (Stage 2: Main Production Application — Daily Active Workload)
    ├── main.tf ──────────► Connects to S3 Remote Backend + Provisions EC2 & SG
    ├── variables.tf
    ├── outputs.tf
    ├── install.sh
    ├── terraform.tfstate ──► 0 Bytes (State migrated securely into remote S3)
    └── terraform.tfstate.backup (12 KB safety backup)
```

### Analogy: Tijori (Safe & Lock) vs Main Makaan (House)
- **`bootstrap/` = Tijori (Safe):** Makaan banane se pehle hum ek tijori aur lock banate hain jisme ghar ke saare official blueprints aur registry safe rahein. Iska kaam ek baar safe create karna hota hai.
- **`infra/` = Main Makaan (Active Real Estate):** Yeh aapka real project hai (WordPress server, Nginx, MySQL, Security Group) jo apni registry us safe (`bootstrap/` ke S3 bucket) ke andar store karta hai.

### Architectural Breakdown Table:

| Dimension | `bootstrap/` Workspace | `infra/` Workspace | Architectural Reason / Trade-off |
| :--- | :--- | :--- | :--- |
| **Architectural Purpose** | **Foundational Backend Vault** | **Production Workload & App Stack** | Infrastructure storage foundation ko application layer se alag rakhna taaki app destroy hone par state bucket delete na ho. |
| **Resources Managed** | 1. `aws_s3_bucket.state`<br>2. `aws_s3_bucket_versioning`<br>3. `aws_s3_bucket_server_side_encryption`<br>4. `aws_s3_bucket_public_access_block`<br>5. `aws_dynamodb_table.locks` | 1. `aws_security_group.web`<br>2. `aws_instance.wp`<br>3. `install.sh` User-Data<br>*(Future: RDS, ALB, ASG)* | S3 + DynamoDB state storage provide karte hain; EC2 + SG WordPress web traffic serve karte hain. |
| **Lifecycle / Execution** | **Run Once & Forget:** Life mein sirf ek baar chalta hai. | **Daily Active:** Har code change, Git commit, aur PR par run hota hai. | Application changes se foundational state storage bucket accidentally delete nahi ho sakti. |
| **State Storage Location** | Local Disk (`bootstrap/terraform.tfstate`) | Remote S3 (`s3://.../prod/terraform.tfstate`) | "Chicken-and-Egg" dependency break karne ke liye bootstrap local state use karta hai. |
| **CI/CD Integration** | Zero CI/CD needed. | **GitHub Actions Pipeline Root:** GitHub Actions isi folder mein run hoga. | CI/CD runners ephemeral hote hain, unhe remote state chahiye jo bootstrap ne banaya. |
| **Which folder to use?** | **Complete:** Ab ise chhedna nahi hai. | **Main Active Workspace:** Saara daily kaam `infra/` mein hota hai. | Real DevOps standard: Single responsibility principle for IaC workspaces. |

### Why not merge them into 1 folder? (The Chicken-and-Egg Dilemma)
Agar `aws_s3_bucket` aur `backend "s3"` ek hi folder ke `main.tf` mein likh diye jaayein, toh `terraform init` crash ho jata hai kyunki remote backend bucket cloud par exist hi nahi karti! Two-stage separation guarantees 100% pure IaC without manual AWS console clicking.

</details>

---

<details>
<summary><h3>📋 Implementation Steps & Progress Tracker</h3></summary>

## Implementation Steps & Progress Tracker

- [x] **Step 1: Install Terraform CLI on Windows & Configure Workspace**
  - Installed HashiCorp Terraform `v1.16.6` via `winget`.
  - Initialized dedicated project directory `infra/`.
- [x] **Step 2: Author Declarative Infrastructure Code (`main.tf`, `variables.tf`, `outputs.tf`, `install.sh`)**
  - Authored AWS provider with `default_tags`, Canonical Ubuntu 24.04 AMI dynamic data lookup.
  - Declared `aws_security_group.web` (ports 80, 443, 22) and `aws_instance.wp` (`t3.micro`, 20GB gp3).
  - Configured automated LEMP stack and WordPress core bootstrap via `install.sh`.
- [x] **Step 3: Execute Terraform Core Workflow (`init`, `validate`, `plan`)**
  - `terraform init`: Resolved and cached HashiCorp AWS provider `v5.100.0`.
  - `terraform validate`: Verified declarative HCL syntax and unquoted type constraints.
  - Generated session credentials and executed `terraform plan` (2 to add, 0 to change, 0 to destroy).
- [x] **Step 4: Provision Cloud Stack & Verify WordPress Web Tier (`apply`)**
  - Provisioned Security Group `sg-035e7f0d68fe6d4dd` and EC2 `i-0af3a3266517a12c6` in 16 seconds.
  - Verified live WordPress web installer at `http://35.154.176.166/wp-admin/install.php` (`200 OK`).
- [x] **Step 5: Provision S3 State Bucket & DynamoDB Lock via Bootstrap Code (`bootstrap/main.tf`)**
  - Authored and applied dedicated bootstrap workspace; provisioned encrypted S3 bucket `wp-lab-tfstate-538820337783` (versioning, AES256, 100% private) and DynamoDB state lock table `wp-lab-tf-locks` in 14 seconds.
- [x] **Step 6: Configure S3 Backend & Migrate Local State**
  - Configured `backend "s3"` in `infra/main.tf`; migrated local state to S3 (`prod/terraform.tfstate`) with DynamoDB lock table `wp-lab-tf-locks`. Local state file vacated to 0 bytes.
- [x] **Step 7: Configure AWS IAM OIDC Provider & GitHub Actions Role**
  - Established OpenID Connect cryptographic trust with GitHub Actions (`token.actions.githubusercontent.com`) and provisioned IAM Role `GitHubActionsTerraformRole` scoped to repository user `akshat009` with `AdministratorAccess` permissions.
- [x] **Step 8: Setup GitHub Actions GitOps CI/CD Workflow (`.github/workflows/terraform.yml`)**
  - Configured passwordless GitHub Actions GitOps workflow with IAM OIDC authentication (`sts.amazonaws.com`).
  - Verified automated `terraform init`, `validate`, `plan`, and `apply` execution: 100% green (`✓ 46s`), zero-drift (`0 added, 0 changed, 0 destroyed`).
  - Configure automated `terraform plan` on Pull Requests and `terraform apply` on merge to `main`.
- [x] **Step 9: Revoke & Delete Root Access Keys**
  - Enforced Zero-Trust Security by permanently deleting static root access key `AKIAX25BR4B3TYTG22TW` from AWS Console. All infrastructure operations now authenticate exclusively via ephemeral 15-minute STS tokens assumed by GitHub Actions OIDC.
- [x] **Step 10: Verify "Done When" Criteria (Teardown & Automated Rebuild)**
  - Executed `terraform destroy` via GitHub Actions pipeline run `#42028596035`: Terminated old EC2 (`i-0af3a3266517a12c6`) and Security Group in 1m 21s; verified site dead (`ERR_CONNECTION_TIMED_OUT`).
  - Executed `terraform apply` via GitHub Actions pipeline run `#42028951514`: Provisioned brand-new EC2 (`i-0fca9a4b647516a51`) and new IP (`35.154.149.207`) in 57s; verified live WordPress installer at `http://35.154.149.207/wp-admin/install.php` (`200 OK`).

</details>

---



<details>
<summary><h3>⚙️ Step 1 Execution Details: Install Terraform CLI & Workspace Setup</h3></summary>

## Step 1 Execution Details: Install Terraform CLI & Workspace Setup

Terraform CLI is HashiCorp's declarative infrastructure-as-code command-line tool. On Windows workstations, installing via `winget` ensures the binary is placed into the system `PATH` and kept up-to-date.

### Step-by-Step Walkthrough:
1. Open **PowerShell** locally on Windows.
2. Execute package installation command: `winget install Hashicorp.Terraform`.
3. Verify hash integrity, package extraction, and environment variable modification.
4. Reload environment variables to make `terraform` alias globally accessible.
5. Create dedicated workspace directory `infra/` and navigate into it.

### 1. Terraform CLI Installation via Windows Package Manager (`winget`):

![Terraform CLI Installed via winget](images/p10-step1-terraform-winget-installed.png)
*Console State:* Executed `winget install Hashicorp.Terraform` in local PowerShell. Successfully downloaded and extracted `terraform_1.16.6_windows_amd64.zip` (35.0 MB). Verified installer hash, modified system `Path` environment variable, and registered global command line alias `"terraform"`.

### 2. PATH Reload & Terraform Version Verification:

![Terraform Version Verified](images/p10-step1-terraform-version-verified.png)
*Console State:* Executed dynamic PATH reload `$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")` followed by `terraform -version`. Successfully verified **Terraform v1.16.6 on windows_amd64**. CLI binary is now globally accessible and operational across the workstation.

### 3. Terraform Infrastructure Workspace (`infra/`) Initialization:

![Infra Directory Created](images/p10-step1-infra-directory-created.png)
*Console State:* Executed `mkdir infra ; cd infra` in PowerShell. Successfully provisioned dedicated `infra/` project directory to house Terraform configuration files (`main.tf`, `variables.tf`, `outputs.tf`), isolated from application and documentation assets.

</details>

---



<details>
<summary><h3>⚙️ Step 2 Execution Details: Author Declarative Infrastructure Code</h3></summary>

## Step 2 Execution Details: Author Declarative Infrastructure Code

To provision the WordPress infrastructure cleanly, the code was organized into dedicated declarative HCL files inside `infra/`:

> [!NOTE]
> **Who Authors These Files?** Terraform is not a screen-recorder and cannot auto-generate code from AWS Console clicks. Cloud/DevOps engineers author these configuration files directly — leveraging official HashiCorp Registry documentation, pre-built modules, and AI pair-programming — to declare the exact desired cloud state in Git.

### 1. Configuration Files Architecture:

| File | Purpose | Key Attributes |
| :--- | :--- | :--- |
| **`main.tf`** | Core cloud resources definition | Provider `aws ~> 5.0`, dynamic Ubuntu AMI data source, `aws_security_group.web`, `aws_instance.wp`. |
| **`variables.tf`** | Reusable input parameters | `aws_region = "ap-south-1"`, `instance_type = "t3.micro"`, `key_name = "wp-lab-key"`. |
| **`outputs.tf`** | Exported cloud attributes | `instance_id`, `instance_public_ip`, `instance_public_dns`, `website_url`. |
| **`install.sh`** | Web tier user-data bootstrap | 2GB swap, Nginx, PHP-FPM, MySQL, WordPress core download, dynamic salts generation. |

#### A. Core Cloud Infrastructure Blueprint (`infra/main.tf`):
```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "wp-lab-tfstate-538820337783"
    key            = "prod/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "wp-lab-tf-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "aws-learning"
      Environment = "lab"
    }
  }
}

# 1. Fetch the latest official Ubuntu 24.04 LTS AMI from Canonical
data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"] # Canonical official AWS account ID
}

# 2. Security Group for WordPress Web Server
resource "aws_security_group" "web" {
  name        = "wp-lab-web-sg"
  description = "Security group for WordPress web server"

  ingress {
    description = "Allow inbound HTTP web traffic"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow inbound HTTPS encrypted web traffic"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow inbound SSH administrative access"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic for OS updates and package installs"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "wp-lab-web-sg"
  }
}

# 3. WordPress EC2 Instance (Auto-provisioned via install.sh)
resource "aws_instance" "wp" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.web.id]

  user_data                   = file("${path.module}/install.sh")
  user_data_replace_on_change = true

  root_block_device {
    volume_size           = 20
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  tags = {
    Name = "wp-lab"
  }
}
```

#### B. Reusable Input Variables (`infra/variables.tf`):
```hcl
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "ap-south-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "key_name" {
  description = "Name of existing EC2 Key Pair for SSH access"
  type        = string
  default     = "wp-lab-key"
}
```

#### C. Exported Attributes (`infra/outputs.tf`):
```hcl
output "instance_id" {
  description = "ID of the provisioned WordPress EC2 instance"
  value       = aws_instance.wp.id
}

output "instance_public_ip" {
  description = "Public IPv4 address of the WordPress server"
  value       = aws_instance.wp.public_ip
}

output "instance_public_dns" {
  description = "Public DNS hostname of the WordPress server"
  value       = aws_instance.wp.public_dns
}

output "website_url" {
  description = "HTTP URL to access WordPress"
  value       = "http://${aws_instance.wp.public_ip}"
}
```

#### D. User-Data Bootstrap Script (`infra/install.sh`):
```bash
#!/bin/bash
set -e

# 1. Add 2GB Swap Memory (Prevent MySQL OOM crashes on t3.micro)
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# 2. System update and package installation
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y nginx mysql-server php-fpm php-mysql php-curl php-gd php-mbstring php-xml php-zip php-intl unzip curl ed

# 3. Enable & start core services
systemctl enable --now nginx
systemctl enable --now mysql

# 4. Automatically locate active PHP-FPM socket path
PHP_SOCKET=$(ls /run/php/php*-fpm.sock | head -n 1)

# 5. Provision MySQL database & dedicated application user
DB_NAME="wordpress"
DB_USER="wpuser"
DB_PASS="SecureLabPass2026!"

mysql -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';"
mysql -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';"
mysql -e "FLUSH PRIVILEGES;"

# 6. Download and deploy WordPress core files
cd /tmp
curl -s -O https://wordpress.org/latest.tar.gz
tar -xzf latest.tar.gz
rm -rf /var/www/html/*
cp -r wordpress/* /var/www/html/

# 7. Apply standard production ownership & permissions
chown -R www-data:www-data /var/www/html
find /var/www/html -type d -exec chmod 755 {} \;
find /var/www/html -type f -exec chmod 644 {} \;

# 8. Configure Nginx Virtual Host for WordPress
cat <<EOF > /etc/nginx/sites-available/default
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    root /var/www/html;
    index index.php index.html index.htm;

    server_name _;

    location / {
        try_files \$uri \$uri/ /index.php?\$args;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:${PHP_SOCKET};
    }

    location ~ /\.ht {
        deny all;
    }
}
EOF

# 9. Verify syntax and reload Nginx
nginx -t && systemctl reload nginx

# 10. Configure wp-config.php with database credentials
cd /var/www/html
cp wp-config-sample.php wp-config.php
sed -i "s/database_name_here/${DB_NAME}/" wp-config.php
sed -i "s/username_here/${DB_USER}/" wp-config.php
sed -i "s/password_here/${DB_PASS}/" wp-config.php

chown www-data:www-data wp-config.php
chmod 640 wp-config.php

echo "WordPress automated installation complete!"
```

### 2. Infrastructure Parameters:

| Parameter | Value | Architectural Purpose |
| :--- | :--- | :--- |
| **AWS Region** | `ap-south-1` (Mumbai) | Minimal latency for local traffic. |
| **Instance Type** | `t3.micro` | AWS Free Tier eligible (2 vCPUs, 1 GiB RAM). |
| **Base AMI** | Canonical Ubuntu 24.04 LTS | Latest stable LTS operating system fetched dynamically via data source. |
| **Root Disk** | 20 GB gp3 (`/dev/sda1`) | 3000 IOPS / 125 MB/s baseline storage for OS and web server. |
| **Inbound Ports** | TCP 80, 443, 22 from `0.0.0.0/0` | Web browsing and administration access. |
| **Resource Tags** | `Project = aws-learning`, `Environment = lab` | Standardized tag inheritance via provider `default_tags`. |

</details>

---



<details>
<summary><h3>⚙️ Step 3 Execution Details: Terraform Core Workflow (Init, Validate, Plan)</h3></summary>

## Step 3 Execution Details: Terraform Core Workflow (Init, Validate, Plan)

### 1. Terraform Provider Plugin Download & Initialization (`terraform init`):

![Terraform Init Success](images/p10-step1-terraform-init-success.png)
*Console State:* Executed `terraform init` inside `infra/`. Successfully resolved HashiCorp AWS provider constraint `~> 5.0` to official signed release **`hashicorp/aws v5.100.0`**. Generated dependency lock file `.terraform.lock.hcl` to ensure deterministic builds across future pipeline runs. Green banner confirmed: `"Terraform has been successfully initialized!"`.

### 2. Infrastructure Code Validation (`terraform validate`):

![Terraform Validate Success](images/p10-step4-terraform-validate-success.png)
*Console State:* Executed `terraform validate` inside `infra/`. Verified declarative HCL syntax, module references, and type constraints across `main.tf`, `variables.tf`, `outputs.tf`, and `install.sh`. Green confirmation message received: `"Success! The configuration is valid."`.

### 3. AWS Programmatic Access Key Generation (Console Walkthrough):

![AWS Root User Access Key Warning](images/p10-step1-aws-root-access-key-warning.png)
*Console State:* Navigated to **Security credentials ➔ Access keys ➔ Create access key**. AWS displays best-practice advisory banner warning that root user access keys grant long-term unrestricted permissions.

![AWS Root Access Key Acknowledged](images/p10-step1-aws-root-access-key-acknowledged.png)
*Console State:* Selected acknowledgement checkbox `[✓] I understand creating a root access key is not a best practice, but I still want to create one.` The bottom-right orange button **`Create access key`** is now active and ready to provision temporary credentials for the local Terraform session.

![AWS Access Key Generated](images/p10-step1-aws-access-key-generated.png)
*Console State:* Clicked **Create access key**. Green confirmation banner confirmed: `"This is the only time that the secret access key can be viewed or downloaded..."`. Secret access key is safely masked. Successfully downloaded credentials via **`Download .csv file`** button to local workstation. Clicked orange **`Done`** button to finalize.

### 4. Execution Plan Generation & Resource Delta (`terraform plan`):

```text
Terraform used the selected providers to generate the following execution plan. Resource actions are indicated with the following symbols:
  + create

Terraform will perform the following actions:

  # aws_instance.wp will be created
  + resource "aws_instance" "wp" {
      + ami                         = "ami-0fc5120b2d80d4749" # Dynamic Ubuntu 24.04 LTS (ap-south-1)
      + instance_type               = "t3.micro"
      + key_name                    = "wp-lab-key"
      + tags_all                    = {
          + "Environment" = "lab"
          + "Name"        = "wp-lab"
          + "Project"     = "aws-learning"
        }
      + user_data                   = "7c1706c7ef8179db18628816fe6a8bbbd6c12d08"
      + root_block_device {
          + volume_size           = 20
          + volume_type           = "gp3"
        }
    }

  # aws_security_group.web will be created
  + resource "aws_security_group" "web" {
      + name        = "wp-lab-web-sg"
      + description = "Security group for WordPress web server"
      + ingress     = [ Inbound HTTP (80), HTTPS (443), SSH (22) from 0.0.0.0/0 ]
      + egress      = [ All Outbound Traffic (-1) to 0.0.0.0/0 ]
    }

Plan: 2 to add, 0 to change, 0 to destroy.

Changes to Outputs:
  + instance_id         = (known after apply)
  + instance_public_dns = (known after apply)
  + instance_public_ip  = (known after apply)
  + website_url         = (known after apply)
```
*Console State:* Executed `terraform plan` inside `infra/`. The HashiCorp AWS provider successfully authenticated using the session environment variables, queried AWS Mumbai (`ap-south-1`), resolved the latest Canonical Ubuntu 24.04 LTS AMI (`ami-0fc5120b2d80d4749`), computed the SHA1 hash of `install.sh`, and confirmed an execution plan of exactly **2 to add, 0 to change, 0 to destroy**.

</details>

---



<details>
<summary><h3>⚙️ Step 4 Execution Details: Provision Cloud Stack & Verify WordPress</h3></summary>

## Step 4 Execution Details: Provision Cloud Stack & Verify WordPress

### 1. Live Cloud Provisioning & Resource Outputs (`terraform apply`):

```text
PS C:\Users\HP\Desktop\Aws-wp-lab\infra> terraform apply

Do you want to perform these actions?
  Terraform will perform the actions described above.
  Only 'yes' will be accepted to approve.

  Enter a value: yes

aws_security_group.web: Creating...
aws_security_group.web: Creation complete after 2s [id=sg-035e7f0d68fe6d4dd]
aws_instance.wp: Creating...
aws_instance.wp: Still creating... [00m10s elapsed]
aws_instance.wp: Creation complete after 14s [id=i-0af3a3266517a12c6]

Apply complete! Resources: 2 added, 0 changed, 0 destroyed.

Outputs:

instance_id = "i-0af3a3266517a12c6"
instance_public_dns = "ec2-35-154-176-166.ap-south-1.compute.amazonaws.com"
instance_public_ip = "35.154.176.166"
website_url = "http://35.154.176.166"
```
*Console State:* Executed `terraform apply` with user approval (`yes`). In exactly **16 seconds**, Terraform provisioned `aws_security_group.web` (`sg-035e7f0d68fe6d4dd`) and deployed the Ubuntu 24.04 EC2 instance `aws_instance.wp` (`i-0af3a3266517a12c6`) with automated `install.sh` bootstrap. Verified public IP `35.154.176.166` actively serving web traffic with `HTTP/1.1 200 OK`.

### 2. End-to-End Functional Verification (Live WordPress Web Access):

![WordPress Live Install Screen](images/p10-step4-terraform-wordpress-live-install-screen.png)
*Console State:* Navigated to `http://35.154.176.166` in browser. Successfully resolved to `http://35.154.176.166/wp-admin/install.php` rendering the WordPress setup language selector. Verified that Nginx, PHP-FPM, MySQL, swap memory, and WordPress core files were provisioned 100% hands-free via Terraform and `install.sh` user-data!

</details>

---



<details>
<summary><h3>⚙️ Step 5 Execution Details: Provision S3 State Bucket & DynamoDB Lock Table via Bootstrap Code</h3></summary>

## Step 5 Execution Details: Provision S3 State Bucket & DynamoDB Lock Table via Bootstrap Code

Rather than manually clicking in the AWS Management Console (ClickOps), we adopt **Option A: Two-Stage Pure Code Bootstrapping**. A dedicated, standalone Terraform module (`bootstrap/`) using local state provisions the encrypted remote state bucket and the distributed DynamoDB state locking table 100% as code.

```text
[Two-Stage Bootstrapping Architecture]
1. bootstrap/ (Local State) ──(terraform apply)──► AWS S3 Bucket (wp-lab-tfstate-538820337783)
                                               └──► AWS DynamoDB Lock (wp-lab-tf-locks)
                                                          │
                                                          ▼ (Backend Ready)
2. infra/     (Migrate State) ──(init -migrate-state)──► Linked to Remote S3 + DynamoDB Backend
```

### 1. Declarative Bootstrap Infrastructure Code (`bootstrap/main.tf`):

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-south-1"

  default_tags {
    tags = {
      Project     = "aws-learning"
      Environment = "bootstrap"
    }
  }
}

# 1. S3 Bucket for Terraform Remote State Storage
resource "aws_s3_bucket" "state" {
  bucket        = "wp-lab-tfstate-538820337783"
  force_destroy = false # Protects state file from accidental destruction

  tags = {
    Name = "wp-lab-tfstate-538820337783"
  }
}

# 2. Enable S3 Bucket Versioning (Instant Disaster Recovery & Rollback)
resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id

  versioning_configuration {
    status = "Enabled"
  }
}

# 3. Enable Server-Side Encryption at Rest (SSE-S3 / AES-256)
resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# 4. Block All Public Access (Zero-Trust Private State Storage)
resource "aws_s3_bucket_public_access_block" "state" {
  bucket = aws_s3_bucket.state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 5. DynamoDB Table for Distributed State Locking (Concurrency Protection)
resource "aws_dynamodb_table" "locks" {
  name         = "wp-lab-tf-locks"
  billing_mode = "PAY_PER_REQUEST" # On-demand, AWS Free Tier friendly
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name = "wp-lab-tf-locks"
  }
}

# Outputs for Verification
output "s3_bucket_name" {
  description = "Remote state S3 bucket name"
  value       = aws_s3_bucket.state.id
}

output "dynamodb_table_name" {
  description = "DynamoDB state locking table name"
  value       = aws_dynamodb_table.locks.name
}
```

### 2. Bootstrap Core Workflow Validation:

#### A. Initializing AWS Provider (`terraform init` in `bootstrap/`):
```text
PS C:\Users\HP\Desktop\Aws-wp-lab\bootstrap> terraform init

Initializing the backend...

Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Installing hashicorp/aws v5.100.0...
- Installed hashicorp/aws v5.100.0 (signed by HashiCorp)

Terraform has created a lock file .terraform.lock.hcl to record the provider
selections it made above.

Terraform has been successfully initialized!
```

#### B. Syntax & HCL Validation (`terraform validate` in `bootstrap/`):
```text
PS C:\Users\HP\Desktop\Aws-wp-lab\bootstrap> terraform validate
Success! The configuration is valid.
```

### 3. Remote State & Locking Architectural Parameters:

| Component | Resource Name | Key Configuration | Architectural Purpose |
| :--- | :--- | :--- | :--- |
| **S3 Remote Bucket** | `wp-lab-tfstate-538820337783` | `force_destroy = false` | Centralized source of truth for cloud state; safe from accidental wipe. |
| **S3 Versioning** | `aws_s3_bucket_versioning` | `status = "Enabled"` | Instant disaster rollback if state file is accidentally corrupted. |
| **S3 Encryption** | `aws_s3_bucket_server_side_encryption` | `AES256` (SSE-S3) | Encrypts state file at rest to protect sensitive database passwords. |
| **Public Access Block** | `aws_s3_bucket_public_access_block` | All 4 ACL/policy flags `true` | Enforces Zero-Trust 100% private bucket isolation. |
| **DynamoDB State Lock** | `wp-lab-tf-locks` | `hash_key = "LockID"`, `PAY_PER_REQUEST` | Prevents race conditions and dual-apply state corruption across teams & CI/CD. |

### 4. Cloud Provisioning Output (`terraform apply`):

```text
PS C:\Users\HP\Desktop\Aws-wp-lab\bootstrap> terraform apply

Plan: 5 to add, 0 to change, 0 to destroy.

Changes to Outputs:
  + dynamodb_table_name = "wp-lab-tf-locks"
  + s3_bucket_name      = (known after apply)
aws_s3_bucket.state: Creating...
aws_dynamodb_table.locks: Creating...
aws_s3_bucket.state: Creation complete after 3s [id=wp-lab-tfstate-538820337783]
aws_s3_bucket_public_access_block.state: Creating...
aws_s3_bucket_server_side_encryption_configuration.state: Creating...
aws_s3_bucket_versioning.state: Creating...
aws_s3_bucket_public_access_block.state: Creation complete after 0s [id=wp-lab-tfstate-538820337783]
aws_s3_bucket_server_side_encryption_configuration.state: Creation complete after 0s [id=wp-lab-tfstate-538820337783]
aws_s3_bucket_versioning.state: Creation complete after 1s [id=wp-lab-tfstate-538820337783]
aws_dynamodb_table.locks: Still creating... [00m10s elapsed]
aws_dynamodb_table.locks: Creation complete after 14s [id=wp-lab-tf-locks]

Apply complete! Resources: 5 added, 0 changed, 0 destroyed.

Outputs:

dynamodb_table_name = "wp-lab-tf-locks"
s3_bucket_name = "wp-lab-tfstate-538820337783"
```
*Console State:* Executed `terraform apply` in `bootstrap/`. In exactly **14 seconds**, Terraform provisioned `wp-lab-tfstate-538820337783` (S3 state storage with SSE-S3 AES-256 encryption, bucket versioning enabled, and all 4 public access blocks strictly enforced) alongside `wp-lab-tf-locks` (DynamoDB table with `LockID` string hash key in Pay-Per-Request on-demand billing mode).

![S3 Remote State Bucket & DynamoDB Lock Created](images/p10-step5-bootstrap-s3-dynamodb-created.png)
*Console State:* Verified 5 resources created in AWS Mumbai (`ap-south-1`). `aws_s3_bucket.state` (`wp-lab-tfstate-538820337783`) provisioned with versioning, SSE-S3 AES-256 encryption, and private public access blocks. `aws_dynamodb_table.locks` (`wp-lab-tf-locks`) provisioned with hash key `LockID` for distributed state locking concurrency protection.

</details>

---

<details>
<summary><h3>⚙️ Step 6 Execution Details: Configure S3 Backend & Migrate Local State</h3></summary>

## Step 6 Execution Details: Configure S3 Backend & Migrate Local State

With our foundational remote state storage bucket and DynamoDB locking table provisioned, we transition the core infrastructure workspace (`infra/`) from local state (`terraform.tfstate` on disk) to remote state hosted securely in Amazon S3.

### 1. Backend Declaration (`infra/main.tf`):

Added the S3 backend configuration block at the top of `infra/main.tf`:

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "wp-lab-tfstate-538820337783"
    key            = "prod/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "wp-lab-tf-locks"
    encrypt        = true
  }
}
```

### 2. State Migration Execution (`terraform init -migrate-state`):

When Terraform detects that the backend has changed from `local` to `s3`, it automatically identifies the existing local `terraform.tfstate` (which contained our Security Group and EC2 Instance from Step 4) and copies it to the remote S3 bucket:

```text
PS C:\Users\HP\Desktop\Aws-wp-lab\infra> terraform init -migrate-state -force-copy

Initializing the backend...

Successfully configured the backend "s3"! Terraform will automatically
use this backend unless the backend configuration changes.

Initializing provider plugins...
- Reusing previous version of hashicorp/aws from the dependency lock file
- Using previously-installed hashicorp/aws v5.100.0

Terraform has been successfully initialized!
```

### 3. Verification & Zero-Drift Remote State Confirmation (`terraform plan`):

```text
PS C:\Users\HP\Desktop\Aws-wp-lab\infra> terraform plan
data.aws_ami.ubuntu: Reading...
aws_security_group.web: Refreshing state... [id=sg-035e7f0d68fe6d4dd]
data.aws_ami.ubuntu: Read complete after 1s [id=ami-0fc5120b2d80d4749]
aws_instance.wp: Refreshing state... [id=i-0af3a3266517a12c6]

No changes. Your infrastructure matches the configuration.
```

![Terraform State Migration & Remote Plan](images/p10-step6-terraform-init-migrate-state.png)
*Console State:* Verified state migration to `s3://wp-lab-tfstate-538820337783/prod/terraform.tfstate`. Terraform refreshed `aws_security_group.web` and `aws_instance.wp` live from S3 remote state and reported zero configuration drift (`No changes`). On the local machine, `infra/terraform.tfstate` was vacated to `0 bytes`, and `terraform.tfstate.backup` retained the safety snapshot.

### 4. Local vs Remote State File Evidence:

| State File Location | File Size Before Migration | File Size After Migration | Architectural Meaning |
| :--- | :--- | :--- | :--- |
| **`infra/terraform.tfstate`** | 12,232 bytes | **0 bytes** | State file completely transferred to AWS S3; local disk holds no sensitive state metadata. |
| **`infra/terraform.tfstate.backup`** | N/A | 12,232 bytes | Automatic safety backup created by Terraform CLI before releasing local state. |
| **`s3://wp-lab-tfstate.../prod/terraform.tfstate`** | 0 bytes (did not exist) | **Active Object in S3** | Encrypted (AES-256), version-controlled single source of truth for CI/CD runners. |

### 5. Hands-on Local Shell Verification Commands:
To independently verify both Step 5 and Step 6 from your own terminal:
* **Verify S3 & DynamoDB in bootstrap:**
  ```powershell
  cd C:\Users\HP\Desktop\Aws-wp-lab\bootstrap
  terraform show
  ```
* **Verify remote state & zero drift in infra:**
  ```powershell
  cd C:\Users\HP\Desktop\Aws-wp-lab\infra
  terraform plan
  ```

</details>

---

<details>
<summary><h3>⚙️ Step 7 Execution Details: Configure AWS IAM OIDC Provider & GitHub Actions Role</h3></summary>

## Step 7 Execution Details: Configure AWS IAM OIDC Provider & GitHub Actions Role

To achieve true enterprise-grade, passwordless GitOps CI/CD, we establish **OpenID Connect (OIDC)** cryptographic trust between GitHub Actions and AWS IAM.

### Why OIDC is the Non-Negotiable Industry Standard (Zero-Trust Security):
1. **The Insecure Legacy Way (Anti-Pattern):** Generating static IAM user access keys and saving them in GitHub Repository Secrets. These keys never expire, require manual 90-day rotation, and pose catastrophic account takeover risks if leaked in CI logs or compromised runner actions.
2. **The Modern OIDC Standard:** GitHub Actions requests a cryptographic JSON Web Token (JWT) on each pipeline run. AWS STS validates the signature against GitHub's public OIDC endpoint and returns a short-lived, 15-minute temporary credential. **Zero static keys are generated, stored, or leaked.**

### ⚖️ The Architectural Trade-off (Interview Answer):

| Dimension | Legacy GitHub Secrets (Old Way) | AWS IAM OIDC (Modern Industry Standard) |
| :--- | :--- | :--- |
| **Setup Time** | **2 Minutes:** Fast, low initial effort. | **10–15 Minutes:** OIDC identity provider and scoped trust policy configuration. |
| **Secret Leak Risk** | **Extremely High:** Static keys leaked = Full account compromise and unauthorized crypto-mining. | **ZERO:** No static keys exist anywhere to steal, leak, or expose in logs. |
| **Key Rotation Overhead** | **Manual Debt:** Ongoing manual secret rotation across repositories every 90 days. | **100% Automated:** AWS STS temporary tokens self-destruct after 15 minutes. |
| **Interview Value** | Junior level (Basic tutorial dependency). | **Senior / Staff DevOps level** (Demonstrates Zero-Trust least-privilege compliance). |

### 1. AWS IAM OpenID Connect (OIDC) Identity Provider Configuration:

![IAM Identity Providers Dashboard](images/p10-step7-iam-identity-providers-dashboard.png)
*Console State:* Navigated to **IAM ➔ Identity providers**. Currently shows `Identity providers (0)`. Initiating provider addition by clicking orange **`Add provider`** button.

- **Provider Type:** OpenID Connect
- **Provider URL:** `https://token.actions.githubusercontent.com`
- **Audience:** `sts.amazonaws.com`
- **Thumbprint:** Auto-resolved via AWS Console `"Get thumbprint"` button.

![Add Identity Provider Form Filled](images/p10-step7-add-identity-provider-form-filled.png)
*Console State:* Configured OpenID Connect provider parameters with Provider URL `https://token.actions.githubusercontent.com` and Audience `sts.amazonaws.com`. Ready to submit via orange **`Add provider`** button.

![OIDC Provider Added Successfully](images/p10-step7-oidc-provider-added-success.png)
*Console State:* Green confirmation banner confirmed: `"token.actions.githubusercontent.com added. You must assign an IAM role to start using this provider."` Verified `token.actions.githubusercontent.com` active in `Identity providers (1)` list with type `OpenID Connect`. Ready to assign role.

### 2. IAM Role Creation for GitHub Actions (Role Wizard):

![Assign Role Modal - Create a New Role](images/p10-step7-assign-role-modal-create-new-role.png)
*Console State:* Clicked **`Assign role`** in the green confirmation banner. In the **Assign role for token.actions.githubusercontent.com** modal, selected radio option **`Create a new role`** and clicked orange button **`Next`** to launch the role creation wizard.

![Create Role - Select Trusted Entity Web Identity](images/p10-step7-create-role-select-trusted-entity-web-identity.png)
*Console State:* In **Create role ➔ Select trusted entity**, `Web identity` automatically selected. Verified Identity provider pre-populated as `token.actions.githubusercontent.com`. Configured Audience `sts.amazonaws.com` and GitHub organization scoping `akshat009`.

![Create Role - Add Permissions](images/p10-step7-create-role-add-permissions.png)
*Console State:* In **Create role ➔ Add permissions**, navigated to the permission policy search catalog (`Permissions policies (1230)`). Initiated search filter for `AdministratorAccess`.'+

![Create Role - AdministratorAccess Selected](images/p10-step7-create-role-administrator-access-selected.png)
*Console State:* In **Create role ➔ Add permissions**, checked `[✓] AdministratorAccess` (`Permissions policies (1/1230)`). Advanced to role review by clicking orange button **`Next`**.

![Create Role - Name, Review, and Create](images/p10-step7-create-role-name-review-and-create.png)
*Console State:* In **Create role ➔ Name, review, and create**, verified generated OIDC Trust Policy (`sts:AssumeRoleWithWebIdentity` federated with `arn:aws:iam::538820337783:oidc-provider/token.actions.githubusercontent.com` scoped to `akshat009`) and attached permissions (`AdministratorAccess`). Named role `GitHubActionsTerraformRole` and submitted.

![GitHub Actions Role Created Successfully](images/p10-step7-github-actions-role-created-success.png)
*Console State:* Green confirmation banner confirmed: `"Role GitHubActionsTerraformRole created."` Verified `GitHubActionsTerraformRole` active in IAM Roles list, federated with `arn:aws:iam::538820337783:oidc-provider/token.actions.githubusercontent.com`. Passwordless Zero-Trust authentication foundation is 100% operational.

</details>

---

<details>
<summary><h3>⚙️ Step 8 Execution Details: Setup GitHub Actions GitOps CI/CD Workflow</h3></summary>

## Step 8 Execution Details: Setup GitHub Actions GitOps CI/CD Workflow

With the IAM OIDC Identity Provider and `GitHubActionsTerraformRole` configured in AWS, we automate the complete deployment lifecycle through GitHub Actions.

### 1. The GitOps Workflow Definition (`.github/workflows/terraform.yml`):

This pipeline implements passwordless Zero-Trust authentication, automatically executing `terraform plan` on Pull Requests and `terraform apply` when code merges into `main`.

```yaml
name: "Terraform GitOps CI/CD"

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main

permissions:
  id-token: write # Required for requesting the OIDC JWT token from GitHub
  contents: read  # Required for actions/checkout to read repo contents

jobs:
  terraform:
    name: "Terraform Plan and Apply"
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: infra

    steps:
      # 1. Checkout repository code
      - name: Checkout Code
        uses: actions/checkout@v4

      # 2. Authenticate to AWS via OIDC (Zero Static Keys!)
      - name: Configure AWS Credentials via OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::538820337783:role/GitHubActionsTerraformRole
          aws-region: ap-south-1

      # 3. Setup Terraform CLI on the runner
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.10.0

      # 4. Initialize Terraform against Remote S3 Backend + DynamoDB Lock
      - name: Terraform Init
        run: terraform init

      # 5. Validate HCL Syntax
      - name: Terraform Validate
        run: terraform validate

      # 6. Generate Execution Plan
      - name: Terraform Plan
        run: terraform plan -no-color

      # 7. Apply Changes Automatically (Only on Merge to Main)
      - name: Terraform Apply
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        run: terraform apply -auto-approve
```

### 2. Breakdown of Critical Pipeline Directives:

| Directive | Architectural Purpose | Why It Matters (Interview Answer) |
| :--- | :--- | :--- |
| **`id-token: write`** | Grants runner permission to request OIDC JSON Web Token (JWT) from GitHub's token authority. | STS authentication fails without this explicit permission block. |
| **`working-directory: infra`** | Runs all Terraform commands directly within the main active workload folder. | Isolates active app infrastructure from the `bootstrap/` vault and root repository docs. |
| **`role-to-assume`** | Specifies the exact ARN of `GitHubActionsTerraformRole` in AWS IAM. | Runner assumes this role for 15 minutes, receives temporary STS credentials, and leaves zero static keys. |
| **`if: github.ref == ...`** | Restricts `terraform apply` exclusively to merged pushes on the `main` branch. | Prevents unreviewed PRs from modifying live production cloud infrastructure. |

### 3. Defense-in-Depth Repository Ignore Rules (`.gitignore`):

To guarantee zero secrets, state, or temporary files are ever pushed to GitHub, `.gitignore` enforces strict exclusions:

```gitignore
# OS
.DS_Store
Thumbs.db

# Editors / IDEs
.vscode/
.idea/

# Environment / secrets
.env
.env.*
*.pem
*.key
*.csv

# Logs
*.log

# Dependencies
node_modules/
vendor/

# Terraform
*.tfstate
*.tfstate.backup
.terraform/

# WordPress
wp-config.php
```

| Pattern | Threat Mitigated |
| :--- | :--- |
| **`*.tfstate`, `*.tfstate.backup`** | Prevents sensitive database passwords, private keys, and cloud metadata from ever entering Git commit history. |
| **`*.pem`, `*.key`, `*.csv`** | Prevents SSH private keys and AWS root credential files (`rootkey.csv`) from being leaked publicly. |
| **`.terraform/`** | Prevents committing hundreds of megabytes of cached AWS provider binaries and plugins. |
| **`wp-config.php`, `.env`** | Prevents live WordPress database connection strings and application environment secrets from exposure. |

### 4. Git Push & Pipeline Trigger Evidence:

![Git Push Main Success](images/p10-step8-git-push-main-success.png)
*Console State:* Executed `git push -u origin main` in PowerShell. Successfully transferred 441 objects (31.99 MiB) to `https://github.com/akshat009/Aws-wp-lab.git` setting up `main` branch to track `origin/main`. Automated GitHub Actions workflow immediately triggered on push.

![GitHub Actions All Workflows Dashboard](images/p10-step8-github-actions-all-workflows-list.png)
*Console State:* In **GitHub ➔ Actions**, verified workflow `Terraform GitOps CI/CD` triggered automatically from the commit. Displays the execution record for `feat: phase 10 enterprise gitops terraform with oidc` on branch `main`.

### 5. Verified Pipeline Execution (100% Green CI/CD):

```text
✓ main Terraform GitOps CI/CD · 42020799853
Triggered via push
✓ Terraform Plan & Apply in 46s (ID 127222778150)
  ✓ Set up job
  ✓ Checkout Code
  ✓ Inspect OIDC Token Claims
  ✓ Configure AWS Credentials via OIDC
  ✓ Setup Terraform
  ✓ Terraform Init
  ✓ Terraform Validate
  ✓ Terraform Plan
  ✓ Terraform Apply
  ✓ Post Configure AWS Credentials via OIDC
  ✓ Post Checkout Code
  ✓ Complete job

Apply complete! Resources: 0 added, 0 changed, 0 destroyed.
```
*Pipeline State:* Successfully assumed IAM Role `GitHubActionsTerraformRole` passwordlessly via GitHub OIDC JWT, verified remote state in S3 `wp-lab-tfstate-538820337783` with DynamoDB lock table `wp-lab-tf-locks`, validated zero infrastructure drift, and completed `terraform apply` in 46 seconds without a single static AWS secret!

</details>

---


<details>
<summary><h3>🛡️ Step 9 Execution Details: Revoke & Delete Root Access Keys (Enforce Zero-Trust)</h3></summary>

## Step 9 Execution Details: Revoke & Delete Root Access Keys (Enforce Zero-Trust)

With GitHub Actions passwordless CI/CD established via AWS IAM OIDC, permanent static credentials are no longer required on developer workstations.

### 1. Zero-Trust Security Enforcement:
- Navigated to **AWS Management Console ➔ Security credentials ➔ Access keys**.
- Permanently deleted root access key `AKIAX25BR4B3TYTG22TW`.
- **Enforces AWS Foundational Security Best Practice:** Zero permanent static access keys exist on developer laptops or in CI/CD configuration.
- All deployments now execute exclusively through short-lived, cryptographically signed 15-minute AWS STS session tokens.

</details>

---

<details>
<summary><h3>🏁 Step 10 Execution Details: Verify "Done When" Criteria (Teardown & Automated Rebuild)</h3></summary>

## Step 10 Execution Details: Verify "Done When" Criteria (Teardown & Automated Rebuild)

The definitive success metric of Phase 10 is the automated lifecycle test:
> *"Done when: `terraform destroy` then `terraform apply` brings the site back"*

### 1. Dual-Action GitOps Workflow (`workflow_dispatch`):
To enable safe manual execution of destroy and rebuild without granting static credentials to developer laptops, `.github/workflows/terraform.yml` includes an on-demand dispatcher:

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
    inputs:
      action:
        description: "Terraform Action to execute"
        required: true
        default: "apply"
        type: choice
        options:
          - apply
          - destroy
```

### 2. Execution Phase A: Infrastructure Teardown (`terraform destroy`):
- **Command:** `gh workflow run terraform.yml -f action=destroy`
- **Result:**
  - GitHub Actions requests OIDC STS session token.
  - Terraform locks state in DynamoDB table `wp-lab-tf-locks`.
  - Terminates EC2 instance `wp-lab-tf` and deletes Security Group `wp-lab-web-sg`.
  - Destroys 2 resources; releases DynamoDB lock.
  - Verified in AWS EC2 Console: Instance state = `Terminated`. Site at previous IP is completely offline.

```text
✓ main Terraform GitOps CI/CD · 42028596035
✓ Terraform Plan & Apply in 1m21s (ID 127248963562)
  ✓ Set up job
  ✓ Checkout Code
  ✓ Inspect OIDC Token Claims
  ✓ Configure AWS Credentials via OIDC
  ✓ Setup Terraform
  ✓ Terraform Init
  ✓ Terraform Validate
  - Terraform Plan (Skipped)
  - Terraform Apply (Skipped)
  ✓ Terraform Destroy (Executed)
  ✓ Complete job

aws_instance.wp: Destroying... [id=i-0af3a3266517a12c6]
aws_security_group.web: Destruction complete after 1s
Destroy complete! Resources: 2 destroyed.
```

![Workflow Dispatch Destroy Triggered](images/p10-step10-workflow-dispatch-destroy-prompt.png)
*Terminal State:* Executed `gh workflow run terraform.yml -f action=destroy`. Pipeline run `#42028596035` executed `terraform destroy -auto-approve` in 1m 21s via passwordless OIDC, completely destroying the compute and firewall tier.

![Site Unreachable Following Terraform Destroy](images/p10-step10-teardown-site-unreachable.png)
*Browser State:* Attempted to access `http://35.154.176.166`. Browser returned `ERR_CONNECTION_TIMED_OUT` ("This site can't be reached"), definitively confirming 100% cloud teardown of the EC2 instance and Security Group.

### 3. Execution Phase B: Automated Rebuild (`terraform apply`):
- **Command:** `gh workflow run terraform.yml -f action=apply` (or automated push to `main`)
- **Execution Log (GitHub Actions Run `#42028951514`):**
  ```text
  ✓ main Terraform GitOps CI/CD · 42028951514
  ✓ Terraform Plan & Apply in 57s
    ✓ Set up job
    ✓ Checkout Code
    ✓ Inspect OIDC Token Claims
    ✓ Configure AWS Credentials via OIDC
    ✓ Setup Terraform
    ✓ Terraform Init
    ✓ Terraform Validate
    ✓ Terraform Plan
    ✓ Terraform Apply
    ✓ Complete job

  Apply complete! Resources: 2 added, 0 changed, 0 destroyed.

  Outputs:
  instance_id = "i-0fca9a4b647516a51"
  instance_public_dns = "ec2-35-154-149-207.ap-south-1.compute.amazonaws.com"
  instance_public_ip = "35.154.149.207"
  website_url = "http://35.154.149.207"
  ```
- **Live Verification:**
  - `http://35.154.149.207/wp-admin/install.php` returned `HTTP 200 OK`.
  - WordPress setup wizard rendered cleanly, confirming full end-to-end automation from code.
  - **Phase 10 Definition of Done Officially Met!**

</details>

---

<details>
<summary><h3>💡 Execution Details & Real-World Gotchas</h3></summary>

## Execution Details & Real-World Gotchas

### Gotcha 1: "The term 'terraform' is not recognized" (PATH Not Reloaded in Existing PowerShell Session)
- **Symptom:** Running `terraform -version` immediately after `winget install Hashicorp.Terraform` in the same shell fails with:
  ```text
  terraform : The term 'terraform' is not recognized as the name of a cmdlet, function, script file, or operable program.
  ```

![Terraform Not Recognized in Same Shell](images/p10-gotcha1-terraform-path-not-recognized-same-shell.png)

- **Cause:** When `winget` completes the package installation, it updates the system `Path` in the Windows Registry. However, active PowerShell processes inherit a snapshot of environment variables at the moment they launch. An existing terminal session cannot see Registry `Path` modifications made by external installers while running.
- **Fix:** Either close and re-open PowerShell, or dynamically reload the session `Path` without restarting using:
  ```powershell
  $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
  ```

### Gotcha 2: Invalid Quoted Type Constraints (`type = "string"`)
- **Symptom:** Running `terraform validate` fails with:
  ```text
  Error: Invalid quoted type constraints
  ```
- **Cause:** In older Terraform versions (v0.11 and earlier), type constraints were quoted strings (e.g. `type = "string"`). In modern Terraform (v0.12+ and v1.0+), primitive types are first-class keywords and must be unquoted (`type = string`, `type = number`, `type = bool`).
- **Fix:** Removed quotes around `string` in `variables.tf`.

### Gotcha 3: Dynamic Public IP vs Elastic IP & Two Parallel Environments
- **Symptom / Question:** *"Did a new Elastic IP get created? Why is `lab.asaxenadev.com` running separately while this runs on `35.154.176.166`?"*
- **Cause:** 
  1. Terraform launched EC2 with AWS's default **Dynamic Public IPv4** (`35.154.176.166`), which is free while the instance is running. No `aws_eip` resource was written, so zero idle Elastic IP charges occur.
  2. AWS Mumbai is actively running two separate servers:
     - *Manual Lab Server (Phases 1–9):* Elastic IP `43.205.26.235` behind ALB.
     - *Terraform Server (Phase 10):* Dynamic IP `35.154.176.166` built from HCL.
- **Fix:** Proves Terraform's superpower to create an isolated clean-room environment in 16 seconds without disturbing or breaking the existing production stack.

### Gotcha 4: Greenfield vs Brownfield Migration (`terraform import` Pitfalls)
- **Symptom / Question:** *"Will we migrate our manual Phase 1–9 server into Terraform?"*
- **Cause:** 
  - **Brownfield (`terraform import`):** Forcing manually clicked resources into Terraform state. High risk due to manual configuration drift (untracked security rules, manual packages).
  - **Greenfield (Clean-Room Approach — Our Strategy):** Writing clean, deterministic code from scratch. Once verified that code rebuilds the complete WordPress stack on demand, the old manual server is retired.
- **Fix:** Focus on *"One Command Up, One Command Down"*. `terraform apply` brings the site up; `terraform destroy` wipes it clean for zero billing.

### Gotcha 5: Custom Domain Resolution (`lab.asaxenadev.com` on Hostinger DNS)
- **Symptom / Question:** *"Will `lab.asaxenadev.com` run through Terraform? Why test with direct IP?"*
- **Cause:** 
  - Domain DNS is managed on **Hostinger Authoritative Nameservers**, not Cloudflare.
  - DNS only routes to an IP or CNAME; it doesn't care if the server was made by hand or by Terraform.
  - Testing is done via direct IP because `terraform destroy` and `apply` cycles change IPs; testing on direct IP avoids waiting for DNS TTL cache propagation.
- **Fix:** Once testing passes, updating Hostinger DNS A-record to the Terraform IP connects `lab.asaxenadev.com` instantly.

### Gotcha 6: The "Chicken-and-Egg" Dilemma of Terraform Remote State Bootstrap
- **Symptom / Question:** *"When we are writing Terraform (IaC) to automate everything, why do we need to touch the AWS Console to create the S3 state bucket and DynamoDB table? Can't Terraform create them itself?"*
- **Cause (The Circular Dependency):**
  - Terraform requires an S3 bucket and a DynamoDB table to *store* its remote state.
  - However, if you declare `aws_s3_bucket` and `aws_dynamodb_table` inside the very same `main.tf` that defines `backend "s3"`, running `terraform init` crashes before anything can be created because the remote backend does not yet exist!
  - You cannot store state in a bucket that hasn't been provisioned, and you cannot provision resources via remote state without an initialized backend.
- **How Industry Resolves This (Trade-offs & Company Archetypes):**

| Approach | Who Uses It? | How it Works | Pros / Benefit | Cons / Architectural Trade-off |
| :--- | :--- | :--- | :--- | :--- |
| **1. One-Time CLI / Console Bootstrap** | Startups, Rapid POCs, Single Projects | Create 1 S3 bucket + 1 DynamoDB table via AWS Console or 1-line AWS CLI once in the account's lifetime. | **Fastest (< 1 min):** Zero code overhead, immediate start. | **Manual Debt:** Initial prerequisite action happens outside Git; not auditable in code. |
| **2. Two-Stage Code Bootstrap (`bootstrap/`)** | Mid-Sized Tech Companies & Senior DevOps | A dedicated `bootstrap/` folder declares the S3 bucket & DynamoDB table using **Local State** (`terraform apply`). Once created, the primary `infra/` workspace links its `backend "s3"` to it. | **100% Pure IaC:** Zero console clicking, fully auditable in Git PRs, automated repeatability. | **Dual State Overhead:** Requires managing 2 separate state files (`bootstrap/` state vs `infra/` state). |
| **3. Pre-Vended Landing Zones (Account Vending)** | Large Enterprises (Netflix, Uber, Banks) | Central Platform Engineering teams deploy AWS Control Tower / CloudFormation StackSets to automatically vend state buckets when accounts are created. | **Zero Dev Friction:** Application teams find state buckets ready on day one. | **High Complexity:** Takes weeks/months to architect; requires dedicated platform teams. |

- **Interview Tip (How to Answer "What is Best Practice?"):**
  > *"Rather than picking a single dogma, answer with the trade-off: In organizations with central platform teams, remote backends are pre-vended via landing zones. In standalone projects without landing zones, the industry gold standard is **Two-Stage Code Bootstrapping (`bootstrap/`)** — this guarantees 100% of infrastructure remains auditable code in Git while accepting the minor overhead of a small, separate bootstrap state file."*

### Gotcha 7: Terraform v1.10+ `dynamodb_table` Deprecation Warning vs `use_lockfile`
- **Symptom:** Running `terraform init` or `terraform plan` outputs:
  ```text
  Warning: Deprecated Parameter
  The parameter "dynamodb_table" is deprecated. Use parameter "use_lockfile" instead.
  ```
- **Cause:** Starting with Terraform v1.10, HashiCorp introduced native S3 object lock state concurrency (`use_lockfile = true`) directly inside S3 buckets, removing the requirement for a separate DynamoDB table. However, AWS enterprise environments have used DynamoDB distributed locking for over a decade, and `dynamodb_table` remains 100% supported and universally recognized.
- **Trade-off:**
  - *Classic DynamoDB Locking (`dynamodb_table`):* Battle-tested over 10+ years across every AWS production workload.
  - *Native S3 Lockfile (`use_lockfile = true`):* Modern single-service convenience that eliminates the DynamoDB table, but requires S3 conditional write features supported in newer Terraform releases.
- **Fix:** Both patterns are completely production-ready. We used DynamoDB to master the classic AWS enterprise locking architecture required in senior DevOps interviews.

### Gotcha 8: Embedded Git Repositories Warning (`warning: adding embedded git repository`) in Monorepos
- **Symptom:** Running `git add .` in the root workspace outputs:
  ```text
  warning: adding embedded git repository: aws-wp-plugin
  hint: You've added another git repository inside your current repository.
  hint: Clones of the outer repository will not contain the contents of
  hint: the embedded repository and will not know how to obtain it.
  hint: If you meant to add a submodule, use:
  hint:   git submodule add <url> aws-wp-plugin
  hint: If you added this path by mistake, you can remove it from the index with:
  hint:   git rm --cached aws-wp-plugin
  ```
- **Cause:** In Phase 3, `aws-wp-plugin` was developed and initialized as a standalone Git repository with its own `.git` directory for testing standalone GitHub Actions CI/CD. When initializing the parent repository (`Aws-wp-lab`) in Phase 10 and executing `git add .`, Git detected the nested `.git` directory and staged it as a **gitlink** (subproject SHA pointer without a remote submodule URL) rather than tracking the PHP files inside it.
- **Why Avoid It / Architectural Risk:**
  1. **Silent Code Loss on Remote Clones:** Anyone cloning `Aws-wp-lab` or pulling the code in CI/CD runners (like GitHub Actions) will find an empty `aws-wp-plugin/` directory.
  2. **Pipeline Build Failures:** Any automated test or build step relying on files inside the nested folder fails because Git never actually committed the source files.
- **Fix & Clean Resolution:**
  1. Delete the nested `.git` metadata folder from the embedded directory:
     ```powershell
     Remove-Item -Recurse -Force aws-wp-plugin\.git
     ```
  2. Unstage the gitlink pointer from Git's index:
     ```powershell
     git rm --cached aws-wp-plugin
     ```
  3. Re-stage all files normally into the root monorepo:
     ```powershell
     git add .
     ```
  4. In large-scale enterprise environments with independent release lifecycles across repositories, use official Git submodules (`git submodule add <url> <path>`) instead of ad-hoc nested Git directories.

### Gotcha 9: GitHub Push Rejected — Missing `workflow` Scope for GitHub Actions
- **Symptom:** Running `git push` or `gh repo create --push` rejects the push with:
  ```text
  ! [remote rejected] HEAD -> main (refusing to allow an OAuth App to create or update workflow '.github/workflows/terraform.yml' without 'workflow' scope)
  error: failed to push some refs to 'https://github.com/akshat009/Aws-wp-lab.git'
  failed to run git: exit status 1
  ```

![GitHub Push Rejected Missing Workflow Scope](images/p10-gotcha9-github-push-workflow-scope-error.png)
*Console State:* Terminal shows repository `akshat009/Aws-wp-lab` created successfully on GitHub and remote added. However, Git rejected pushing `main` because GitHub CLI's OAuth token did not possess the privileged `workflow` scope required to write into `.github/workflows/`.

- **Cause:** GitHub treats GitHub Actions workflows as sensitive security boundaries. A compromised third-party app or token with standard `repo` scope could inject malicious CI/CD code (e.g. secret stealers or crypto-miners). Therefore, GitHub strictly mandates that any OAuth app or CLI pushing to `.github/workflows/*.yml` must be explicitly authorized with the dedicated `workflow` permission scope.
- **Fix:** Refresh the GitHub CLI authentication session to add the `workflow` scope:
  ```powershell
  gh auth refresh -s workflow
  ```

![GitHub Device Authorization](images/p10-step8-github-device-authorization-prompt.png)
*Console State:* Executing `gh auth refresh -s workflow` prints an 8-character one-time verification code in PowerShell (e.g. `XXXX-XXXX`) and automatically opens `https://github.com/login/device`. Pasting the code and clicking **Continue ➔ Authorize github** initiates the additional scope approval.

![GitHub CLI Requesting Workflow Scope](images/p10-step8-github-cli-authorize-workflow-scope.png)
*Console State:* On `https://github.com/login/device/confirmation`, GitHub displays the explicit permission elevation request: `"GitHub CLI by GitHub would like additional permissions to: Workflow (Update GitHub Action workflow files)"`. Clicking the green **`Authorize github`** button permanently grants workflow permissions to the local CLI session.

![GitHub Device Authorization Success](images/p10-step8-github-device-connected-success.png)
*Console State:* Browser navigates to `https://github.com/login/device/success` rendering green confirmation: `"Congratulations, you're all set! Your device is now connected."` GitHub CLI is now fully authorized with the `workflow` OAuth scope.

  Complete the browser/device code authentication prompt, then re-push cleanly:
  ```powershell
  git push -u origin main
  ```

### Gotcha 10: OIDC AssumeRole Denied — "Not authorized to perform sts:AssumeRoleWithWebIdentity" (Subject Claim `sub` Mismatch)
- **Symptom:** In the GitHub Actions runner execution log for step `Configure AWS Credentials via OIDC`, the workflow fails with:
  ```text
  Assuming role with OIDC
  Assuming role with OIDC
  ...
  ##[error]Could not assume role with OIDC: Not authorized to perform sts:AssumeRoleWithWebIdentity
  ```

![GitHub Actions OIDC AssumeRole Failed Annotation](images/p10-step8-github-actions-oidc-error-annotations.png)
*Console State:* In **GitHub Actions ➔ Summary**, the workflow execution reports `Annotations: 1 error`: `"Could not assume role with OIDC: Not authorized to perform sts:AssumeRoleWithWebIdentity"`. AWS STS denied role assumption due to token claim mismatch.
- **Cause:** 
  1. OpenID Connect relies on cryptographic claims packaged inside a JSON Web Token (JWT) issued by GitHub's token authority (`token.actions.githubusercontent.com`).
  2. When GitHub Actions triggers, the JWT contains:
     - `iss`: `https://token.actions.githubusercontent.com`
     - `aud`: `sts.amazonaws.com`
     - `sub`: `repo:<owner>/<repo-name>:ref:refs/heads/<branch>` (e.g. `repo:akshat009/Aws-wp-lab:ref:refs/heads/main`).
  3. In AWS IAM, the Role's **Trust Policy** defines who is permitted to call `sts:AssumeRoleWithWebIdentity`.
  4. When the role is created via the AWS Console wizard before the repository is created on GitHub, the wizard creates a broad or malformed condition (e.g. `"repo:akshat009/*:*"` or `"repo:akshat009:*"` with `StringEquals`). Because the format has colons separating repo, ref type, and branch, any mismatch between the token's `sub` claim and the IAM Trust Policy condition results in AWS STS returning `HTTP 403 AccessDenied`.
- **Architectural Trade-offs & Security Risks:**
  - **Overly Permissive Anti-Pattern:** Setting `"token.actions.githubusercontent.com:sub": "repo:*"` allows *any* GitHub repository in the world to assume your AWS Administrator role!
  - **Overly Restrictive Anti-Pattern:** Setting `StringEquals` to `"repo:akshat009/Aws-wp-lab:ref:refs/heads/main"` breaks Pull Request checks (`pull_request` event has `ref:refs/pull/1/merge` which fails `StringEquals`).
  - **Enterprise Best Practice:** Use `StringLike` scoped to the exact repository followed by a wildcard `*` (`repo:akshat009/Aws-wp-lab:*`).
- **Fix & Clean Resolution:**
  1. Open **AWS Management Console** ➔ **IAM** ➔ **Roles** ➔ Click **`GitHubActionsTerraformRole`**.
  2. Navigate to **Trust relationships** tab ➔ Click **Edit trust policy**.
  3. Update the trust policy to use `StringLike` matching the repository namespace:
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Effect": "Allow",
           "Principal": {
             "Federated": "arn:aws:iam::538820337783:oidc-provider/token.actions.githubusercontent.com"
           },
           "Action": "sts:AssumeRoleWithWebIdentity",
           "Condition": {
             "StringEquals": {
               "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
             },
             "StringLike": {
               "token.actions.githubusercontent.com:sub": [
                 "repo:akshat009/Aws-wp-lab:*",
                 "repo:akshat009/aws-wp-lab:*"
               ]
             }
           }
         }
       ]
     }
     ```

![Edit Trust Policy Wildcard Advisory Warning](images/p10-gotcha10-edit-trust-policy-wildcard-warning.png)
*Console State:* In **IAM ➔ Roles ➔ GitHubActionsTerraformRole ➔ Edit trust policy**, pasted the updated repository trust policy. AWS displays `Errors: 0` and an advisory notification: `"Using a wildcard (*) in token.actions.githubusercontent.com:sub can allow requests from more sources than you intended"`. This warning confirms that both `main` branch pushes and Pull Request workflows from `akshat009/Aws-wp-lab` can assume the role. Ready to finalize via orange **`Update policy`** button.

#### ⚠️ Deep Dive: Why AWS Displays "Warnings: 1" for Wildcard (*) in `sub`:
- **The AWS Advisory Warning:**
  > *"Using a wildcard (*) in token.actions.githubusercontent.com:sub can allow requests from more sources than you intended. Specify the value of token.actions.githubusercontent.com:sub with the repository and branch name. If the subject claim does not include the branch, specify it in a token.actions.githubusercontent.com:ref condition key."*
- **Why This Warning is 100% Safe & Architecturally Necessary (The GitOps Reality):**
  1. **AWS's Ultra-Defensive Stance:** AWS IAM warns you because it considers locking down the role to a single hardcoded branch (like `main`) as the strictest possible constraint.
  2. **Why Locking to `main` Breaks GitOps Workflows:** In real-world software engineering, developers do not push directly to `main`. They create feature branches (e.g., `feat/rds-multi-az`) and submit **Pull Requests (PRs)**. During a PR, GitHub Actions automatically executes `terraform plan` to preview the cost and infrastructure diff *before* merging.
  3. **The Token Ref Format Difference:**
     - A push to `main` sends `sub`: `repo:akshat009/Aws-wp-lab:ref:refs/heads/main`.
     - A Pull Request sends `sub`: `repo:akshat009/Aws-wp-lab:pull_request` (or `ref:refs/pull/1/merge`).
     If you eliminate the `*` wildcard and hardcode `:ref:refs/heads/main`, every single Pull Request pipeline run will immediately crash with `HTTP 403 / AssumeRoleWithWebIdentity AccessDenied`!
  4. **The Security Guarantee:** Because the condition begins with `repo:akshat009/Aws-wp-lab:*`, **zero outside repositories can ever assume this role**. Only GitHub Actions pipelines running code inside your exact repository can authenticate. This strikes the perfect balance between Zero-Trust least privilege and functional GitOps automation.

  4. Click **Update policy** to apply the fix.

![IAM Trust Policy Updated Success](images/p10-gotcha10-trust-policy-updated-success.png)
*Console State:* Clicked orange button **`Update policy`**. Top green confirmation banner confirmed: `"Trust policy updated."` The IAM Role now actively trusts both `repo:akshat009/Aws-wp-lab:*` and `repo:akshat009/aws-wp-lab:*` with `sts.amazonaws.com` audience, allowing GitHub Actions OIDC to authenticate passwordless.

### Gotcha 11: GitHub Actions OIDC Default Audience Mismatch (`aud` Claim: Repo Owner URL vs `sts.amazonaws.com`)
- **Symptom:** Even after updating the IAM Role Trust Policy with valid `repo:akshat009/Aws-wp-lab:*` subject conditions, GitHub Actions continues to fail at `Configure AWS Credentials via OIDC` with:
  ```text
  ##[error]Could not assume role with OIDC: Not authorized to perform sts:AssumeRoleWithWebIdentity
  ```
- **Cause (The Implicit Default Audience Pitfall):**
  1. OpenID Connect relies on the `aud` (Audience / Client ID) claim to prevent token replay attacks across different platforms.
  2. In AWS IAM, the OIDC Identity Provider and Role Trust Policy explicitly require:
     ```json
     "StringEquals": {
       "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
     }
     ```
  3. However, under GitHub's official OIDC specification, when a workflow step uses `aws-actions/configure-aws-credentials` without an explicit `audience` parameter, GitHub's token authority defaults the minted JWT's `aud` claim to the **repository owner URL** (e.g., `https://github.com/akshat009`).
  4. When GitHub Actions presents this JWT to AWS STS, STS inspects `aud`. Because `https://github.com/akshat009` does not equal `sts.amazonaws.com`, AWS STS terminates the authentication handshake with `HTTP 403 AccessDenied`.
- **Architectural Security Purpose (Why Audience Exists):**
  - Audience validation prevents "Confused Deputy" attacks. If AWS STS accepted tokens with arbitrary audiences, a token minted for a harmless third-party reporting service could be intercepted and maliciously used to assume high-privilege AWS IAM administrator roles.
- **Fix & Clean Resolution:**
  Explicitly pass `audience: sts.amazonaws.com` in `.github/workflows/terraform.yml`:
  ```yaml
  - name: Configure AWS Credentials via OIDC
    uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::538820337783:role/GitHubActionsTerraformRole
      aws-region: ap-south-1
      audience: sts.amazonaws.com
  ```
  Additionally, adding an OIDC inspection debug step (`curl -sLS "${ACTIONS_ID_TOKEN_REQUEST_URL}&audience=sts.amazonaws.com" ... | jq .`) allows developers to decode and audit the live JWT payload (`iss`, `aud`, `sub`) directly in CI runner logs.




### Gotcha 12: GitHub OIDC Immutable Repository/Owner Numeric IDs in `sub` Claim (`@<id>`)

- **Symptom:** Even after adding `audience: sts.amazonaws.com` and setting up the IAM Trust Policy for `"repo:akshat009/Aws-wp-lab:*"`, GitHub Actions fails at `Configure AWS Credentials via OIDC` with:

  ```text

  ##[error]Could not assume role with OIDC: Not authorized to perform sts:AssumeRoleWithWebIdentity

  ```

- **Discovery (The Decoded OIDC Token Clue):**

  By adding an OIDC JWT inspection step to `.github/workflows/terraform.yml`, we extracted and decoded the live token payload minted by GitHub's token endpoint (`ACTIONS_ID_TOKEN_REQUEST_URL`):

  ```json

  {

    "iss": "https://token.actions.githubusercontent.com",

    "aud": "sts.amazonaws.com",

    "sub": "repo:akshat009@23046599/Aws-wp-lab@1446782706:ref:refs/heads/main",

    "repository": "akshat009/Aws-wp-lab",

    "repository_owner": "akshat009",

    "ref": "refs/heads/main",

    "event_name": "push"

  }

  ```

- **Cause (Immutable Database IDs in Subject Claim):**

  1. Notice the `sub` claim value:

     `repo:akshat009@23046599/Aws-wp-lab@1446782706:ref:refs/heads/main`

  2. GitHub Actions dynamically appends the **immutable user ID** (`@23046599`) and **immutable repository ID** (`@1446782706`) into the subject string.

  3. **Why GitHub does this:** To prevent "repo-jacking" and "account renaming" exploits. If an organization deletes a repo or renames an account, an attacker could recreate the same repository name and inherit the AWS IAM Role if IAM only matched the plain string name. Adding immutable IDs ensures cryptographic binding to that exact database record on GitHub.

  4. **Why AWS STS Failed:** The AWS IAM Role Trust Policy was checking `StringLike` for `"repo:akshat009/Aws-wp-lab:*"`. Because of the `@23046599` and `@1446782706` suffixes, AWS IAM evaluated `"repo:akshat009@..."` against `"repo:akshat009/..."`, which failed string matching and resulted in `sts:AssumeRoleWithWebIdentity: AccessDenied`.

- **Fix (Multi-Pattern Condition in IAM Trust Policy):**

  Update the IAM Role Trust Policy to include both wildcard pattern matching (`repo:akshat009*/Aws-wp-lab*:*`) and the exact immutable ID string:

  ```json

  {

    "Version": "2012-10-17",

    "Statement": [

      {

        "Effect": "Allow",

        "Principal": {

          "Federated": "arn:aws:iam::538820337783:oidc-provider/token.actions.githubusercontent.com"

        },

        "Action": "sts:AssumeRoleWithWebIdentity",

        "Condition": {

          "StringEquals": {

            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"

          },

          "StringLike": {

            "token.actions.githubusercontent.com:sub": [

              "repo:akshat009@23046599/Aws-wp-lab@1446782706:*",

              "repo:akshat009*/Aws-wp-lab*:*",

              "repo:akshat009/Aws-wp-lab:*",

              "repo:akshat009/aws-wp-lab:*"

            ]

          }

        }

      }

    ]

  }

  ```

*Console State:* Updated the IAM Role Trust Policy with GitHub's immutable numeric identifiers (`repo:akshat009@23046599/Aws-wp-lab@1446782706:*`). Top green banner confirms `"Trust policy updated."`.

![IAM Role Trust Policy Updated with Immutable IDs](images/p10-step8-iam-trust-policy-immutable-id-updated.png)




</details>

---



<details>
<summary><h3>🏢 Enterprise Best Practices vs Lab Setup Trade-offs</h3></summary>

## 🏢 Enterprise Best Practices vs Lab Setup Trade-offs

```text
[Developer Workstation] ──(PR in GitHub)──► [CI/CD Pipeline: GitHub Actions]
                                                           │
                                                           │ OIDC Token (Zero Static Secrets!)
                                                           ▼
                                                  [AWS IAM Role: AssumeRole]
                                                           │
                                        ┌──────────────────┴──────────────────┐
                                        ▼                                     ▼
                            [Remote S3 State + DynamoDB]         [AWS Cloud Infrastructure]
                            (SSE-KMS + Versioning + State Lock)  (VPC, EC2, RDS, ALB, ASG)
```

### 1. Authentication (Zero Static Keys Policy)
- **Lab Setup:** Temporary Root / IAM User Access Key & Secret Key used locally in PowerShell.
- **Enterprise Practice:** 
  - Storing permanent static AWS access keys on developer laptops is strictly forbidden.
  - **AWS IAM Identity Center (AWS SSO) + STS Tokens:** Developers authenticate via short-lived credentials:
    ```bash
    aws sso login --profile production
    ```
    AWS Security Token Service (STS) issues a temporary token valid for only 1 to 8 hours. If the laptop is lost or compromised, the credentials expire automatically.

### 2. Infrastructure Delivery: Local Apply vs GitOps CI/CD
- **Lab Setup:** Developer runs `terraform apply` directly from local terminal.
- **Enterprise Practice:** 
  - Direct local `terraform apply` is blocked by IAM permission boundaries. All changes follow **GitOps**:
    1. Developer creates a branch and opens a **Pull Request (PR)** on GitHub/GitLab.
    2. Automated CI/CD pipeline triggers:
       - `terraform fmt -check` (Enforces uniform HCL formatting)
       - `tflint` & `tfsec` / `checkov` (Static security analysis to catch open ports or unencrypted disks)
       - `infracost` (Calculates monthly cost impact and posts breakdown as a PR comment)
       - `terraform plan` (Outputs preview of changes directly in PR)
    3. Peer review and approvals are required before merge. Merging to `main` automatically runs `terraform apply`.

### 3. Pipeline Authentication: OIDC (OpenID Connect) vs Static Secrets
- **Why NOT GitHub Secrets? (The Critical Security Trade-offs):**
  1. **Permanent Blast Radius:** Static keys (`AKIA...` and Secret Access Key) remain active forever until manually deleted. If leaked via accidental `echo` in runner scripts, compromised third-party GitHub Actions, or repository permission slips, attackers immediately gain unrestricted, continuous account access (typically executing unauthorized GPU instances or crypto-mining).
  2. **The 90-Day Key Rotation Maintenance Debt:** Enterprise security governance (SOC 2, ISO 27001) mandates rotating access keys every 90 days. For an organization managing hundreds of microservices, manually renewing and pasting keys into hundreds of GitHub Secrets causes massive operational overhead and inevitable pipeline outages when keys expire.
  3. **Global vs Scoped Access:** A stolen static key works from any laptop or IP address anywhere on the planet. In contrast, an IAM OIDC Role strictly requires cryptographic verification that the token originated specifically from `repo:akshat009/Aws-wp-lab:*`.
- **Enterprise Standard (OIDC Zero-Trust):** 
  - GitHub Actions requests an ephemeral cryptographic JSON Web Token (JWT) on each pipeline execution.
  - AWS STS verifies GitHub's signature against GitHub's public OIDC keys and issues a temporary 15-minute STS session token. **Zero static credentials are generated, stored, or managed.**
- **The Bank Account Analogy (Why Role ARN is Not a Secret):**
  - Committing an IAM Role ARN (`arn:aws:iam::538820337783:role/GitHubActionsTerraformRole`) to Git is like sharing a bank account number. An account number is an identifier/address, not a password. Money cannot be withdrawn without a cryptographic signature (the OIDC JWT verified by AWS STS). Knowing the Role ARN provides zero access to an attacker outside the trusted GitHub runner.

| Dimension | Legacy GitHub Secrets (Old Way) | AWS IAM OIDC (Modern Industry Standard) | Architectural Trade-off (Interview Answer) |
| :--- | :--- | :--- | :--- |
| **Credentials Type** | **Permanent Static Keys:** `AKIA...` valid indefinitely. | **Zero Static Keys:** Ephemeral 15-minute STS session tokens. | Permanent key leak compromises account; OIDC leaves zero static credentials to steal. |
| **Secret Leak Risk** | **Extremely High:** Accidental CI log printing, compromised actions. | **ZERO:** No credentials stored on GitHub servers. | Zero-Trust compliance strictly prohibits static keys in CI/CD runners. |
| **Key Rotation Overhead** | **Manual Pain:** Rotating secrets every 90 days across repos. | **100% Automated:** Token self-destructs after 15 minutes. | Eliminates human maintenance debt and pipeline downtime from expired secrets. |
| **Target Binding (Scoping)** | **Global Access:** Stolen key usable from any machine on Earth. | **Repository Bound:** Scoped strictly to `repo:akshat009/Aws-wp-lab:*`. | Attacker with Role ARN cannot assume role outside authorized GitHub repo. |
| **Interview Value** | Junior level (Basic tutorial approach). | **Senior DevOps level** (Google, Netflix, Amazon standard). | Demonstrates Zero-Trust architectural mastery. |

### 4. State Management & Concurrency Locking
- **Lab Setup:** Local `terraform.tfstate` file stored on developer machine.
- **Enterprise Practice:** 
  - Remote S3 bucket with **SSE-KMS server-side encryption** and **S3 Versioning** (to restore corrupted state).
  - **DynamoDB State Locking:** Prevents race conditions by locking `LockID` during active `plan`/`apply` runs so two engineers or pipelines cannot write simultaneously.

### 5. Infrastructure Provisioning (Terraform) vs Application Configuration (WP-CLI / Docker)
- **Discussion Context:** Why does visiting `http://35.154.176.166` display the WordPress Installation Wizard instead of a fully configured, logged-in dashboard? Does Terraform only do "basic" setup?
- **The Core Architectural Boundary (Separation of Concerns):**
  - **Infrastructure as Code (IaC - Terraform):** "Building the House" (VPC, Subnets, Security Groups, EC2 compute instances, S3 storage, RDS databases).
  - **Configuration Management / Application Deployment (Ansible, WP-CLI, Docker):** "Furnishing the House" (Configuring `wp-config.php`, running database schema migrations, installing themes/plugins, creating admin users).
- **Can Terraform Automate Full Application Setup?**
  - Yes! Adding WP-CLI commands (`wp core install --url=... --title=... --admin_user=...`) to `install.sh` would automatically complete the WordPress installation without human browser interaction.
- **Why Enterprises Strictly Decouple Infrastructure from Application (The Trade-offs):**
  1. **Blast Radius & Re-creation Danger:** Terraform tracks infrastructure resources, not database rows. If an engineer updates an EC2 AMI ID or changes a security group rule, Terraform might trigger an instance replacement (destroy + recreate). If the application state and database credentials were tied directly to that instance lifecycle, all user data would be destroyed.
  2. **Lifecycle & Velocity Mismatch:** Infrastructure changes occur infrequently (e.g. once a month for capacity planning or networking). Application deployments (code changes, content updates, plugin patches) occur dozens of times a day. Tying application deployments directly to Terraform runs risks accidental infrastructure modifications on daily code deploys.
  3. **Role Separation (DevOps vs App Developers):** Cloud engineering teams maintain the infrastructure foundations via Terraform; application developers maintain application code, Docker containers, and CI/CD releases.

| Dimension | Infrastructure as Code (Terraform) | Configuration Management (Ansible / WP-CLI) | Containerization (Docker - Post-Phase 12) |
| :--- | :--- | :--- | :--- |
| **Primary Scope** | Cloud resources: EC2, RDS, VPC, S3, ALB. | In-OS config: packages, files, services, `wp-config.php`. | Immutable package: OS + Apache + PHP + WordPress core. |
| **Execution Trigger** | Cloud infrastructure provisioning / resizing. | Post-boot bootstrap, server patching, app config. | Container startup on ECS, EKS, or Docker host. |
| **State Awareness** | Tracks cloud resource ARNs and metadata in `.tfstate`. | Procedural / idempotent OS command execution. | Stateless container image running against remote RDS/S3. |
| **Enterprise Best Practice** | Day-0 provisioning of the underlying compute & network. | Day-1 configuration of software and application runtime. | Modern standard: eliminates in-place server configuration. |

### 6. Domain & Traffic Routing: Static Elastic IP (A Record) vs Load Balancer / CloudFront (Alias Record)
- **Discussion Context:** In Phase 10 prototyping, Terraform outputs a raw dynamic public IP (`http://35.154.176.166`). How does an enterprise map a custom domain (e.g. `https://lab.asaxenadev.com`) via code, and should Route 53 point directly to an EC2 instance?
- **How Route 53 Mappings Work in Terraform:**
  1. **Direct EC2 Pattern (Lab / Dev):**
     An `aws_eip` resource creates a permanent public IP, and an `aws_route53_record` (Type `A`) routes domain traffic directly to the instance:
     ```hcl
     resource "aws_eip" "wp_eip" {
       instance = aws_instance.wp.id
     }

     resource "aws_route53_record" "wp_domain" {
       zone_id = var.hosted_zone_id
       name    = "lab.asaxenadev.com"
       type    = "A"
       ttl     = 300
       records = [aws_eip.wp_eip.public_ip]
     }
     ```
  2. **Enterprise Production Pattern (Zero-Downtime HA):**
     In production, pointing a domain directly to an EC2 IP is strictly avoided. Route 53 maps via an **Alias Record** to an **Application Load Balancer (ALB)** or **Amazon CloudFront CDN**:
     ```hcl
     resource "aws_route53_record" "wp_alias" {
       zone_id = var.hosted_zone_id
       name    = "lab.asaxenadev.com"
       type    = "A"

       alias {
         name                   = aws_lb.wp_alb.dns_name
         zone_id                = aws_lb.wp_alb.zone_id
         evaluate_target_health = true
       }
     }
     ```
- **The 3 Critical Production Trade-offs (Why Direct EC2 IP Fails in Production):**
  1. **Single Point of Failure (High Availability):** If that single EC2 instance experiences kernel panic, hardware failure, or an AZ outage, the entire domain goes completely offline. An ALB continuously health-checks a fleet of EC2 instances across multiple Availability Zones, automatically routing traffic away from failed nodes.
  2. **SSL/TLS Certificate Lifecycle Debt:** Managing Let's Encrypt certificates directly inside an EC2 instance requires OS-level certbot cron jobs, which frequently fail or break during system upgrades. With an ALB/CloudFront, AWS Certificate Manager (ACM) provisions free public SSL certificates with **100% automated renewal**, terminating SSL at the load balancer with zero compute overhead on WordPress.
  3. **Auto-Scaling & Blue/Green Deployments:** A static IP binds a domain to one specific physical server. An ALB decouples the public endpoint from the backend compute tier, enabling dynamic Auto Scaling Groups (Phase 9) and seamless zero-downtime rolling/canary deployments.

| Dimension | Route 53 ➔ EC2 Elastic IP (Direct) | Route 53 ➔ ALB / CloudFront (Alias Record) | Enterprise Trade-off (Interview Answer) |
| :--- | :--- | :--- | :--- |
| **High Availability** | **Zero:** Single point of failure if EC2 crashes. | **Multi-AZ Redundancy:** Automatic health checks and failover. | ALB prevents total site downtime during hardware or instance failures. |
| **SSL/TLS Termination** | In-OS via Certbot / Apache (Manual cron maintenance). | **AWS ACM Managed:** Free, zero-maintenance auto-renewing SSL. | Eliminates certificate expiry outages and offloads TLS crypto from EC2. |
| **Scalability** | Fixed to 1 single virtual machine. | **Elastic:** Distributes load across 1 to 100+ auto-scaling instances. | Required foundation for auto-scaling stateless WordPress fleets (Phase 9). |
| **Architecture Cost** | Low (Elastic IP is free when attached to a running instance). | Higher (~$16–$22/month baseline for ALB). | Cost of ALB is mandatory enterprise insurance against downtime. |

### ⚖️ Enterprise vs Lab Architecture Trade-off Matrix

| Dimension | Static Keys / Local Apply (Lab Setup) | IAM SSO + OIDC + GitOps CI/CD (Enterprise) | Real-World Trade-off (What it Costs) |
| :--- | :--- | :--- | :--- |
| **Setup Speed** | **Fastest (< 2 mins):** Minimal friction for rapid prototyping and learning. | **Slow (2–3 days):** Requires AWS Organizations, IAM OIDC providers, and pipeline scripts. | Enterprise security adds operational setup overhead upfront. |
| **Security Risk** | **High:** If laptop is compromised or keys committed to Git, full access is leaked until revoked. | **Zero:** Temporary short-lived tokens with automatic expiration and least-privilege scoping. | Developers must re-authenticate daily via SSO. |
| **Auditability** | **Poor:** Changes made locally leave no Git PR review trail. | **100% Auditable:** Every change is linked to a Git commit, PR discussion, and AWS CloudTrail event. | Hotfixes require going through standard PR review rather than immediate ad-hoc fixes. |
| **Backend Bootstrapping** | **Manual / CLI (< 1 min):** Fast start, but requires 1 manual action outside Git. | **Two-Stage Code (`bootstrap/`) or Landing Zones:** 100% codified and auditable. | Requires managing two separate state files or enterprise landing zone automation. |

</details>

---



<details>
<summary><h3>🎯 Phase 10 Cloud Architecture Interview Questions & Answers</h3></summary>

## Phase 10 Cloud Architecture Interview Questions & Answers

### Q1: What is the purpose of the `terraform.tfstate` file, and why is keeping state files in local git repositories a critical security anti-pattern?
- **Answer:** 
  - **Purpose of State:** Terraform is a declarative tool. The state file acts as the single source of truth mapping your declared HCL code resources to the real-world cloud resource IDs created in AWS (e.g. mapping `aws_instance.web` to `i-0454e55a303f5f9ae`). It also tracks metadata, resource dependencies, and cache attributes.
  - **The Local Git Anti-Pattern:**
    1. **Plaintext Secrets Exposure:** The state file records every resource attribute in plain JSON text, including database master passwords and private keys. Committing state to git permanently exposes root credentials.
    2. **State Corruption & Desynchronization:** If multiple team members run `terraform apply` locally, their local state files diverge, leading to overwritten resources and corrupted infrastructure.
  - **Production Practice:** Always use a **Remote Backend** (Amazon S3 with SSE-KMS encryption and DynamoDB state locking).

### Q2: How does Terraform State Locking with Amazon DynamoDB work? What happens without it?
- **Answer:** 
  - When a remote S3 backend is paired with a DynamoDB table, Terraform writes an item with a unique `LockID` into DynamoDB the moment anyone runs `terraform plan` or `terraform apply`.
  - If Engineer A is running an `apply`, and Engineer B runs an `apply` at the exact same time, Engineer B's execution immediately fails with: `Error: Error acquiring the state lock: ConditionalCheckFailedException`.
  - Once Engineer A's apply finishes, the lock item is deleted from DynamoDB. This guarantees atomic, serialized operations and prevents race conditions from corrupting the cloud state.

### Q3: What is "Configuration Drift", and how does Terraform detect and remediate it?
- **Answer:** 
  - **Drift:** When someone manually modifies a resource in the AWS Console (e.g. changing an EC2 Security Group port or resizing an EBS volume) outside of Terraform code.
  - **Detection:** During `terraform plan`, Terraform performs a **Refresh** phase: it makes API calls to AWS, queries the actual live configuration of every resource, compares it against `terraform.tfstate`, and highlights the exact differences.
  - **Remediation:** If the code says Port 22 should be closed, but someone manually opened it in AWS Console, running `terraform apply` will forcefully overwrite the manual console change and revert the Security Group back to the desired code state.

### Q4: What is the difference between `variable`, `locals`, and `output` in Terraform HCL?
- **Answer:** 
  - `variable` (Inputs): Parameterized inputs passed into a Terraform module from the command line, environment variables (`TF_VAR_`), or `.tfvars` files to make code reusable across environments (Dev, Staging, Prod).
  - `locals` (Internal Constants): Intermediate calculations or scoped expressions defined within the module to prevent repetitive logic (e.g. `common_tags = { Environment = var.env, Project = "lab" }`).
  - `output` (Return Values): Values returned by a module after provisioning (e.g. database endpoint, ALB DNS name) to display in the CLI terminal or pass to other downstream modules via `terraform_remote_state`.

### Q5: What is `create_before_destroy` in Terraform lifecycle blocks, and why is it critical for zero-downtime updates?
- **Answer:** 
  - By default, when a resource attribute forces recreation (e.g. changing an EC2 instance AMI or security group name), Terraform's default behavior is **Destroy then Create**: it terminates the existing server first, causing downtime, before creating the new one.
  - Adding `lifecycle { create_before_destroy = true }` reverses this order: Terraform provisions and verifies the new resource first, updates routing/associations, and only terminates the old resource once the replacement is fully operational, guaranteeing zero downtime.

### Q6: How should sensitive database passwords be handled in Terraform without exposing them in code?
- **Answer:** 
  - **Never hardcode secrets:** Use `variable "db_password" { type = string; sensitive = true }`. Setting `sensitive = true` prevents Terraform from printing the secret in CLI logs or CI/CD execution consoles.
  - Pass the secret via `TF_VAR_db_password` environment variables or fetch it dynamically at runtime using the `aws_secretsmanager_secret_version` data source.
  - Ensure the S3 remote state bucket has bucket encryption (`aws:kms`), bucket access logging, and strict IAM restrictions.

### Q7: What is the "Chicken-and-Egg" dilemma when provisioning a Terraform remote backend with Terraform itself, and how is it resolved in production?
- **Answer:** 
  - **The Dilemma:** Terraform requires an existing remote backend (S3 bucket + DynamoDB table) to execute `terraform init` and store its state. If the remote backend is declared in the same configuration that requires it, `init` fails because the destination bucket does not exist yet.
  - **Production Resolutions:**
    1. **Two-Stage Bootstrapping:** A lightweight root module (e.g. `bootstrap/`) provisions the S3 bucket (with SSE-KMS and S3 Versioning) and DynamoDB lock table using local state (`backend "local"`). Once applied, the primary workload module points its `backend "s3"` to the provisioned bucket and executes `terraform init -migrate-state`.
    2. **Account Vending Foundation:** In enterprise landing zones, the state storage foundation is provisioned upstream via AWS Organizations, CloudFormation StackSets, or AWS Control Tower when the AWS account is automatically vended, completely shielding application developers from manual bootstrap friction.

### Q8: Why should organizations use AWS IAM OpenID Connect (OIDC) for GitHub Actions instead of storing long-lived AWS Access Keys in GitHub Repository Secrets?
- **Answer:** 
  - **1. Zero Static Secrets (Eliminates Blast Radius):** 
    - *Legacy Secrets Anti-Pattern:* Generating permanent `AKIA...` access keys and storing them in GitHub Secrets leaves credentials vulnerable indefinitely. If leaked via CI log printing, malicious third-party GitHub Actions, or repository compromises, attackers gain persistent, unrestricted account access to spin up unauthorized crypto-mining or data exfiltration infrastructure.
    - *OIDC Zero-Trust:* No static keys are generated, stored, or managed. On each pipeline run, GitHub mints a short-lived, cryptographically signed JSON Web Token (JWT). AWS STS verifies the token against GitHub's public OIDC keys and grants temporary 15-minute STS credentials that self-destruct upon job completion.
  - **2. Zero Key Rotation Maintenance Debt:**
    - Enterprise security compliance frameworks (SOC 2, ISO 27001, PCI-DSS) strictly mandate 90-day credential rotation. In an organization managing 200+ microservices, manually rotating static keys across hundreds of repositories introduces massive operational overhead and risks pipeline downtime when keys expire. OIDC automates rotation dynamically on every pipeline execution.
  - **3. Cryptographic Scoping (Repository & Branch Level):**
    - Static access keys can be stolen and used from *any* laptop or external IP address in the world.
    - An IAM Role federated with OIDC strictly enforces that the caller must match the exact repository namespace (`repo:akshat009/Aws-wp-lab:*`). Even if a malicious actor acquires the Role ARN, it is completely inert outside the authenticated GitHub runner.
  - **The Bank Account Analogy (Why Role ARN is Not a Secret):**
    - Committing a Role ARN to Git is like sharing a bank account number: an account number is merely an address/identifier, not a credential. Money cannot be withdrawn without a cryptographic signature (the OIDC JWT verified by AWS STS).

### Q9: Why does Terraform provision the web server and WordPress core files, but leave the application setup (database schema, site title, admin credentials) unconfigured? Why not automate the complete WordPress installation inside Terraform?
- **Answer:**
  - **1. Separation of Concerns (IaC vs App Deployment):**
    - Terraform is a declarative **Infrastructure Provisioning** tool designed to manage cloud resource lifecycles (EC2 virtual machines, VPC networks, RDS databases, S3 storage buckets).
    - Application configuration (creating database tables, provisioning WordPress admin accounts, setting up plugins) is the domain of **Configuration Management / Application Deployment** tools (WP-CLI, Ansible, or immutable Docker containers).
  - **2. Blast Radius & Lifecycle Velocity Mismatch:**
    - Infrastructure foundations evolve on a slow lifecycle (monthly architectural resizing, network updates).
    - Application code and content updates evolve on a rapid lifecycle (multiple daily pushes).
    - If application installation is tightly coupled to Terraform's `user_data`, every code deployment would require executing `terraform apply` with high-privilege cloud IAM credentials, exposing the underlying VPC and database infrastructure to accidental drift or unintended destruction.
  - **3. The Re-creation Danger (Stateless vs Stateful Boundaries):**
    - In Terraform, updating certain EC2 properties forces an instance replacement (`Destroy and Recreate`).
    - By decoupling infrastructure provisioning from application state, the compute layer can be destroyed and rebuilt without corrupting or destroying application databases (RDS) or media files (S3).
  - **4. Production Standard (The Docker Evolution):**
    - In Phase 10, Terraform automates Day-0 web stack provisioning (Apache + PHP 8.3 + WordPress files).
    - In modern cloud-native architectures (Bonus Phase: Docker & ECS/EKS), WordPress is packaged as a pre-baked, immutable Docker container image. Terraform provisions the ECS cluster and RDS database, while the CI/CD pipeline deploys the container, ensuring 100% automated, instant application startup without manual web installer friction.

### Q10: In Terraform, how do you map a domain to your infrastructure, and why shouldn't Route 53 point directly to an EC2 Elastic IP in production?
- **Answer:**
  - **The Direct IP Anti-Pattern:**
    - Mapping an `A` record directly to an EC2 Elastic IP binds the domain to a single virtual machine.
    - *Fatal Weaknesses:* It introduces a **Single Point of Failure (SPOF)** — if the instance crashes, undergoes patching, or fails an AZ health check, the site is completely dead. Furthermore, SSL certificates must be managed locally on the host (e.g. Certbot cron jobs), risking certificate expiration downtime.
  - **The Production Standard (Route 53 Alias to ALB / CloudFront):**
    - In enterprise architectures, Route 53 uses an **Alias `A` Record** pointing to an Application Load Balancer (ALB) or Amazon CloudFront distribution (`aws_route53_record.alias`).
    - *Key Architectural Benefits:*
      1. **Multi-AZ High Availability:** The ALB health-checks target EC2 instances across multiple Availability Zones and routes requests exclusively to healthy nodes.
      2. **Centralized SSL/TLS Offloading:** AWS Certificate Manager (ACM) provisions free SSL certificates that auto-renew without human intervention, terminating encryption at the load balancer.
      3. **Horizontal Auto-Scaling:** Decouples the domain from backend compute, allowing the WordPress web tier to scale dynamically from 2 to 50 instances based on CPU and request count.

</details>
