with open('notes/phase-9.md', 'r', encoding='utf-8') as f:
    text = f.read()

target = """## Implementation Steps & Progress Tracker

- [ ] **Step 1: Create Golden AMI from Web Server**
  - Stop instance briefly to prevent filesystem writes.
  - Create AMI `wp-lab-golden-v1`.
- [ ] **Step 2: Create EC2 Launch Template**
  - Name: `wp-lab-lt`.
  - Reference AMI `wp-lab-golden-v1` and instance type `t3.micro`.
  - Attach IAM Role `wp-lab-s3-role`.
  - Configure User Data script to pull latest configurations on boot.
- [ ] **Step 3: Provision Application Load Balancer (ALB) & Target Group**
  - Create Target Group `wp-lab-tg` (Health check path: `/wp-login.php`, success code: `200`).
  - Create internet-facing ALB `wp-lab-alb` across 2 public subnets.
- [ ] **Step 4: Create Auto Scaling Group (ASG)**
  - Group name: `wp-lab-asg`.
  - Desired capacity: 2, Min: 2, Max: 4.
  - Enable Target Group health checks.
- [ ] **Step 5: Definition of Done Chaos Engineering Test**
  - Open ALB DNS name in browser.
  - Manually terminate EC2 Instance A from AWS Console.
  - Continuously refresh ALB URL: verify 0 downtime.
  - Verify Auto Scaling detects failure and launches Instance C automatically!

</details>

---

<details>
<summary><h3>💡 Execution Details & Real-World Gotchas (Click to Expand)</h3></summary>"""

replacement = """## Implementation Steps & Progress Tracker

- [ ] **Step 1: Create Amazon Machine Image (AMI) of `wp-lab`**
  - Select running instance `wp-lab` (`i-0454e55a303f5f9ae`).
  - Actions ➔ Image and templates ➔ Create image (`wp-lab-golden-ami`).
  - Wait for status to transition from `pending` to `available`.
- [ ] **Step 2: Create Application Load Balancer Security Group (`wp-lab-alb-sg`)**
  - Allow Inbound HTTP (80) & HTTPS (443) from `0.0.0.0/0`.
  - Update `wp-lab-sg` to accept web traffic strictly from `wp-lab-alb-sg` (Security Group Chaining).
- [ ] **Step 3: Create Target Group (`wp-lab-tg`)**
  - Target type: Instances, Protocol: HTTP, Port: 80, VPC: Default VPC.
  - Health check path: `/` (or `/wp-login.php`), Success codes: `200,301,302`.
- [ ] **Step 4: Provision Application Load Balancer (`wp-lab-alb`)**
  - Internet-facing ALB deployed across at least 2 public AZs (`ap-south-1a`, `ap-south-1b`).
  - Attach listener forwarding traffic to `wp-lab-tg`.
- [ ] **Step 5: Create EC2 Launch Template (`wp-lab-lt`)**
  - Base AMI: `wp-lab-golden-ami`, Instance Type: `t3.micro`.
  - Security Group: `wp-lab-sg`, IAM Role: `wp-lab-s3-role` / SSM profile.
- [ ] **Step 6: Provision Auto Scaling Group (`wp-lab-asg`)**
  - Desired: 2, Min: 1, Max: 3 across multiple AZs.
  - Attach to existing Target Group `wp-lab-tg` and enable ELB health checks.
- [ ] **Step 7: Verify "Done When" Criteria (High Availability & Self-Healing)**
  - Access site via ALB DNS name: `http://<alb-dns-name>` loads cleanly.
  - Manually terminate one EC2 instance from EC2 Dashboard.
  - Verify zero site downtime on ALB URL and confirm ASG automatically spawns a replacement node.

</details>

---

<details open>
<summary><h3>⚙️ Step 1 Execution Details: Create Golden AMI from Web Server (Click to Expand)</h3></summary>

## Step 1 Execution Details: Create Golden AMI from Web Server

A **Golden AMI** (Amazon Machine Image) is a pre-configured, battle-tested machine image containing the entire operating system, web server (Nginx), PHP runtime (PHP 8.5-FPM), compiled C-extensions (`php-redis`), application code (WordPress), and configuration (`wp-config.php`). 

### Why a Golden AMI is Essential for Auto Scaling:
If an Auto Scaling Group launches generic Ubuntu instances from scratch, each new instance must execute bootstrap scripts (`apt update`, `apt install nginx`, download WordPress, configure DB salts). This bootstrapping process takes 5 to 10 minutes, creating a dangerous lag during sudden traffic spikes. With a Golden AMI, new instances boot up into a fully operational, warm state in under 60 seconds.

### 1. EC2 Dashboard Instance Selection & Create Image Action:

![EC2 Dashboard Actions Create Image Menu](images/p9-step1-ec2-actions-create-image-menu.png)
*Console State:* Navigated to **EC2 Dashboard ➔ Instances** in `ap-south-1` Mumbai. Verified `wp-lab` (`i-0454e55a303f5f9ae`) is in **Running** state with **2/2 checks passed**. Selected instance checkbox and opened top-right dropdown: **Actions ➔ Image and templates ➔ Create image**.

### 2. Golden AMI Configuration Parameters:

| Parameter | Value | Architectural Purpose |
| :--- | :--- | :--- |
| **Source Instance** | `i-0454e55a303f5f9ae` (`wp-lab`) | Capture fully decoupled WordPress stack (Phases 1–8). |
| **Image Name** | `wp-lab-golden-ami` | Identifiable golden image reference for Launch Template. |
| **Image Description** | `Golden AMI for WordPress lab auto scaling (Phases 1-8 configured)` | Documentation & auditing clarity. |
| **No Reboot** | **Unchecked** (Default) | AWS cleanly flushes cached filesystem blocks to EBS before snapshotting. |
| **Root Volume** | 8 GB gp3 (Default) | Preserves exact disk layout and OS partition structure. |
| **Tags** | `Name: wp-lab-golden-ami` | Cost allocation and resource inventory tracking. |

</details>

---

<details>
<summary><h3>💡 Execution Details & Real-World Gotchas (Click to Expand)</h3></summary>"""

if target in text:
    text = text.replace(target, replacement)
    with open('notes/phase-9.md', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: Updated phase-9.md")
else:
    print("Target not found in phase-9.md")

