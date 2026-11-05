with open('notes/phase-9.md', 'r', encoding='utf-8') as f:
    text = f.read()

target = """### 1. Target Group Creation & Health Check Configuration:
*(Target Group form and created target group screenshots to be attached)*"""

replacement = """### 1. Existing Target Groups on EC2 Dashboard:

![Target Groups Landing Page](images/p9-step3-target-groups-landing-page.png)
*Console State:* Navigated to **EC2 Dashboard ➔ Load Balancing ➔ Target Groups** in `ap-south-1` Mumbai. Verified zero active target groups. Ready to click top-right orange **Create target group** button.

### 2. Target Group Creation & Health Check Configuration:
*(Target Group form and created target group screenshots to be attached)*"""

if target in text:
    text = text.replace(target, replacement)
    with open('notes/phase-9.md', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: Updated phase-9.md with Target Groups landing page screenshot!")
else:
    print("Target not found")

