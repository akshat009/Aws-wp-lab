with open('notes/phase-9.md', 'r', encoding='utf-8') as f:
    text = f.read()

target = """<details>
<summary><h3>⚙️ Step 2 Execution Details: Create ALB Security Group (Click to Expand)</h3></summary>

## Step 2 Execution Details: Create ALB Security Group

*(To be documented during Step 2 execution)*

</details>"""

replacement = """<details open>
<summary><h3>⚙️ Step 2 Execution Details: Create ALB Security Group & Security Group Chaining (Click to Expand)</h3></summary>

## Step 2 Execution Details: Create ALB Security Group & Security Group Chaining

Security Group Chaining is an enterprise cloud architecture defense-in-depth pattern. Web servers behind an Application Load Balancer must **never** accept direct HTTP/HTTPS connections from the public internet. Instead:
1. The **ALB Security Group (`wp-lab-alb-sg`)** accepts public traffic on Ports 80 and 443 from `0.0.0.0/0`.
2. The **EC2 Security Group (`wp-lab-sg` / `launch-wizard-4`)** restricts inbound web traffic strictly to packets originating from `wp-lab-alb-sg`.

### Security Group Architecture Matrix:

| Security Group | Inbound Ports | Source / Chaining Rule | Architectural Purpose |
| :--- | :--- | :--- | :--- |
| **`wp-lab-alb-sg`** (ALB) | TCP `80` (HTTP)<br>TCP `443` (HTTPS) | `0.0.0.0/0` (Anywhere IPv4) | Public internet access point for web visitors. |
| **`wp-lab-sg`** (EC2 Web) | TCP `80` (HTTP) | `wp-lab-alb-sg` (Chained SG ID) | Only traffic routed through ALB can reach web workers. |
| **`wp-lab-redis-sg`** (Cache) | TCP `6379` (Redis) | `wp-lab-sg` (`sg-05f3d510a4a41385e`) | Only web workers can read/write memory cache. |

### 1. Existing Security Groups on EC2 Dashboard:

![Security Groups Dashboard](images/p9-step2-security-groups-dashboard.png)
*Console State:* Navigated to **EC2 Dashboard ➔ Network & Security ➔ Security Groups** in `ap-south-1` Mumbai. Verified existing web server security group `launch-wizard-4` (`sg-05f3d510a4a41385e`) and ElastiCache Redis security group `wp-lab-redis-sg` (`sg-02b787ce6751bd8e3`). Ready to click top-right orange **Create security group** button.

### 2. Create ALB Security Group Form & Configuration:
*(Create form and created security group screenshots to be attached)*

</details>"""

if target in text:
    text = text.replace(target, replacement)
    with open('notes/phase-9.md', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: Updated phase-9.md with Step 2 SG details!")
else:
    print("Target not found")

