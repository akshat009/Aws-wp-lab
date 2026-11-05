with open('notes/phase-9.md', 'r', encoding='utf-8') as f:
    text = f.read()

target = """### 2. Create ALB Security Group Form & Configuration:
*(Create form and created security group screenshots to be attached)*"""

replacement = """### 2. Create ALB Security Group Form Configured:

![Create ALB Security Group Form](images/p9-step2-create-alb-sg-form-configured.png)
*Console State:* Configured `wp-lab-alb-sg` in default VPC `vpc-09f8bf588537d19f`. Set Inbound Rule 1 to **HTTP (Port 80)** from `0.0.0.0/0` (Anywhere-IPv4) and Inbound Rule 2 to **HTTPS (Port 443)** from `0.0.0.0/0` (Anywhere-IPv4). Outbound rule set to All traffic (`0.0.0.0/0`). Ready to click bottom-right orange **Create security group** button.

### 3. ALB Security Group Created & Security Group Chaining:
*(Created security group and EC2 security group chained rule screenshots to be attached)*"""

if target in text:
    text = text.replace(target, replacement)
    with open('notes/phase-9.md', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: Updated phase-9.md with Step 2 form screenshot!")
else:
    print("Target not found")

