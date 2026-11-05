with open('notes/phase-9.md', 'r', encoding='utf-8') as f:
    text = f.read()

target = """### 2. Target Group Creation & Health Check Configuration:
*(Target Group form and created target group screenshots to be attached)*"""

replacement = """### 2. Target Group Creation & Health Check Configuration:

![Create Target Group Form Configured](images/p9-step3-create-target-group-form-configured.png)
*Console State:* Configured **Create target group** form for `wp-lab-tg`. Selected target type `Instances`, protocol `HTTP:80`, IPv4, default VPC `vpc-09f8bf588537d19f`, and protocol version `HTTP1`. Configured health check path to `/` and opened **Advanced health check settings** to set Success codes to `200,301,302` and Healthy threshold to `2`. Ready to click bottom-right orange **Next** button.

### 3. Target Group Created Successfully:
*(Created target group list screenshot to be attached)*"""

if target in text:
    text = text.replace(target, replacement)
    with open('notes/phase-9.md', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: Updated phase-9.md with Target Group form screenshot!")
else:
    print("Target not found")

