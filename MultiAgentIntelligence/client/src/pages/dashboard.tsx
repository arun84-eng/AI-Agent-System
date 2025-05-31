import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import FileUpload from "@/components/FileUpload";
import AgentStatus from "@/components/AgentStatus";
import ProcessingResults from "@/components/ProcessingResults";
import AuditTrail from "@/components/AuditTrail";
import { 
  Bot, 
  Clock, 
  FileText, 
  Settings, 
  CheckCircle,
  Activity,
  Brain,
  ServerCog,
  Route,
  Check
} from "lucide-react";

export default function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["/api/dashboard/stats"],
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  const { data: agents, isLoading: agentsLoading } = useQuery({
    queryKey: ["/api/agents/status"],
    refetchInterval: 3000, // Refresh every 3 seconds
  });

  const { data: recentFiles } = useQuery({
    queryKey: ["/api/files"],
    refetchInterval: 2000, // Refresh every 2 seconds
  });

  const { data: recentActions } = useQuery({
    queryKey: ["/api/actions"],
    refetchInterval: 2000,
  });

  if (statsLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="processing-animation w-8 h-8 bg-primary rounded-full mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card border-b border-border px-6 py-4">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center space-x-4">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <Bot className="w-5 h-5 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-foreground">AI Agent System</h1>
              <p className="text-sm text-muted-foreground">Multi-Format Processing</p>
            </div>
            <Badge variant="default" className="bg-carbon-green text-white">
              ONLINE
            </Badge>
          </div>
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-2 text-sm text-muted-foreground">
              <Clock className="w-4 h-4" />
              <span>Online for 2h 34m</span>
            </div>
            <div className="flex items-center space-x-2 text-sm text-muted-foreground">
              <FileText className="w-4 h-4" />
              <span>{stats?.processedToday || 0} processed today</span>
            </div>
            <Button variant="ghost" size="sm">
              <Settings className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Processing Pipeline Overview */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-foreground mb-4">Processing Pipeline</h3>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="pipeline-step active flex flex-col items-center">
                  <div className="w-12 h-12 bg-primary rounded-full flex items-center justify-center text-primary-foreground mb-2">
                    <FileText className="w-6 h-6" />
                  </div>
                  <div className="text-center">
                    <p className="font-medium text-foreground">Input Detection</p>
                    <p className="text-xs text-muted-foreground">Email, JSON, PDF</p>
                  </div>
                </div>
                
                <div className="pipeline-step active flex flex-col items-center">
                  <div className="w-12 h-12 bg-primary rounded-full flex items-center justify-center text-primary-foreground mb-2">
                    <Brain className="w-6 h-6" />
                  </div>
                  <div className="text-center">
                    <p className="font-medium text-foreground">Classification</p>
                    <p className="text-xs text-muted-foreground">Format + Intent</p>
                  </div>
                </div>
                
                <div className="pipeline-step processing-animation flex flex-col items-center">
                  <div className="w-12 h-12 bg-carbon-yellow rounded-full flex items-center justify-center text-white mb-2">
                    <ServerCog className="w-6 h-6" />
                  </div>
                  <div className="text-center">
                    <p className="font-medium text-foreground">Agent Processing</p>
                    <p className="text-xs text-muted-foreground">Specialized Extraction</p>
                  </div>
                </div>
                
                <div className="pipeline-step flex flex-col items-center">
                  <div className="w-12 h-12 bg-muted rounded-full flex items-center justify-center text-muted-foreground mb-2">
                    <Route className="w-6 h-6" />
                  </div>
                  <div className="text-center">
                    <p className="font-medium text-muted-foreground">Action Router</p>
                    <p className="text-xs text-muted-foreground">Follow-up Actions</p>
                  </div>
                </div>
                
                <div className="pipeline-step flex flex-col items-center">
                  <div className="w-12 h-12 bg-muted rounded-full flex items-center justify-center text-muted-foreground mb-2">
                    <Check className="w-6 h-6" />
                  </div>
                  <div className="text-center">
                    <p className="font-medium text-muted-foreground">Complete</p>
                    <p className="text-xs text-muted-foreground">Audit & Store</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Processed Today</p>
                  <p className="text-2xl font-bold text-foreground">{stats?.processedToday || 0}</p>
                </div>
                <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                  <FileText className="w-6 h-6 text-primary" />
                </div>
              </div>
              <div className="mt-4 flex items-center text-sm">
                <span className="text-carbon-green font-medium">↗ 12%</span>
                <span className="text-muted-foreground ml-2">vs yesterday</span>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Active Agents</p>
                  <p className="text-2xl font-bold text-foreground">{stats?.activeAgents || 4}</p>
                </div>
                <div className="w-12 h-12 bg-carbon-green/10 rounded-lg flex items-center justify-center">
                  <Bot className="w-6 h-6 text-carbon-green" />
                </div>
              </div>
              <div className="mt-4 flex items-center text-sm">
                <span className="text-carbon-green font-medium">Online</span>
                <span className="text-muted-foreground ml-2">All operational</span>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Success Rate</p>
                  <p className="text-2xl font-bold text-foreground">{stats?.successRate?.toFixed(1) || 98.2}%</p>
                </div>
                <div className="w-12 h-12 bg-carbon-green/10 rounded-lg flex items-center justify-center">
                  <CheckCircle className="w-6 h-6 text-carbon-green" />
                </div>
              </div>
              <div className="mt-4 flex items-center text-sm">
                <span className="text-carbon-green font-medium">↗ 0.8%</span>
                <span className="text-muted-foreground ml-2">this week</span>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Avg. Process Time</p>
                  <p className="text-2xl font-bold text-foreground">{(stats?.averageProcessingTime / 1000)?.toFixed(1) || 2.4}s</p>
                </div>
                <div className="w-12 h-12 bg-carbon-yellow/10 rounded-lg flex items-center justify-center">
                  <Clock className="w-6 h-6 text-carbon-yellow" />
                </div>
              </div>
              <div className="mt-4 flex items-center text-sm">
                <span className="text-carbon-green font-medium">↘ 0.3s</span>
                <span className="text-muted-foreground ml-2">faster</span>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* File Upload + Agent Status */}
          <div className="lg:col-span-2 space-y-6">
            <FileUpload />
            <ProcessingResults files={recentFiles} />
          </div>
          
          {/* Agent Status + Memory/Actions */}
          <div className="space-y-6">
            <AgentStatus agents={agents} isLoading={agentsLoading} />
            
            {/* Memory Store */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Shared Memory</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Total Records</span>
                  <span className="font-semibold text-foreground">1,247</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Memory Usage</span>
                  <span className="font-semibold text-foreground">64.2 MB</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Cache Hit Rate</span>
                  <span className="font-semibold text-foreground">94.1%</span>
                </div>
                <Progress value={64.2} className="w-full" />
              </CardContent>
            </Card>
            
            {/* Recent Actions */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Recent Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {recentActions?.slice(0, 3).map((action: any, index: number) => (
                  <div key={index} className="flex items-start space-x-3 p-3 bg-muted/50 rounded-lg">
                    <div className="flex-shrink-0 mt-1">
                      <div className={`w-2 h-2 rounded-full ${
                        action.priority === 'high' ? 'bg-carbon-red' : 
                        action.priority === 'medium' ? 'bg-carbon-yellow' : 'bg-carbon-green'
                      }`}></div>
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium text-sm text-foreground">{action.actionType}</h4>
                        <span className="text-xs text-muted-foreground">
                          {new Date(action.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">{action.description}</p>
                      <div className="flex items-center space-x-2 mt-2">
                        <Badge variant={action.priority === 'high' ? 'destructive' : action.priority === 'medium' ? 'default' : 'secondary'}>
                          {action.priority.toUpperCase()}
                        </Badge>
                      </div>
                    </div>
                  </div>
                ))}
                {(!recentActions || recentActions.length === 0) && (
                  <div className="text-center py-4">
                    <Activity className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                    <p className="text-sm text-muted-foreground">No recent actions</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Audit Trail */}
        <div className="mt-6">
          <AuditTrail />
        </div>
      </div>
    </div>
  );
}
