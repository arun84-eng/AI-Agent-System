#!/usr/bin/env python3
"""
Email Agent - Specialized email processing and tone analysis
Extracts structured fields, analyzes sentiment, and triggers escalation based on urgency
"""

import re
import os
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
import aiohttp
from datetime import datetime
import email
from email.parser import Parser
from email.policy import default

logger = logging.getLogger(__name__)

class EmailAgent:
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        self.model = "gpt-3.5-turbo"
        
        # Tone analysis patterns for fallback
        self.tone_patterns = {
            "angry": [
                "furious", "outraged", "disgusted", "livid", "infuriated", "incensed",
                "terrible", "awful", "horrible", "disgusting", "unacceptable",
                "demand", "immediately", "ridiculous", "pathetic", "useless"
            ],
            "frustrated": [
                "frustrated", "annoyed", "disappointed", "fed up", "tired of",
                "repeatedly", "still not", "how many times", "again and again"
            ],
            "threatening": [
                "lawyer", "legal action", "sue", "court", "report to", "authorities",
                "better business bureau", "cease and desist", "lawsuit"
            ],
            "urgent": [
                "urgent", "asap", "immediately", "emergency", "critical", "time sensitive",
                "deadline", "expires", "due today", "before close of business"
            ],
            "polite": [
                "please", "thank you", "appreciate", "grateful", "kindly", "respectfully",
                "sincerely", "best regards", "looking forward", "hope to hear"
            ]
        }
        
        # Priority escalation rules
        self.escalation_rules = {
            "immediate": ["threatening", "angry", "urgent"],
            "high": ["frustrated", "complaint", "deadline"],
            "medium": ["question", "request", "inquiry"],
            "low": ["polite", "thank_you", "routine"]
        }

    async def process_email(self, file_path: str, content: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process email with comprehensive field extraction and tone analysis
        
        Args:
            file_path: Path to the email file
            content: Raw email content
            classification: Classification result from classifier agent
            
        Returns:
            Extracted email data with tone analysis and escalation recommendation
        """
        try:
            # Parse email structure
            email_data = self._parse_email_structure(content)
            
            # Extract sender information
            sender_info = self._extract_sender_info(email_data)
            
            # Analyze tone and sentiment
            tone_analysis = await self._analyze_tone(email_data.get('body', ''), email_data.get('subject', ''))
            
            # Determine urgency and escalation
            urgency_assessment = self._assess_urgency(tone_analysis, classification, email_data)
            
            # Extract key entities and context
            entities = await self._extract_entities(email_data.get('body', ''))
            
            # Compile comprehensive result
            result = {
                "email_structure": email_data,
                "sender": sender_info,
                "tone_analysis": tone_analysis,
                "urgency_assessment": urgency_assessment,
                "extracted_entities": entities,
                "classification_context": classification,
                "processing_timestamp": datetime.now().isoformat(),
                "escalation_recommendation": self._determine_escalation_action(urgency_assessment, tone_analysis)
            }
            
            logger.info(f"Email processing completed: {sender_info.get('email', 'unknown')} - {tone_analysis.get('primary_tone', 'neutral')}")
            return result
            
        except Exception as e:
            logger.error(f"Email processing error: {e}")
            return self._fallback_email_processing(content, classification)

    def _parse_email_structure(self, content: str) -> Dict[str, Any]:
        """Parse email structure from raw content"""
        try:
            # Try to parse as proper email message
            if content.startswith('From:') or 'Subject:' in content[:200]:
                parser = Parser(policy=default)
                msg = parser.parsestr(content)
                
                return {
                    "subject": self._clean_header(msg.get('Subject', '')),
                    "from": self._clean_header(msg.get('From', '')),
                    "to": self._clean_header(msg.get('To', '')),
                    "cc": self._clean_header(msg.get('Cc', '')),
                    "date": self._clean_header(msg.get('Date', '')),
                    "body": self._extract_body(msg),
                    "attachments": self._extract_attachments(msg),
                    "headers": dict(msg.items())
                }
            else:
                # Fallback parsing for plain text
                return self._parse_plain_text_email(content)
                
        except Exception as e:
            logger.warning(f"Email parsing error: {e}, falling back to plain text parsing")
            return self._parse_plain_text_email(content)

    def _parse_plain_text_email(self, content: str) -> Dict[str, Any]:
        """Parse plain text email content"""
        lines = content.split('\n')
        
        email_data = {
            "subject": "",
            "from": "",
            "to": "",
            "cc": "",
            "date": "",
            "body": content,
            "attachments": [],
            "headers": {}
        }
        
        # Extract headers from beginning of content
        body_start = 0
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                body_start = i + 1
                break
            
            if line.lower().startswith('subject:'):
                email_data["subject"] = line[8:].strip()
            elif line.lower().startswith('from:'):
                email_data["from"] = line[5:].strip()
            elif line.lower().startswith('to:'):
                email_data["to"] = line[3:].strip()
            elif line.lower().startswith('cc:'):
                email_data["cc"] = line[3:].strip()
            elif line.lower().startswith('date:'):
                email_data["date"] = line[5:].strip()
        
        # Extract body
        if body_start < len(lines):
            email_data["body"] = '\n'.join(lines[body_start:]).strip()
        
        return email_data

    def _clean_header(self, header: str) -> str:
        """Clean email header content"""
        if not header:
            return ""
        return re.sub(r'\s+', ' ', header.strip())

    def _extract_body(self, msg) -> str:
        """Extract body content from email message"""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_content()
                elif part.get_content_type() == "text/html" and not msg.get_content():
                    # Fallback to HTML if no plain text
                    html_content = part.get_content()
                    # Simple HTML tag removal
                    return re.sub(r'<[^>]+>', '', html_content)
        else:
            return msg.get_content() or ""
        
        return ""

    def _extract_attachments(self, msg) -> List[str]:
        """Extract attachment information"""
        attachments = []
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename:
                        attachments.append(filename)
        return attachments

    def _extract_sender_info(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract detailed sender information"""
        from_field = email_data.get('from', '')
        
        # Extract email address
        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', from_field)
        email_address = email_match.group(1) if email_match else ""
        
        # Extract name
        name = re.sub(r'<.*?>', '', from_field).strip()
        name = re.sub(r'"', '', name).strip()
        
        # Determine sender type
        sender_type = "external"
        if email_address:
            domain = email_address.split('@')[1]
            # You could add internal domain detection here
            
        return {
            "email": email_address,
            "name": name,
            "display_name": from_field,
            "domain": email_address.split('@')[1] if email_address else "",
            "sender_type": sender_type,
            "is_verified": bool(email_address)  # Basic verification
        }

    async def _analyze_tone(self, body: str, subject: str) -> Dict[str, Any]:
        """Analyze email tone and sentiment using AI or rule-based fallback"""
        
        if self.openai_api_key:
            try:
                return await self._ai_tone_analysis(body, subject)
            except Exception as e:
                logger.warning(f"AI tone analysis failed: {e}, using rule-based fallback")
        
        return self._rule_based_tone_analysis(body, subject)

    async def _ai_tone_analysis(self, body: str, subject: str) -> Dict[str, Any]:
        """AI-powered tone analysis using OpenAI"""
        
        combined_text = f"Subject: {subject}\n\nBody: {body[:1500]}"
        
        prompt = f"""Analyze the tone and sentiment of this email:

{combined_text}

Provide a detailed analysis including:
1. Primary tone (angry, frustrated, polite, neutral, urgent, threatening)
2. Emotional intensity (1-10 scale)
3. Urgency level (1-10 scale)
4. Professional/unprofessional language indicators
5. Escalation risk assessment
6. Key emotional indicators found in the text

Respond in JSON format:
{{
    "primary_tone": "tone_category",
    "emotional_intensity": 1-10,
    "urgency_level": 1-10,
    "professionalism_score": 1-10,
    "escalation_risk": "low/medium/high",
    "emotional_indicators": ["list", "of", "key", "phrases"],
    "sentiment_score": -1.0 to 1.0,
    "confidence": 0.0 to 1.0
}}"""

        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an expert in email tone analysis and customer sentiment. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.openai.com/v1/chat/completions", 
                                  headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result["choices"][0]["message"]["content"]
                    analysis = json.loads(content)
                    analysis["analysis_method"] = "ai_powered"
                    return analysis
                else:
                    raise Exception(f"OpenAI API error: {response.status}")

    def _rule_based_tone_analysis(self, body: str, subject: str) -> Dict[str, Any]:
        """Rule-based tone analysis as fallback"""
        
        combined_text = (subject + " " + body).lower()
        
        # Score each tone category
        tone_scores = {}
        for tone, patterns in self.tone_patterns.items():
            score = sum(1 for pattern in patterns if pattern in combined_text)
            tone_scores[tone] = score
        
        # Determine primary tone
        primary_tone = max(tone_scores, key=tone_scores.get) if any(tone_scores.values()) else "neutral"
        
        # Calculate metrics
        emotional_intensity = min(max(tone_scores.get(primary_tone, 0) * 2, 1), 10)
        urgency_level = min(tone_scores.get("urgent", 0) * 3 + tone_scores.get("angry", 0), 10)
        
        # Calculate professionalism score (inverse of negative tone indicators)
        unprofessional_indicators = tone_scores.get("angry", 0) + tone_scores.get("threatening", 0)
        professionalism_score = max(10 - unprofessional_indicators * 2, 1)
        
        # Determine escalation risk
        escalation_risk = "high" if tone_scores.get("threatening", 0) > 0 or tone_scores.get("angry", 0) > 2 else \
                         "medium" if tone_scores.get("frustrated", 0) > 1 or tone_scores.get("urgent", 0) > 1 else "low"
        
        # Extract emotional indicators
        emotional_indicators = []
        for tone, patterns in self.tone_patterns.items():
            if tone_scores.get(tone, 0) > 0:
                found_patterns = [pattern for pattern in patterns if pattern in combined_text]
                emotional_indicators.extend(found_patterns[:3])  # Limit per category
        
        return {
            "primary_tone": primary_tone,
            "emotional_intensity": emotional_intensity,
            "urgency_level": urgency_level,
            "professionalism_score": professionalism_score,
            "escalation_risk": escalation_risk,
            "emotional_indicators": emotional_indicators[:10],  # Limit total
            "sentiment_score": self._calculate_sentiment_score(tone_scores),
            "confidence": 0.6,  # Lower confidence for rule-based
            "tone_scores": tone_scores,
            "analysis_method": "rule_based"
        }

    def _calculate_sentiment_score(self, tone_scores: Dict[str, int]) -> float:
        """Calculate sentiment score from -1.0 (negative) to 1.0 (positive)"""
        negative_score = tone_scores.get("angry", 0) + tone_scores.get("frustrated", 0) + tone_scores.get("threatening", 0)
        positive_score = tone_scores.get("polite", 0)
        
        if negative_score == 0 and positive_score == 0:
            return 0.0
        
        total = negative_score + positive_score
        return (positive_score - negative_score) / max(total, 1)

    def _assess_urgency(self, tone_analysis: Dict[str, Any], classification: Dict[str, Any], email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall urgency and priority"""
        
        urgency_factors = {
            "tone_urgency": tone_analysis.get("urgency_level", 1),
            "classification_urgency": {"high": 8, "medium": 5, "low": 2}.get(classification.get("urgency", "medium"), 5),
            "business_intent_urgency": {"Complaint": 7, "Fraud Risk": 9, "Invoice": 5, "RFQ": 4}.get(classification.get("business_intent", ""), 3),
            "escalation_risk": {"high": 8, "medium": 5, "low": 2}.get(tone_analysis.get("escalation_risk", "low"), 2)
        }
        
        # Calculate composite urgency score
        weighted_urgency = (
            urgency_factors["tone_urgency"] * 0.3 +
            urgency_factors["classification_urgency"] * 0.25 +
            urgency_factors["business_intent_urgency"] * 0.25 +
            urgency_factors["escalation_risk"] * 0.2
        )
        
        # Determine final urgency level
        if weighted_urgency >= 7:
            final_urgency = "high"
        elif weighted_urgency >= 4:
            final_urgency = "medium"
        else:
            final_urgency = "low"
        
        return {
            "urgency_level": final_urgency,
            "urgency_score": round(weighted_urgency, 2),
            "urgency_factors": urgency_factors,
            "requires_immediate_attention": weighted_urgency >= 8,
            "estimated_response_time": self._estimate_response_time(final_urgency),
            "priority_reason": self._explain_urgency_reasoning(urgency_factors, tone_analysis, classification)
        }

    def _estimate_response_time(self, urgency: str) -> str:
        """Estimate appropriate response time based on urgency"""
        response_times = {
            "high": "Within 1 hour",
            "medium": "Within 4 hours",
            "low": "Within 24 hours"
        }
        return response_times.get(urgency, "Within 24 hours")

    def _explain_urgency_reasoning(self, factors: Dict, tone_analysis: Dict, classification: Dict) -> str:
        """Provide human-readable explanation of urgency assessment"""
        reasons = []
        
        if factors["escalation_risk"] >= 7:
            reasons.append(f"High escalation risk detected ({tone_analysis.get('escalation_risk', 'unknown')})")
        
        if factors["business_intent_urgency"] >= 7:
            reasons.append(f"Business intent requires attention ({classification.get('business_intent', 'unknown')})")
        
        if factors["tone_urgency"] >= 7:
            reasons.append(f"Urgent tone detected ({tone_analysis.get('primary_tone', 'unknown')})")
        
        if not reasons:
            reasons.append("Standard processing priority")
        
        return "; ".join(reasons)

    async def _extract_entities(self, body: str) -> Dict[str, Any]:
        """Extract key entities and information from email body"""
        
        entities = {
            "phone_numbers": re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', body),
            "email_addresses": re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', body),
            "account_numbers": re.findall(r'\b(?:account|acct|ref)[\s#]*(\w+)\b', body, re.IGNORECASE),
            "monetary_amounts": re.findall(r'\$[\d,]+\.?\d*', body),
            "dates": re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', body),
            "urls": re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', body)
        }
        
        # Clean up empty lists
        entities = {k: v for k, v in entities.items() if v}
        
        return entities

    def _determine_escalation_action(self, urgency_assessment: Dict[str, Any], tone_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the appropriate escalation action"""
        
        urgency = urgency_assessment.get("urgency_level", "low")
        escalation_risk = tone_analysis.get("escalation_risk", "low")
        
        if urgency == "high" or escalation_risk == "high":
            action = "immediate_escalation"
            description = "Escalate to senior customer service representative immediately"
            external_api = "/api/external/crm/escalate"
        elif urgency == "medium" or escalation_risk == "medium":
            action = "priority_queue"
            description = "Add to priority support queue for expedited handling"
            external_api = "/api/external/crm/priority"
        else:
            action = "standard_processing"
            description = "Process through standard customer service workflow"
            external_api = None
        
        return {
            "action_type": action,
            "description": description,
            "external_api_call": external_api,
            "recommended_assignee": self._recommend_assignee(urgency, tone_analysis),
            "follow_up_required": urgency in ["high", "medium"],
            "sla_deadline": self._calculate_sla_deadline(urgency)
        }

    def _recommend_assignee(self, urgency: str, tone_analysis: Dict[str, Any]) -> str:
        """Recommend appropriate assignee based on email characteristics"""
        
        if tone_analysis.get("escalation_risk") == "high":
            return "senior_customer_service_manager"
        elif urgency == "high":
            return "senior_customer_service_rep"
        elif tone_analysis.get("primary_tone") in ["threatening", "angry"]:
            return "customer_retention_specialist"
        else:
            return "customer_service_rep"

    def _calculate_sla_deadline(self, urgency: str) -> str:
        """Calculate SLA deadline based on urgency"""
        from datetime import timedelta
        
        hours_map = {"high": 1, "medium": 4, "low": 24}
        deadline = datetime.now() + timedelta(hours=hours_map.get(urgency, 24))
        return deadline.isoformat()

    def _fallback_email_processing(self, content: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback processing when main processing fails"""
        
        return {
            "email_structure": self._parse_plain_text_email(content),
            "sender": {"email": "unknown", "name": "unknown"},
            "tone_analysis": {"primary_tone": "neutral", "confidence": 0.3},
            "urgency_assessment": {"urgency_level": "medium", "urgency_score": 5.0},
            "extracted_entities": {},
            "classification_context": classification,
            "processing_timestamp": datetime.now().isoformat(),
            "escalation_recommendation": {
                "action_type": "standard_processing",
                "description": "Standard processing (fallback mode)",
                "external_api_call": None
            },
            "processing_status": "fallback_mode"
        }

# Global instance
email_agent = EmailAgent()
