with open('notes/phase-9.md', 'r', encoding='utf-8') as f:
    text = f.read()

target = """![Edit Inbound Rules Form Initial](images/p9-step2-edit-inbound-rules-form-initial.png)
*Console State:* In **Edit inbound rules** modal for `sg-05f3d510a4a41385e`. Removing public `0.0.0.0/0` on HTTP Port 80 and HTTPS Port 443 and chaining source to `sg-0307c2acd8052208f` (`wp-lab-alb-sg`).

*(Chained inbound rules saved screenshot to be attached)*"""

replacement = """![Edit Inbound Rules Form Initial](images/p9-step2-edit-inbound-rules-form-initial.png)
*Console State:* In **Edit inbound rules** modal for `sg-05f3d510a4a41385e`. Removing public `0.0.0.0/0` on HTTP Port 80 and HTTPS Port 443 and chaining source to `sg-0307c2acd8052208f` (`wp-lab-alb-sg`).

![Security Group Dropdown Selection](images/p9-step2-edit-inbound-rules-dropdown-selection.png)
*Console State:* In **Edit inbound rules** modal, opened the Source dropdown for HTTP (Port 80). AWS lists available Security Groups in the VPC. Selected **`wp-lab-alb-sg | sg-0307c2acd8052208f`**, cleanly enforcing Security Group Chaining without manually typing or risking optical ID errors. Deleted the redundant HTTPS Port 443 rule.

*(Chained inbound rules saved screenshot to be attached)*"""

if target in text:
    text = text.replace(target, replacement)
    with open('notes/phase-9.md', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: Updated phase-9.md with SG dropdown screenshot!")
else:
    print("Target not found")

