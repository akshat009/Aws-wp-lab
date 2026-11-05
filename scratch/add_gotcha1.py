with open('notes/phase-9.md', 'r', encoding='utf-8') as f:
    text = f.read()

target = """<details>
<summary><h3>💡 Execution Details & Real-World Gotchas (Click to Expand)</h3></summary>

## Execution Details & Real-World Gotchas

*(To be documented during Phase 9 live execution)*

</details>"""

replacement = """<details open>
<summary><h3>💡 Execution Details & Real-World Gotchas (Click to Expand)</h3></summary>

## Execution Details & Real-World Gotchas

### Gotcha 1: In-Place Rule Type Mutation Error ("You may not specify a referenced group id for an existing IPv4 CIDR rule")
- **Symptom:** When editing inbound rules for the EC2 Security Group, deleting `0.0.0.0/0` and pasting the ALB Security Group ID (`sg-0307c2acd8052208f`) into the same row causes AWS to throw a red validation error:
  ```text
  You may not specify a referenced group id for an existing IPv4 CIDR rule.
  ```

![Security Group Rule Type Mutation Error](images/p9-gotcha1-referenced-group-id-existing-cidr-error.png)

- **Cause:** In AWS EC2, each security group rule is assigned an immutable internal rule ID (`sgr-xxxxxxxxxxxxxxxxx`) and a typed schema (e.g., `IPv4 CIDR` vs `Security Group Reference`). AWS does NOT permit mutating an existing CIDR-typed rule into a Security Group Reference rule in-place.
- **Fix:** Do not overwrite the existing CIDR row. Instead:
  1. Click **Delete** on both existing rows (HTTPS 443 and HTTP 80).
  2. Click **Add rule** to create a fresh, unassigned rule row.
  3. Configure Type: `HTTP`, Port: `80`, Source: Select `wp-lab-alb-sg` (`sg-0307c2acd8052208f`).
  4. Click **Save rules**. AWS provisions a fresh Security Group Reference rule without schema collision!

</details>"""

if target in text:
    text = text.replace(target, replacement)
    with open('notes/phase-9.md', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: Added Gotcha 1 to phase-9.md!")
else:
    print("Target not found")

