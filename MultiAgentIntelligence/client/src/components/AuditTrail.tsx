import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  Download, 
  Filter,
  ChevronLeft,
  ChevronRight,
  Database,
  Activity
} from "lucide-react";

export default function AuditTrail() {
  const { data: activities, isLoading } = useQuery({
    queryKey: ["/api/activities"],
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  const getAgentBadge = (agentName: string) => {
    const variants: Record<string, string> = {
      'Classifier Agent': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      'Email Agent': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      'JSON Agent': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      'PDF Agent': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      'Action Router': 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
    };
    
    return (
      <Badge className={variants[agentName] || 'bg-gray-100 text-gray-800'}>
        {agentName}
      </Badge>
    );
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'success':
        return <Badge className="bg-carbon-green text-white">Success</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      case 'pending':
        return <Badge className="bg-carbon-yellow text-white">Pending</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const formatOutput = (output: any) => {
    if (!output) return 'N/A';
    if (typeof output === 'string') return output;
    if (typeof output === 'object') {
      // Show key highlights from the output
      if (output.business_intent) return `${output.format || 'Unknown'}, ${output.business_intent}`;
      if (output.sender) return `Sender: ${output.sender}`;
      if (output.record_count) return `Records: ${output.record_count}`;
      if (output.page_count) return `Pages: ${output.page_count}`;
      return JSON.stringify(output).substring(0, 50) + '...';
    }
    return String(output);
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Shared Memory & Audit Trail</CardTitle>
          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm">
              <Download className="w-4 h-4 mr-1" />
              Export
            </Button>
            <Button variant="outline" size="sm">
              <Filter className="w-4 h-4 mr-1" />
              Filter
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-6 text-center">
            <div className="processing-animation w-8 h-8 bg-primary rounded-full mx-auto mb-4"></div>
            <p className="text-sm text-muted-foreground">Loading audit trail...</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/50">
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">Timestamp</th>
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">Agent</th>
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">Action</th>
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">Input</th>
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">Output</th>
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {activities?.map((activity: any) => (
                    <tr key={activity.id} className="border-b border-border hover:bg-muted/25">
                      <td className="py-3 px-4 text-muted-foreground">
                        {formatTimestamp(activity.timestamp)}
                      </td>
                      <td className="py-3 px-4">
                        {getAgentBadge(activity.agentName)}
                      </td>
                      <td className="py-3 px-4 font-medium text-foreground">
                        {activity.action}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {activity.input?.file_path ? 'File uploaded' : 
                         activity.input?.fileType || 
                         (typeof activity.input === 'string' ? activity.input : 'Processing data')}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {formatOutput(activity.output)}
                      </td>
                      <td className="py-3 px-4">
                        {getStatusBadge(activity.status)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              
              {(!activities || activities.length === 0) && (
                <div className="text-center py-8">
                  <Database className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">No audit trail data available</p>
                  <p className="text-xs text-muted-foreground mt-1">Activity logs will appear here as files are processed</p>
                </div>
              )}
            </div>
            
            {activities && activities.length > 0 && (
              <div className="flex items-center justify-between p-6 border-t border-border bg-muted/25">
                <p className="text-sm text-muted-foreground">
                  Showing {Math.min(activities.length, 50)} of {activities.length} entries
                </p>
                <div className="flex items-center space-x-2">
                  <Button variant="outline" size="sm" disabled>
                    <ChevronLeft className="w-4 h-4 mr-1" />
                    Previous
                  </Button>
                  <span className="text-sm text-muted-foreground">1 of 1</span>
                  <Button variant="outline" size="sm" disabled>
                    Next
                    <ChevronRight className="w-4 h-4 ml-1" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
