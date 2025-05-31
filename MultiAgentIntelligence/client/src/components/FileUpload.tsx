import { useState, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { 
  Upload, 
  FileText, 
  Mail, 
  Code, 
  File,
  CheckCircle,
  Clock,
  AlertCircle
} from "lucide-react";

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  status: 'uploading' | 'processing' | 'completed' | 'failed';
  progress: number;
}

export default function FileUpload() {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await apiRequest('POST', '/api/upload', formData);
      return response.json();
    },
    onSuccess: (data, file) => {
      toast({
        title: "File uploaded successfully",
        description: `${file.name} is now being processed by AI agents.`,
      });
      
      // Update file status to processing
      setUploadedFiles(prev => prev.map(f => 
        f.name === file.name ? { ...f, status: 'processing', progress: 50 } : f
      ));
      
      // Simulate processing completion after delay
      setTimeout(() => {
        setUploadedFiles(prev => prev.map(f => 
          f.name === file.name ? { ...f, status: 'completed', progress: 100 } : f
        ));
      }, 3000);
      
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['/api/files'] });
      queryClient.invalidateQueries({ queryKey: ['/api/dashboard/stats'] });
    },
    onError: (error: Error, file) => {
      toast({
        title: "Upload failed",
        description: error.message || `Failed to upload ${file.name}`,
        variant: "destructive",
      });
      
      setUploadedFiles(prev => prev.map(f => 
        f.name === file.name ? { ...f, status: 'failed', progress: 0 } : f
      ));
    },
  });

  const handleFileSelect = (files: FileList | null) => {
    if (!files) return;
    
    const allowedTypes = ['.pdf', '.eml', '.msg', '.json'];
    const validFiles: File[] = [];
    
    Array.from(files).forEach(file => {
      const extension = '.' + file.name.split('.').pop()?.toLowerCase();
      if (allowedTypes.includes(extension)) {
        validFiles.push(file);
      } else {
        toast({
          title: "Unsupported file type",
          description: `${file.name} is not supported. Please upload PDF, Email (.eml, .msg), or JSON files.`,
          variant: "destructive",
        });
      }
    });
    
    if (validFiles.length === 0) return;
    
    // Add files to upload queue
    const newFiles: UploadedFile[] = validFiles.map(file => ({
      id: Date.now() + Math.random().toString(),
      name: file.name,
      size: file.size,
      type: getFileTypeIcon(file.name),
      status: 'uploading',
      progress: 0
    }));
    
    setUploadedFiles(prev => [...newFiles, ...prev]);
    
    // Upload each file
    validFiles.forEach(file => {
      uploadMutation.mutate(file);
    });
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const getFileTypeIcon = (filename: string) => {
    const extension = filename.split('.').pop()?.toLowerCase();
    switch (extension) {
      case 'pdf':
        return 'pdf';
      case 'eml':
      case 'msg':
        return 'email';
      case 'json':
        return 'json';
      default:
        return 'file';
    }
  };

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'pdf':
        return <File className="w-5 h-5 text-red-500" />;
      case 'email':
        return <Mail className="w-5 h-5 text-blue-500" />;
      case 'json':
        return <Code className="w-5 h-5 text-green-500" />;
      default:
        return <FileText className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-carbon-green" />;
      case 'processing':
        return <Clock className="w-4 h-4 text-carbon-yellow processing-animation" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-carbon-red" />;
      default:
        return <Clock className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-carbon-green text-white">COMPLETE</Badge>;
      case 'processing':
        return <Badge className="bg-carbon-yellow text-white">PROCESSING</Badge>;
      case 'failed':
        return <Badge variant="destructive">FAILED</Badge>;
      default:
        return <Badge variant="secondary">UPLOADING</Badge>;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Input Processing</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Upload Zones */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div 
            className={`upload-zone cursor-pointer ${isDragOver ? 'dragover' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={handleClick}
          >
            <Mail className="w-8 h-8 text-primary mx-auto mb-3" />
            <h3 className="font-medium text-foreground mb-2">Email Processing</h3>
            <p className="text-sm text-muted-foreground">Upload .eml or .msg files</p>
          </div>
          
          <div 
            className={`upload-zone cursor-pointer ${isDragOver ? 'dragover' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={handleClick}
          >
            <Code className="w-8 h-8 text-primary mx-auto mb-3" />
            <h3 className="font-medium text-foreground mb-2">JSON Data</h3>
            <p className="text-sm text-muted-foreground">Upload JSON files or webhook data</p>
          </div>
          
          <div 
            className={`upload-zone cursor-pointer ${isDragOver ? 'dragover' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={handleClick}
          >
            <File className="w-8 h-8 text-primary mx-auto mb-3" />
            <h3 className="font-medium text-foreground mb-2">PDF Documents</h3>
            <p className="text-sm text-muted-foreground">Upload invoices, contracts, policies</p>
          </div>
        </div>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.eml,.msg,.json"
          onChange={(e) => handleFileSelect(e.target.files)}
          className="hidden"
        />

        {/* Processing Queue */}
        {uploadedFiles.length > 0 && (
          <div className="border-t border-border pt-4">
            <h3 className="font-medium text-foreground mb-3">Processing Queue</h3>
            <div className="space-y-3">
              {uploadedFiles.slice(0, 5).map((file) => (
                <div key={file.id} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                  <div className="flex items-center space-x-3 flex-1">
                    {getFileIcon(file.type)}
                    <div className="flex-1">
                      <p className="font-medium text-sm text-foreground">{file.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {file.status === 'uploading' && 'Uploading...'}
                        {file.status === 'processing' && 'Classifying format and intent...'}
                        {file.status === 'completed' && 'Processing completed successfully'}
                        {file.status === 'failed' && 'Processing failed'}
                      </p>
                      {(file.status === 'uploading' || file.status === 'processing') && (
                        <Progress value={file.progress} className="w-full mt-1 h-1" />
                      )}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {getStatusIcon(file.status)}
                    {getStatusBadge(file.status)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
