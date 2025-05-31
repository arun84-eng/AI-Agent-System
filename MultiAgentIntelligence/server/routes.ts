import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { insertProcessedFileSchema, insertAgentActivitySchema, insertTriggeredActionSchema } from "@shared/schema";
import multer from "multer";
import path from "path";
import { spawn } from "child_process";
import fs from "fs";

const upload = multer({ dest: 'uploads/' });

export async function registerRoutes(app: Express): Promise<Server> {
  
  // File upload endpoint
  app.post("/api/upload", upload.single('file'), async (req, res) => {
    try {
      if (!req.file) {
        return res.status(400).json({ error: "No file uploaded" });
      }

      const fileExtension = path.extname(req.file.originalname).toLowerCase();
      let fileType = 'unknown';
      
      if (['.pdf'].includes(fileExtension)) {
        fileType = 'PDF';
      } else if (['.eml', '.msg'].includes(fileExtension)) {
        fileType = 'Email';
      } else if (['.json'].includes(fileExtension)) {
        fileType = 'JSON';
      } else {
        return res.status(400).json({ error: "Unsupported file type. Please upload PDF, Email (.eml, .msg), or JSON files." });
      }

      const processedFile = await storage.createProcessedFile({
        filename: req.file.filename,
        originalName: req.file.originalname,
        fileType,
        size: req.file.size,
        status: "pending",
        classificationResult: null,
        extractedData: null,
        businessIntent: null,
        priority: "low",
        agentAssigned: null,
      });

      // Trigger AI processing
      processFileWithAI(processedFile.id, req.file.path, fileType);

      res.json({ 
        success: true, 
        fileId: processedFile.id,
        message: "File uploaded successfully and processing started" 
      });
    } catch (error) {
      console.error("Upload error:", error);
      res.status(500).json({ error: "Failed to upload file" });
    }
  });

  // Get processed files
  app.get("/api/files", async (req, res) => {
    try {
      const files = await storage.getProcessedFiles(50);
      res.json(files);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch files" });
    }
  });

  // Get specific file details
  app.get("/api/files/:id", async (req, res) => {
    try {
      const file = await storage.getProcessedFile(parseInt(req.params.id));
      if (!file) {
        return res.status(404).json({ error: "File not found" });
      }
      res.json(file);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch file" });
    }
  });

  // Get agent activities
  app.get("/api/activities", async (req, res) => {
    try {
      const fileId = req.query.fileId ? parseInt(req.query.fileId as string) : undefined;
      const activities = await storage.getAgentActivities(fileId, 100);
      res.json(activities);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch activities" });
    }
  });

  // Get triggered actions
  app.get("/api/actions", async (req, res) => {
    try {
      const actions = await storage.getTriggeredActions(50);
      res.json(actions);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch actions" });
    }
  });

  // Get dashboard stats
  app.get("/api/dashboard/stats", async (req, res) => {
    try {
      const stats = await storage.getDashboardStats();
      res.json(stats);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch dashboard stats" });
    }
  });

  // Get agent status
  app.get("/api/agents/status", async (req, res) => {
    try {
      const agents = [
        {
          name: "Classifier Agent",
          type: "classifier",
          status: "active",
          processedCount: await storage.getAgentActivitiesByAgent("Classifier Agent").then(a => a.length),
          accuracy: 97.8
        },
        {
          name: "Email Agent", 
          type: "email",
          status: "active",
          processedCount: await storage.getAgentActivitiesByAgent("Email Agent").then(a => a.length),
          queueSize: await storage.getProcessedFilesByStatus("processing").then(f => f.filter(file => file.fileType === "Email").length),
          escalatedToday: await storage.getTriggeredActions().then(a => a.filter(action => action.actionType === "escalate" && new Date(action.timestamp).toDateString() === new Date().toDateString()).length)
        },
        {
          name: "JSON Agent",
          type: "json", 
          status: "active",
          processedCount: await storage.getAgentActivitiesByAgent("JSON Agent").then(a => a.length),
          validatedCount: await storage.getProcessedFiles().then(f => f.filter(file => file.fileType === "JSON" && file.status === "completed").length),
          anomaliesCount: await storage.getTriggeredActions().then(a => a.filter(action => action.actionType === "flag" && action.description.includes("anomaly")).length)
        },
        {
          name: "PDF Agent",
          type: "pdf",
          status: "active", 
          processedCount: await storage.getAgentActivitiesByAgent("PDF Agent").then(a => a.length),
          parsedCount: await storage.getProcessedFiles().then(f => f.filter(file => file.fileType === "PDF" && file.status === "completed").length),
          flaggedCount: await storage.getTriggeredActions().then(a => a.filter(action => action.actionType === "flag" && action.description.includes("high")).length)
        }
      ];
      
      res.json(agents);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch agent status" });
    }
  });

  // Simulate external API calls for CRM/Risk alerts
  app.post("/api/external/crm/escalate", async (req, res) => {
    console.log("CRM Escalation triggered:", req.body);
    res.json({ success: true, ticketId: `CRM-${Date.now()}` });
  });

  app.post("/api/external/risk/alert", async (req, res) => {
    console.log("Risk Alert triggered:", req.body);
    res.json({ success: true, alertId: `RISK-${Date.now()}` });
  });

  const httpServer = createServer(app);
  return httpServer;
}

async function processFileWithAI(fileId: number, filePath: string, fileType: string) {
  try {
    // Update status to processing
    await storage.updateProcessedFile(fileId, { 
      status: "processing",
      processedAt: new Date()
    });

    // Log start of processing
    await storage.createAgentActivity({
      fileId,
      agentName: "Classifier Agent",
      action: "Start Processing",
      input: { fileType, filePath },
      output: null,
      status: "pending",
      processingTime: null,
      errorMessage: null
    });

    // Call Python AI system
    const pythonProcess = spawn('python3', ['server/ai_system.py', fileId.toString(), filePath, fileType]);
    
    pythonProcess.stdout.on('data', (data) => {
      console.log(`AI System Output: ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
      console.error(`AI System Error: ${data}`);
    });

    pythonProcess.on('close', async (code) => {
      if (code === 0) {
        console.log(`File ${fileId} processed successfully`);
      } else {
        console.error(`File ${fileId} processing failed with code ${code}`);
        await storage.updateProcessedFile(fileId, { status: "failed" });
      }
    });

  } catch (error) {
    console.error("Processing error:", error);
    await storage.updateProcessedFile(fileId, { status: "failed" });
  }
}
