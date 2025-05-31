import { pgTable, text, serial, integer, boolean, timestamp, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
});

export const processedFiles = pgTable("processed_files", {
  id: serial("id").primaryKey(),
  filename: text("filename").notNull(),
  originalName: text("original_name").notNull(),
  fileType: text("file_type").notNull(), // PDF, Email, JSON
  size: integer("size").notNull(),
  uploadedAt: timestamp("uploaded_at").defaultNow().notNull(),
  processedAt: timestamp("processed_at"),
  status: text("status").notNull().default("pending"), // pending, processing, completed, failed
  classificationResult: jsonb("classification_result"),
  extractedData: jsonb("extracted_data"),
  businessIntent: text("business_intent"), // RFQ, Complaint, Invoice, Regulation, Fraud Risk
  priority: text("priority").default("low"), // low, medium, high
  agentAssigned: text("agent_assigned"),
});

export const agentActivities = pgTable("agent_activities", {
  id: serial("id").primaryKey(),
  fileId: integer("file_id").references(() => processedFiles.id),
  agentName: text("agent_name").notNull(),
  action: text("action").notNull(),
  input: jsonb("input"),
  output: jsonb("output"),
  status: text("status").notNull(), // success, failed, pending
  timestamp: timestamp("timestamp").defaultNow().notNull(),
  processingTime: integer("processing_time"), // in milliseconds
  errorMessage: text("error_message"),
});

export const triggeredActions = pgTable("triggered_actions", {
  id: serial("id").primaryKey(),
  fileId: integer("file_id").references(() => processedFiles.id),
  actionType: text("action_type").notNull(), // escalate, flag, log, alert
  description: text("description").notNull(),
  priority: text("priority").notNull(),
  status: text("status").notNull().default("pending"), // pending, completed, failed
  externalApiCall: text("external_api_call"),
  timestamp: timestamp("timestamp").defaultNow().notNull(),
  metadata: jsonb("metadata"),
});

export const systemMetrics = pgTable("system_metrics", {
  id: serial("id").primaryKey(),
  metricName: text("metric_name").notNull(),
  metricValue: text("metric_value").notNull(),
  timestamp: timestamp("timestamp").defaultNow().notNull(),
});

export const insertUserSchema = createInsertSchema(users).pick({
  username: true,
  password: true,
});

export const insertProcessedFileSchema = createInsertSchema(processedFiles).omit({
  id: true,
  uploadedAt: true,
  processedAt: true,
});

export const insertAgentActivitySchema = createInsertSchema(agentActivities).omit({
  id: true,
  timestamp: true,
});

export const insertTriggeredActionSchema = createInsertSchema(triggeredActions).omit({
  id: true,
  timestamp: true,
});

export const insertSystemMetricSchema = createInsertSchema(systemMetrics).omit({
  id: true,
  timestamp: true,
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;
export type ProcessedFile = typeof processedFiles.$inferSelect;
export type InsertProcessedFile = z.infer<typeof insertProcessedFileSchema>;
export type AgentActivity = typeof agentActivities.$inferSelect;
export type InsertAgentActivity = z.infer<typeof insertAgentActivitySchema>;
export type TriggeredAction = typeof triggeredActions.$inferSelect;
export type InsertTriggeredAction = z.infer<typeof insertTriggeredActionSchema>;
export type SystemMetric = typeof systemMetrics.$inferSelect;
export type InsertSystemMetric = z.infer<typeof insertSystemMetricSchema>;
