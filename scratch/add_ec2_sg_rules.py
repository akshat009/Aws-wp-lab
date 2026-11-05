with open('notes/phase-9.md', 'r', encoding='utf-8') as f:
    text = f.read()

target = """### 4. Security Group Chaining (Updating EC2 Web Server Inbound Rules):
*(EC2 security group edit inbound rules screenshot to be attached)*"""

replacement = """### 4. Security Group Chaining (Updating EC2 Web Server Inbound Rules):

![EC2 Current Inbound Rules Before Chaining](images/p9-step2-ec2-sg-current-inbound-rules.png)
*Console State:* Navigated to **`launch-wizard-4` (`sg-05f3d510a4a41385e`)** details page. Currently, inbound rules allow public HTTP (Port 80) and HTTPS (Port 443) from `0.0.0.0/0`. We click **Edit inbound rules** to replace public `0.0.0.0/0` with our ALB Security Group ID (`sg-0307c2acd8052208f`), enforcing strict Security Group Chaining.

*(Chained inbound rules saved screenshot to be attached)*"""

if target in text:
    text = text.replace(target, replacement)
    with open('notes/phase-9.md', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: Updated phase-9.md with EC2 SG current rules screenshot!")
else:
    print("Target not found")

