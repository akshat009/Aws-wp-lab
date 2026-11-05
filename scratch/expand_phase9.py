with open('notes/phase-9.md', 'r', encoding='utf-8') as f:
    text = f.read()

target_start = "<details open>\n<summary><h3>⚙️ Step 1 Execution Details: Create Golden AMI from Web Server (Click to Expand)</h3></summary>"

replacement = """<details open>
<summary><h3>⚙️ Step 1 Execution Details: Create Golden AMI from Web Server (Click to Expand)</h3></summary>

## Step 1 Execution Details: Create Golden AMI from Web Server

A **Golden AMI** (Amazon Machine Image) is a pre-configured, battle-tested machine image containing the entire operating system, web server (Nginx), PHP runtime (PHP 8.5-FPM), compiled C-extensions (`php-redis`), application code (WordPress), and configuration (`wp-config.php`). 

### Why a Golden AMI is Essential for Auto Scaling:
If an Auto Scaling Group launches generic Ubuntu instances from scratch, each new instance must execute bootstrap scripts (`apt update`, `apt install nginx`, download WordPress, configure DB salts). This bootstrapping process takes 5 to 10 minutes, creating a dangerous lag during sudden traffic spikes. With a Golden AMI, new instances boot up into a fully operational, warm state in under 60 seconds.

### Step-by-Step Console Walkthrough:
1. Navigate to **EC2 Dashboard ➔ Instances** (`ap-south-1` Mumbai).
2. Select the checkbox for running instance `wp-lab` (`i-0454e55a303f5f9ae`).
3. Click top-right dropdown: **Actions ➔ Image and templates ➔ Create image**.
4. Configure the image parameters:
   - **Image name:** `wp-lab-golden-ami`
   - **Image description:** `Golden AMI for WordPress lab auto scaling (Phases 1-8 configured)`
   - **No reboot:** Keep **unchecked** (default) to ensure dirty filesystem buffers are cleanly synced to EBS.
   - **Tag:** `Key: Name`, `Value: wp-lab-golden-ami`
5. Click **Create image** button.
6. Verify status in **Images ➔ AMIs** (Status transitions from `pending` to `available`).

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

### 3. AMI Creation Status & Availability:
*(AMI creation form and pending/available status screenshots to be attached)*

</details>

---

<details>
<summary><h3>⚙️ Step 2 Execution Details: Create ALB Security Group (Click to Expand)</h3></summary>

## Step 2 Execution Details: Create ALB Security Group

*(To be documented during Step 2 execution)*

</details>

---

<details>
<summary><h3>⚙️ Step 3 Execution Details: Create Target Group (Click to Expand)</h3></summary>

## Step 3 Execution Details: Create Target Group

*(To be documented during Step 3 execution)*

</details>

---

<details>
<summary><h3>⚙️ Step 4 Execution Details: Provision Application Load Balancer (Click to Expand)</h3></summary>

## Step 4 Execution Details: Provision Application Load Balancer

*(To be documented during Step 4 execution)*

</details>

---

<details>
<summary><h3>⚙️ Step 5 Execution Details: Create EC2 Launch Template (Click to Expand)</h3></summary>

## Step 5 Execution Details: Create EC2 Launch Template

*(To be documented during Step 5 execution)*

</details>

---

<details>
<summary><h3>⚙️ Step 6 Execution Details: Provision Auto Scaling Group (Click to Expand)</h3></summary>

## Step 6 Execution Details: Provision Auto Scaling Group

*(To be documented during Step 6 execution)*

</details>

---

<details>
<summary><h3>⚙️ Step 7 Execution Details: Chaos Engineering & High Availability Verification (Click to Expand)</h3></summary>

## Step 7 Execution Details: Chaos Engineering & High Availability Verification

*(To be documented during Step 7 execution)*

</details>"""

# find start
idx = text.find(target_start)
if idx != -1:
    # find where Gotchas start
    gotchas_idx = text.find("<details>\n<summary><h3>💡 Execution Details & Real-World Gotchas")
    if gotchas_idx != -1:
        text = text[:idx] + replacement + "\n\n---\n\n" + text[gotchas_idx:]
        with open('notes/phase-9.md', 'w', encoding='utf-8') as f:
            f.write(text)
        print("SUCCESS: Fully structured phase-9.md with all steps!")
    else:
        print("Gotchas index not found")
else:
    print("target_start not found")

