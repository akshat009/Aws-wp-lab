with open('AGENTS.md', 'r', encoding='utf-8') as f:
    text = f.read()

target = """### 📋 Tomorrow Session Startup Checklist (Before Executing Phase 9)

> **Current Infrastructure Status:** EC2 (`wp-lab`) and RDS MySQL (`wp-lab-db`) should be stopped tonight. When starting tomorrow:

#### Startup Checklist for Tomorrow:
- [ ] **Step 1: Start Amazon RDS MySQL Database:**
  - Go to **RDS Console ➔ Databases** (`ap-south-1` Mumbai).
  - Select `wp-lab-db` ➔ Click **Actions ➔ Start**.
  - Wait ~2–3 minutes for status to change from `Starting` to `Available`.
- [ ] **Step 2: Start AWS EC2 Web Server:**
  - Go to **EC2 Dashboard ➔ Instances** (`ap-south-1` Mumbai).
  - Select `wp-lab` ➔ Click **Instance state ➔ Start instance**.
  - Wait for Status check to reach `2/2 checks passed`.
- [ ] **Step 3: Verify / Start ElastiCache Redis:**
  - Go to **Amazon ElastiCache ➔ Redis OSS caches**.
  - If cluster `wp-lab-redis` was kept running: Verify status is `Available`.
  - If cluster was deleted: Recreate with exact name `wp-lab-redis`, `cache.t3.micro`, attach `wp-lab-redis-sg` (`sg-02b787ce6751bd8e3`).
- [ ] **Step 4: Quick Health Check:**
  - Open `https://lab.asaxenadev.com` in browser. Confirm site loads with HTTP 200 OK.
  - Open `https://lab.asaxenadev.com/wp-admin/` ➔ **Settings ➔ Redis**. Confirm Status is **Connected**."""

replacement = """### 📋 Tomorrow Session Startup Checklist (Before Executing Phase 9)

> **Current Infrastructure Status:** WordPress and MySQL are running on EC2 (`wp-lab`). When `wp-lab` is stopped, local MySQL stops automatically with it. When starting tomorrow:

#### Startup Checklist for Tomorrow:
- [ ] **Step 1: Start AWS EC2 Web Server:**
  - Go to **EC2 Dashboard ➔ Instances** (`ap-south-1` Mumbai).
  - Select `wp-lab` ➔ Click **Instance state ➔ Start instance**.
  - Wait ~1–2 minutes for Status check to reach `2/2 checks passed`.
- [ ] **Step 2: Verify / Start ElastiCache Redis:**
  - Go to **Amazon ElastiCache ➔ Redis OSS caches**.
  - If cluster `wp-lab-redis` was kept running: Verify status is `Available`.
  - If cluster was deleted: Recreate with exact name `wp-lab-redis`, `cache.t3.micro`, attach `wp-lab-redis-sg` (`sg-02b787ce6751bd8e3`).
- [ ] **Step 3: Quick Health Check:**
  - Open `https://lab.asaxenadev.com` in browser. Confirm site loads with HTTP 200 OK.
  - Open `https://lab.asaxenadev.com/wp-admin/` ➔ **Settings ➔ Redis**. Confirm Status is **Connected**."""

if target in text:
    text = text.replace(target, replacement)
    with open('AGENTS.md', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: Updated AGENTS.md")
else:
    print("Target not found")

