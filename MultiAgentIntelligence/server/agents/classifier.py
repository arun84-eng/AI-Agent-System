#!/usr/bin/env python3
"""
Classifier Agent - Multi-format AI classification system
Detects file format and business intent using few-shot learning and OpenAI API
"""

import os
import json
import logging
from typing import Dict, Any, Optional
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)

class ClassifierAgent:
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        self.model = "gpt-3.5-turbo"
        
        # Few-shot examples for business intent classification
        self.few_shot_examples = {
            "email_examples": [
                {
                    "content": "Subject: Urgent - Payment Issue\nI am extremely frustrated with your service. The payment was processed but my account still shows unpaid.",
                    "classification": {"format": "Email", "business_intent": "Complaint", "urgency": "high", "tone": "angry"}
                },
                {
                    "content": "Subject: Thank you for your service\nDear team, I wanted to express my gratitude for the excellent support provided.",
                    "classification": {"format": "Email", "business_intent": "Feedback", "urgency": "low", "tone": "polite"}
                }
            ],
            "json_examples": [
                {
                    "content": '{"rfq_id": "RFQ-2024-001", "company": "ABC Corp", "items": [{"product": "Widget A", "quantity": 100}]}',
                    "classification": {"format": "JSON", "business_intent": "RFQ", "urgency": "medium", "data_type": "request_for_quote"}
                },
                {
                    "content": '{"transaction_id": "TXN-2024-001", "amount_suspicious": true, "risk_score": 0.95}',
                    "classification": {"format": "JSON", "business_intent": "Fraud Risk", "urgency": "high", "data_type": "fraud_detection"}
                }
            ],
            "pdf_examples": [
                {
                    "content": "INVOICE #INV-2024-001 Total Amount: $15,000.00 Due Date: 30 days",
                    "classification": {"format": "PDF", "business_intent": "Invoice", "urgency": "medium", "document_type": "financial"}
                },
                {
                    "content": "GDPR Compliance Policy This document outlines data protection requirements under GDPR",
                    "classification": {"format": "PDF", "business_intent": "Regulation", "urgency": "high", "document_type": "compliance"}
                }
            ]
        }

    async def classify_content(self, content: str, file_type: str, filename: str = "") -> Dict[str, Any]:
        """
        Classify file content using OpenAI API with few-shot learning
        
        Args:
            content: Text content extracted from file
            file_type: PDF, Email, or JSON
            filename: Original filename for additional context
            
        Returns:
            Classification result with format, business_intent, confidence, urgency
        """
        try:
            if not self.openai_api_key:
                logger.warning("No OpenAI API key provided, using rule-based fallback")
                return self._rule_based_classification(content, file_type, filename)
            
            # Get relevant few-shot examples
            examples = self._get_relevant_examples(file_type)
            
            # Construct the prompt with few-shot learning
            prompt = self._build_classification_prompt(content, file_type, examples, filename)
            
            # Call OpenAI API
            classification = await self._call_openai_api(prompt)
            
            # Validate and enhance classification
            validated_classification = self._validate_classification(classification, file_type)
            
            logger.info(f"Classification completed for {file_type}: {validated_classification}")
            return validated_classification
            
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return self._rule_based_classification(content, file_type, filename)

    def _get_relevant_examples(self, file_type: str) -> list:
        """Get few-shot examples relevant to the file type"""
        type_mapping = {
            "Email": "email_examples",
            "PDF": "pdf_examples", 
            "JSON": "json_examples"
        }
        
        example_key = type_mapping.get(file_type, "email_examples")
        return self.few_shot_examples.get(example_key, [])

    def _build_classification_prompt(self, content: str, file_type: str, examples: list, filename: str) -> str:
        """Build the classification prompt with few-shot examples"""
        
        # Limit content length for API efficiency
        truncated_content = content[:2000] if len(content) > 2000 else content
        
        prompt = f"""You are an expert AI classifier for business documents. Your task is to classify the format and business intent of the given content.

File Type: {file_type}
Filename: {filename}

Few-shot examples for {file_type}:
"""
        
        # Add few-shot examples
        for i, example in enumerate(examples[:2], 1):
            prompt += f"""
Example {i}:
Content: {example['content'][:200]}...
Classification: {json.dumps(example['classification'])}
"""
        
        prompt += f"""
Now classify this content:
Content: {truncated_content}

Business Intent Categories:
- RFQ (Request for Quote)
- Complaint
- Invoice  
- Regulation
- Fraud Risk
- Feedback
- Support Request

Urgency Levels: low, medium, high
Confidence: 0.0 to 1.0

Response format (JSON only):
{{
    "format": "{file_type}",
    "business_intent": "one of the categories above",
    "confidence": 0.0-1.0,
    "urgency": "low/medium/high",
    "reasoning": "brief explanation",
    "extracted_indicators": ["key phrases that led to classification"]
}}"""

        return prompt

    async def _call_openai_api(self, prompt: str) -> Dict[str, Any]:
        """Make API call to OpenAI"""
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system", 
                    "content": "You are a precise business document classifier. Always respond with valid JSON containing the exact fields requested."
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 400,
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.openai.com/v1/chat/completions", 
                                  headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result["choices"][0]["message"]["content"]
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse OpenAI response as JSON: {e}")
                        logger.error(f"Raw response: {content}")
                        raise
                else:
                    error_text = await response.text()
                    logger.error(f"OpenAI API error {response.status}: {error_text}")
                    raise Exception(f"OpenAI API error: {response.status}")

    def _validate_classification(self, classification: Dict[str, Any], file_type: str) -> Dict[str, Any]:
        """Validate and enhance the classification result"""
        
        # Valid business intents
        valid_intents = ["RFQ", "Complaint", "Invoice", "Regulation", "Fraud Risk", "Feedback", "Support Request"]
        valid_urgencies = ["low", "medium", "high"]
        
        # Ensure required fields exist
        validated = {
            "format": classification.get("format", file_type),
            "business_intent": classification.get("business_intent", "Unknown"),
            "confidence": min(max(float(classification.get("confidence", 0.5)), 0.0), 1.0),
            "urgency": classification.get("urgency", "medium"),
            "reasoning": classification.get("reasoning", ""),
            "extracted_indicators": classification.get("extracted_indicators", []),
            "classification_timestamp": datetime.now().isoformat()
        }
        
        # Validate business intent
        if validated["business_intent"] not in valid_intents:
            logger.warning(f"Invalid business intent: {validated['business_intent']}, defaulting to 'Unknown'")
            validated["business_intent"] = "Unknown"
            validated["confidence"] *= 0.5  # Reduce confidence for invalid classification
        
        # Validate urgency
        if validated["urgency"] not in valid_urgencies:
            logger.warning(f"Invalid urgency: {validated['urgency']}, defaulting to 'medium'")
            validated["urgency"] = "medium"
        
        # Auto-adjust urgency based on business intent
        if validated["business_intent"] in ["Fraud Risk", "Complaint"] and validated["urgency"] == "low":
            validated["urgency"] = "high"
            validated["reasoning"] += " (Urgency auto-elevated for fraud/complaint)"
        
        return validated

    def _rule_based_classification(self, content: str, file_type: str, filename: str) -> Dict[str, Any]:
        """Fallback rule-based classification when OpenAI API is unavailable"""
        
        content_lower = content.lower()
        filename_lower = filename.lower()
        
        # Business intent detection using keywords
        intent_keywords = {
            "RFQ": ["request for quote", "rfq", "quotation", "proposal", "bid"],
            "Complaint": ["complaint", "issue", "problem", "frustrated", "angry", "terrible", "awful", "unacceptable"],
            "Invoice": ["invoice", "payment", "amount", "total", "bill", "charge"],
            "Regulation": ["gdpr", "compliance", "regulation", "policy", "fda", "sox", "hipaa"],
            "Fraud Risk": ["fraud", "suspicious", "risk", "anomaly", "unusual", "irregular"]
        }
        
        # Urgency detection
        urgency_keywords = {
            "high": ["urgent", "immediate", "asap", "critical", "emergency", "fraud", "suspicious"],
            "medium": ["soon", "important", "review", "attention"],
            "low": ["routine", "regular", "standard", "normal"]
        }
        
        # Detect business intent
        detected_intent = "Unknown"
        confidence = 0.3  # Lower confidence for rule-based
        
        for intent, keywords in intent_keywords.items():
            if any(keyword in content_lower or keyword in filename_lower for keyword in keywords):
                detected_intent = intent
                confidence = 0.7
                break
        
        # Detect urgency
        detected_urgency = "medium"
        for urgency, keywords in urgency_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                detected_urgency = urgency
                break
        
        return {
            "format": file_type,
            "business_intent": detected_intent,
            "confidence": confidence,
            "urgency": detected_urgency,
            "reasoning": "Rule-based classification (OpenAI API unavailable)",
            "extracted_indicators": [],
            "classification_timestamp": datetime.now().isoformat(),
            "method": "rule_based"
        }

    def get_classification_stats(self) -> Dict[str, Any]:
        """Get classifier performance statistics"""
        return {
            "total_classifications": getattr(self, '_total_classifications', 0),
            "successful_classifications": getattr(self, '_successful_classifications', 0),
            "api_available": bool(self.openai_api_key),
            "model_used": self.model,
            "few_shot_examples_count": sum(len(examples) for examples in self.few_shot_examples.values())
        }

    async def update_few_shot_examples(self, file_type: str, content: str, correct_classification: Dict[str, Any]):
        """Update few-shot examples based on correct classifications (for continuous learning)"""
        type_mapping = {
            "Email": "email_examples",
            "PDF": "pdf_examples",
            "JSON": "json_examples"
        }
        
        example_key = type_mapping.get(file_type)
        if example_key:
            # Add new example (limit to prevent prompt bloat)
            new_example = {
                "content": content[:200],
                "classification": correct_classification
            }
            
            if len(self.few_shot_examples[example_key]) >= 5:
                # Remove oldest example
                self.few_shot_examples[example_key].pop(0)
            
            self.few_shot_examples[example_key].append(new_example)
            logger.info(f"Added new few-shot example for {file_type}")

# Global instance
classifier_agent = ClassifierAgent()
