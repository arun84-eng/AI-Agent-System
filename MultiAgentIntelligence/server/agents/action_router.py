#!/usr/bin/env python3
"""
Action Router - Orchestrates follow-up actions based on agent processing results
Routes actions to external APIs, manages escalation workflows, and handles retry logic
"""

import os
import json
import logging
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class ActionType(Enum):
    ESCALATE = "escalate"
    FLAG = "flag"
    LOG = "log"
    ALERT = "alert"
    APPROVE = "approve"
    REJECT = "reject"
    REVIEW = "review"

class Priority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class ActionStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class ActionRouter:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.max_retries = 3
        self.retry_delays = [1, 5, 15]  # seconds
        
        # External API endpoints
        self.external_apis = {
            "crm_escalate": "/api/external/crm/escalate",
            "crm_priority": "/api/external/crm/priority",
            "risk_alert": "/api/external/risk/alert",
            "compliance_review": "/api/external/compliance/review",
            "finance_approval": "/api/external/finance/approval",
            "audit_log": "/api/external/audit/log"
        }
        
        # Action routing rules based on agent results
        self.routing_rules = {
            "email": {
                "high_urgency": {
                    "action": ActionType.ESCALATE,
                    "priority": Priority.CRITICAL,
                    "api": "crm_escalate",
                    "sla_hours": 1
                },
                "medium_urgency": {
                    "action": ActionType.REVIEW,
                    "priority": Priority.HIGH,
                    "api": "crm_priority",
                    "sla_hours": 4
                },
                "low_urgency": {
                    "action": ActionType.LOG,
                    "priority": Priority.LOW,
                    "api": "audit_log",
                    "sla_hours": 24
                }
            },
            "pdf": {
                "high_value": {
                    "action": ActionType.FLAG,
                    "priority": Priority.HIGH,
                    "api": "finance_approval",
                    "sla_hours": 2
                },
                "compliance_required": {
                    "action": ActionType.ALERT,
                    "priority": Priority.HIGH,
                    "api": "compliance_review",
                    "sla_hours": 4
                },
                "standard": {
                    "action": ActionType.LOG,
                    "priority": Priority.LOW,
                    "api": "audit_log",
                    "sla_hours": 24
                }
            },
            "json": {
                "anomalies_detected": {
                    "action": ActionType.FLAG,
                    "priority": Priority.MEDIUM,
                    "api": "risk_alert",
                    "sla_hours": 4
                },
                "validation_failed": {
                    "action": ActionType.ALERT,
                    "priority": Priority.HIGH,
                    "api": "risk_alert",
                    "sla_hours": 2
                },
                "standard": {
                    "action": ActionType.LOG,
                    "priority": Priority.LOW,
                    "api": "audit_log",
                    "sla_hours": 24
                }
            }
        }

    async def route_actions(self, file_id: int, file_type: str, classification_result: Dict[str, Any], 
                           agent_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Route actions based on classification and agent processing results
        
        Args:
            file_id: ID of the processed file
            file_type: Type of file (Email, PDF, JSON)
            classification_result: Result from classifier agent
            agent_results: Combined results from specialized agents
            
        Returns:
            List of triggered actions with their execution results
        """
        try:
            triggered_actions = []
            
            # Determine actions based on file type and results
            if file_type.lower() == "email":
                actions = await self._route_email_actions(file_id, classification_result, agent_results)
            elif file_type.lower() == "pdf":
                actions = await self._route_pdf_actions(file_id, classification_result, agent_results)
            elif file_type.lower() == "json":
                actions = await self._route_json_actions(file_id, classification_result, agent_results)
            else:
                actions = await self._route_default_actions(file_id, classification_result, agent_results)
            
            # Execute each action
            for action in actions:
                execution_result = await self._execute_action(action)
                triggered_actions.append(execution_result)
            
            # Log routing summary
            logger.info(f"Action routing completed for file {file_id}: {len(triggered_actions)} actions triggered")
            
            return triggered_actions
            
        except Exception as e:
            logger.error(f"Action routing error for file {file_id}: {e}")
            # Return fallback action
            return [await self._create_fallback_action(file_id, str(e))]

    async def _route_email_actions(self, file_id: int, classification: Dict[str, Any], 
                                 agent_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Route actions for email processing results"""
        actions = []
        
        # Extract email-specific data
        email_data = agent_results.get("email_agent", {})
        urgency_assessment = email_data.get("urgency_assessment", {})
        tone_analysis = email_data.get("tone_analysis", {})
        
        urgency_level = urgency_assessment.get("urgency_level", "low")
        escalation_risk = tone_analysis.get("escalation_risk", "low")
        primary_tone = tone_analysis.get("primary_tone", "neutral")
        
        # Determine routing based on urgency and tone
        if urgency_level == "high" or escalation_risk == "high" or primary_tone in ["angry", "threatening"]:
            rule = self.routing_rules["email"]["high_urgency"]
            actions.append(self._create_action(
                file_id=file_id,
                action_type=rule["action"],
                priority=rule["priority"],
                description=f"High-priority email escalation: {primary_tone} tone with {urgency_level} urgency",
                api_endpoint=rule["api"],
                sla_hours=rule["sla_hours"],
                metadata={
                    "sender": email_data.get("sender", {}).get("email", "unknown"),
                    "subject": email_data.get("email_structure", {}).get("subject", ""),
                    "tone": primary_tone,
                    "urgency": urgency_level,
                    "escalation_risk": escalation_risk
                }
            ))
        elif urgency_level == "medium" or escalation_risk == "medium":
            rule = self.routing_rules["email"]["medium_urgency"]
            actions.append(self._create_action(
                file_id=file_id,
                action_type=rule["action"],
                priority=rule["priority"],
                description=f"Medium-priority email review: {primary_tone} tone requires attention",
                api_endpoint=rule["api"],
                sla_hours=rule["sla_hours"],
                metadata={
                    "sender": email_data.get("sender", {}).get("email", "unknown"),
                    "subject": email_data.get("email_structure", {}).get("subject", ""),
                    "tone": primary_tone,
                    "urgency": urgency_level
                }
            ))
        else:
            rule = self.routing_rules["email"]["low_urgency"]
            actions.append(self._create_action(
                file_id=file_id,
                action_type=rule["action"],
                priority=rule["priority"],
                description="Routine email processed and logged",
                api_endpoint=rule["api"],
                sla_hours=rule["sla_hours"],
                metadata={
                    "sender": email_data.get("sender", {}).get("email", "unknown"),
                    "subject": email_data.get("email_structure", {}).get("subject", ""),
                    "tone": primary_tone
                }
            ))
        
        return actions

    async def _route_pdf_actions(self, file_id: int, classification: Dict[str, Any], 
                                agent_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Route actions for PDF processing results"""
        actions = []
        
        # Extract PDF-specific data
        pdf_data = agent_results.get("pdf_agent", {})
        financial_info = pdf_data.get("financial_information", {})
        compliance_analysis = pdf_data.get("compliance_analysis", {})
        risk_assessment = pdf_data.get("risk_assessment", {})
        
        largest_amount = financial_info.get("largest_amount", 0)
        regulations_detected = compliance_analysis.get("regulations_detected", [])
        risk_level = risk_assessment.get("risk_level", "low")
        
        # High-value amount flagging
        if largest_amount > 10000:
            rule = self.routing_rules["pdf"]["high_value"]
            actions.append(self._create_action(
                file_id=file_id,
                action_type=rule["action"],
                priority=rule["priority"],
                description=f"High-value document flagged: ${largest_amount:,.2f} requires finance approval",
                api_endpoint=rule["api"],
                sla_hours=rule["sla_hours"],
                metadata={
                    "amount": largest_amount,
                    "document_type": pdf_data.get("document_type", {}).get("primary_type", "unknown"),
                    "invoice_numbers": financial_info.get("invoice_numbers", []),
                    "risk_level": risk_level
                }
            ))
        
        # Compliance requirements
        if regulations_detected:
            rule = self.routing_rules["pdf"]["compliance_required"]
            reg_names = [reg["regulation"] for reg in regulations_detected]
            actions.append(self._create_action(
                file_id=file_id,
                action_type=rule["action"],
                priority=rule["priority"],
                description=f"Compliance review required: {', '.join(reg_names)} regulations detected",
                api_endpoint=rule["api"],
                sla_hours=rule["sla_hours"],
                metadata={
                    "regulations": reg_names,
                    "compliance_score": compliance_analysis.get("compliance_score", 0),
                    "document_type": pdf_data.get("document_type", {}).get("primary_type", "unknown"),
                    "risk_level": risk_level
                }
            ))
        
        # High risk assessment
        if risk_level == "high":
            actions.append(self._create_action(
                file_id=file_id,
                action_type=ActionType.ALERT,
                priority=Priority.CRITICAL,
                description=f"Critical risk document: {risk_level} risk level requires immediate attention",
                api_endpoint="risk_alert",
                sla_hours=1,
                metadata={
                    "risk_factors": risk_assessment.get("risk_factors", []),
                    "risk_score": risk_assessment.get("risk_score", 0),
                    "document_type": pdf_data.get("document_type", {}).get("primary_type", "unknown")
                }
            ))
        
        # Standard processing if no special conditions
        if not actions:
            rule = self.routing_rules["pdf"]["standard"]
            actions.append(self._create_action(
                file_id=file_id,
                action_type=rule["action"],
                priority=rule["priority"],
                description="PDF document processed successfully",
                api_endpoint=rule["api"],
                sla_hours=rule["sla_hours"],
                metadata={
                    "document_type": pdf_data.get("document_type", {}).get("primary_type", "unknown"),
                    "pages": pdf_data.get("document_metadata", {}).get("actual_pages", 1)
                }
            ))
        
        return actions

    async def _route_json_actions(self, file_id: int, classification: Dict[str, Any], 
                                 agent_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Route actions for JSON processing results"""
        actions = []
        
        # Extract JSON-specific data
        json_data = agent_results.get("json_agent", {})
        schema_validation = json_data.get("schema_validation", {})
        anomaly_analysis = json_data.get("anomaly_analysis", {})
        business_validation = json_data.get("business_validation", {})
        risk_assessment = json_data.get("risk_assessment", {})
        
        schema_valid = schema_validation.get("is_valid", True)
        anomaly_count = anomaly_analysis.get("anomaly_count", 0)
        anomaly_risk = anomaly_analysis.get("risk_level", "low")
        business_valid = business_validation.get("is_valid", True)
        
        # Schema validation failures
        if not schema_valid:
            rule = self.routing_rules["json"]["validation_failed"]
            actions.append(self._create_action(
                file_id=file_id,
                action_type=rule["action"],
                priority=rule["priority"],
                description=f"JSON schema validation failed: {len(schema_validation.get('errors', []))} errors detected",
                api_endpoint=rule["api"],
                sla_hours=rule["sla_hours"],
                metadata={
                    "validation_errors": schema_validation.get("errors", []),
                    "schema_score": schema_validation.get("schema_score", 0),
                    "detected_type": json_data.get("json_structure", {}).get("detected_type", "unknown")
                }
            ))
        
        # Anomaly detection
        if anomaly_count > 0 or anomaly_risk in ["medium", "high"]:
            rule = self.routing_rules["json"]["anomalies_detected"]
            actions.append(self._create_action(
                file_id=file_id,
                action_type=rule["action"],
                priority=rule["priority"],
                description=f"JSON anomalies detected: {anomaly_count} anomalies with {anomaly_risk} risk level",
                api_endpoint=rule["api"],
                sla_hours=rule["sla_hours"],
                metadata={
                    "anomaly_count": anomaly_count,
                    "anomaly_risk": anomaly_risk,
                    "anomalies": anomaly_analysis.get("anomalies", [])[:5],  # Limit for payload size
                    "detected_type": json_data.get("json_structure", {}).get("detected_type", "unknown")
                }
            ))
        
        # Business rule violations
        if not business_valid:
            actions.append(self._create_action(
                file_id=file_id,
                action_type=ActionType.ALERT,
                priority=Priority.HIGH,
                description=f"Business rule violations detected: {len(business_validation.get('violations', []))} violations",
                api_endpoint="risk_alert",
                sla_hours=2,
                metadata={
                    "violations": business_validation.get("violations", []),
                    "business_score": business_validation.get("business_score", 0),
                    "detected_type": json_data.get("json_structure", {}).get("detected_type", "unknown")
                }
            ))
        
        # Standard processing if no issues
        if not actions:
            rule = self.routing_rules["json"]["standard"]
            actions.append(self._create_action(
                file_id=file_id,
                action_type=rule["action"],
                priority=rule["priority"],
                description="JSON data validated successfully",
                api_endpoint=rule["api"],
                sla_hours=rule["sla_hours"],
                metadata={
                    "record_count": json_data.get("json_structure", {}).get("record_count", 0),
                    "detected_type": json_data.get("json_structure", {}).get("detected_type", "unknown"),
                    "quality_score": json_data.get("data_quality", {}).get("overall_score", 0)
                }
            ))
        
        return actions

    async def _route_default_actions(self, file_id: int, classification: Dict[str, Any], 
                                   agent_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Route default actions for unknown file types"""
        return [self._create_action(
            file_id=file_id,
            action_type=ActionType.LOG,
            priority=Priority.LOW,
            description="Unknown file type processed with standard workflow",
            api_endpoint="audit_log",
            sla_hours=24,
            metadata={
                "file_type": classification.get("format", "unknown"),
                "business_intent": classification.get("business_intent", "unknown")
            }
        )]

    def _create_action(self, file_id: int, action_type: ActionType, priority: Priority, 
                      description: str, api_endpoint: str, sla_hours: int, 
                      metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create action object"""
        
        sla_deadline = datetime.now() + timedelta(hours=sla_hours)
        
        return {
            "file_id": file_id,
            "action_type": action_type.value,
            "priority": priority.value,
            "description": description,
            "status": ActionStatus.PENDING.value,
            "api_endpoint": api_endpoint,
            "sla_deadline": sla_deadline.isoformat(),
            "metadata": metadata,
            "created_at": datetime.now().isoformat(),
            "retry_count": 0,
            "execution_log": []
        }

    async def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute individual action with retry logic"""
        
        action["status"] = ActionStatus.IN_PROGRESS.value
        action["execution_log"].append({
            "timestamp": datetime.now().isoformat(),
            "event": "execution_started",
            "details": "Action execution initiated"
        })
        
        # Determine if external API call is needed
        api_endpoint = action.get("api_endpoint")
        if api_endpoint and api_endpoint in self.external_apis:
            execution_result = await self._call_external_api_with_retry(action)
        else:
            # Internal processing only
            execution_result = await self._process_internal_action(action)
        
        # Update action with execution result
        action.update(execution_result)
        
        # Log action to storage
        try:
            await self._log_action_to_storage(action)
        except Exception as e:
            logger.error(f"Failed to log action to storage: {e}")
        
        return action

    async def _call_external_api_with_retry(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Call external API with retry logic"""
        
        api_endpoint = action["api_endpoint"]
        full_url = f"{self.base_url}{self.external_apis[api_endpoint]}"
        
        for attempt in range(self.max_retries + 1):
            try:
                action["execution_log"].append({
                    "timestamp": datetime.now().isoformat(),
                    "event": f"api_call_attempt_{attempt + 1}",
                    "details": f"Calling {full_url}"
                })
                
                # Prepare payload
                payload = {
                    "file_id": action["file_id"],
                    "action_type": action["action_type"],
                    "priority": action["priority"],
                    "description": action["description"],
                    "metadata": action["metadata"],
                    "sla_deadline": action["sla_deadline"]
                }
                
                # Make API call
                async with aiohttp.ClientSession() as session:
                    timeout = aiohttp.ClientTimeout(total=30)
                    async with session.post(full_url, json=payload, timeout=timeout) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            action["execution_log"].append({
                                "timestamp": datetime.now().isoformat(),
                                "event": "api_call_success",
                                "details": f"API call succeeded: {result}"
                            })
                            
                            return {
                                "status": ActionStatus.COMPLETED.value,
                                "external_api_response": result,
                                "external_ticket_id": result.get("ticketId") or result.get("alertId") or result.get("id"),
                                "completed_at": datetime.now().isoformat()
                            }
                        else:
                            error_text = await response.text()
                            raise Exception(f"API call failed with status {response.status}: {error_text}")
                            
            except Exception as e:
                action["execution_log"].append({
                    "timestamp": datetime.now().isoformat(),
                    "event": f"api_call_error_attempt_{attempt + 1}",
                    "details": f"Error: {str(e)}"
                })
                
                if attempt < self.max_retries:
                    # Wait before retry
                    delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                    action["execution_log"].append({
                        "timestamp": datetime.now().isoformat(),
                        "event": "retry_delay",
                        "details": f"Waiting {delay} seconds before retry"
                    })
                    await asyncio.sleep(delay)
                    action["retry_count"] += 1
                    action["status"] = ActionStatus.RETRYING.value
                else:
                    # All retries exhausted
                    return {
                        "status": ActionStatus.FAILED.value,
                        "error_message": str(e),
                        "failed_at": datetime.now().isoformat(),
                        "final_retry_count": self.max_retries
                    }
        
        # Should not reach here
        return {
            "status": ActionStatus.FAILED.value,
            "error_message": "Unexpected execution path",
            "failed_at": datetime.now().isoformat()
        }

    async def _process_internal_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Process internal actions that don't require external API calls"""
        
        action_type = action["action_type"]
        
        action["execution_log"].append({
            "timestamp": datetime.now().isoformat(),
            "event": "internal_processing",
            "details": f"Processing {action_type} action internally"
        })
        
        # Simulate internal processing based on action type
        if action_type == "log":
            # Logging action - always succeeds
            return {
                "status": ActionStatus.COMPLETED.value,
                "internal_log_id": f"LOG_{action['file_id']}_{int(datetime.now().timestamp())}",
                "completed_at": datetime.now().isoformat()
            }
        else:
            # Other internal actions
            return {
                "status": ActionStatus.COMPLETED.value,
                "internal_reference": f"{action_type.upper()}_{action['file_id']}_{int(datetime.now().timestamp())}",
                "completed_at": datetime.now().isoformat()
            }

    async def _log_action_to_storage(self, action: Dict[str, Any]) -> None:
        """Log action to storage system"""
        
        try:
            # Convert action to storage format
            storage_action = {
                "fileId": action["file_id"],
                "actionType": action["action_type"],
                "description": action["description"],
                "priority": action["priority"],
                "status": action["status"],
                "externalApiCall": self.external_apis.get(action.get("api_endpoint", ""), ""),
                "metadata": {
                    **action["metadata"],
                    "execution_log": action["execution_log"],
                    "retry_count": action["retry_count"],
                    "sla_deadline": action["sla_deadline"]
                }
            }
            
            # Add completion data if available
            if "external_ticket_id" in action:
                storage_action["metadata"]["external_ticket_id"] = action["external_ticket_id"]
            if "external_api_response" in action:
                storage_action["metadata"]["external_api_response"] = action["external_api_response"]
            if "error_message" in action:
                storage_action["metadata"]["error_message"] = action["error_message"]
            
            # Make API call to store action
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/actions"
                timeout = aiohttp.ClientTimeout(total=10)
                
                # Use PUT method for action updates if it has an ID, otherwise POST
                method = "POST"  # Always POST for new actions in this implementation
                
                async with session.request(method, url, json=storage_action, timeout=timeout) as response:
                    if response.status not in [200, 201]:
                        error_text = await response.text()
                        logger.error(f"Failed to store action: {response.status} - {error_text}")
                    else:
                        logger.info(f"Action stored successfully for file {action['file_id']}")
                        
        except Exception as e:
            logger.error(f"Error storing action to storage: {e}")
            # Don't raise - storage failure shouldn't stop action execution

    async def _create_fallback_action(self, file_id: int, error_message: str) -> Dict[str, Any]:
        """Create fallback action when routing fails"""
        
        fallback_action = self._create_action(
            file_id=file_id,
            action_type=ActionType.ALERT,
            priority=Priority.MEDIUM,
            description=f"Action routing failed: {error_message}",
            api_endpoint="audit_log",
            sla_hours=4,
            metadata={
                "error_type": "routing_failure",
                "error_message": error_message,
                "fallback_action": True
            }
        )
        
        # Execute the fallback action
        return await self._execute_action(fallback_action)

    async def get_action_status(self, action_id: str) -> Dict[str, Any]:
        """Get status of a specific action"""
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/actions/{action_id}"
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"Action not found: {action_id}"}
        except Exception as e:
            return {"error": f"Failed to get action status: {str(e)}"}

    async def retry_failed_action(self, action_id: str) -> Dict[str, Any]:
        """Retry a failed action"""
        
        # This would typically fetch the action from storage and retry it
        # For now, return a placeholder response
        return {
            "action_id": action_id,
            "status": "retry_initiated",
            "message": "Action retry has been queued"
        }

    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get routing statistics and performance metrics"""
        
        return {
            "total_rules": sum(len(rules) for rules in self.routing_rules.values()),
            "supported_file_types": list(self.routing_rules.keys()),
            "external_apis": list(self.external_apis.keys()),
            "max_retries": self.max_retries,
            "retry_delays": self.retry_delays,
            "last_updated": datetime.now().isoformat()
        }

    async def update_routing_rules(self, new_rules: Dict[str, Any]) -> Dict[str, Any]:
        """Update routing rules (for dynamic configuration)"""
        
        try:
            # Validate new rules structure
            for file_type, rules in new_rules.items():
                if not isinstance(rules, dict):
                    raise ValueError(f"Invalid rules structure for {file_type}")
            
            # Update rules
            self.routing_rules.update(new_rules)
            
            logger.info(f"Routing rules updated: {list(new_rules.keys())}")
            
            return {
                "status": "success",
                "updated_types": list(new_rules.keys()),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to update routing rules: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }

# Global instance
action_router = ActionRouter()
