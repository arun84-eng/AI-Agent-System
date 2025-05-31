#!/usr/bin/env python3
"""
JSON Agent - Specialized JSON/webhook data processing and validation
Validates schema, detects anomalies, and processes structured data
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional, Union
import jsonschema
from jsonschema import validate, ValidationError, Draft7Validator
from datetime import datetime
import re
import hashlib

logger = logging.getLogger(__name__)

class JSONAgent:
    def __init__(self):
        # Common schema patterns for different business contexts
        self.schema_patterns = {
            "rfq": {
                "required_fields": ["rfq_id", "company", "items"],
                "optional_fields": ["deadline", "contact", "requirements"],
                "data_types": {
                    "rfq_id": str,
                    "company": str,
                    "items": list,
                    "deadline": str,
                    "contact": dict
                }
            },
            "webhook": {
                "required_fields": ["timestamp", "event_type", "data"],
                "optional_fields": ["source", "version", "signature"],
                "data_types": {
                    "timestamp": str,
                    "event_type": str,
                    "data": dict
                }
            },
            "transaction": {
                "required_fields": ["transaction_id", "amount", "currency"],
                "optional_fields": ["description", "timestamp", "risk_score"],
                "data_types": {
                    "transaction_id": str,
                    "amount": (int, float),
                    "currency": str,
                    "risk_score": (int, float)
                }
            },
            "customer_data": {
                "required_fields": ["customer_id", "name", "email"],
                "optional_fields": ["phone", "address", "preferences"],
                "data_types": {
                    "customer_id": str,
                    "name": str,
                    "email": str,
                    "phone": str
                }
            }
        }
        
        # Anomaly detection patterns
        self.anomaly_patterns = {
            "suspicious_values": [
                r"<script.*?>.*?</script>",  # XSS attempts
                r"union\s+select",  # SQL injection
                r"javascript:",  # JavaScript injection
                r"data:text/html",  # Data URI schemes
            ],
            "unusual_patterns": [
                r"(.)\1{10,}",  # Repeated characters (potential DoS)
                r"[^\x00-\x7F]{50,}",  # Long non-ASCII strings
                r"\d{16,}",  # Very long numbers
            ],
            "high_risk_keywords": [
                "admin", "root", "password", "secret", "token", "key",
                "hack", "exploit", "payload", "injection"
            ]
        }
        
        # Business logic validation rules
        self.business_rules = {
            "amount_limits": {
                "max_transaction": 100000,
                "suspicious_threshold": 50000
            },
            "email_validation": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "phone_validation": r"^\+?[\d\s\-\(\)]+$",
            "date_formats": [
                r"\d{4}-\d{2}-\d{2}",  # YYYY-MM-DD
                r"\d{2}/\d{2}/\d{4}",  # MM/DD/YYYY
                r"\d{2}-\d{2}-\d{4}"   # DD-MM-YYYY
            ]
        }

    async def process_json(self, file_path: str, content: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process JSON data with comprehensive validation and anomaly detection
        
        Args:
            file_path: Path to the JSON file
            content: Raw JSON content as string
            classification: Classification result from classifier agent
            
        Returns:
            Processed JSON data with validation results and anomaly flags
        """
        try:
            # Parse JSON content
            json_data = json.loads(content)
            
            # Detect JSON structure type
            detected_type = self._detect_json_type(json_data)
            
            # Validate schema
            schema_validation = self._validate_schema(json_data, detected_type)
            
            # Detect anomalies
            anomaly_analysis = self._detect_anomalies(json_data, content)
            
            # Business logic validation
            business_validation = self._validate_business_logic(json_data, detected_type)
            
            # Data quality assessment
            quality_assessment = self._assess_data_quality(json_data)
            
            # Generate summary
            processing_summary = self._generate_processing_summary(
                json_data, schema_validation, anomaly_analysis, business_validation, quality_assessment
            )
            
            result = {
                "json_structure": {
                    "detected_type": detected_type,
                    "record_count": self._count_records(json_data),
                    "data_size": len(content),
                    "nesting_depth": self._calculate_nesting_depth(json_data),
                    "unique_keys": self._extract_unique_keys(json_data)
                },
                "schema_validation": schema_validation,
                "anomaly_analysis": anomaly_analysis,
                "business_validation": business_validation,
                "data_quality": quality_assessment,
                "processing_summary": processing_summary,
                "classification_context": classification,
                "processing_timestamp": datetime.now().isoformat(),
                "risk_assessment": self._assess_overall_risk(anomaly_analysis, business_validation)
            }
            
            logger.info(f"JSON processing completed: {detected_type} - {len(anomaly_analysis.get('anomalies', []))} anomalies detected")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return self._handle_json_parse_error(content, str(e), classification)
        except Exception as e:
            logger.error(f"JSON processing error: {e}")
            return self._fallback_json_processing(content, classification)

    def _detect_json_type(self, data: Any) -> str:
        """Detect the type/purpose of JSON data based on structure and content"""
        
        if isinstance(data, dict):
            keys = set(data.keys())
            
            # Check for RFQ pattern
            if any(key in keys for key in ["rfq_id", "quote_request", "request_for_quote"]):
                return "rfq"
            
            # Check for webhook pattern
            if any(key in keys for key in ["event_type", "webhook", "event", "payload"]):
                return "webhook"
            
            # Check for transaction pattern
            if any(key in keys for key in ["transaction_id", "amount", "payment", "transfer"]):
                return "transaction"
            
            # Check for customer data pattern
            if any(key in keys for key in ["customer_id", "user_id", "client_id"]) and "email" in keys:
                return "customer_data"
            
            # Check for API response pattern
            if any(key in keys for key in ["status", "data", "response", "result"]):
                return "api_response"
            
            # Check for configuration pattern
            if any(key in keys for key in ["config", "settings", "configuration", "options"]):
                return "configuration"
                
        elif isinstance(data, list) and len(data) > 0:
            # Analyze first item to determine array type
            first_item = data[0]
            if isinstance(first_item, dict):
                item_type = self._detect_json_type(first_item)
                return f"{item_type}_array"
        
        return "generic"

    def _validate_schema(self, data: Any, detected_type: str) -> Dict[str, Any]:
        """Validate JSON against expected schema patterns"""
        
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "missing_required": [],
            "type_mismatches": [],
            "schema_score": 100
        }
        
        # Get base type (remove _array suffix)
        base_type = detected_type.replace("_array", "")
        
        if base_type in self.schema_patterns:
            pattern = self.schema_patterns[base_type]
            
            # Handle array data
            if detected_type.endswith("_array") and isinstance(data, list):
                validation_result = self._validate_array_schema(data, pattern)
            elif isinstance(data, dict):
                validation_result = self._validate_object_schema(data, pattern)
            else:
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"Expected object or array for {detected_type}")
                validation_result["schema_score"] = 0
        else:
            # Generic validation for unknown types
            validation_result = self._generic_schema_validation(data)
        
        return validation_result

    def _validate_object_schema(self, data: Dict, pattern: Dict) -> Dict[str, Any]:
        """Validate single object against schema pattern"""
        
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "missing_required": [],
            "type_mismatches": [],
            "schema_score": 100
        }
        
        data_keys = set(data.keys())
        required_fields = set(pattern["required_fields"])
        
        # Check for missing required fields
        missing_required = required_fields - data_keys
        if missing_required:
            validation_result["missing_required"] = list(missing_required)
            validation_result["errors"].extend([f"Missing required field: {field}" for field in missing_required])
            validation_result["is_valid"] = False
        
        # Check data types
        for field, expected_type in pattern["data_types"].items():
            if field in data:
                if not isinstance(data[field], expected_type):
                    validation_result["type_mismatches"].append({
                        "field": field,
                        "expected": str(expected_type),
                        "actual": str(type(data[field]))
                    })
                    validation_result["errors"].append(f"Type mismatch for {field}: expected {expected_type}")
        
        # Check for unexpected fields (warnings only)
        expected_fields = set(pattern["required_fields"] + pattern["optional_fields"])
        unexpected_fields = data_keys - expected_fields
        if unexpected_fields:
            validation_result["warnings"].extend([f"Unexpected field: {field}" for field in unexpected_fields])
        
        # Calculate schema score
        total_errors = len(validation_result["errors"])
        total_warnings = len(validation_result["warnings"])
        validation_result["schema_score"] = max(0, 100 - (total_errors * 20) - (total_warnings * 5))
        
        return validation_result

    def _validate_array_schema(self, data: List, pattern: Dict) -> Dict[str, Any]:
        """Validate array of objects against schema pattern"""
        
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "missing_required": [],
            "type_mismatches": [],
            "schema_score": 100,
            "item_validation_summary": {
                "total_items": len(data),
                "valid_items": 0,
                "invalid_items": 0,
                "validation_details": []
            }
        }
        
        for i, item in enumerate(data):
            if isinstance(item, dict):
                item_validation = self._validate_object_schema(item, pattern)
                validation_result["item_validation_summary"]["validation_details"].append({
                    "index": i,
                    "is_valid": item_validation["is_valid"],
                    "errors": item_validation["errors"]
                })
                
                if item_validation["is_valid"]:
                    validation_result["item_validation_summary"]["valid_items"] += 1
                else:
                    validation_result["item_validation_summary"]["invalid_items"] += 1
                    validation_result["errors"].extend([f"Item {i}: {error}" for error in item_validation["errors"]])
                
                validation_result["warnings"].extend([f"Item {i}: {warning}" for warning in item_validation["warnings"]])
            else:
                validation_result["errors"].append(f"Item {i}: Expected object, got {type(item)}")
                validation_result["item_validation_summary"]["invalid_items"] += 1
        
        # Overall validation status
        if validation_result["item_validation_summary"]["invalid_items"] > 0:
            validation_result["is_valid"] = False
        
        # Calculate schema score based on item validation
        if len(data) > 0:
            valid_ratio = validation_result["item_validation_summary"]["valid_items"] / len(data)
            validation_result["schema_score"] = int(valid_ratio * 100)
        
        return validation_result

    def _generic_schema_validation(self, data: Any) -> Dict[str, Any]:
        """Generic validation for unknown JSON types"""
        
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "missing_required": [],
            "type_mismatches": [],
            "schema_score": 80  # Lower score for unknown types
        }
        
        # Basic structural validation
        if isinstance(data, dict):
            if not data:
                validation_result["warnings"].append("Empty object")
        elif isinstance(data, list):
            if not data:
                validation_result["warnings"].append("Empty array")
            elif len(set(type(item) for item in data)) > 1:
                validation_result["warnings"].append("Mixed types in array")
        
        return validation_result

    def _detect_anomalies(self, data: Any, raw_content: str) -> Dict[str, Any]:
        """Detect various types of anomalies in JSON data"""
        
        anomalies = []
        risk_level = "low"
        
        # Content-based anomaly detection
        content_anomalies = self._detect_content_anomalies(raw_content)
        anomalies.extend(content_anomalies)
        
        # Structure-based anomaly detection
        structure_anomalies = self._detect_structure_anomalies(data)
        anomalies.extend(structure_anomalies)
        
        # Value-based anomaly detection
        value_anomalies = self._detect_value_anomalies(data)
        anomalies.extend(value_anomalies)
        
        # Determine overall risk level
        high_risk_count = len([a for a in anomalies if a.get("severity") == "high"])
        medium_risk_count = len([a for a in anomalies if a.get("severity") == "medium"])
        
        if high_risk_count > 0:
            risk_level = "high"
        elif medium_risk_count > 2 or len(anomalies) > 5:
            risk_level = "medium"
        
        return {
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "risk_level": risk_level,
            "anomaly_categories": self._categorize_anomalies(anomalies),
            "detection_timestamp": datetime.now().isoformat()
        }

    def _detect_content_anomalies(self, content: str) -> List[Dict[str, Any]]:
        """Detect anomalies in raw content"""
        anomalies = []
        
        # Check for suspicious patterns
        for pattern in self.anomaly_patterns["suspicious_values"]:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            if matches:
                anomalies.append({
                    "type": "suspicious_content",
                    "severity": "high",
                    "description": f"Potential security threat detected: {pattern}",
                    "matches": matches[:5]  # Limit matches
                })
        
        # Check for unusual patterns
        for pattern in self.anomaly_patterns["unusual_patterns"]:
            matches = re.findall(pattern, content)
            if matches:
                anomalies.append({
                    "type": "unusual_pattern",
                    "severity": "medium",
                    "description": f"Unusual pattern detected: {pattern}",
                    "match_count": len(matches)
                })
        
        # Check for high-risk keywords
        found_keywords = [keyword for keyword in self.anomaly_patterns["high_risk_keywords"] 
                         if keyword.lower() in content.lower()]
        if found_keywords:
            anomalies.append({
                "type": "high_risk_keywords",
                "severity": "medium",
                "description": "High-risk keywords detected",
                "keywords": found_keywords
            })
        
        return anomalies

    def _detect_structure_anomalies(self, data: Any) -> List[Dict[str, Any]]:
        """Detect structural anomalies in JSON data"""
        anomalies = []
        
        # Check nesting depth
        depth = self._calculate_nesting_depth(data)
        if depth > 10:
            anomalies.append({
                "type": "excessive_nesting",
                "severity": "medium",
                "description": f"Excessive nesting depth: {depth} levels",
                "depth": depth
            })
        
        # Check for very large arrays
        if isinstance(data, list) and len(data) > 10000:
            anomalies.append({
                "type": "large_array",
                "severity": "medium",
                "description": f"Very large array: {len(data)} items",
                "size": len(data)
            })
        
        # Check for inconsistent array schemas
        if isinstance(data, list) and len(data) > 1:
            inconsistencies = self._check_array_consistency(data)
            if inconsistencies:
                anomalies.append({
                    "type": "inconsistent_schema",
                    "severity": "low",
                    "description": "Inconsistent object schemas in array",
                    "inconsistencies": inconsistencies
                })
        
        return anomalies

    def _detect_value_anomalies(self, data: Any) -> List[Dict[str, Any]]:
        """Detect anomalies in data values"""
        anomalies = []
        
        def check_values(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # Check for null/empty values in important fields
                    if key in ["id", "email", "amount", "timestamp"] and (value is None or value == ""):
                        anomalies.append({
                            "type": "null_important_field",
                            "severity": "medium",
                            "description": f"Null/empty value in important field: {current_path}",
                            "field": current_path
                        })
                    
                    # Check for suspiciously long strings
                    if isinstance(value, str) and len(value) > 1000:
                        anomalies.append({
                            "type": "suspicious_long_string",
                            "severity": "low",
                            "description": f"Unusually long string in field: {current_path}",
                            "length": len(value),
                            "field": current_path
                        })
                    
                    # Recursively check nested objects
                    check_values(value, current_path)
                    
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_values(item, f"{path}[{i}]")
        
        check_values(data)
        return anomalies

    def _validate_business_logic(self, data: Any, detected_type: str) -> Dict[str, Any]:
        """Validate business logic rules"""
        
        validation_result = {
            "is_valid": True,
            "violations": [],
            "warnings": [],
            "business_score": 100
        }
        
        def validate_values(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # Validate email addresses
                    if "email" in key.lower() and isinstance(value, str):
                        if not re.match(self.business_rules["email_validation"], value):
                            validation_result["violations"].append({
                                "rule": "email_format",
                                "field": current_path,
                                "value": value,
                                "description": "Invalid email format"
                            })
                    
                    # Validate amounts
                    if "amount" in key.lower() and isinstance(value, (int, float)):
                        if value > self.business_rules["amount_limits"]["max_transaction"]:
                            validation_result["violations"].append({
                                "rule": "amount_limit",
                                "field": current_path,
                                "value": value,
                                "description": f"Amount exceeds maximum limit: {value}"
                            })
                        elif value > self.business_rules["amount_limits"]["suspicious_threshold"]:
                            validation_result["warnings"].append({
                                "rule": "suspicious_amount",
                                "field": current_path,
                                "value": value,
                                "description": f"Amount above suspicious threshold: {value}"
                            })
                    
                    # Validate phone numbers
                    if "phone" in key.lower() and isinstance(value, str):
                        if not re.match(self.business_rules["phone_validation"], value):
                            validation_result["warnings"].append({
                                "rule": "phone_format",
                                "field": current_path,
                                "value": value,
                                "description": "Potentially invalid phone format"
                            })
                    
                    # Recursively validate nested objects
                    validate_values(value, current_path)
                    
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    validate_values(item, f"{path}[{i}]")
        
        validate_values(data)
        
        # Calculate business score
        violation_count = len(validation_result["violations"])
        warning_count = len(validation_result["warnings"])
        validation_result["business_score"] = max(0, 100 - (violation_count * 25) - (warning_count * 10))
        
        if violation_count > 0:
            validation_result["is_valid"] = False
        
        return validation_result

    def _assess_data_quality(self, data: Any) -> Dict[str, Any]:
        """Assess overall data quality"""
        
        metrics = {
            "completeness": self._assess_completeness(data),
            "consistency": self._assess_consistency(data),
            "validity": self._assess_validity(data),
            "uniqueness": self._assess_uniqueness(data)
        }
        
        # Calculate overall quality score
        overall_score = sum(metrics.values()) / len(metrics)
        
        quality_level = "high" if overall_score >= 80 else "medium" if overall_score >= 60 else "low"
        
        return {
            "metrics": metrics,
            "overall_score": round(overall_score, 2),
            "quality_level": quality_level,
            "recommendations": self._generate_quality_recommendations(metrics)
        }

    def _assess_completeness(self, data: Any) -> float:
        """Assess data completeness (percentage of non-null/non-empty values)"""
        total_fields = 0
        complete_fields = 0
        
        def count_fields(obj):
            nonlocal total_fields, complete_fields
            
            if isinstance(obj, dict):
                for value in obj.values():
                    total_fields += 1
                    if value is not None and value != "":
                        complete_fields += 1
                    if isinstance(value, (dict, list)):
                        count_fields(value)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        count_fields(item)
        
        count_fields(data)
        return (complete_fields / max(total_fields, 1)) * 100

    def _assess_consistency(self, data: Any) -> float:
        """Assess data consistency across similar records"""
        if isinstance(data, list) and len(data) > 1:
            inconsistencies = self._check_array_consistency(data)
            consistency_score = max(0, 100 - len(inconsistencies) * 10)
            return consistency_score
        return 100  # Single records are considered consistent

    def _assess_validity(self, data: Any) -> float:
        """Assess data validity based on format and type checks"""
        # This would integrate with the business validation results
        # For now, return a basic score
        return 85  # Placeholder

    def _assess_uniqueness(self, data: Any) -> float:
        """Assess data uniqueness (check for duplicates)"""
        if isinstance(data, list):
            # Check for duplicate records based on hash
            hashes = []
            for item in data:
                if isinstance(item, dict):
                    item_hash = hashlib.md5(json.dumps(item, sort_keys=True).encode()).hexdigest()
                    hashes.append(item_hash)
            
            if hashes:
                unique_ratio = len(set(hashes)) / len(hashes)
                return unique_ratio * 100
        
        return 100  # Single records are considered unique

    def _check_array_consistency(self, data: List) -> List[str]:
        """Check consistency of objects in an array"""
        if not data or len(data) < 2:
            return []
        
        inconsistencies = []
        
        # Get the schema of the first item
        if isinstance(data[0], dict):
            reference_keys = set(data[0].keys())
            reference_types = {key: type(value) for key, value in data[0].items()}
            
            for i, item in enumerate(data[1:], 1):
                if isinstance(item, dict):
                    item_keys = set(item.keys())
                    
                    # Check for missing keys
                    missing_keys = reference_keys - item_keys
                    if missing_keys:
                        inconsistencies.append(f"Item {i}: Missing keys {missing_keys}")
                    
                    # Check for extra keys
                    extra_keys = item_keys - reference_keys
                    if extra_keys:
                        inconsistencies.append(f"Item {i}: Extra keys {extra_keys}")
                    
                    # Check for type mismatches
                    for key in item_keys & reference_keys:
                        if type(item[key]) != reference_types[key]:
                            inconsistencies.append(f"Item {i}: Type mismatch for {key}")
                else:
                    inconsistencies.append(f"Item {i}: Expected dict, got {type(item)}")
        
        return inconsistencies

    def _generate_quality_recommendations(self, metrics: Dict[str, float]) -> List[str]:
        """Generate recommendations based on quality metrics"""
        recommendations = []
        
        if metrics["completeness"] < 80:
            recommendations.append("Consider adding validation for required fields to improve completeness")
        
        if metrics["consistency"] < 70:
            recommendations.append("Review data schema consistency across records")
        
        if metrics["validity"] < 75:
            recommendations.append("Implement stricter data format validation")
        
        if metrics["uniqueness"] < 90:
            recommendations.append("Check for and remove duplicate records")
        
        return recommendations

    def _generate_processing_summary(self, data: Any, schema_validation: Dict, anomaly_analysis: Dict, 
                                   business_validation: Dict, quality_assessment: Dict) -> Dict[str, Any]:
        """Generate comprehensive processing summary"""
        
        # Determine overall status
        overall_status = "success"
        if not schema_validation["is_valid"] or not business_validation["is_valid"]:
            overall_status = "failed"
        elif anomaly_analysis["risk_level"] == "high" or anomaly_analysis["anomaly_count"] > 5:
            overall_status = "warning"
        
        # Generate recommendations
        recommendations = []
        
        if schema_validation["schema_score"] < 80:
            recommendations.append("Review and fix schema validation errors")
        
        if anomaly_analysis["anomaly_count"] > 0:
            recommendations.append(f"Investigate {anomaly_analysis['anomaly_count']} detected anomalies")
        
        if business_validation["violations"]:
            recommendations.append("Address business rule violations")
        
        if quality_assessment["quality_level"] == "low":
            recommendations.extend(quality_assessment["recommendations"])
        
        return {
            "overall_status": overall_status,
            "processing_score": self._calculate_processing_score(schema_validation, anomaly_analysis, business_validation, quality_assessment),
            "recommendations": recommendations,
            "key_findings": self._extract_key_findings(data, schema_validation, anomaly_analysis, business_validation),
            "next_actions": self._suggest_next_actions(overall_status, anomaly_analysis, business_validation)
        }

    def _calculate_processing_score(self, schema_validation: Dict, anomaly_analysis: Dict, 
                                  business_validation: Dict, quality_assessment: Dict) -> float:
        """Calculate overall processing score"""
        
        scores = {
            "schema": schema_validation["schema_score"],
            "business": business_validation["business_score"],
            "quality": quality_assessment["overall_score"],
            "anomaly": max(0, 100 - (anomaly_analysis["anomaly_count"] * 10))
        }
        
        # Weighted average
        weights = {"schema": 0.3, "business": 0.3, "quality": 0.2, "anomaly": 0.2}
        weighted_score = sum(scores[key] * weights[key] for key in scores)
        
        return round(weighted_score, 2)

    def _extract_key_findings(self, data: Any, schema_validation: Dict, anomaly_analysis: Dict, business_validation: Dict) -> List[str]:
        """Extract key findings from processing results"""
        findings = []
        
        # Record count
        record_count = self._count_records(data)
        findings.append(f"Processed {record_count} record(s)")
        
        # Schema findings
        if schema_validation["missing_required"]:
            findings.append(f"Missing required fields: {', '.join(schema_validation['missing_required'])}")
        
        # Anomaly findings
        if anomaly_analysis["anomaly_count"] > 0:
            findings.append(f"Detected {anomaly_analysis['anomaly_count']} anomalies (risk level: {anomaly_analysis['risk_level']})")
        
        # Business rule findings
        if business_validation["violations"]:
            findings.append(f"Found {len(business_validation['violations'])} business rule violations")
        
        return findings

    def _suggest_next_actions(self, status: str, anomaly_analysis: Dict, business_validation: Dict) -> List[str]:
        """Suggest next actions based on processing results"""
        actions = []
        
        if status == "failed":
            actions.append("Fix validation errors before proceeding")
        
        if anomaly_analysis["risk_level"] == "high":
            actions.append("Escalate to security team for review")
        elif anomaly_analysis["risk_level"] == "medium":
            actions.append("Flag for manual review")
        
        if business_validation["violations"]:
            actions.append("Contact data source to correct business rule violations")
        
        if not actions:
            actions.append("Proceed with standard processing workflow")
        
        return actions

    def _assess_overall_risk(self, anomaly_analysis: Dict, business_validation: Dict) -> Dict[str, Any]:
        """Assess overall risk level and provide risk summary"""
        
        risk_factors = []
        risk_score = 0
        
        # Anomaly-based risk
        anomaly_risk = anomaly_analysis.get("risk_level", "low")
        if anomaly_risk == "high":
            risk_score += 40
            risk_factors.append("High-risk anomalies detected")
        elif anomaly_risk == "medium":
            risk_score += 20
            risk_factors.append("Medium-risk anomalies detected")
        
        # Business validation risk
        violation_count = len(business_validation.get("violations", []))
        if violation_count > 0:
            risk_score += violation_count * 15
            risk_factors.append(f"{violation_count} business rule violations")
        
        # Determine overall risk level
        if risk_score >= 50:
            overall_risk = "high"
        elif risk_score >= 25:
            overall_risk = "medium"
        else:
            overall_risk = "low"
        
        return {
            "risk_level": overall_risk,
            "risk_score": min(risk_score, 100),
            "risk_factors": risk_factors,
            "requires_escalation": overall_risk == "high",
            "recommended_action": self._get_risk_action(overall_risk)
        }

    def _get_risk_action(self, risk_level: str) -> str:
        """Get recommended action based on risk level"""
        actions = {
            "high": "Immediate escalation and manual review required",
            "medium": "Flag for priority review within 4 hours",
            "low": "Continue with standard processing"
        }
        return actions.get(risk_level, "Standard processing")

    def _count_records(self, data: Any) -> int:
        """Count the number of records in JSON data"""
        if isinstance(data, list):
            return len(data)
        elif isinstance(data, dict):
            return 1
        else:
            return 1

    def _calculate_nesting_depth(self, data: Any, depth: int = 0) -> int:
        """Calculate maximum nesting depth of JSON structure"""
        if isinstance(data, dict):
            if not data:
                return depth
            return max(self._calculate_nesting_depth(value, depth + 1) for value in data.values())
        elif isinstance(data, list):
            if not data:
                return depth
            return max(self._calculate_nesting_depth(item, depth + 1) for item in data)
        else:
            return depth

    def _extract_unique_keys(self, data: Any) -> List[str]:
        """Extract all unique keys from JSON structure"""
        keys = set()
        
        def extract_keys(obj):
            if isinstance(obj, dict):
                keys.update(obj.keys())
                for value in obj.values():
                    extract_keys(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_keys(item)
        
        extract_keys(data)
        return sorted(list(keys))

    def _categorize_anomalies(self, anomalies: List[Dict]) -> Dict[str, int]:
        """Categorize anomalies by type"""
        categories = {}
        for anomaly in anomalies:
            anomaly_type = anomaly.get("type", "unknown")
            categories[anomaly_type] = categories.get(anomaly_type, 0) + 1
        return categories

    def _handle_json_parse_error(self, content: str, error: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JSON parsing errors"""
        return {
            "json_structure": {
                "detected_type": "invalid_json",
                "record_count": 0,
                "data_size": len(content),
                "parse_error": error
            },
            "schema_validation": {
                "is_valid": False,
                "errors": [f"JSON parsing failed: {error}"],
                "schema_score": 0
            },
            "anomaly_analysis": {
                "anomalies": [{"type": "parse_error", "severity": "high", "description": "Invalid JSON format"}],
                "anomaly_count": 1,
                "risk_level": "high"
            },
            "business_validation": {"is_valid": False, "violations": [], "business_score": 0},
            "data_quality": {"overall_score": 0, "quality_level": "low"},
            "processing_summary": {
                "overall_status": "failed",
                "processing_score": 0,
                "recommendations": ["Fix JSON syntax errors", "Validate JSON format before processing"],
                "key_findings": ["Invalid JSON format detected"],
                "next_actions": ["Contact data source to provide valid JSON"]
            },
            "classification_context": classification,
            "processing_timestamp": datetime.now().isoformat(),
            "risk_assessment": {
                "risk_level": "high",
                "risk_score": 100,
                "requires_escalation": True,
                "recommended_action": "Fix JSON format before processing"
            }
        }

    def _fallback_json_processing(self, content: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback processing when main processing fails"""
        return {
            "json_structure": {
                "detected_type": "unknown",
                "record_count": 0,
                "data_size": len(content),
                "processing_error": "Processing failed"
            },
            "schema_validation": {"is_valid": False, "errors": ["Processing failed"], "schema_score": 0},
            "anomaly_analysis": {"anomalies": [], "anomaly_count": 0, "risk_level": "unknown"},
            "business_validation": {"is_valid": False, "violations": [], "business_score": 0},
            "data_quality": {"overall_score": 0, "quality_level": "unknown"},
            "processing_summary": {
                "overall_status": "failed",
                "processing_score": 0,
                "recommendations": ["Review processing logs", "Contact system administrator"],
                "key_findings": ["Processing failed due to system error"],
                "next_actions": ["Retry processing or escalate to technical team"]
            },
            "classification_context": classification,
            "processing_timestamp": datetime.now().isoformat(),
            "risk_assessment": {
                "risk_level": "medium",
                "risk_score": 50,
                "requires_escalation": False,
                "recommended_action": "Retry processing"
            },
            "processing_status": "fallback_mode"
        }

# Global instance
json_agent = JSONAgent()
