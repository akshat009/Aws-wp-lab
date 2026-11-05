with open('notes/phase-9.md', 'r', encoding='utf-8') as f:
    text = f.read()

target = """### 3. Target Group Created Successfully:
*(Created target group list screenshot to be attached)*"""

replacement = """### 3. Register Targets (Dynamic Auto Scaling Pattern):

![Register Targets Empty](images/p9-step3-register-targets-empty-selection.png)
*Console State:* In **Step 2: Register targets** wizard. We intentionally do NOT manually register the existing `wp-lab` instance. In an auto-scaled elastic architecture, instances are dynamic and disposable. The Auto Scaling Group (ASG) provisioned in Step 6 will dynamically register and deregister instances with this target group automatically as it scales. Ready to click orange **Next / Create target group** button.

### 4. Target Group Created Successfully:
*(Created target group list screenshot to be attached)*"""

if target in text:
    text = text.replace(target, replacement)
    with open('notes/phase-9.md', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: Updated phase-9.md with register targets screenshot!")
else:
    print("Target not found")

