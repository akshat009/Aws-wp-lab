with open('notes/phase-9.md', 'r', encoding='utf-8') as f:
    text = f.read()

target = """### 2. Golden AMI Configuration Parameters:

| Parameter | Value | Architectural Purpose |
| :--- | :--- | :--- |
| **Source Instance** | `i-0454e55a303f5f9ae` (`wp-lab`) | Capture fully decoupled WordPress stack (Phases 1–8). |
| **Image Name** | `wp-lab-golden-ami` | Identifiable golden image reference for Launch Template. |
| **Image Description** | `Golden AMI for WordPress lab auto scaling (Phases 1-8 configured)` | Documentation & auditing clarity. |
| **No Reboot** | **Unchecked** (Default) | AWS cleanly flushes cached filesystem blocks to EBS before snapshotting. |
| **Root Volume** | 8 GB gp3 (Default) | Preserves exact disk layout and OS partition structure. |
| **Tags** | `Name: wp-lab-golden-ami` | Cost allocation and resource inventory tracking. |

### 3. AMI Creation Status & Availability:
*(AMI creation form and pending/available status screenshots to be attached)*"""

replacement = """### 2. Create Image Form Configured:

![Create Image Form Configured](images/p9-step1-create-image-form-configured.png)
*Console State:* Configured **Create image** form for source instance `i-0454e55a303f5f9ae (wp-lab)`. Set Image name to `wp-lab-golden-ami`, description to `Golden AMI for WordPress lab auto scaling (Phases 1-8 configured)`, Boot mode override to `Default`, and confirmed **Reboot instance** is enabled to ensure filesystem cache is flushed to disk. Attached 20 GB gp3 root volume. Ready to click bottom-right orange **Create image** button.

### 3. Golden AMI Configuration Parameters:

| Parameter | Value | Architectural Purpose |
| :--- | :--- | :--- |
| **Source Instance** | `i-0454e55a303f5f9ae` (`wp-lab`) | Capture fully decoupled WordPress stack (Phases 1–8). |
| **Image Name** | `wp-lab-golden-ami` | Identifiable golden image reference for Launch Template. |
| **Image Description** | `Golden AMI for WordPress lab auto scaling (Phases 1-8 configured)` | Documentation & auditing clarity. |
| **Reboot Instance** | **Checked** (Default) | AWS cleanly reboots so data is at rest when snapshots are taken. |
| **Root Volume** | 20 GB gp3 (`/dev/sda1`) | Preserves exact disk layout and OS partition structure. |
| **Tags** | `Name: wp-lab-golden-ami` | Cost allocation and resource inventory tracking. |

### 4. AMI Creation Status & Availability:
*(Pending / available status screenshot to be attached)*"""

if target in text:
    text = text.replace(target, replacement)
    with open('notes/phase-9.md', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: Updated phase-9.md with form screenshot!")
else:
    print("Target not found")

