with open('notes/phase-9.md', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update progress tracker for Step 2
target_tracker = """- [ ] **Step 2: Create Application Load Balancer Security Group (`wp-lab-alb-sg`)**
  - Allow Inbound HTTP (80) & HTTPS (443) from `0.0.0.0/0`.
  - Update `wp-lab-sg` to accept web traffic strictly from `wp-lab-alb-sg` (Security Group Chaining)."""

replacement_tracker = """- [x] **Step 2: Create Application Load Balancer Security Group (`wp-lab-alb-sg`)**
  - Created `wp-lab-alb-sg` (`sg-0307c2acd8052208f`) allowing Inbound HTTP (80) & HTTPS (443) from `0.0.0.0/0`.
  - Updated EC2 web server SG `launch-wizard-4` (`sg-05f3d510a4a41385e`) to accept HTTP (80) strictly from `sg-0307c2acd8052208f` (**Security Group Chaining Verified**)."""

if target_tracker in text:
    text = text.replace(target_tracker, replacement_tracker)

# 2. Update Step 2 screenshot & open Step 3
target_step2 = """*(Chained inbound rules saved screenshot to be attached)*

</details>

---

<details>
<summary><h3>⚙️ Step 3 Execution Details: Create Target Group (Click to Expand)</h3></summary>

## Step 3 Execution Details: Create Target Group

*(To be documented during Step 3 execution)*

</details>"""

replacement_step2 = """![Chained Inbound Rule Configured](images/p9-step2-ec2-sg-chained-rule-configured.png)
*Console State:* Cleanly resolved the rule mutation gotcha by creating a fresh HTTP (Port 80) rule. Inbound traffic is strictly authorized from source **`sg-0307c2acd8052208f`** (`wp-lab-alb-sg`). Deleted all public `0.0.0.0/0` entries. Clicked orange **Save rules** button to lock down the EC2 instances.

</details>

---

<details open>
<summary><h3>⚙️ Step 3 Execution Details: Create Target Group (Click to Expand)</h3></summary>

## Step 3 Execution Details: Create Target Group (`wp-lab-tg`)

A **Target Group** routes requests to one or more registered targets (such as EC2 instances) and performs automated periodic health checks:
- If a target returns successful HTTP response codes (e.g., `200,301,302`), the load balancer keeps sending traffic to it.
- If a target crashes or returns 5xx errors, the ALB marks it **Unhealthy** and stops routing visitor traffic to it.

### Target Group Configuration Matrix:

| Parameter | Configuration Value | Architectural Purpose |
| :--- | :--- | :--- |
| **Target Type** | `Instances` | Route traffic to dynamically scaled EC2 instances. |
| **Target Group Name** | `wp-lab-tg` | Identifiable backend pool for WordPress web servers. |
| **Protocol : Port** | `HTTP : 80` | Internal unencrypted traffic between ALB and Nginx. |
| **IP Address Type** | `IPv4` | Standard VPC IPv4 addressing. |
| **VPC** | Default VPC (`vpc-09f8bf588537d19f`) | Must match the VPC where EC2 web instances live. |
| **Protocol Version** | `HTTP1` | Standard HTTP/1.1 communication with backend Nginx. |
| **Health Check Protocol** | `HTTP` | Standard HTTP GET ping. |
| **Health Check Path** | `/` (or `/wp-login.php`) | Tests if Nginx and PHP-FPM are responding. |
| **Healthy Threshold** | `2` | 2 consecutive successes to mark node healthy. |
| **Unhealthy Threshold**| `2` | 2 consecutive failures to mark node unhealthy and stop traffic. |
| **Timeout / Interval** | `5 seconds` / `15 seconds` | Fast failure detection and recovery. |
| **Success Codes** | `200,301,302` | Accounts for WordPress canonical redirects and login page hits. |

### 1. Target Group Creation & Health Check Configuration:
*(Target Group form and created target group screenshots to be attached)*

</details>"""

if target_step2 in text:
    text = text.replace(target_step2, replacement_step2)
    with open('notes/phase-9.md', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: Updated phase-9.md with chained rule screenshot and Step 3 details!")
else:
    print("Target step2 not found")

