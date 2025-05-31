import { 
  users, 
  processedFiles, 
  agentActivities, 
  triggeredActions, 
  systemMetrics,
  type User, 
  type InsertUser,
  type ProcessedFile,
  type InsertProcessedFile,
  type AgentActivity,
  type InsertAgentActivity,
  type TriggeredAction,
  type InsertTriggeredAction,
  type SystemMetric,
  type InsertSystemMetric
} from "@shared/schema";

export interface IStorage {
  getUser(id: number): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  
  // Processed Files
  createProcessedFile(file: InsertProcessedFile): Promise<ProcessedFile>;
  updateProcessedFile(id: number, updates: Partial<ProcessedFile>): Promise<ProcessedFile>;
  getProcessedFile(id: number): Promise<ProcessedFile | undefined>;
  getProcessedFiles(limit?: number): Promise<ProcessedFile[]>;
  getProcessedFilesByStatus(status: string): Promise<ProcessedFile[]>;
  
  // Agent Activities
  createAgentActivity(activity: InsertAgentActivity): Promise<AgentActivity>;
  getAgentActivities(fileId?: number, limit?: number): Promise<AgentActivity[]>;
  getAgentActivitiesByAgent(agentName: string): Promise<AgentActivity[]>;
  
  // Triggered Actions
  createTriggeredAction(action: InsertTriggeredAction): Promise<TriggeredAction>;
  getTriggeredActions(limit?: number): Promise<TriggeredAction[]>;
  updateTriggeredAction(id: number, updates: Partial<TriggeredAction>): Promise<TriggeredAction>;
  
  // System Metrics
  createSystemMetric(metric: InsertSystemMetric): Promise<SystemMetric>;
  getSystemMetrics(metricName?: string, limit?: number): Promise<SystemMetric[]>;
  getLatestMetric(metricName: string): Promise<SystemMetric | undefined>;
  
  // Dashboard Stats
  getDashboardStats(): Promise<{
    processedToday: number;
    totalProcessed: number;
    successRate: number;
    averageProcessingTime: number;
    activeAgents: number;
  }>;
}

export class MemStorage implements IStorage {
  private users: Map<number, User>;
  private processedFiles: Map<number, ProcessedFile>;
  private agentActivities: Map<number, AgentActivity>;
  private triggeredActions: Map<number, TriggeredAction>;
  private systemMetrics: Map<number, SystemMetric>;
  private currentId: number;

  constructor() {
    this.users = new Map();
    this.processedFiles = new Map();
    this.agentActivities = new Map();
    this.triggeredActions = new Map();
    this.systemMetrics = new Map();
    this.currentId = 1;
  }

  async getUser(id: number): Promise<User | undefined> {
    return this.users.get(id);
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(
      (user) => user.username === username,
    );
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const id = this.currentId++;
    const user: User = { ...insertUser, id };
    this.users.set(id, user);
    return user;
  }

  async createProcessedFile(file: InsertProcessedFile): Promise<ProcessedFile> {
    const id = this.currentId++;
    const processedFile: ProcessedFile = {
      ...file,
      id,
      uploadedAt: new Date(),
      processedAt: null,
    };
    this.processedFiles.set(id, processedFile);
    return processedFile;
  }

  async updateProcessedFile(id: number, updates: Partial<ProcessedFile>): Promise<ProcessedFile> {
    const existing = this.processedFiles.get(id);
    if (!existing) {
      throw new Error(`ProcessedFile with id ${id} not found`);
    }
    const updated = { ...existing, ...updates };
    this.processedFiles.set(id, updated);
    return updated;
  }

  async getProcessedFile(id: number): Promise<ProcessedFile | undefined> {
    return this.processedFiles.get(id);
  }

  async getProcessedFiles(limit = 50): Promise<ProcessedFile[]> {
    return Array.from(this.processedFiles.values())
      .sort((a, b) => new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime())
      .slice(0, limit);
  }

  async getProcessedFilesByStatus(status: string): Promise<ProcessedFile[]> {
    return Array.from(this.processedFiles.values()).filter(f => f.status === status);
  }

  async createAgentActivity(activity: InsertAgentActivity): Promise<AgentActivity> {
    const id = this.currentId++;
    const agentActivity: AgentActivity = {
      ...activity,
      id,
      timestamp: new Date(),
    };
    this.agentActivities.set(id, agentActivity);
    return agentActivity;
  }

  async getAgentActivities(fileId?: number, limit = 50): Promise<AgentActivity[]> {
    let activities = Array.from(this.agentActivities.values());
    if (fileId) {
      activities = activities.filter(a => a.fileId === fileId);
    }
    return activities
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, limit);
  }

  async getAgentActivitiesByAgent(agentName: string): Promise<AgentActivity[]> {
    return Array.from(this.agentActivities.values()).filter(a => a.agentName === agentName);
  }

  async createTriggeredAction(action: InsertTriggeredAction): Promise<TriggeredAction> {
    const id = this.currentId++;
    const triggeredAction: TriggeredAction = {
      ...action,
      id,
      timestamp: new Date(),
    };
    this.triggeredActions.set(id, triggeredAction);
    return triggeredAction;
  }

  async getTriggeredActions(limit = 50): Promise<TriggeredAction[]> {
    return Array.from(this.triggeredActions.values())
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, limit);
  }

  async updateTriggeredAction(id: number, updates: Partial<TriggeredAction>): Promise<TriggeredAction> {
    const existing = this.triggeredActions.get(id);
    if (!existing) {
      throw new Error(`TriggeredAction with id ${id} not found`);
    }
    const updated = { ...existing, ...updates };
    this.triggeredActions.set(id, updated);
    return updated;
  }

  async createSystemMetric(metric: InsertSystemMetric): Promise<SystemMetric> {
    const id = this.currentId++;
    const systemMetric: SystemMetric = {
      ...metric,
      id,
      timestamp: new Date(),
    };
    this.systemMetrics.set(id, systemMetric);
    return systemMetric;
  }

  async getSystemMetrics(metricName?: string, limit = 50): Promise<SystemMetric[]> {
    let metrics = Array.from(this.systemMetrics.values());
    if (metricName) {
      metrics = metrics.filter(m => m.metricName === metricName);
    }
    return metrics
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, limit);
  }

  async getLatestMetric(metricName: string): Promise<SystemMetric | undefined> {
    const metrics = await this.getSystemMetrics(metricName, 1);
    return metrics[0];
  }

  async getDashboardStats(): Promise<{
    processedToday: number;
    totalProcessed: number;
    successRate: number;
    averageProcessingTime: number;
    activeAgents: number;
  }> {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const allFiles = Array.from(this.processedFiles.values());
    const todayFiles = allFiles.filter(f => new Date(f.uploadedAt) >= today);
    const completedFiles = allFiles.filter(f => f.status === 'completed');
    
    const activities = Array.from(this.agentActivities.values());
    const avgProcessingTime = activities.length > 0 
      ? activities.reduce((sum, a) => sum + (a.processingTime || 0), 0) / activities.length
      : 0;

    const uniqueAgents = new Set(activities.map(a => a.agentName)).size;

    return {
      processedToday: todayFiles.length,
      totalProcessed: allFiles.length,
      successRate: allFiles.length > 0 ? (completedFiles.length / allFiles.length) * 100 : 0,
      averageProcessingTime: avgProcessingTime,
      activeAgents: uniqueAgents || 4, // Default to 4 agents
    };
  }
}

export const storage = new MemStorage();
