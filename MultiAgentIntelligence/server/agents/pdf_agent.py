#!/usr/bin/env python3
"""
PDF Agent - Specialized PDF document processing and compliance checking
Extracts text, analyzes content, detects compliance requirements, and flags high-value items
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
import aiohttp
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

class PDFAgent:
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        self.model = "gpt-3.5-turbo"
        
        # Compliance keywords and patterns
        self.compliance_patterns = {
            "GDPR": [
                "gdpr", "general data protection regulation", "data protection",
                "personal data", "data subject", "privacy policy", "consent",
                "data processing", "data controller", "data processor"
            ],
            "HIPAA": [
                "hipaa", "health insurance portability", "phi", "protected health information",
                "healthcare", "medical records", "patient data", "health information"
            ],
            "SOX": [
                "sarbanes oxley", "sox", "financial reporting", "internal controls",
                "financial statements", "audit", "compliance certification"
            ],
            "PCI": [
                "pci dss", "payment card industry", "cardholder data", "credit card",
                "payment processing", "card data security"
            ],
            "FDA": [
                "fda", "food and drug administration", "medical device", "pharmaceutical",
                "clinical trial", "drug approval", "medical regulation"
            ],
            "ISO": [
                "iso 27001", "iso certification", "information security management",
                "quality management", "security standards"
            ]
        }
        
        # Financial patterns for invoice/amount detection
        self.financial_patterns = {
            "currency_symbols": ["$", "€", "£", "¥", "₹", "CAD", "USD", "EUR", "GBP"],
            "amount_patterns": [
                r"\$[\d,]+\.?\d*",  # $1,234.56
                r"USD\s*[\d,]+\.?\d*",  # USD 1234.56
                r"€[\d,]+\.?\d*",  # €1,234.56
                r"£[\d,]+\.?\d*",  # £1,234.56
                r"[\d,]+\.?\d*\s*(?:dollars?|USD|€|euros?)",  # 1234.56 dollars
                r"(?:total|amount|sum|invoice|bill|payment|cost|price)[\s:]*\$?[\d,]+\.?\d*"
            ],
            "invoice_keywords": [
                "invoice", "bill", "payment", "amount due", "total", "subtotal",
                "tax", "discount", "balance", "charges", "fees"
            ]
        }
        
        # Document type patterns
        self.document_types = {
            "invoice": ["invoice", "bill", "payment request", "statement", "receipt"],
            "contract": ["contract", "agreement", "terms", "conditions", "obligations"],
            "policy": ["policy", "procedure", "guidelines", "standards", "regulations"],
            "report": ["report", "analysis", "summary", "findings", "assessment"],
            "certificate": ["certificate", "certification", "accreditation", "license"]
        }
        
        # Risk indicators
        self.risk_indicators = {
            "high_value": 10000,  # Amount threshold for high-value flagging
            "suspicious_threshold": 50000,  # Suspicious amount threshold
            "compliance_keywords": ["audit", "violation", "non-compliance", "breach", "penalty"]
        }

    async def process_pdf(self, file_path: str, content: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process PDF with comprehensive text extraction and analysis
        
        Args:
            file_path: Path to the PDF file
            content: Extracted text content from PDF
            classification: Classification result from classifier agent
            
        Returns:
            Processed PDF data with extracted information and compliance flags
        """
        try:
            # Extract document metadata
            document_metadata = self._extract_document_metadata(file_path, content)
            
            # Detect document type
            document_type = self._detect_document_type(content, classification)
            
            # Extract financial information
            financial_info = await self._extract_financial_information(content)
            
            # Check compliance requirements
            compliance_analysis = self._analyze_compliance(content)
            
            # Extract entities and key information
            extracted_entities = await self._extract_entities(content, document_type)
            
            # Analyze document structure
            structure_analysis = self._analyze_document_structure(content)
            
            # Risk assessment
            risk_assessment = self._assess_document_risk(financial_info, compliance_analysis, document_type, content)
            
            # Generate processing summary
            processing_summary = self._generate_processing_summary(
                document_metadata, financial_info, compliance_analysis, risk_assessment
            )
            
            result = {
                "document_metadata": document_metadata,
                "document_type": document_type,
                "financial_information": financial_info,
                "compliance_analysis": compliance_analysis,
                "extracted_entities": extracted_entities,
                "structure_analysis": structure_analysis,
                "risk_assessment": risk_assessment,
                "processing_summary": processing_summary,
                "classification_context": classification,
                "processing_timestamp": datetime.now().isoformat(),
                "flagging_recommendation": self._determine_flagging_action(risk_assessment, financial_info, compliance_analysis)
            }
            
            logger.info(f"PDF processing completed: {document_type.get('primary_type', 'unknown')} - Risk: {risk_assessment.get('risk_level', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"PDF processing error: {e}")
            return self._fallback_pdf_processing(content, classification)

    def _extract_document_metadata(self, file_path: str, content: str) -> Dict[str, Any]:
        """Extract basic document metadata"""
        
        metadata = {
            "file_path": file_path,
            "content_length": len(content),
            "estimated_pages": self._estimate_page_count(content),
            "word_count": len(content.split()) if content else 0,
            "character_count": len(content),
            "content_hash": hashlib.md5(content.encode('utf-8', errors='ignore')).hexdigest(),
            "extracted_at": datetime.now().isoformat()
        }
        
        # Try to extract actual page count using PyPDF2 if available
        try:
            import PyPDF2
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                metadata["actual_pages"] = len(reader.pages)
                
                # Extract PDF metadata if available
                if reader.metadata:
                    pdf_info = reader.metadata
                    metadata["pdf_metadata"] = {
                        "title": pdf_info.get("/Title", ""),
                        "author": pdf_info.get("/Author", ""),
                        "subject": pdf_info.get("/Subject", ""),
                        "creator": pdf_info.get("/Creator", ""),
                        "producer": pdf_info.get("/Producer", ""),
                        "creation_date": str(pdf_info.get("/CreationDate", "")),
                        "modification_date": str(pdf_info.get("/ModDate", ""))
                    }
        except Exception as e:
            logger.warning(f"Could not extract PDF metadata: {e}")
            metadata["actual_pages"] = metadata["estimated_pages"]
        
        return metadata

    def _estimate_page_count(self, content: str) -> int:
        """Estimate page count based on content length"""
        if not content:
            return 0
        
        # Rough estimation: ~500 words per page
        words_per_page = 500
        word_count = len(content.split())
        estimated_pages = max(1, word_count // words_per_page)
        
        return estimated_pages

    def _detect_document_type(self, content: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """Detect specific document type based on content analysis"""
        
        content_lower = content.lower()
        
        # Score each document type
        type_scores = {}
        for doc_type, keywords in self.document_types.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                type_scores[doc_type] = score
        
        # Determine primary type
        primary_type = max(type_scores, key=type_scores.get) if type_scores else "unknown"
        
        # Use classification context if available
        business_intent = classification.get("business_intent", "").lower()
        if business_intent in ["invoice", "contract", "regulation"]:
            primary_type = business_intent
        
        # Additional analysis for specific types
        type_confidence = type_scores.get(primary_type, 0) / max(1, len(self.document_types[primary_type]) * 0.5)
        type_confidence = min(type_confidence, 1.0)
        
        return {
            "primary_type": primary_type,
            "confidence": type_confidence,
            "type_scores": type_scores,
            "classification_business_intent": classification.get("business_intent", ""),
            "detected_patterns": self._get_type_specific_patterns(content_lower, primary_type)
        }

    def _get_type_specific_patterns(self, content: str, doc_type: str) -> List[str]:
        """Get specific patterns found for document type"""
        patterns = []
        
        if doc_type == "invoice":
            if "invoice number" in content or "invoice #" in content:
                patterns.append("invoice_number_found")
            if "due date" in content:
                patterns.append("due_date_found")
            if "tax" in content:
                patterns.append("tax_information_found")
        elif doc_type == "contract":
            if "whereas" in content:
                patterns.append("contract_preamble")
            if "signature" in content:
                patterns.append("signature_block")
            if "effective date" in content:
                patterns.append("effective_date")
        elif doc_type == "policy":
            if "section" in content and "subsection" in content:
                patterns.append("structured_policy")
            if "compliance" in content:
                patterns.append("compliance_policy")
        
        return patterns

    async def _extract_financial_information(self, content: str) -> Dict[str, Any]:
        """Extract financial information and amounts from document"""
        
        financial_info = {
            "amounts_found": [],
            "currency_detected": [],
            "invoice_numbers": [],
            "dates": [],
            "financial_keywords": [],
            "largest_amount": 0.0,
            "total_amounts": [],
            "tax_information": [],
            "payment_terms": []
        }
        
        # Extract amounts using patterns
        for pattern in self.financial_patterns["amount_patterns"]:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Clean and parse amount
                cleaned_amount = self._parse_amount(match)
                if cleaned_amount > 0:
                    financial_info["amounts_found"].append({
                        "raw_text": match,
                        "parsed_amount": cleaned_amount,
                        "currency": self._detect_currency(match)
                    })
        
        # Extract invoice numbers
        invoice_patterns = [
            r"invoice\s*#?\s*:?\s*([A-Z0-9\-]+)",
            r"inv\s*#?\s*:?\s*([A-Z0-9\-]+)",
            r"bill\s*#?\s*:?\s*([A-Z0-9\-]+)"
        ]
        
        for pattern in invoice_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            financial_info["invoice_numbers"].extend(matches)
        
        # Extract dates
        date_patterns = [
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b"
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            financial_info["dates"].extend(matches)
        
        # Find financial keywords
        found_keywords = [keyword for keyword in self.financial_patterns["invoice_keywords"] 
                         if keyword.lower() in content.lower()]
        financial_info["financial_keywords"] = found_keywords
        
        # Calculate totals
        amounts = [item["parsed_amount"] for item in financial_info["amounts_found"]]
        if amounts:
            financial_info["largest_amount"] = max(amounts)
            financial_info["total_amounts"] = amounts
        
        # Extract tax information
        tax_patterns = [
            r"tax[\s:]*\$?[\d,]+\.?\d*",
            r"vat[\s:]*\$?[\d,]+\.?\d*",
            r"sales tax[\s:]*\$?[\d,]+\.?\d*"
        ]
        
        for pattern in tax_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            financial_info["tax_information"].extend(matches)
        
        # Extract payment terms
        payment_terms_patterns = [
            r"net\s+\d+\s+days?",
            r"due\s+(?:in\s+)?\d+\s+days?",
            r"payment\s+terms?[\s:]+[^.]+\."
        ]
        
        for pattern in payment_terms_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            financial_info["payment_terms"].extend(matches)
        
        return financial_info

    def _parse_amount(self, amount_text: str) -> float:
        """Parse amount from text and return float value"""
        try:
            # Remove currency symbols and commas
            cleaned = re.sub(r'[^\d.]', '', amount_text)
            if cleaned:
                return float(cleaned)
        except ValueError:
            pass
        return 0.0

    def _detect_currency(self, amount_text: str) -> str:
        """Detect currency from amount text"""
        for symbol in self.financial_patterns["currency_symbols"]:
            if symbol in amount_text:
                return symbol
        return "USD"  # Default

    def _analyze_compliance(self, content: str) -> Dict[str, Any]:
        """Analyze document for compliance requirements and regulations"""
        
        compliance_analysis = {
            "regulations_detected": [],
            "compliance_score": 0,
            "risk_level": "low",
            "compliance_keywords_found": [],
            "regulatory_requirements": [],
            "compliance_gaps": [],
            "recommended_actions": []
        }
        
        content_lower = content.lower()
        total_score = 0
        
        # Check for each compliance framework
        for regulation, keywords in self.compliance_patterns.items():
            found_keywords = [keyword for keyword in keywords if keyword in content_lower]
            
            if found_keywords:
                compliance_analysis["regulations_detected"].append({
                    "regulation": regulation,
                    "keywords_found": found_keywords,
                    "keyword_count": len(found_keywords),
                    "confidence": min(len(found_keywords) / len(keywords), 1.0)
                })
                total_score += len(found_keywords)
        
        # Calculate compliance score
        if compliance_analysis["regulations_detected"]:
            compliance_analysis["compliance_score"] = min(total_score * 10, 100)
            
            # Determine risk level
            if total_score >= 5:
                compliance_analysis["risk_level"] = "high"
            elif total_score >= 2:
                compliance_analysis["risk_level"] = "medium"
            else:
                compliance_analysis["risk_level"] = "low"
        
        # Check for compliance-related keywords
        compliance_keywords = self.risk_indicators["compliance_keywords"]
        found_compliance_keywords = [keyword for keyword in compliance_keywords 
                                   if keyword in content_lower]
        compliance_analysis["compliance_keywords_found"] = found_compliance_keywords
        
        # Generate regulatory requirements based on detected regulations
        for detected in compliance_analysis["regulations_detected"]:
            regulation = detected["regulation"]
            requirements = self._get_regulatory_requirements(regulation)
            compliance_analysis["regulatory_requirements"].extend(requirements)
        
        # Generate recommendations
        compliance_analysis["recommended_actions"] = self._generate_compliance_recommendations(
            compliance_analysis["regulations_detected"],
            found_compliance_keywords
        )
        
        return compliance_analysis

    def _get_regulatory_requirements(self, regulation: str) -> List[str]:
        """Get specific requirements for detected regulations"""
        requirements_map = {
            "GDPR": [
                "Ensure data subject consent is documented",
                "Implement data retention policies",
                "Establish data breach notification procedures",
                "Conduct privacy impact assessments"
            ],
            "HIPAA": [
                "Secure transmission of health information",
                "Implement access controls for PHI",
                "Conduct regular risk assessments",
                "Train staff on HIPAA compliance"
            ],
            "SOX": [
                "Maintain accurate financial records",
                "Implement internal controls testing",
                "Ensure management certification",
                "Conduct regular compliance audits"
            ],
            "PCI": [
                "Secure cardholder data storage",
                "Implement strong access controls",
                "Regular security testing",
                "Maintain secure networks"
            ],
            "FDA": [
                "Follow FDA guidelines for documentation",
                "Implement quality management systems",
                "Conduct regular compliance reviews",
                "Maintain traceability records"
            ]
        }
        
        return requirements_map.get(regulation, [])

    def _generate_compliance_recommendations(self, detected_regulations: List[Dict], 
                                           compliance_keywords: List[str]) -> List[str]:
        """Generate compliance recommendations"""
        recommendations = []
        
        if detected_regulations:
            recommendations.append("Review document for compliance with detected regulations")
            recommendations.append("Consult with legal/compliance team")
            
            for reg_info in detected_regulations:
                regulation = reg_info["regulation"]
                if reg_info["confidence"] > 0.7:
                    recommendations.append(f"Implement {regulation} compliance measures")
        
        if compliance_keywords:
            recommendations.append("Address compliance issues mentioned in document")
            recommendations.append("Conduct compliance gap analysis")
        
        return recommendations

    async def _extract_entities(self, content: str, document_type: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key entities based on document type"""
        
        entities = {
            "organizations": [],
            "people": [],
            "addresses": [],
            "phone_numbers": [],
            "email_addresses": [],
            "account_numbers": [],
            "reference_numbers": [],
            "dates": [],
            "amounts": [],
            "urls": []
        }
        
        # Extract email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        entities["email_addresses"] = re.findall(email_pattern, content)
        
        # Extract phone numbers
        phone_patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            r'\(\d{3}\)\s*\d{3}[-.]?\d{4}',
            r'\+\d{1,3}\s*\d{3,4}[-.]?\d{3,4}[-.]?\d{3,4}'
        ]
        
        for pattern in phone_patterns:
            entities["phone_numbers"].extend(re.findall(pattern, content))
        
        # Extract account/reference numbers
        account_patterns = [
            r'(?:account|acct|ref|reference)[\s#]*:?\s*([A-Z0-9\-]+)',
            r'(?:po|purchase order)[\s#]*:?\s*([A-Z0-9\-]+)',
            r'(?:contract|agreement)[\s#]*:?\s*([A-Z0-9\-]+)'
        ]
        
        for pattern in account_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            entities["reference_numbers"].extend(matches)
        
        # Extract URLs
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        entities["urls"] = re.findall(url_pattern, content)
        
        # Extract addresses (basic pattern)
        address_pattern = r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)'
        entities["addresses"] = re.findall(address_pattern, content, re.IGNORECASE)
        
        # Document-type specific extraction
        if document_type.get("primary_type") == "invoice":
            entities.update(self._extract_invoice_entities(content))
        elif document_type.get("primary_type") == "contract":
            entities.update(self._extract_contract_entities(content))
        
        # Clean up empty lists
        entities = {k: list(set(v)) for k, v in entities.items() if v}
        
        return entities

    def _extract_invoice_entities(self, content: str) -> Dict[str, List[str]]:
        """Extract invoice-specific entities"""
        invoice_entities = {
            "vendor_info": [],
            "customer_info": [],
            "invoice_numbers": [],
            "po_numbers": []
        }
        
        # Extract vendor/customer blocks (simplified)
        vendor_patterns = [
            r'(?:bill to|invoice to)[\s:]*([^\n]+(?:\n[^\n]+)*?)(?:\n\s*\n|$)',
            r'(?:vendor|supplier)[\s:]*([^\n]+)'
        ]
        
        for pattern in vendor_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            invoice_entities["vendor_info"].extend(matches)
        
        return invoice_entities

    def _extract_contract_entities(self, content: str) -> Dict[str, List[str]]:
        """Extract contract-specific entities"""
        contract_entities = {
            "parties": [],
            "effective_dates": [],
            "termination_dates": [],
            "contract_terms": []
        }
        
        # Extract contract parties
        party_patterns = [
            r'between\s+([^,\n]+)\s+and\s+([^,\n]+)',
            r'party of the first part[\s:]*([^\n]+)',
            r'party of the second part[\s:]*([^\n]+)'
        ]
        
        for pattern in party_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                if isinstance(matches[0], tuple):
                    contract_entities["parties"].extend(matches[0])
                else:
                    contract_entities["parties"].extend(matches)
        
        return contract_entities

    def _analyze_document_structure(self, content: str) -> Dict[str, Any]:
        """Analyze document structure and formatting"""
        
        structure = {
            "has_headers": bool(re.search(r'^[A-Z\s]{10,}$', content, re.MULTILINE)),
            "has_sections": bool(re.search(r'(?:section|chapter)\s+\d+', content, re.IGNORECASE)),
            "has_bullet_points": bool(re.search(r'^\s*[•\-\*]\s+', content, re.MULTILINE)),
            "has_numbered_lists": bool(re.search(r'^\s*\d+\.\s+', content, re.MULTILINE)),
            "has_tables": bool(re.search(r'\|\s*[^\|]+\s*\|', content)),
            "paragraph_count": len(re.split(r'\n\s*\n', content)),
            "line_count": len(content.split('\n')),
            "average_line_length": sum(len(line) for line in content.split('\n')) / max(len(content.split('\n')), 1),
            "formatting_quality": "good"  # Placeholder
        }
        
        # Assess formatting quality
        quality_score = 0
        if structure["has_headers"]:
            quality_score += 20
        if structure["has_sections"]:
            quality_score += 20
        if structure["has_bullet_points"] or structure["has_numbered_lists"]:
            quality_score += 15
        if structure["paragraph_count"] > 1:
            quality_score += 15
        if 50 < structure["average_line_length"] < 120:
            quality_score += 30
        
        if quality_score >= 80:
            structure["formatting_quality"] = "excellent"
        elif quality_score >= 60:
            structure["formatting_quality"] = "good"
        elif quality_score >= 40:
            structure["formatting_quality"] = "fair"
        else:
            structure["formatting_quality"] = "poor"
        
        structure["quality_score"] = quality_score
        
        return structure

    def _assess_document_risk(self, financial_info: Dict[str, Any], compliance_analysis: Dict[str, Any], 
                            document_type: Dict[str, Any], content: str) -> Dict[str, Any]:
        """Assess overall document risk level"""
        
        risk_factors = []
        risk_score = 0
        
        # Financial risk assessment
        largest_amount = financial_info.get("largest_amount", 0)
        if largest_amount > self.risk_indicators["suspicious_threshold"]:
            risk_score += 40
            risk_factors.append(f"Extremely high amount detected: ${largest_amount:,.2f}")
        elif largest_amount > self.risk_indicators["high_value"]:
            risk_score += 25
            risk_factors.append(f"High-value amount detected: ${largest_amount:,.2f}")
        
        # Compliance risk assessment
        compliance_risk = compliance_analysis.get("risk_level", "low")
        if compliance_risk == "high":
            risk_score += 30
            risk_factors.append("High compliance risk detected")
        elif compliance_risk == "medium":
            risk_score += 15
            risk_factors.append("Medium compliance risk detected")
        
        # Document type risk assessment
        doc_type = document_type.get("primary_type", "unknown")
        if doc_type in ["contract", "policy"] and compliance_analysis["regulations_detected"]:
            risk_score += 10
            risk_factors.append("Regulatory document requiring review")
        
        # Content-based risk indicators
        risk_keywords = ["urgent", "immediate", "critical", "emergency", "escalate"]
        found_risk_keywords = [keyword for keyword in risk_keywords if keyword.lower() in content.lower()]
        if found_risk_keywords:
            risk_score += len(found_risk_keywords) * 5
            risk_factors.append(f"Urgency indicators found: {', '.join(found_risk_keywords)}")
        
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
            "requires_escalation": risk_score >= 50,
            "requires_manual_review": risk_score >= 25,
            "financial_risk": largest_amount > self.risk_indicators["high_value"],
            "compliance_risk": compliance_risk in ["medium", "high"],
            "recommended_action": self._get_risk_action(overall_risk, risk_score)
        }

    def _get_risk_action(self, risk_level: str, risk_score: int) -> str:
        """Get recommended action based on risk assessment"""
        if risk_level == "high":
            return "Immediate escalation to compliance and finance teams required"
        elif risk_level == "medium":
            return "Flag for priority review within 4 hours"
        else:
            return "Continue with standard document processing"

    def _generate_processing_summary(self, document_metadata: Dict, financial_info: Dict, 
                                   compliance_analysis: Dict, risk_assessment: Dict) -> Dict[str, Any]:
        """Generate comprehensive processing summary"""
        
        key_findings = []
        
        # Document findings
        pages = document_metadata.get("actual_pages", document_metadata.get("estimated_pages", 0))
        key_findings.append(f"Processed {pages}-page document")
        
        # Financial findings
        largest_amount = financial_info.get("largest_amount", 0)
        if largest_amount > 0:
            key_findings.append(f"Largest amount detected: ${largest_amount:,.2f}")
        
        # Compliance findings
        regulations = compliance_analysis.get("regulations_detected", [])
        if regulations:
            reg_names = [reg["regulation"] for reg in regulations]
            key_findings.append(f"Compliance requirements: {', '.join(reg_names)}")
        
        # Risk findings
        risk_level = risk_assessment.get("risk_level", "low")
        key_findings.append(f"Risk level: {risk_level}")
        
        # Determine overall status
        if risk_assessment.get("requires_escalation", False):
            overall_status = "requires_escalation"
        elif risk_assessment.get("requires_manual_review", False):
            overall_status = "requires_review"
        else:
            overall_status = "processed"
        
        # Generate recommendations
        recommendations = []
        
        if financial_info.get("largest_amount", 0) > self.risk_indicators["high_value"]:
            recommendations.append("Finance team review recommended for high-value amounts")
        
        if compliance_analysis.get("regulations_detected"):
            recommendations.append("Compliance review required")
        
        if risk_assessment.get("risk_level") == "high":
            recommendations.extend(risk_assessment.get("risk_factors", []))
        
        if not recommendations:
            recommendations.append("Standard document processing completed")
        
        return {
            "overall_status": overall_status,
            "processing_score": self._calculate_processing_score(document_metadata, financial_info, compliance_analysis, risk_assessment),
            "key_findings": key_findings,
            "recommendations": recommendations,
            "next_actions": self._suggest_next_actions(overall_status, risk_assessment, compliance_analysis),
            "processing_quality": self._assess_processing_quality(document_metadata, financial_info)
        }

    def _calculate_processing_score(self, document_metadata: Dict, financial_info: Dict, 
                                  compliance_analysis: Dict, risk_assessment: Dict) -> float:
        """Calculate overall processing quality score"""
        
        scores = {
            "extraction_completeness": min(100, len(financial_info.get("amounts_found", [])) * 20 + 50),
            "compliance_detection": compliance_analysis.get("compliance_score", 50),
            "risk_assessment": 100 - min(risk_assessment.get("risk_score", 0), 50),
            "content_quality": min(100, document_metadata.get("word_count", 0) / 10)
        }
        
        # Weighted average
        weights = {"extraction_completeness": 0.3, "compliance_detection": 0.3, "risk_assessment": 0.2, "content_quality": 0.2}
        weighted_score = sum(scores[key] * weights[key] for key in scores)
        
        return round(weighted_score, 2)

    def _assess_processing_quality(self, document_metadata: Dict, financial_info: Dict) -> str:
        """Assess the quality of processing based on extracted information"""
        
        quality_indicators = 0
        
        # Check if we extracted meaningful content
        if document_metadata.get("word_count", 0) > 100:
            quality_indicators += 1
        
        # Check if we found financial information
        if financial_info.get("amounts_found"):
            quality_indicators += 1
        
        # Check if we found structured data
        if financial_info.get("invoice_numbers") or financial_info.get("dates"):
            quality_indicators += 1
        
        if quality_indicators >= 3:
            return "high"
        elif quality_indicators >= 2:
            return "medium"
        else:
            return "low"

    def _suggest_next_actions(self, status: str, risk_assessment: Dict, compliance_analysis: Dict) -> List[str]:
        """Suggest next actions based on processing results"""
        actions = []
        
        if status == "requires_escalation":
            actions.append("Escalate to senior management immediately")
            actions.append("Notify compliance and legal teams")
        elif status == "requires_review":
            actions.append("Schedule manual review within 4 hours")
            actions.append("Flag for priority processing")
        
        if compliance_analysis.get("regulations_detected"):
            actions.append("Route to compliance team for regulatory review")
        
        if risk_assessment.get("financial_risk"):
            actions.append("Route to finance team for approval")
        
        if not actions:
            actions.append("Continue with standard workflow")
        
        return actions

    def _determine_flagging_action(self, risk_assessment: Dict, financial_info: Dict, compliance_analysis: Dict) -> Dict[str, Any]:
        """Determine the appropriate flagging action"""
        
        largest_amount = financial_info.get("largest_amount", 0)
        risk_level = risk_assessment.get("risk_level", "low")
        compliance_detected = bool(compliance_analysis.get("regulations_detected"))
        
        if largest_amount > self.risk_indicators["suspicious_threshold"] or risk_level == "high":
            action = "immediate_flag"
            description = f"High-risk document flagged: ${largest_amount:,.2f} amount with {risk_level} risk level"
            external_api = "/api/external/risk/alert"
        elif largest_amount > self.risk_indicators["high_value"] or compliance_detected:
            action = "review_flag"
            description = f"Document flagged for review: High-value amount (${largest_amount:,.2f}) or compliance requirements detected"
            external_api = "/api/external/risk/alert"
        else:
            action = "standard_processing"
            description = "Document processed without flags"
            external_api = None
        
        return {
            "action_type": action,
            "description": description,
            "external_api_call": external_api,
            "recommended_reviewer": self._recommend_reviewer(risk_level, compliance_detected, largest_amount),
            "priority_level": self._determine_priority_level(risk_level, largest_amount),
            "sla_deadline": self._calculate_sla_deadline(risk_level)
        }

    def _recommend_reviewer(self, risk_level: str, compliance_detected: bool, amount: float) -> str:
        """Recommend appropriate reviewer based on document characteristics"""
        
        if risk_level == "high" or amount > self.risk_indicators["suspicious_threshold"]:
            return "senior_finance_manager"
        elif compliance_detected:
            return "compliance_officer"
        elif amount > self.risk_indicators["high_value"]:
            return "finance_supervisor"
        else:
            return "document_processor"

    def _determine_priority_level(self, risk_level: str, amount: float) -> str:
        """Determine priority level for processing"""
        
        if risk_level == "high" or amount > self.risk_indicators["suspicious_threshold"]:
            return "critical"
        elif risk_level == "medium" or amount > self.risk_indicators["high_value"]:
            return "high"
        else:
            return "normal"

    def _calculate_sla_deadline(self, risk_level: str) -> str:
        """Calculate SLA deadline based on risk level"""
        from datetime import timedelta
        
        hours_map = {"high": 1, "medium": 4, "low": 24}
        deadline = datetime.now() + timedelta(hours=hours_map.get(risk_level, 24))
        return deadline.isoformat()

    def _fallback_pdf_processing(self, content: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback processing when main processing fails"""
        
        return {
            "document_metadata": {
                "content_length": len(content) if content else 0,
                "estimated_pages": 1,
                "processing_error": "Processing failed"
            },
            "document_type": {"primary_type": "unknown", "confidence": 0.3},
            "financial_information": {"amounts_found": [], "largest_amount": 0.0},
            "compliance_analysis": {"regulations_detected": [], "risk_level": "unknown"},
            "extracted_entities": {},
            "structure_analysis": {"formatting_quality": "unknown"},
            "risk_assessment": {
                "risk_level": "medium",
                "risk_score": 50,
                "requires_escalation": False,
                "recommended_action": "Retry processing"
            },
            "processing_summary": {
                "overall_status": "failed",
                "processing_score": 0,
                "key_findings": ["Processing failed due to system error"],
                "recommendations": ["Review processing logs", "Contact system administrator"],
                "next_actions": ["Retry processing or escalate to technical team"]
            },
            "classification_context": classification,
            "processing_timestamp": datetime.now().isoformat(),
            "flagging_recommendation": {
                "action_type": "standard_processing",
                "description": "Standard processing (fallback mode)",
                "external_api_call": None
            },
            "processing_status": "fallback_mode"
        }

# Global instance
pdf_agent = PDFAgent()
