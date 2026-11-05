# Strategy — Covering AWS Through One WordPress Project

One site, built up in phases. Each phase adds real capability to the site *and* covers a chunk of the syllabus.

**Rule every session:** build → verify → note it down → delete → check Billing

## How to read this doc

The steps are generic. Every command shows a **worked example** so you can copy
and run it, but nothing here is tied to those particular names — substitute your
own and the steps are unchanged.

| Placeholder | What it is | Example used throughout |
|---|---|---|
| `<PROJECT>` | Your instance / resource name | `wp-lab` |
| `<KEY>.pem` | The key pair file you downloaded at launch | `wp-lab-key.pem` |
| `<REGION>` | The region you build in — pick the one nearest your users | `ap-south-1` (Mumbai) |
| `<PUBLIC-IP>` | The instance's public IPv4, from the EC2 console | `15.252.183.223` |
| `<EIP>` | The Elastic IP once allocated (Phase 2) | — |
| `<DOMAIN>` | The subdomain you point at the instance | `lab.example.com` |
| `<DB-NAME>` / `<DB-USER>` / `<DB-PASS>` | WordPress database credentials you choose | `wordpress` / `wpuser` / your own |
| `<RDS-ENDPOINT>` | The RDS hostname (Phase 4) | — |
| `<BUCKET>` | Your S3 bucket name — must be globally unique (Phase 5) | — |
| `<REDIS-ENDPOINT>` | ElastiCache endpoint (Phase 8) | — |
| `<PHP-VERSION>` | Whatever `ls /run/php/` reports — depends on your Ubuntu release | `php8.5` on Ubuntu 26.04 |

**Things that genuinely vary and must be checked, not copied:**

- **PHP version** — `ls /run/php/` on your own server. Ubuntu 24.04 gives 8.3, 26.04 gives 8.5. Copying the wrong one is the usual cause of `502 Bad Gateway`.
- **Region** — every console screen must show the same one, or resources scatter across regions and can't see each other.
- **Your own public IP** — the SSH rule is tied to it, and it changes when your connection does.
- **Instance size** — `t3.micro` here. Anything with 1 GB of RAM needs the swap step; larger instances don't.

If you're following along with a different domain, bucket or region, only these
values change. The order of the phases and the reasoning behind each one stay
the same.

---

## The shape of it

| Phase | You build | Syllabus covered |
|---|---|---|
| 1 | WordPress on EC2 | EC2, EBS, VPC, security groups, key pairs |
| 2 | Domain + HTTPS | Elastic IP, DNS, Route 53, certificates |
| 3 | Deploy pipeline | GitHub Actions, SSH deploys, secrets |
| 4 | Database to RDS | RDS, private subnets, SG-to-SG rules |
| 5 | Media to S3 + CDN | S3, CloudFront, IAM roles, bucket policies |
| 6 | Harden it | IAM deep, KMS, Secrets Manager, WAF, SSM |
| 7 | Email + monitoring | SES, DKIM/SPF, CloudWatch, alarms |
| 8 | Cache | ElastiCache Redis, object vs page cache |
| 9 | Scale it | ALB, Auto Scaling, AMIs, EFS, Multi-AZ |
| 10 | Codify it | Terraform, destroy and rebuild from code |
| 11 | Cost | Tagging, Cost Explorer, right-sizing |
| 12 | Odds and ends | Lambda, EventBridge, SQS, SNS, DynamoDB |

Phases 1–5 are the site. 6–11 are the same site, improved. 12 is the only throwaway work.

---

# BEFORE YOU START — YOUR MACHINE

## Where each thing actually happens

| Where | What you do there |
|---|---|
| **AWS Console** (browser) | Launch the instance, Elastic IP, security groups, RDS, S3 bucket, CloudFront, IAM roles and policies, SES, CloudWatch alarms, ElastiCache, ALB, Auto Scaling, Budgets, Cost Explorer |
| **SSH into the instance** (terminal) | Everything inside Ubuntu: nginx, PHP, MySQL, WordPress files, Certbot, mysqldump, php-redis, CloudWatch agent |
| **Your own machine** | Git, editing the workflow YAML, Terraform, AWS CLI, `dig` to check DNS |
| **GitHub** (browser) | Repo secrets, Actions logs |
| **hPanel** (browser) | The DNS A record and the SES DKIM records |

Nothing in this project requires the console and the terminal at the same time, so a laptop with a browser and a terminal is the whole toolkit.

## Windows vs Mac/Linux — side by side

**Only commands you run on your own machine differ.** Once you're connected over SSH, everything is Linux on both — all the `apt`, `nano`, `systemctl` and `mysql` commands in the phases below are identical. WSL is optional; plain PowerShell finishes this project.

### Everyday commands

| Task | Windows (PowerShell) | Mac / Linux |
|---|---|---|
| Open a terminal in a folder | File Explorer → address bar → type `powershell` → Enter | Right-click folder → New Terminal at Folder (Mac), or `cd <path>` |
| Fix key permissions | `icacls .\wp-lab-key.pem /inheritance:r`<br>`icacls .\wp-lab-key.pem /grant:r "$($env:USERNAME):(R)"` | `chmod 400 wp-lab-key.pem` |
| Connect over SSH | `ssh -i .\wp-lab-key.pem ubuntu@<IP>` | `ssh -i wp-lab-key.pem ubuntu@<IP>` |
| Check DNS (Phase 2) | `Resolve-DnsName lab.example.com` | `dig lab.example.com +short` |
| Copy a file to the server | `scp .\file ubuntu@<IP>:/tmp/` | `scp file ubuntu@<IP>:/tmp/` |
| Sync a folder (`rsync`) | Not available — use `scp`, or WSL | `rsync -avz ./ ubuntu@<IP>:/path/` |
| Edit a server file | `nano` over SSH | `nano` over SSH |

`rsync` missing on Windows barely matters: the Phase 3 pipeline runs it on GitHub's Ubuntu runner, not your machine.

### Tools

| Tool | Windows | Mac | Needed for |
|---|---|---|---|
| SSH client | Built into Win 10/11 | Built in | Phase 1 onward |
| Git | `winget install Git.Git` | `brew install git` | Repo work |
| AWS CLI v2 | `winget install Amazon.AWSCLI` | `brew install awscli` | Phase 10 onward |
| Terraform | `winget install Hashicorp.Terraform` | `brew install terraform` | Phase 10 |
| Nicer terminal | Windows Terminal (Store) | Built in | Optional |
| Linux shell | WSL2: `wsl --install` | Already Unix | Optional |
| PuTTY | Optional GUI alternative | n/a | Only if you prefer it — convert `.pem` to `.ppk` first |

### Gotchas, by platform

| | Windows | Mac / Linux |
|---|---|---|
| Key permissions | SSH refuses the key until `icacls` is run — "unprotected private key file" | `chmod 400` and done |
| Line endings | A Windows editor writes CRLF; `install.sh` then fails on Ubuntu with `bad interpreter`. In VS Code click `CRLF` in the status bar → `LF` | Not an issue |
| Paths | Backslashes and `.\` prefix; quote paths with spaces | Forward slashes, `~` for home |
| Paste into terminal | Right-click pastes in PowerShell | Cmd+V / Ctrl+Shift+V |

Install WSL later if you tire of translating. It isn't needed to finish.

## Making SSH less painful (any OS)

Add this to `~/.ssh/config` (on Windows, `C:\Users\<you>\.ssh\config` or inside WSL):

```
Host wplab
    HostName lab.example.com
    User ubuntu
    IdentityFile ~/.ssh/wp-lab-key.pem
```
Then connecting is just:
```bash
ssh wplab
```

## Skipping SSH entirely

From Phase 6 you'll set up **SSM Session Manager**, which gives you a shell in the browser from the EC2 console — no key file, no port 22 open, and no OS differences at all. If key permissions on Windows are giving you trouble, you can set that up early: attach `AmazonSSMManagedInstanceCore` to the instance role and use **EC2 → Connect → Session Manager**.

There's also **EC2 Instance Connect** in the console, which works in the browser for Ubuntu AMIs without any setup, as long as the security group allows SSH from the console's IP range.

---

---

# PHASE 1 — WordPress on EC2

### Step 1: launch the instance

Console → **EC2** → check region says Mumbai → **Launch instance**

- **Name:** `wp-lab`
- **AMI:** Ubuntu Server 24.04 LTS (64-bit x86)
- **Instance type:** `t3.micro`
- **Key pair:** Create new → name `wp-lab-key` → RSA → `.pem` → Download. Save it; it cannot be downloaded again.
- **Network settings** → Edit:
  - Allow SSH — source **My IP**
  - Allow HTTP — source Anywhere
  - Allow HTTPS — source Anywhere
- **Storage:** 20 GB gp3
- **Launch instance**

Wait for Instance state **Running** and status checks 2/2.

### Step 2: connect

On Mac/Linux:
```bash
chmod 400 ~/Downloads/wp-lab-key.pem
ssh -i ~/Downloads/wp-lab-key.pem ubuntu@<PUBLIC-IP>
```
On Windows, use PowerShell with the same command, or PuTTY after converting the key with PuTTYgen.

If it hangs: the security group's SSH rule has the wrong IP (yours changed), or you used the wrong username — Ubuntu AMIs use `ubuntu`, not `root` or `ec2-user`.

### Step 2b: verify the security group actually saved

The launch wizard's HTTP/HTTPS checkboxes don't always persist. Check before
you go further, because a missing port 80 rule looks exactly like a broken
server later on.

EC2 → instance → **Security** tab → security group → **Inbound rules**.
You should see three rules: 22 (My IP), 80 (0.0.0.0/0), 443 (0.0.0.0/0).

Missing? **Edit inbound rules → Add rule** → Type **HTTP**, Source
**Anywhere-IPv4**. Repeat for **HTTPS**. Save.

### Step 2c: add swap (do this before installing MySQL)

`t3.micro` has 1 GB of RAM. nginx + PHP-FPM + MySQL together will exhaust it,
and MySQL gets killed by the kernel with
`Job for mysql.service failed because of an out-of-memory (OOM) situation`.

A 2 GB swap file prevents it:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h          # Swap line should show 2.0Gi
```

The `/etc/fstab` line makes it survive a reboot. Swap is disk used as slow
extra RAM — normal practice on small instances, not a hack.

### Step 3: install the stack

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y nginx mysql-server php-fpm php-mysql php-curl php-gd \
  php-mbstring php-xml php-zip php-intl unzip
```

Check the PHP-FPM socket path — you need it for the nginx config:
```bash
ls /run/php/
```
Whatever version appears (e.g. `php8.5-fpm.sock`) is what goes in
`fastcgi_pass` in Step 6. Ubuntu 26.04 ships PHP 8.5, not 8.3.

### Step 4: create the database

```bash
sudo mysql
```
```sql
CREATE DATABASE wordpress DEFAULT CHARACTER SET utf8mb4;
CREATE USER 'wpuser'@'localhost' IDENTIFIED BY 'a-strong-password';
GRANT ALL ON wordpress.* TO 'wpuser'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Step 5: install WordPress

```bash
cd /tmp
curl -O https://wordpress.org/latest.tar.gz
tar xzf latest.tar.gz
sudo rm -rf /var/www/html/*
sudo cp -r wordpress/* /var/www/html/
sudo chown -R www-data:www-data /var/www/html
sudo find /var/www/html -type d -exec chmod 755 {} \;
sudo find /var/www/html -type f -exec chmod 644 {} \;
```

### Step 6: configure nginx

```bash
sudo nano /etc/nginx/sites-available/wordpress
```
```nginx
server {
    listen 80;
    server_name _;
    root /var/www/html;
    index index.php index.html;

    location / {
        try_files $uri $uri/ /index.php?$args;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php8.3-fpm.sock;   # match Step 3
    }

    location ~ /\.ht { deny all; }
    client_max_body_size 64M;
}
```
```bash
sudo ln -s /etc/nginx/sites-available/wordpress /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### Step 7: finish in the browser

Open `http://<PUBLIC-IP>` and run the WordPress installer with the database name, user and password from Step 4.

### Troubleshooting

**The single most useful diagnostic:** run `curl -I http://localhost` on the
instance. It tells you which side of the firewall the problem is on.

| Symptom | Meaning | Fix |
|---|---|---|
| Browser: `ERR_CONNECTION_TIMED_OUT`, but `curl -I http://localhost` returns 200/302 | The server is fine — traffic isn't reaching it | Security group is missing the port 80 rule (Step 2b). Also check `sudo ufw status` is inactive |
| `502 Bad Gateway` | nginx can't reach PHP | `fastcgi_pass` socket path doesn't match `ls /run/php/` |
| Blank page, or the browser downloads the PHP file | PHP isn't being handled | The `location ~ \.php$` block is missing, or nginx wasn't reloaded |
| "Error establishing a database connection" | MySQL is down or credentials are wrong | `sudo systemctl status mysql --no-pager`, then test with `mysql -u wpuser -p wordpress` |
| `ERROR 2002 ... Can't connect through socket` | MySQL isn't running | `sudo systemctl start mysql`. If it fails with OOM, add swap (Step 2c) |
| SSH stops working after a few days | Your home IP changed | Security group → edit the SSH rule → **My IP** again |

Remember the distinction: **timeout = firewall, error page = server.** A
timeout never means nginx is broken, because nothing reached nginx at all.

### Note down
Why SSH is limited to your IP; what the key pair actually is; what `chown www-data` fixes; why timeout and error page point at different layers; what went wrong first time.

### End of session
Stop the instance (don't terminate — you'll continue next session). A stopped instance costs only the disk.

---

# PHASE 2 — Domain and HTTPS

### Step 1: Elastic IP

EC2 → **Elastic IPs** → Allocate Elastic IP address → Allocate → select it → **Actions → Associate** → choose `wp-lab`.

Note the IP. This is now permanent across restarts.

### Step 2: DNS at Hostinger

hPanel → **Domains** → your domain → **DNS Zone Editor** → Add record:
- Type **A**, Name `lab`, Points to `<EIP>`, TTL default

Check it from your laptop after a few minutes:
```bash
dig lab.example.com +short
```
It must return your Elastic IP before you attempt SSL.

### Step 3: tell WordPress its address

```bash
sudo nano /var/www/html/wp-config.php
```
```php
define('WP_HOME','http://lab.example.com');
define('WP_SITEURL','http://lab.example.com');
```
Also set `server_name lab.example.com;` in the nginx config, then reload.

### Step 4: certificate

```bash
sudo snap install core && sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
sudo certbot --nginx -d lab.example.com
```
Choose the redirect option. Certbot edits the nginx config and installs a renewal timer.

Then change the two wp-config lines to `https://`.

Test renewal:
```bash
sudo certbot renew --dry-run
```

### Optional: Route 53 for one session
Route 53 → Hosted zones → Create hosted zone for the domain → note the four nameservers → change nameservers at the registrar → recreate your records. Look at alias records and routing policies, then decide whether to keep it or revert.

### Note down
Why the Elastic IP matters, why Certbot needs DNS first, what the TTL did.

---

# PHASE 3 — Deploy pipeline

### Step 1: deploy key

On the instance:
```bash
ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/deploy_key -N ""
cat ~/.ssh/deploy_key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
cat ~/.ssh/deploy_key        # copy this private key
```

### Step 2: repo secrets

GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**:
- `SSH_PRIVATE_KEY` — the private key you just copied
- `SSH_HOST` — `lab.example.com`
- `SSH_USER` — `ubuntu`

### Step 3: the workflow

`.github/workflows/deploy.yml`:
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
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: shivammathur/setup-php@v2
        with:
          php-version: '8.3'
      - run: composer install --no-interaction
      - run: composer run phpcs
      - run: composer run phpunit

  deploy:
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
            --exclude='.git*' --exclude='node_modules' --exclude='tests' \
            ./ ${{ secrets.SSH_USER }}@${{ secrets.SSH_HOST }}:/var/www/html/wp-content/plugins/my-plugin/
```

Make sure the target directory is writable by `ubuntu`, or deploy to a staging path and move it with a remote command.

### Step 4: prove the gate works
Break a test on purpose, push, and confirm the deploy job never runs.

### Step 5: make it atomic (the upgrade worth doing)

Deploy into a timestamped directory and switch a symlink:
```yaml
      - name: Atomic deploy
        run: |
          REL=$(date +%Y%m%d%H%M%S)
          rsync -avz ./ ${{ secrets.SSH_USER }}@${{ secrets.SSH_HOST }}:/var/www/releases/$REL/
          ssh ${{ secrets.SSH_USER }}@${{ secrets.SSH_HOST }} \
            "ln -sfn /var/www/releases/$REL /var/www/html/wp-content/plugins/my-plugin && \
             ls -1dt /var/www/releases/* | tail -n +6 | xargs rm -rf"
```
Rollback is pointing the symlink at the previous release.

### Note down
What happened when the test failed; what a half-finished rsync does to a live site.

---

# PHASE 4 — Database to RDS

### Step 1: create the database

RDS → **Create database** → Standard create
- Engine **MySQL**, Templates **Free tier** if offered (else Dev/Test)
- DB instance identifier `wp-lab-db`, master username `admin`, set a password
- Instance class `db.t3.micro`, 20 GB gp3
- **Public access: No**
- VPC security group: create new, `rds-sg`
- Additional configuration → Initial database name `wordpress`
- **Create database** (takes ~10 minutes)

### Step 2: the security group rule that matters

EC2 → Security Groups → `rds-sg` → Inbound rules → Edit:
- Type MySQL/Aurora (3306), **Source: the EC2 instance's security group** — start typing `sg-` and pick it. Not an IP.

### Step 3: migrate the data

On the instance:
```bash
mysqldump -u wpuser -p wordpress > ~/wp.sql
sudo apt install -y mysql-client
mysql -h <RDS-ENDPOINT> -u admin -p wordpress < ~/wp.sql
```

### Step 4: point WordPress at it

```php
define('DB_HOST', '<RDS-ENDPOINT>');
define('DB_USER', 'admin');
define('DB_PASSWORD', 'the-rds-password');
```

Reload the site. If it loads, you're on RDS. Confirm by stopping local MySQL:
```bash
sudo systemctl stop mysql
```
Site still works → the migration is real.

### Step 5: try the resilience features
RDS → Modify → enable **Multi-AZ** → Apply immediately. Then **Actions → Reboot with failover** and watch the site during it. Add a read replica just to see the endpoint and lag metric.

### End of session
Delete the RDS instance (skip the final snapshot), revert `DB_HOST` to `localhost`, restart local MySQL.

---

# PHASE 5 — Media to S3 and CloudFront

### Step 1: bucket

S3 → Create bucket → name `wp-lab-media-<something-unique>` → region Mumbai → keep **Block all public access ON** → Create.

### Step 2: IAM role instead of keys

IAM → **Roles → Create role** → AWS service → EC2 → Next → Create a policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:PutObject","s3:GetObject","s3:DeleteObject","s3:ListBucket"],
    "Resource": [
      "arn:aws:s3:::<BUCKET>",
      "arn:aws:s3:::<BUCKET>/*"
    ]
  }]
}
```
Name the role `wp-lab-s3-role`. Then EC2 → select instance → **Actions → Security → Modify IAM role** → attach it.

### Step 3: the plugin

Install **WP Offload Media Lite**. With the instance role attached it should detect credentials automatically; otherwise set in wp-config.php:
```php
define('AS3CF_SETTINGS', serialize(['provider' => 'aws', 'use-server-roles' => true]));
```
Set the bucket in the plugin settings and upload a test image. Check it appears in S3 and the URL points at the bucket.

### Step 4: CloudFront

CloudFront → Create distribution
- Origin: your S3 bucket
- Origin access: **Origin access control**, then copy the generated bucket policy into S3 → Permissions
- Default cache behaviour: redirect HTTP to HTTPS
- Create, wait ~15 minutes

Then set the CloudFront domain as the custom media domain in the offload plugin.

### Step 5: lifecycle rule
S3 → bucket → Management → Create lifecycle rule → transition objects to Standard-IA after 30 days.

### Note down
Why the role beats keys in wp-config.php; what breaks when the bucket policy is wrong.

---

# PHASE 6 — Harden it

### Secrets Manager for the DB password
Secrets Manager → Store a new secret → Credentials for RDS → pick the instance → name `wp-lab/db`.
Add to the instance role: `secretsmanager:GetSecretValue` on that secret's ARN.
In wp-config.php, fetch it at runtime with the AWS SDK instead of hardcoding, and cache it in APCu or a file with tight permissions.

### KMS encryption
RDS: set at creation (can't be added later — recreate from a snapshot).
EBS: EC2 → Settings → **Always encrypt new EBS volumes**.
S3: bucket → Properties → Default encryption → SSE-KMS.

### Close SSH entirely
Attach `AmazonSSMManagedInstanceCore` to the instance role, then:
```bash
sudo snap install amazon-ssm-agent --classic
sudo systemctl enable --now snap.amazon-ssm-agent.amazon-ssm-agent.service
```
Now EC2 → Connect → **Session Manager** works. Remove the SSH inbound rule from the security group.

### WAF
WAF → Create web ACL → associate with the CloudFront distribution → add the AWS managed common rule set → add a rate-based rule limiting requests to `/wp-login.php`.

### Deliberately break a policy
Remove `s3:PutObject` from the role, try a media upload, read the exact access-denied error, put it back. That error message is the best interview material in this phase.

---

# PHASE 7 — Email and monitoring

### SES
SES → **Verified identities → Create identity → Domain** → enter your domain → enable **Easy DKIM** → copy the three CNAME records into Hostinger's DNS zone.
Then SMTP settings → **Create SMTP credentials** (this creates an IAM user with SES permissions).
In WordPress, install WP Mail SMTP, choose Other SMTP, host `email-smtp.ap-south-1.amazonaws.com`, port 587, TLS, with those credentials. Send a test.

Note the sandbox: until you request production access you can only send to verified addresses.

### CloudWatch agent
```bash
wget https://amazoncloudwatch-agent.s3.amazonaws.com/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard
```
Add `CloudWatchAgentServerPolicy` to the instance role. Memory and disk metrics only exist with the agent.

### Alarms
CloudWatch → Alarms → Create alarm → CPUUtilization > 80% for 5 minutes → SNS topic → your email (confirm the subscription email). Repeat for low disk space.

---

# PHASE 8 — Cache

### Create the cluster
ElastiCache → Redis OSS caches → Create → Design your own → Cluster mode disabled → node type `cache.t3.micro` → 0 replicas → same VPC → new security group.

Security group inbound: port **6379** from the EC2 instance's security group.

### Wire up WordPress
```bash
sudo apt install -y php-redis
sudo systemctl restart php8.3-fpm
redis-cli -h <REDIS-ENDPOINT> ping     # expect PONG
```
```php
define('WP_REDIS_HOST', '<REDIS-ENDPOINT>');
define('WP_REDIS_PORT', 6379);
```
Install **Redis Object Cache** → Settings → **Enable Object Cache**. Status should read Connected.

### Measure it
Install Query Monitor and compare query counts and admin page load with the cache enabled and disabled.

### End of session
Delete the ElastiCache cluster — it bills per hour. For everyday use, `sudo apt install redis-server` on the instance does the same job for free.

---

# PHASE 9 — Scale it

One session, torn down the same day.

### Step 1: AMI
EC2 → select instance → **Actions → Image and templates → Create image**. Wait until available.

### Step 2: launch template
EC2 → Launch templates → Create → use your AMI, `t3.micro`, the same security group, the same IAM role.

### Step 3: target group and ALB
EC2 → Target groups → Create → Instances → HTTP 80 → health check path `/`.
EC2 → Load balancers → Create → **Application Load Balancer** → internet-facing → at least two subnets in different AZs → listener HTTP 80 → forward to the target group.

### Step 4: auto scaling group
EC2 → Auto Scaling groups → Create → your launch template → two subnets → attach the existing target group → min 1, desired 2, max 2 → target tracking on 70% CPU.

### Step 5: watch it work
Open the ALB DNS name. Terminate one instance manually and watch a replacement launch and become healthy.

### What you're meant to notice
Uploads differ per server unless media is on S3 (Phase 5 fixed that). The object cache must be shared (Phase 8). WP-Cron would run on both — disable it in wp-config and run it from one place.

### Delete the same day
Auto scaling group first (set desired to 0, then delete), then the ALB, target group, extra instances, and the AMI + its snapshot.

---

# PHASE 10 — Codify it

### Setup
```bash
# install terraform, then:
mkdir infra && cd infra
```
`main.tf`:
```hcl
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = "ap-south-1"
}

resource "aws_security_group" "web" {
  name        = "wp-lab-web"
  description = "WordPress web tier"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "wp" {
  ami                    = "ami-xxxxxxxx"   # your Ubuntu AMI id for ap-south-1
  instance_type          = "t3.micro"
  key_name               = "wp-lab-key"
  vpc_security_group_ids = [aws_security_group.web.id]
  user_data              = file("install.sh")

  tags = {
    Name        = "wp-lab"
    Project     = "aws-learning"
    Environment = "lab"
  }
}
```

Put the Phase 1 install commands into `install.sh` as the user-data script, so a fresh instance builds itself.

```bash
terraform init
terraform plan
terraform apply
# ...work...
terraform destroy
```

### Why this phase matters most
Every later session becomes one command up and one command down, nothing gets forgotten and left billing, and it's the difference between clicking through a console and being able to hand the setup to a team.

---

# PHASE 11 — Cost

### Tag everything
Every resource gets `Project = aws-learning` and `Environment = lab`. In Terraform, use `default_tags` in the provider block so it happens automatically.

### Activate the tags for billing
Billing → **Cost allocation tags** → activate your tag keys. They take up to 24 hours to appear in reports.

### Look at where the money went
Cost Explorer → group by **Service**, then by **Tag**. Set the date range to the whole project.

### Right-size
Use the CloudWatch CPU and memory data you now have to decide whether `t3.micro` was over- or under-sized, and what you'd choose for a real site.

### Note down
Which service actually cost the most, and whether it surprised you.

---

# PHASE 12 — The leftovers

One hour each, deleted immediately. Goal is recognition, not depth.

- **Lambda + S3:** create a Python function, add an S3 trigger on your media bucket, resize an image with Pillow on upload, check CloudWatch Logs.
- **EventBridge:** schedule that Lambda with a `rate(5 minutes)` rule.
- **SQS:** create a queue, send a message in the console, receive it with the CLI.
- **SNS:** create a topic, subscribe your email, publish, connect it to a CloudWatch alarm.
- **DynamoDB:** create a table, put an item, query it.
- **ECS/Fargate:** deploy the `nginx` image as a service behind a public IP.
- **Athena:** upload a CSV to S3, create a table over it, run a `SELECT`.

---

# What to record

**Per phase, in the repo:**
- `notes/<phase>.md` — one line on what it does, why you'd choose it, what surprised you, what it cost, how to delete it
- the commands and config you actually used
- screenshots of the working thing

**A screen recording** helps for steps you'll repeat. The written note is what you'll revise from before an interview.

**The README** is what an employer sees: architecture diagram, what runs where, and why each choice was made.

---

# Session discipline

**Start:** confirm region is Mumbai; decide what you're building today.

**End, every time:**
- [ ] Terminate EC2 instances
- [ ] Delete RDS, ElastiCache, ALBs, NAT gateways
- [ ] Release unattached Elastic IPs
- [ ] Delete stray EBS volumes, snapshots, AMIs
- [ ] Billing → Bills → Charges by service
- [ ] Commit notes and config to the repo

After Phase 10, that whole checklist is one `terraform destroy`.

---

# Rough pacing

Phases 1–3 are one weekend and give you a working site with a pipeline — the part the job listings actually name. Phases 4–8 are a weekend each. Phases 9–12 are single sessions.

Finish Phase 1 before planning further.

---

# POST-PHASE 12 — Docker & Containerization (The Next Frontier)

### Why Docker Belongs AFTER Phase 12 (Not Before):
1. **The Stateless Prerequisite:**
   - In Phases 1–2, the server is a monolith (DB, files, web server on one box).
   - In Phases 4–9, we decouple the stack:
     - MySQL moves to AWS RDS (Phase 4).
     - Uploaded media moves to AWS S3 + CloudFront (Phase 5).
     - Object caching moves to AWS ElastiCache Redis (Phase 8).
     - Traffic routes through Application Load Balancer (Phase 9).
   - By Phase 9, the EC2 server has zero state. **A stateless app is the exact prerequisite for Docker.**
2. **Avoiding Cognitive Overload:**
   - Introducing Docker during Phases 3–9 forces you to learn two massive systems simultaneously (AWS VPC/IAM vs Docker bridge networking/volumes).
   - Once AWS infrastructure is mastered, Docker becomes a simple, enjoyable 2-day exercise because you already know Nginx, PHP-FPM, and Linux internals inside out.

### The Post-Phase 12 Docker Milestone:
- Write a clean `Dockerfile` for WordPress + Nginx + PHP-FPM.
- Package the decoupled application into a Docker container.
- Push the Docker image to **AWS ECR** (Elastic Container Registry).
- Deploy the container serverlessly onto **AWS ECS with AWS Fargate**!
