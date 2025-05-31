import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  Mail, 
  FileText, 
  Code, 
  FileCheck,
  AlertTriangle,
  CheckCircle
} from "lucide-react";

interface ProcessedFile {
  id: number;
  originalName: string;
  fileType: string;
  businessIntent: string;
  status: string;
  priority: string;
  uploadedAt: string;
}

interface ProcessingResultsProps {
  files?: ProcessedFile[];
}

export default function ProcessingResults({ files }: ProcessingResultsProps) {
  const getFileIcon = (type: string) => {
    switch (type) {
      case 'PDF':
        return <FileText className="w-4 h-4 text-red-500" />;
      case 'Email':
        return <Mail className="w-4 h-4 text-blue-500" />;
      case 'JSON':
        return <Code className="w-4 h-4 text-green-500" />;
      default:
        return <FileCheck className="w-4 h-4 text-gray-500" />;
    }
  };

  const getFormatBadge = (type: string) => {
    const variants: Record<string, string> = {
      'Email': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      'PDF': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      'JSON': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
    };
    
    return (
      <Badge className={variants[type] || 'bg-gray-100 text-gray-800'}>
        {type}
      </Badge>
    );
  };

  const getIntentBadge = (intent: string) => {
    const variants: Record<string, string> = {
      'Complaint': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      'Invoice': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      'RFQ': 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
      'Regulation': 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
      'Fraud Risk': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    };
    
    return (
      <Badge className={variants[intent] || 'bg-gray-100 text-gray-800'}>
        {intent || 'Unknown'}
      </Badge>
    );
  };

  const getActionBadge = (priority: string, status: string) => {
    if (status === 'failed') {
      return <Badge variant="destructive">Failed</Badge>;
    }
    
    switch (priority) {
      case 'high':
        return <Badge className="bg-carbon-red text-white">Escalated</Badge>;
      case 'medium':
        return <Badge className="bg-carbon-yellow text-white">Flagged</Badge>;
      case 'low':
        return <Badge className="bg-carbon-green text-white">Processed</Badge>;
      default:
        return <Badge variant="secondary">Pending</Badge>;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-carbon-green" />;
      case 'processing':
        return <div className="processing-animation w-4 h-4 bg-carbon-yellow rounded-full"></div>;
      case 'failed':
        return <AlertTriangle className="w-4 h-4 text-carbon-red" />;
      default:
        return <div className="w-4 h-4 bg-muted rounded-full"></div>;
    }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Recent Classifications</CardTitle>
          <Button variant="ghost" size="sm">
            View All
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left p-4 text-sm font-medium text-muted-foreground">File</th>
                <th className="text-left p-4 text-sm font-medium text-muted-foreground">Format</th>
                <th className="text-left p-4 text-sm font-medium text-muted-foreground">Intent</th>
                <th className="text-left p-4 text-sm font-medium text-muted-foreground">Action</th>
                <th className="text-left p-4 text-sm font-medium text-muted-foreground">Status</th>
              </tr>
            </thead>
            <tbody>
              {files?.slice(0, 10).map((file) => (
                <tr key={file.id} className="border-b border-border hover:bg-muted/25">
                  <td className="p-4">
                    <div className="flex items-center space-x-2">
                      {getFileIcon(file.fileType)}
                      <span className="text-sm font-medium text-foreground">{file.originalName}</span>
                    </div>
                  </td>
                  <td className="p-4">
                    {getFormatBadge(file.fileType)}
                  </td>
                  <td className="p-4">
                    {getIntentBadge(file.businessIntent)}
                  </td>
                  <td className="p-4">
                    {getActionBadge(file.priority, file.status)}
                  </td>
                  <td className="p-4">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(file.status)}
                      <span className="text-sm text-muted-foreground capitalize">{file.status}</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {(!files || files.length === 0) && (
            <div className="text-center py-8">
              <FileCheck className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">No files processed yet</p>
              <p className="text-xs text-muted-foreground mt-1">Upload files to see processing results</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
