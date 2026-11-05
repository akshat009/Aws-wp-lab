import sys

with open('AGENTS.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_section = [
    '## Current phase: 9\n',
    '\n',
    'Phase 8 completed and verified (Amazon ElastiCache Redis OSS 7.1.0 standalone cluster `wp-lab-redis` provisioned on `cache.t3.micro` in default VPC with Security Group chaining via `wp-lab-redis-sg` authorizing inbound port 6379 from `wp-lab-sg`; PHP Redis C-extension `php-redis` (6.2.0) and `redis-tools` installed on Ubuntu EC2 `wp-lab` and verified via `redis-cli ping` returning `PONG`; WordPress configured with `WP_REDIS_HOST`, `WP_REDIS_PORT`, `WP_CACHE_KEY_SALT` in `wp-config.php`; Redis Object Cache plugin activated with Status **Connected**, Filesystem **Writeable**, Redis **Reachable**; Query Monitor plugin verified database query count dropped by **97.1%** down to **1 single query (0.0005s)**; `notes/phase-8.md` documented with 13 verified screenshots, 9 gotchas, 8 cloud architecture interview Q&As, and complete Definition of Done verification). Next: Phase 9 (Scale it — Amazon Machine Image (AMI) from `wp-lab`, Application Load Balancer (ALB) across multiple AZs, Target Group, EC2 Launch Template, Auto Scaling Group (ASG), and instance termination survival verification).\n',
    '\n',
    '---\n',
    '\n',
    '### 📋 Phase 9 Execution Plan (Scale it — Application Load Balancer & Auto Scaling)\n',
    '\n',
    '> **Current Infrastructure Status:** EC2 (`wp-lab`), RDS MySQL (`wp-lab-db`), ElastiCache Redis (`wp-lab-redis`), and CloudFront/S3 are all active, running, and fully decoupled. We now scale the stateless web tier horizontally.\n',
    '\n',
    '#### Execution Checklist for Phase 9:\n',
    '- [ ] **Step 1: Create Amazon Machine Image (AMI) of `wp-lab`:**\n',
    '  - Create an AMI named `wp-lab-golden-ami` from the running `wp-lab` EC2 instance.\n',
    '  - Wait for AMI status to transition from `pending` to `available`.\n',
    '- [ ] **Step 2: Create Application Load Balancer (ALB) Security Group:**\n',
    '  - Create `wp-lab-alb-sg` permitting inbound HTTP (Port 80) and HTTPS (Port 443) from `0.0.0.0/0`.\n',
    '  - Update EC2 Security Group `wp-lab-sg` to permit HTTP/HTTPS traffic strictly from `wp-lab-alb-sg` (Security Group Chaining).\n',
    '- [ ] **Step 3: Create Target Group:**\n',
    '  - Target type: Instances, Protocol: HTTP, Port 80, VPC: Default VPC.\n',
    '  - Health check path: `/` (or custom health check path), Success codes: `200,301,302`.\n',
    '- [ ] **Step 4: Provision Application Load Balancer (ALB):**\n',
    '  - Name: `wp-lab-alb`, Internet-facing, IPv4.\n',
    '  - Subnets: Select at least 2 Availability Zones (e.g. `ap-south-1a`, `ap-south-1b`).\n',
    '  - Listeners: HTTP Port 80 (forwarding to Target Group) and HTTPS Port 443 (with ACM SSL certificate).\n',
    '- [ ] **Step 5: Create Launch Template:**\n',
    '  - Name: `wp-lab-lt`.\n',
    '  - AMI: `wp-lab-golden-ami`, Instance Type: `t3.micro`, SG: `wp-lab-sg`, IAM Role: SSM Profile.\n',
    '- [ ] **Step 6: Provision Auto Scaling Group (ASG):**\n',
    '  - Name: `wp-lab-asg`.\n',
    '  - Desired: 2, Min: 1, Max: 3.\n',
    '  - Attach to existing Target Group (`wp-lab-tg`).\n',
    '  - Enable ELB Health Checks.\n',
    '- [ ] **Step 7: Verify "Done When" Criteria:**\n',
    '  - Access site via ALB DNS name: `http://<alb-dns-name>` loads cleanly.\n',
    '  - Terminate one EC2 instance manually in EC2 Dashboard.\n',
    '  - Confirm ALB continues serving traffic uninterrupted without downtime, and ASG automatically launches a replacement instance to restore Desired capacity.\n',
    '\n',
    '---\n'
]

start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if line.startswith('## Current phase:'):
        start_idx = i
    elif start_idx is not None and i > start_idx + 10 and line.strip() == '---':
        end_idx = i + 1
        break

if start_idx is not None and end_idx is not None:
    lines = lines[:start_idx] + new_section + lines[end_idx:]
    with open('AGENTS.md', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print('SUCCESS: AGENTS.md updated!')
else:
    print(f'Indices not found: {start_idx}, {end_idx}')

