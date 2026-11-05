with open('notes/phase-9.md', 'r', encoding='utf-8') as f:
    text = f.read()

target = """![Chained Inbound Rule Configured](images/p9-step2-ec2-sg-chained-rule-configured.png)
*Console State:* Cleanly resolved the rule mutation gotcha by creating a fresh HTTP (Port 80) rule. Inbound traffic is strictly authorized from source **`sg-0307c2acd8052208f`** (`wp-lab-alb-sg`). Deleted all public `0.0.0.0/0` entries. Clicked orange **Save rules** button to lock down the EC2 instances.

</details>"""

replacement = """![Chained Inbound Rule Configured](images/p9-step2-ec2-sg-chained-rule-configured.png)
*Console State:* Cleanly resolved the rule mutation gotcha by creating a fresh HTTP (Port 80) rule. Inbound traffic is strictly authorized from source **`sg-0307c2acd8052208f`** (`wp-lab-alb-sg`). Deleted all public `0.0.0.0/0` entries. Clicked orange **Save rules** button to lock down the EC2 instances.

![EC2 Inbound Rules Chained Successfully](images/p9-step2-ec2-sg-chained-rules-saved-success.png)
*Console State:* Navigated to `launch-wizard-4` (`sg-05f3d510a4a41385e`) details page. Verified green confirmation banner: *"Inbound security group rules successfully modified"*. Exactly one permission entry is active: TCP Port 80 authorized exclusively from `sg-0307c2acd8052208f` (`wp-lab-alb-sg`). Public internet access directly to EC2 web workers is now 100% eliminated!

</details>"""

if target in text:
    text = text.replace(target, replacement)
    with open('notes/phase-9.md', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: Updated phase-9.md with chained rules saved screenshot!")
else:
    print("Target not found")

