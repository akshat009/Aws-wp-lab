# Bonus Phase — Kubernetes (Amazon EKS) for Enterprise WordPress at Scale

> **Definition of Done:** Stateless WordPress deployed to an Amazon Elastic Kubernetes Service (EKS) cluster across multiple worker nodes, managed via Kubernetes manifests (Deployment, Service, Ingress, HPA), routed through the AWS Load Balancer Controller, and auto-scaling based on CPU/Memory load.

---

<details>
<summary><h3>🧠 Conceptual Foundations, Architecture & Trade-offs (Click to Expand)</h3></summary>

## What it does

Elevates containerized WordPress to enterprise-grade cloud orchestration using **Kubernetes (K8s) on Amazon EKS**:
1. Provisions a managed **Amazon EKS (Elastic Kubernetes Service)** control plane with managed node groups.
2. Deploys stateless WordPress **Pods** managed by a **Kubernetes Deployment** with self-healing, rolling updates, and liveness/readiness probes.
3. Automatically provisions an **Application Load Balancer (ALB)** using the **AWS Load Balancer Controller** via a Kubernetes `Ingress` resource.
4. Implements **Horizontal Pod Autoscaler (HPA)** to scale Pod replicas dynamically based on real-time CPU and Memory utilization.

---

## Why choose it (Over AWS ECS & Plain EC2)

- **Eliminates Cloud Vendor Lock-In:**
  AWS ECS is proprietary to Amazon Web Services. Kubernetes is an open-source CNCF standard. A Kubernetes deployment manifest runs identically on Amazon EKS, Google Kubernetes Engine (GKE), Microsoft Azure AKS, or on-premises bare-metal clusters.
- **Advanced Traffic Routing & Canary Deployments:**
  Kubernetes allows advanced traffic splitting, blue/green deployments, canary rollouts, and service mesh architectures (Istio / Linkerd) that are far more powerful than basic AWS Auto Scaling.
- **Granular Resource Packing & Cost Efficiency:**
  Multiple different microservices, background cron jobs, and WordPress pods can share the same underlying EKS worker nodes, optimizing hardware utilization down to millicores (`m`) and megabytes (`Mi`).

---

## Trade-offs

- **Operational Complexity (Day 2 Operations):**
  Kubernetes has a steep learning curve. Managing Kubernetes API version upgrades, Helm charts, CSI/CNI drivers, RBAC roles, and etcd backups requires specialized DevOps expertise.
- **Fixed Control Plane Cost:**
  Amazon EKS charges **$0.10 per hour ($73/month)** just for the managed EKS cluster control plane, regardless of whether you have 1 pod or 1,000 pods running. (ECS has zero cluster fee).
- **The "Stateful WordPress on K8s" Pitfall:**
  Many developers ruin their Kubernetes experience by trying to run stateful MySQL pods with persistent volume claims (PVC) or NFS (EFS) for shared uploads. Because we already decoupled state to **RDS (Phase 4)** and **S3 (Phase 5)**, our WordPress pods are 100% stateless and effortless to run on K8s!

---

## Architecture Diagram (Amazon EKS Enterprise Architecture)

```text
                                [Global Web Visitors]
                                          │
                                          │ HTTPS (lab.asaxenadev.com)
                                          ▼
                      [AWS Application Load Balancer (ALB)]
                        (Provisioned by AWS LB Controller)
                                          │
                       Traffic Routed to Pod IPs via AWS VPC CNI
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Amazon EKS Cluster (VPC Subnets)                      │
│                                                                             │
│  [Namespace: production]                                                    │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Kubernetes Deployment: wordpress-app               │  │
│  │                                                                       │  │
│  │  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────┐ │  │
│  │  │ Pod 1 (Node AZ-a)    │  │ Pod 2 (Node AZ-b)    │  │ Pod 3 (HPA)  │ │  │
│  │  │ ├── Nginx Container  │  │ ├── Nginx Container  │  │ (Auto-Scaled)│ │  │
│  │  │ └── PHP-FPM Container│  │ └── PHP-FPM Container│  │              │ │  │
│  │  └──────────┬───────────┘  └──────────┬───────────┘  └──────┬───────┘ │  │
│  └─────────────┼─────────────────────────┼─────────────────────┼─────────┘  │
│                │                         │                     │            │
│  [Horizontal Pod Autoscaler (HPA)] ──────┴─────────────────────┘            │
│  (Target: 70% CPU Utilization)                                              │
└────────────────┼─────────────────────────┼─────────────────────┼────────────┘
                 │                         │                     │
  ┌──────────────┴─────────────────────────┴─────────────────────┴─────────┐
  │                                                                        │
  ▼                                                                        ▼
[Amazon RDS MySQL (Phase 4)]                                 [Amazon S3 Media (Phase 5)]
(External DB via Secret)                                     (Offloaded via IAM IRSA)
```

</details>

---

<details>
<summary><h3>🚀 Production Kubernetes Manifests (Click to Expand)</h3></summary>

## Production Kubernetes Manifests

### 1. `deployment.yaml` (Stateless Deployment with Probes & Limits)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wordpress-deployment
  namespace: default
  labels:
    app: wordpress
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: wordpress
  template:
    metadata:
      labels:
        app: wordpress
    spec:
      containers:
      - name: wordpress
        image: 538820337781.dkr.ecr.ap-south-1.amazonaws.com/wp-lab-app:v1.0
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: "250m"
            memory: "512Mi"
          limits:
            cpu: "500m"
            memory: "1Gi"
        env:
        - name: DB_HOST
          valueFrom:
            configMapKeyRef:
              name: wp-config
              key: DB_HOST
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: wp-secrets
              key: DB_PASSWORD
        # Probes ensure zero downtime during rollouts
        readinessProbe:
          httpGet:
            path: /wp-login.php
            port: 80
          initialDelaySeconds: 10
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /wp-login.php
            port: 80
          initialDelaySeconds: 30
          periodSeconds: 10
```

---

### 2. `service.yaml` (ClusterIP Internal Routing)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: wordpress-service
  namespace: default
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 80
    protocol: TCP
  selector:
    app: wordpress
```

---

### 3. `ingress.yaml` (AWS Load Balancer Controller Integration)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: wordpress-ingress
  namespace: default
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:ap-south-1:538820337781:certificate/xxxx-xxxx
    alb.ingress.kubernetes.io/ssl-redirect: '443'
spec:
  rules:
  - host: lab.asaxenadev.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: wordpress-service
            port:
              number: 80
```

---

### 4. `hpa.yaml` (Horizontal Pod Autoscaler)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: wordpress-hpa
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: wordpress-deployment
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

</details>

---

<details>
<summary><h3>📦 IAM Roles for Service Accounts (IRSA) — Pod-Level Least Privilege (Click to Expand)</h3></summary>

## IAM Roles for Service Accounts (IRSA) — Pod-Level Least Privilege

In Kubernetes on AWS, pods should never use EC2 node instance credentials. Instead, Amazon EKS uses **IAM Roles for Service Accounts (IRSA)**:
1. An OIDC identity provider is associated with the EKS cluster.
2. A Kubernetes `ServiceAccount` is annotated with the IAM Role ARN:
   ```yaml
   apiVersion: v1
   kind: ServiceAccount
   metadata:
     name: wp-s3-serviceaccount
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::538820337781:role/wp-eks-s3-role
   ```
3. The pod assumes that IAM role directly via projected service account tokens, allowing only the WordPress pod to access `wp-lab-media-akshat-01` in S3!

</details>

---

<details>
<summary><h3>💡 Gotchas & Real-World Troubleshooting Log (Click to Expand)</h3></summary>

## Gotchas & Real-World Troubleshooting Log

### 💡 Gotcha 1: The Liveness vs Readiness Probe Distinction
- **What happens:** If `livenessProbe` is set too aggressively on WordPress, a heavy page load or plugin activation causes the probe to timeout, triggering Kubernetes to kill and restart the pod in an endless `CrashLoopBackOff`!
- **Rule of Thumb:**
  - `readinessProbe` tells K8s: *"Is the pod ready to receive user traffic?"* (If fails, remove from ALB target group, but do not kill).
  - `livenessProbe` tells K8s: *"Is the process deadlocked or completely hung?"* (If fails, terminate and restart container). Set `initialDelaySeconds` generously (30s+).

### 💡 Gotcha 2: Subnet Tagging for AWS Load Balancer Controller
- **Problem:** When applying the Ingress manifest, the ALB fails to create and logs: `Could not find any subnets for ALB`.
- **Root Cause:** AWS Load Balancer Controller discovers VPC subnets using specific tags:
  - Public Subnets (for Internet ALB): `kubernetes.io/role/elb = 1`
  - Private Subnets (for Internal ALB): `kubernetes.io/role/internal-elb = 1`

</details>

---

<details>
<summary><h3>🎯 Kubernetes & EKS Cloud Architecture Interview Questions & Answers (Click to Expand)</h3></summary>

## Kubernetes & EKS Cloud Architecture Interview Questions & Answers

### Q1: Why is running WordPress on Kubernetes an anti-pattern when using Persistent Volumes (EFS/NFS), but a best practice when using S3?
- **Answer:** 
  - Standard WordPress requires shared access to `/wp-content/uploads/`. If multiple pods mount an NFS/EFS persistent volume (`ReadWriteMany`), they hit severe network latency, IOPS bottlenecks, and file-locking corruption.
  - By offloading uploads to Amazon S3 (Phase 5), the pods require zero shared persistent storage. Pods become **100% stateless**, allowing Kubernetes to scale pods up and down across any availability zone instantly without storage degradation.

### Q2: What is the architectural difference between Amazon ECS and Amazon EKS?
- **Answer:**
  - **Amazon ECS:** AWS-native container orchestrator. Tightly integrated with AWS IAM, CloudWatch, and ALB out-of-the-box. Simpler control plane, zero cluster fee, but locked into the AWS ecosystem.
  - **Amazon EKS:** Managed Kubernetes. Industry-standard open-source API with no vendor lock-in. Supports rich ecosystem tooling (Helm, ArgoCD, Istio, Prometheus, KEDA). Costs $73/month for the control plane and requires higher operational expertise.

### Q3: What is IAM Roles for Service Accounts (IRSA) in EKS, and why is it preferred over node IAM roles?
- **Answer:** In traditional EC2, any pod running on a worker node inherits the node's IAM role, violating the Principle of Least Privilege (e.g. a frontend pod could access backend S3 buckets). **IRSA** uses OpenID Connect (OIDC) federation: each individual Kubernetes ServiceAccount is mapped to a specific IAM role. AWS injects temporary session credentials directly into the designated pod via a signed JWT token, guaranteeing strict pod-level least-privilege isolation.

</details>
