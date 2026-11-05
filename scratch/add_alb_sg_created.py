with open('notes/phase-9.md', 'r', encoding='utf-8') as f:
    text = f.read()

target = """### 3. ALB Security Group Created & Security Group Chaining:
*(Created security group and EC2 security group chained rule screenshots to be attached)*"""

replacement = """### 3. ALB Security Group Created Successfully:

![ALB Security Group Created](images/p9-step2-alb-sg-created-success.png)
*Console State:* Provisioned `wp-lab-alb-sg` with Security Group ID **`sg-0307c2acd8052208f`** in default VPC `vpc-09f8bf588537d19f`. Active inbound rules allow HTTP (Port 80) and HTTPS (Port 443) from `0.0.0.0/0`. Outbound policy permits all traffic to `0.0.0.0/0`. Next, we reference this Security Group ID to configure Security Group Chaining on the EC2 web server firewall.

### 4. Security Group Chaining (Updating EC2 Web Server Inbound Rules):
*(EC2 security group edit inbound rules screenshot to be attached)*"""

if target in text:
    text = text.replace(target, replacement)
    with open('notes/phase-9.md', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: Updated phase-9.md with Step 2 created SG screenshot!")
else:
    print("Target not found")

