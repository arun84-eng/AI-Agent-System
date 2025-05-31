# AI-Agent-System
# 🤖 Multi-Format Autonomous AI System with Contextual Decisioning & Chained Actions

# 🎯 Objective

A multi-agent AI system that autonomously processes inputs across multiple formats (Email, JSON, PDF), detects business intent, classifies content, and dynamically triggers follow-up actions based on contextual understanding. All agent activities are logged in a shared memory store to enable traceability and auditability.

---

# 🧠 Core Capabilities

- Format detection (Email, JSON, PDF)
- Business intent classification (RFQ, Complaint, Invoice, Regulation, Fraud Risk)
- Routing to format-specialized agents
- Field extraction, tone/urgency detection, anomaly flagging
- Chained follow-up actions (e.g., escalate CRM, log alert)
- Shared memory store for input metadata, agent traces, and actions
- End-to-end automation from input to decision trace

---

# 🧩 Agentic Architecture

```plaintext
           +---------------------------+
           |      Input (Email /      |
           |        JSON / PDF)       |
           +------------+-------------+
                        |
                        v
         +--------------+--------------+
         |    🔍 Classifier Agent      |
         | - Detect format             |
         | - Identify business intent  |
         +--------------+--------------+
                        |
                        v
     +------------------+------------------+
     |       Format-Specific Agents        |
     | +-----------------+  +------------+ |
     | |  📧 Email Agent  |  | 📄 PDF Agent | |
     | |  - Sender, tone  |  | - Invoices, | |
     | |  - Urgency       |  |   Policies  | |
     | +-----------------+  +------------+ |
     | +----------------------------+     |
     | |  🔧 JSON Agent             |     |
     | |  - Schema validation       |     |
     | |  - Anomaly detection       |     |
     | +----------------------------+     |
     +------------------+------------------+
                        |
                        v
         +--------------+--------------+
         |  🚦 Action Router          |
         | - POST /crm, /risk_alert   |
         | - Trigger follow-up flows  |
         +--------------+--------------+
                        |
                        v
               +--------+--------+
               |  🧠 Shared Memory |
               | - Input metadata |
               | - Agent outputs  |
               | - Actions log    |
               +-----------------+
