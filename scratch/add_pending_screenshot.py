with open('notes/phase-9.md', 'r', encoding='utf-8') as f:
    text = f.read()

target = """### 4. AMI Creation Status & Availability:
*(Pending / available status screenshot to be attached)*"""

replacement = """### 4. AMI Creation Status & Availability:

![AMI Status Pending](images/p9-step1-ami-status-pending.png)
*Console State:* Navigated to **EC2 Dashboard ➔ Images ➔ AMIs** in `ap-south-1` Mumbai under filter `Owned by me`. Successfully confirmed image `wp-lab-golden-ami` in **`pending`** status with root device type `ebs`. AWS is actively creating the underlying Amazon EBS volume snapshot in the background. Once the snapshot completes, status will transition to **`available`**."""

if target in text:
    text = text.replace(target, replacement)
    with open('notes/phase-9.md', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: Updated phase-9.md with AMI pending screenshot!")
else:
    print("Target not found")

