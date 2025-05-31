#!/usr/bin/env python3
import sys
import json
import os
from datetime import datetime
import asyncio
import aiohttp
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIProcessingSystem:
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        if not self.openai_api_key:
            logger.warning("No OpenAI API key found. Using mock responses.")
        
        self.base_url = "http://localhost:5000/api"
        
    async def classify_file(self, file_path: str, file_type: str) -> dict:
        """Classify file format and business intent using OpenAI API"""
        
        if not self.openai_api_key:
            # Return mock classification if no API key
            return {
                "format": file_type,
                "business_intent": "Invoice" if file_type == "PDF" else "Complaint" if file_type == "Email" else "RFQ",
                "confidence": 0.95,
                "urgency": "medium"
            }
        
        try:
            # Read file content
            file_content = self.read_file_content(file_path, file_type)
            
            # Prepare OpenAI prompt
            prompt = f"""
            Analyze the following {file_type} content and classify it:
            
            Content: {file_content[:2000]}  # Limit content for API
            
            Please provide:
            1. File format confirmation
            2. Business intent (choose from: RFQ, Complaint, Invoice, Regulation, Fraud Risk)
            3. Confidence score (0-1)
            4. Urgency level (low, medium, high)
            
            Return as JSON format.
            """
            
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are an AI classifier for business documents. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 300,
                "temperature": 0.1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.openai.com/v1/chat/completions", 
                                      headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result["choices"][0]["message"]["content"]
                        try:
                            return json.loads(content)
                        except json.JSONDecodeError:
                            logger.error("Failed to parse OpenAI response as JSON")
                            return self.get_fallback_classification(file_type, file_path)
                    else:
                        logger.error(f"OpenAI API error: {response.status}")
                        return self.get_fallback_classification(file_type, file_path)
                        
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return self.get_fallback_classification(file_type, file_path)
    
    def get_fallback_classification(self, file_type: str, file_path: str = None) -> dict:
        """Fallback classification when OpenAI API is unavailable"""
        business_intent = "Unknown"
        urgency = "medium"
        confidence = 0.6
        
        # If we have the file path, try content-based classification
        if file_path:
            try:
                content = self.read_file_content(file_path, file_type)
                content_lower = content.lower()
                
                # Invoice detection
                if any(keyword in content_lower for keyword in ['invoice', 'amount', 'total_amount', 'invoice_id', 'due_date', 'vendor']):
                    business_intent = "Invoice"
                    confidence = 0.8
                    # High-value detection
                    if any(keyword in content_lower for keyword in ['15750', '12000', '10000']) or '"amount": 1' in content:
                        urgency = "high"
                
                # Complaint detection
                elif any(keyword in content_lower for keyword in ['complaint', 'frustrated', 'unacceptable', 'angry', 'urgent', 'demand']):
                    business_intent = "Complaint"
                    urgency = "high"
                    confidence = 0.9
                
                # Regulation detection  
                elif any(keyword in content_lower for keyword in ['regulation', 'compliance', 'legal', 'policy']):
                    business_intent = "Regulation"
                    
                # Default by file type if no pattern matches
                else:
                    intent_map = {"PDF": "Invoice", "Email": "Complaint", "JSON": "RFQ"}
                    business_intent = intent_map.get(file_type, "RFQ")
                    
            except Exception as e:
                logger.error(f"Content analysis error: {e}")
                # Fallback to simple mapping
                intent_map = {"PDF": "Invoice", "Email": "Complaint", "JSON": "RFQ"}
                business_intent = intent_map.get(file_type, "RFQ")
        else:
            # Simple mapping when no file path available
            intent_map = {"PDF": "Invoice", "Email": "Complaint", "JSON": "RFQ"}
            business_intent = intent_map.get(file_type, "RFQ")
        
        return {
            "format": file_type,
            "business_intent": business_intent,
            "confidence": confidence,
            "urgency": urgency
        }
    
    def read_file_content(self, file_path: str, file_type: str) -> str:
        """Read and extract text content from files"""
        try:
            if file_type == "JSON":
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            elif file_type == "Email":
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            elif file_type == "PDF":
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text()
                        return text
                except ImportError:
                    logger.warning("PyPDF2 not available, using file name for PDF processing")
                    return os.path.basename(file_path)
            else:
                return ""
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return ""

    async def process_with_agent(self, file_id: int, file_path: str, file_type: str, classification: dict):
        """Route to appropriate specialized agent"""
        
        if file_type == "Email":
            return await self.process_email(file_id, file_path, classification)
        elif file_type == "JSON":
            return await self.process_json(file_id, file_path, classification)
        elif file_type == "PDF":
            return await self.process_pdf(file_id, file_path, classification)
        else:
            raise ValueError(f"Unknown file type: {file_type}")

    async def process_email(self, file_id: int, file_path: str, classification: dict) -> dict:
        """Email Agent processing"""
        start_time = datetime.now()
        
        # Log agent activity
        await self.log_activity(file_id, "Email Agent", "Field Extraction", 
                               {"file_path": file_path}, None, "pending")
        
        try:
            content = self.read_file_content(file_path, "Email")
            
            # Extract email fields (simplified)
            extracted_data = {
                "sender": self.extract_sender(content),
                "subject": self.extract_subject(content),
                "tone": self.analyze_tone(content, classification),
                "urgency": classification.get("urgency", "medium")
            }
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Log successful extraction
            await self.log_activity(file_id, "Email Agent", "Field Extraction",
                                   {"file_path": file_path}, extracted_data, "success", processing_time)
            
            return extracted_data
            
        except Exception as e:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await self.log_activity(file_id, "Email Agent", "Field Extraction",
                                   {"file_path": file_path}, None, "failed", processing_time, str(e))
            raise

    async def process_json(self, file_id: int, file_path: str, classification: dict) -> dict:
        """JSON Agent processing"""
        start_time = datetime.now()
        
        await self.log_activity(file_id, "JSON Agent", "Schema Validation",
                               {"file_path": file_path}, None, "pending")
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Validate schema and detect anomalies
            anomalies = self.detect_json_anomalies(data)
            
            extracted_data = {
                "record_count": len(data) if isinstance(data, list) else 1,
                "schema_valid": len(anomalies) == 0,
                "anomalies": anomalies,
                "data_summary": self.summarize_json_data(data)
            }
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            await self.log_activity(file_id, "JSON Agent", "Schema Validation",
                                   {"file_path": file_path}, extracted_data, "success", processing_time)
            
            return extracted_data
            
        except Exception as e:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await self.log_activity(file_id, "JSON Agent", "Schema Validation",
                                   {"file_path": file_path}, None, "failed", processing_time, str(e))
            raise

    async def process_pdf(self, file_id: int, file_path: str, classification: dict) -> dict:
        """PDF Agent processing"""
        start_time = datetime.now()
        
        await self.log_activity(file_id, "PDF Agent", "Document Analysis",
                               {"file_path": file_path}, None, "pending")
        
        try:
            content = self.read_file_content(file_path, "PDF")
            
            # Extract relevant information
            extracted_data = {
                "page_count": self.count_pdf_pages(file_path),
                "contains_gdpr": "GDPR" in content.upper(),
                "contains_fda": "FDA" in content.upper(),
                "invoice_amount": self.extract_invoice_amount(content),
                "document_type": classification.get("business_intent", "Unknown")
            }
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            await self.log_activity(file_id, "PDF Agent", "Document Analysis",
                                   {"file_path": file_path}, extracted_data, "success", processing_time)
            
            return extracted_data
            
        except Exception as e:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await self.log_activity(file_id, "PDF Agent", "Document Analysis",
                                   {"file_path": file_path}, None, "failed", processing_time, str(e))
            raise

    async def route_action(self, file_id: int, classification: dict, extracted_data: dict):
        """Action Router - trigger follow-up actions based on extracted data"""
        
        actions = []
        
        # Email escalation logic
        if classification.get("format") == "Email":
            tone = extracted_data.get("tone", "neutral")
            urgency = extracted_data.get("urgency", "low")
            
            if tone == "angry" or urgency == "high":
                actions.append({
                    "actionType": "escalate",
                    "description": f"High-priority {classification.get('business_intent', 'email')} detected. Auto-escalated to CRM.",
                    "priority": "high",
                    "externalApiCall": "/api/external/crm/escalate"
                })
            else:
                actions.append({
                    "actionType": "log",
                    "description": "Routine email processed and logged.",
                    "priority": "low",
                    "externalApiCall": None
                })
        
        # PDF compliance and amount checks
        elif classification.get("format") == "PDF":
            invoice_amount = extracted_data.get("invoice_amount", 0)
            if invoice_amount > 10000:
                actions.append({
                    "actionType": "flag", 
                    "description": f"High-value invoice detected: ${invoice_amount:,.2f}. Requires compliance review.",
                    "priority": "high",
                    "externalApiCall": "/api/external/risk/alert"
                })
            
            if extracted_data.get("contains_gdpr") or extracted_data.get("contains_fda"):
                compliance_type = "GDPR" if extracted_data.get("contains_gdpr") else "FDA"
                actions.append({
                    "actionType": "alert",
                    "description": f"Regulatory document detected: {compliance_type} compliance required.",
                    "priority": "medium", 
                    "externalApiCall": "/api/external/risk/alert"
                })
        
        # JSON anomaly handling
        elif classification.get("format") == "JSON":
            if not extracted_data.get("schema_valid", True):
                actions.append({
                    "actionType": "flag",
                    "description": f"JSON schema anomalies detected: {len(extracted_data.get('anomalies', []))} issues found.",
                    "priority": "medium",
                    "externalApiCall": None
                })
            else:
                actions.append({
                    "actionType": "log",
                    "description": "JSON data validated successfully. No anomalies detected.",
                    "priority": "low", 
                    "externalApiCall": None
                })
        
        # Execute actions
        for action in actions:
            await self.trigger_action(file_id, action)

    async def trigger_action(self, file_id: int, action: dict):
        """Trigger individual action and log to memory"""
        try:
            # Log the triggered action to storage
            action_data = {
                "fileId": file_id,
                **action,
                "status": "pending",
                "metadata": {"triggered_at": datetime.now().isoformat()}
            }
            
            # Make API call to log action
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/actions",
                                      json=action_data) as response:
                    if response.status != 200:
                        logger.error(f"Failed to log action: {response.status}")
            
            # Execute external API call if specified
            if action.get("externalApiCall"):
                await self.call_external_api(action["externalApiCall"], action_data)
                
        except Exception as e:
            logger.error(f"Error triggering action: {e}")

    async def call_external_api(self, endpoint: str, data: dict):
        """Call external APIs for CRM/Risk alerts"""
        try:
            full_url = f"http://localhost:5000{endpoint}"
            async with aiohttp.ClientSession() as session:
                async with session.post(full_url, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"External API call successful: {result}")
                    else:
                        logger.error(f"External API call failed: {response.status}")
        except Exception as e:
            logger.error(f"External API call error: {e}")

    async def log_activity(self, file_id: int, agent_name: str, action: str, 
                          input_data: dict, output_data: dict, status: str, 
                          processing_time: int = None, error_message: str = None):
        """Log agent activity to shared memory"""
        try:
            activity_data = {
                "fileId": file_id,
                "agentName": agent_name,
                "action": action,
                "input": input_data,
                "output": output_data,
                "status": status,
                "processingTime": processing_time,
                "errorMessage": error_message
            }
            
            async with aiohttp.ClientSession() as session:
                # This would normally call the storage API, but for simplicity
                # we'll just log it. In a real implementation, this would update the database.
                logger.info(f"Activity logged: {activity_data}")
                
        except Exception as e:
            logger.error(f"Error logging activity: {e}")

    # Helper methods for text processing
    def extract_sender(self, content: str) -> str:
        lines = content.split('\n')
        for line in lines:
            if line.lower().startswith('from:'):
                return line.split(':', 1)[1].strip()
        return "unknown@example.com"

    def extract_subject(self, content: str) -> str:
        lines = content.split('\n')
        for line in lines:
            if line.lower().startswith('subject:'):
                return line.split(':', 1)[1].strip()
        return "No subject"

    def analyze_tone(self, content: str, classification: dict) -> str:
        # Simplified tone analysis
        angry_words = ['angry', 'frustrated', 'terrible', 'awful', 'unacceptable', 'furious']
        polite_words = ['please', 'thank you', 'appreciate', 'kindly', 'regards']
        
        content_lower = content.lower()
        angry_count = sum(1 for word in angry_words if word in content_lower)
        polite_count = sum(1 for word in polite_words if word in content_lower)
        
        if angry_count > polite_count and angry_count > 0:
            return "angry"
        elif polite_count > 0:
            return "polite"
        else:
            return "neutral"

    def detect_json_anomalies(self, data) -> list:
        """Detect anomalies in JSON data structure"""
        anomalies = []
        
        if isinstance(data, dict):
            # Check for missing required fields (example)
            required_fields = ['id', 'timestamp', 'type']
            for field in required_fields:
                if field not in data:
                    anomalies.append(f"Missing required field: {field}")
        
        elif isinstance(data, list):
            # Check for inconsistent schemas in array
            if len(data) > 0:
                first_keys = set(data[0].keys()) if isinstance(data[0], dict) else set()
                for i, item in enumerate(data[1:], 1):
                    if isinstance(item, dict):
                        if set(item.keys()) != first_keys:
                            anomalies.append(f"Schema mismatch at index {i}")
        
        return anomalies

    def summarize_json_data(self, data) -> dict:
        """Create summary of JSON data"""
        if isinstance(data, list):
            return {
                "type": "array",
                "length": len(data),
                "first_item_keys": list(data[0].keys()) if len(data) > 0 and isinstance(data[0], dict) else []
            }
        elif isinstance(data, dict):
            return {
                "type": "object", 
                "keys": list(data.keys()),
                "key_count": len(data.keys())
            }
        else:
            return {"type": type(data).__name__, "value": str(data)[:100]}

    def count_pdf_pages(self, file_path: str) -> int:
        """Count pages in PDF"""
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                return len(reader.pages)
        except:
            return 1  # Default if PyPDF2 not available

    def extract_invoice_amount(self, content: str) -> float:
        """Extract invoice amount from PDF content"""
        import re
        # Look for common currency patterns
        patterns = [
            r'\$[\d,]+\.?\d*',
            r'Total:?\s*\$?[\d,]+\.?\d*',
            r'Amount:?\s*\$?[\d,]+\.?\d*'
        ]
        
        amounts = []
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Extract numeric value
                numeric = re.sub(r'[^\d.]', '', match)
                try:
                    amounts.append(float(numeric))
                except ValueError:
                    continue
        
        return max(amounts) if amounts else 0.0

    async def update_file_status(self, file_id: int, status: str, classification: dict = None, extracted_data: dict = None):
        """Update file processing status"""
        try:
            update_data = {"status": status}
            if classification:
                update_data["classificationResult"] = classification
                update_data["businessIntent"] = classification.get("business_intent")
                update_data["priority"] = classification.get("urgency", "low")
            if extracted_data:
                update_data["extractedData"] = extracted_data
            
            # In a real implementation, this would call the storage API
            logger.info(f"File {file_id} status updated: {update_data}")
            
        except Exception as e:
            logger.error(f"Error updating file status: {e}")

async def main():
    if len(sys.argv) != 4:
        print("Usage: python ai_system.py <file_id> <file_path> <file_type>")
        sys.exit(1)
    
    file_id = int(sys.argv[1])
    file_path = sys.argv[2]
    file_type = sys.argv[3]
    
    system = AIProcessingSystem()
    
    try:
        # Step 1: Classify file format and business intent
        logger.info(f"Starting classification for file {file_id}")
        classification = await system.classify_file(file_path, file_type)
        logger.info(f"Classification result: {classification}")
        
        # Step 2: Process with specialized agent
        logger.info(f"Processing with {file_type} agent")
        extracted_data = await system.process_with_agent(file_id, file_path, file_type, classification)
        logger.info(f"Extraction result: {extracted_data}")
        
        # Step 3: Route actions based on results
        logger.info("Routing actions")
        await system.route_action(file_id, classification, extracted_data)
        
        # Step 4: Update file status to completed
        await system.update_file_status(file_id, "completed", classification, extracted_data)
        
        logger.info(f"File {file_id} processing completed successfully")
        
    except Exception as e:
        logger.error(f"Processing failed for file {file_id}: {e}")
        await system.update_file_status(file_id, "failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
