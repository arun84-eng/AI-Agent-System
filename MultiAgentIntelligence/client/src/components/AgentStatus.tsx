import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { 
  Brain, 
  Mail, 
  Code, 
  FileText,
  Activity
} from "lucide-react";

interface Agent {
  name: string;
  type: string;
  status: string;
  processedCount: number;
  accuracy?: number;
  queueSize?: number;
  escalatedToday?: number;
  validatedCount?: number;
  anomaliesCount?: number;
  parsedCount?: number;
  flaggedCount?: number;
}

interface AgentStatusProps {
  agents?: Agent[];
  isLoading: boolean;
}

export default function AgentStatus({ agents, isLoading }: AgentStatusProps) {
  const getAgentIcon = (type: string) => {
    switch (type) {
      case 'classifier':
        return <Brain className="w-5 h-5 text-white" />;
      case 'email':
        return <Mail className="w-5 h-5 text-white" />;
      case 'json':
        return <Code className="w-5 h-5 text-white" />;
      case 'pdf':
        return <FileText className="w-5 h-5 text-white" />;
      default:
        return <Activity className="w-5 h-5 text-white" />;
    }
  };

  const getAgentIconBg = (type: string) => {
    switch (type) {
      case 'classifier':
        return 'bg-primary';
      case 'email':
        return 'bg-blue-500';
      case 'json':
        return 'bg-green-500';
      case 'pdf':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge className="bg-carbon-green text-white">Active</Badge>;
      case 'processing':
        return <Badge className="bg-carbon-yellow text-white">Processing</Badge>;
      case 'idle':
        return <Badge variant="secondary">Idle</Badge>;
      default:
        return <Badge variant="outline">Unknown</Badge>;
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Agent Status</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-muted/50 rounded">
              <div className="flex items-center space-x-3">
                <Skeleton className="w-10 h-10 rounded-lg" />
                <div>
                  <Skeleton className="h-4 w-24 mb-1" />
                  <Skeleton className="h-3 w-32" />
                </div>
              </div>
              <Skeleton className="h-6 w-16" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Agent Status</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {agents?.map((agent) => (
          <div key={agent.name} className="agent-card rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-3">
                <div className={`w-10 h-10 ${getAgentIconBg(agent.type)} rounded-lg flex items-center justify-center`}>
                  {getAgentIcon(agent.type)}
                </div>
                <div>
                  <h4 className="font-semibold text-foreground">{agent.name}</h4>
                  <p className="text-sm text-muted-foreground">
                    {agent.type === 'classifier' && 'Format & Intent Detection'}
                    {agent.type === 'email' && 'Email Processing & Tone Analysis'}
                    {agent.type === 'json' && 'Webhook & Schema Validation'}
                    {agent.type === 'pdf' && 'Document Parsing & Compliance'}
                  </p>
                </div>
              </div>
              {getStatusBadge(agent.status)}
            </div>
            
            <div className="grid grid-cols-2 gap-4 text-sm">
              {agent.type === 'classifier' && (
                <>
                  <div>
                    <p className="text-muted-foreground">Processed</p>
                    <p className="font-semibold text-foreground">{agent.processedCount} files</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Accuracy</p>
                    <p className="font-semibold text-foreground">{agent.accuracy}%</p>
                  </div>
                </>
              )}
              
              {agent.type === 'email' && (
                <>
                  <div>
                    <p className="text-muted-foreground">Queue</p>
                    <p className="font-semibold text-foreground">{agent.queueSize || 0} emails</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Escalated</p>
                    <p className="font-semibold text-foreground">{agent.escalatedToday || 0} today</p>
                  </div>
                </>
              )}
              
              {agent.type === 'json' && (
                <>
                  <div>
                    <p className="text-muted-foreground">Validated</p>
                    <p className="font-semibold text-foreground">{agent.validatedCount || 0} requests</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Anomalies</p>
                    <p className="font-semibold text-foreground">{agent.anomaliesCount || 0} flagged</p>
                  </div>
                </>
              )}
              
              {agent.type === 'pdf' && (
                <>
                  <div>
                    <p className="text-muted-foreground">Parsed</p>
                    <p className="font-semibold text-foreground">{agent.parsedCount || 0} documents</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Flagged</p>
                    <p className="font-semibold text-foreground">{agent.flaggedCount || 0} high-value</p>
                  </div>
                </>
              )}
            </div>
          </div>
        ))}
        
        {(!agents || agents.length === 0) && (
          <div className="text-center py-6">
            <Activity className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">No agent data available</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
