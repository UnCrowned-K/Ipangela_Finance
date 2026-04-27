"""
Invoice Core Module

Comprehensive invoice management system with PDF generation,
data validation, storage management, and email sending capabilities.

Features:
- Create, edit, and manage invoices
- Sequential invoice number generation
- Multi-currency support
- Tax handling and discount applications
- PDF generation for professional invoices
- Email sending functionality
- Payment status tracking
"""

import json
import os
import re
import uuid
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from utils import ValidationUtils


class PaymentStatus(Enum):
    """Enumeration of possible payment statuses."""
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Currency(Enum):
    """Supported currencies with symbol and formatting."""
    USD = {"symbol": "$", "code": "USD", "position": "left"}
    EUR = {"symbol": "€", "code": "EUR", "position": "left"}
    GBP = {"symbol": "£", "code": "GBP", "position": "left"}
    ZAR = {"symbol": "R", "code": "ZAR", "position": "left"}
    JPY = {"symbol": "¥", "code": "JPY", "position": "left"}
    CAD = {"symbol": "C$", "code": "CAD", "position": "left"}
    AUD = {"symbol": "A$", "code": "AUD", "position": "left"}
    CHF = {"symbol": "CHF", "code": "CHF", "position": "left"}


@dataclass
class ClientDetails:
    """Data class for client information."""
    name: str
    email: str
    phone: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = ""
    company: str = ""
    tax_id: str = ""
    
    def __post_init__(self):
        """Validate and sanitize client data after initialization."""
        self.name = ValidationUtils.sanitize_string(self.name, "Client name")
        self.email = ValidationUtils.validate_email(self.email)
        self.phone = ValidationUtils.sanitize_string(self.phone, "Phone")
        self.address = ValidationUtils.sanitize_string(self.address, "Address")
        self.city = ValidationUtils.sanitize_string(self.city, "City")
        self.state = ValidationUtils.sanitize_string(self.state, "State")
        self.postal_code = ValidationUtils.sanitize_string(self.postal_code, "Postal code")
        self.country = ValidationUtils.sanitize_string(self.country, "Country")
        self.company = ValidationUtils.sanitize_string(self.company, "Company")
        self.tax_id = ValidationUtils.sanitize_string(self.tax_id, "Tax ID")
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "company": self.company,
            "tax_id": self.tax_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "ClientDetails":
        """Create instance from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class LineItem:
    """Data class for invoice line items."""
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount_percent: Decimal = Decimal("0")
    tax_percent: Decimal = Decimal("0")
    sku: str = ""
    
    def __post_init__(self):
        """Validate and calculate line item values."""
        self.description = ValidationUtils.sanitize_string(self.description, "Description")
        self.sku = ValidationUtils.sanitize_string(self.sku, "SKU")
        
        # Convert to Decimal if needed
        if isinstance(self.quantity, (int, float)):
            self.quantity = Decimal(str(self.quantity))
        if isinstance(self.unit_price, (int, float)):
            self.unit_price = Decimal(str(self.unit_price))
        if isinstance(self.discount_percent, (int, float)):
            self.discount_percent = Decimal(str(self.discount_percent))
        if isinstance(self.tax_percent, (int, float)):
            self.tax_percent = Decimal(str(self.tax_percent))
        
        # Validate positive values
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.unit_price < 0:
            raise ValueError("Unit price cannot be negative")
        if self.discount_percent < 0 or self.discount_percent > 100:
            raise ValueError("Discount must be between 0 and 100")
        if self.tax_percent < 0 or self.tax_percent > 100:
            raise ValueError("Tax must be between 0 and 100")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "description": self.description,
            "quantity": float(self.quantity),
            "unit_price": float(self.unit_price),
            "discount_percent": float(self.discount_percent),
            "tax_percent": float(self.tax_percent),
            "sku": self.sku,
            "subtotal": float(self.subtotal),
            "discount_amount": float(self.discount_amount),
            "tax_amount": float(self.tax_amount),
            "total": float(self.total)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LineItem":
        """Create instance from dictionary."""
        return cls(
            description=data["description"],
            quantity=data["quantity"],
            unit_price=data["unit_price"],
            discount_percent=data.get("discount_percent", 0),
            tax_percent=data.get("tax_percent", 0),
            sku=data.get("sku", "")
        )


@dataclass
class Invoice:
    """Main invoice data class."""
    invoice_number: str
    client: ClientDetails
    line_items: List[LineItem]
    currency: str = "ZAR"
    status: str = PaymentStatus.DRAFT.value
    issue_date: str = field(default_factory=lambda: date.today().isoformat())
    due_date: str = ""
    notes: str = ""
    terms: str = ""
    business_name: str = ""
    business_address: str = ""
    business_email: str = ""
    business_phone: str = ""
    business_logo: str = ""
    invoice_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    payment_instructions: str = ""
    discount_percent: Decimal = Decimal("0")
    discount_type: str = "percent"  # percent or fixed
    
    def __post_init__(self):
        """Validate and calculate invoice values."""
        self.invoice_number = ValidationUtils.sanitize_string(self.invoice_number, "Invoice number")
        self.currency = self.currency.upper()
        if self.currency not in [c.value for c in Currency]:
            self.currency = "USD"
        
        # Validate dates
        if self.due_date:
            try:
                datetime.strptime(self.due_date, "%Y-%m-%d")
            except ValueError:
                self.due_date = ""
        
        try:
            datetime.strptime(self.issue_date, "%Y-%m-%d")
        except ValueError:
            self.issue_date = date.today().isoformat()
        
        self.notes = ValidationUtils.sanitize_string(self.notes, "Notes")
        self.terms = ValidationUtils.sanitize_string(self.terms, "Terms")
        self.business_name = ValidationUtils.sanitize_string(self.business_name, "Business name")
        self.business_address = ValidationUtils.sanitize_string(self.business_address, "Business address")
        self.business_email = ValidationUtils.validate_email(self.business_email)
        self.business_phone = ValidationUtils.sanitize_string(self.business_phone, "Business phone")
        self.payment_instructions = ValidationUtils.sanitize_string(self.payment_instructions, "Payment instructions")
        
        if isinstance(self.discount_percent, (int, float)):
            self.discount_percent = Decimal(str(self.discount_percent))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "invoice_id": self.invoice_id,
            "invoice_number": self.invoice_number,
            "client": self.client.to_dict(),
            "line_items": [item.to_dict() for item in self.line_items],
            "currency": self.currency,
            "currency_info": self.currency_info,
            "status": self.status,
            "issue_date": self.issue_date,
            "due_date": self.due_date,
            "notes": self.notes,
            "terms": self.terms,
            "business_name": self.business_name,
            "business_address": self.business_address,
            "business_email": self.business_email,
            "business_phone": self.business_phone,
            "business_logo": self.business_logo,
            "subtotal": float(self.subtotal),
            "total_discount": float(self.total_discount),
            "total_tax": float(self.total_tax),
            "grand_total": float(self.grand_total),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "payment_instructions": self.payment_instructions,
            "discount_percent": float(self.discount_percent),
            "discount_type": self.discount_type,
            "is_overdue": self.is_overdue,
            "days_until_due": self.days_until_due
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Invoice":
        """Create instance from dictionary."""
        client = ClientDetails.from_dict(data["client"])
        line_items = [LineItem.from_dict(item) for item in data.get("line_items", [])]
        
        return cls(
            invoice_number=data["invoice_number"],
            client=client,
            line_items=line_items,
            currency=data.get("currency", "USD"),
            status=data.get("status", PaymentStatus.DRAFT.value),
            issue_date=data.get("issue_date", date.today().isoformat()),
            due_date=data.get("due_date", ""),
            notes=data.get("notes", ""),
            terms=data.get("terms", ""),
            business_name=data.get("business_name", ""),
            business_address=data.get("business_address", ""),
            business_email=data.get("business_email", ""),
            business_phone=data.get("business_phone", ""),
            business_logo=data.get("business_logo", ""),
            invoice_id=data.get("invoice_id", str(uuid.uuid4())),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            payment_instructions=data.get("payment_instructions", ""),
            discount_percent=data.get("discount_percent", 0),
            discount_type=data.get("discount_type", "percent")
        )


class InvoiceStorage:
    """Manages invoice storage and retrieval from JSON files."""
    
    def __init__(self, storage_dir: str = "invoices"):
        """Initialize storage with specified directory."""
        self.storage_dir = storage_dir
        self._ensure_storage_directory()
    
    def _ensure_storage_directory(self) -> None:
        """Create storage directory if it doesn't exist."""
        os.makedirs(self.storage_dir, exist_ok=True)
    
    def _get_filepath(self, invoice_id: str) -> str:
        """Get file path for an invoice."""
        return os.path.join(self.storage_dir, f"{invoice_id}.json")
    
    def save(self, invoice: Invoice) -> Tuple[bool, str]:
        """Save invoice to storage."""
        try:
            filepath = self._get_filepath(invoice.invoice_id)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(invoice.to_dict(), f, indent=4, ensure_ascii=False)
            return True, f"Invoice saved successfully: {invoice.invoice_number}"
        except Exception as e:
            return False, f"Error saving invoice: {str(e)}"
    
    def load(self, invoice_id: str) -> Tuple[Optional[Invoice], str]:
        """Load invoice from storage."""
        try:
            filepath = self._get_filepath(invoice_id)
            if not os.path.exists(filepath):
                return None, f"Invoice not found: {invoice_id}"
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            invoice = Invoice.from_dict(data)
            return invoice, "Invoice loaded successfully"
        except Exception as e:
            return None, f"Error loading invoice: {str(e)}"
    
    def load_all(self) -> Tuple[List[Invoice], str]:
        """Load all invoices from storage."""
        invoices = []
        try:
            if not os.path.exists(self.storage_dir):
                return invoices, "No invoices found"
            
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.json'):
                    invoice_id = filename.replace('.json', '')
                    invoice, message = self.load(invoice_id)
                    if invoice:
                        invoices.append(invoice)
            
            return invoices, f"Loaded {len(invoices)} invoices"
        except Exception as e:
            return invoices, f"Error loading invoices: {str(e)}"
    
    def delete(self, invoice_id: str) -> Tuple[bool, str]:
        """Delete invoice from storage."""
        try:
            filepath = self._get_filepath(invoice_id)
            if not os.path.exists(filepath):
                return False, f"Invoice not found: {invoice_id}"
            
            os.remove(filepath)
            return True, f"Invoice deleted successfully"
        except Exception as e:
            return False, f"Error deleting invoice: {str(e)}"
    
    def list_invoices(self) -> List[Dict[str, Any]]:
        """List all invoices with summary information."""
        invoices, _ = self.load_all()
        return [
            {
                "invoice_id": inv.invoice_id,
                "invoice_number": inv.invoice_number,
                "client_name": inv.client.name,
                "grand_total": float(inv.grand_total),
                "currency": inv.currency,
                "status": inv.status,
                "issue_date": inv.issue_date,
                "due_date": inv.due_date
            }
            for inv in sorted(invoices, key=lambda x: x.created_at, reverse=True)
        ]


class InvoiceNumberGenerator:
    """Generates sequential invoice numbers."""
    
    def __init__(self, storage_dir: str = "invoices"):
        """Initialize with storage directory."""
        self.storage_dir = storage_dir
        self._counter_file = os.path.join(storage_dir, ".invoice_counter")
    
    def get_next_number(self) -> str:
        """Get next sequential invoice number."""
        self._ensure_storage_directory()
        current = self._load_counter()
        next_num = current + 1
        
        # Format: INV-YYYY-XXXXXX
        year = datetime.now().year
        formatted = f"INV-{year}-{next_num:06d}"
        
        self._save_counter(next_num)
        return formatted
    
    def _ensure_storage_directory(self) -> None:
        """Create storage directory if it doesn't exist."""
        os.makedirs(self.storage_dir, exist_ok=True)
    
    def _load_counter(self) -> int:
        """Load current counter value."""
        try:
            if os.path.exists(self._counter_file):
                with open(self._counter_file, 'r') as f:
                    return int(f.read().strip())
        except Exception:
            pass
        return 0
    
    def _save_counter(self, value: int) -> None:
        """Save counter value."""
        try:
            with open(self._counter_file, 'w') as f:
                f.write(str(value))
        except Exception as e:
            print(f"Warning: Could not save invoice counter: {e}")


class InvoiceValidator:
    """Validates invoice data."""
    
    @staticmethod
    def validate_invoice(invoice: Invoice) -> Tuple[bool, List[str]]:
        """Validate invoice data."""
        errors = []
        
        # Validate invoice number
        if not invoice.invoice_number:
            errors.append("Invoice number is required")
        
        # Validate client
        if not invoice.client.name:
            errors.append("Client name is required")
        if not invoice.client.email:
            errors.append("Client email is required")
        
        # Validate line items
        if not invoice.line_items:
            errors.append("At least one line item is required")
        else:
            for i, item in enumerate(invoice.line_items):
                if not item.description:
                    errors.append(f"Line item {i+1}: Description is required")
                if item.quantity <= 0:
                    errors.append(f"Line item {i+1}: Quantity must be positive")
        
        # Validate dates
        if invoice.due_date:
            try:
                due = datetime.strptime(invoice.due_date, "%Y-%m-%d").date()
                if due < date.today():
                    errors.append("Due date cannot be in the past")
            except ValueError:
                errors.append("Invalid due date format. Use YYYY-MM-DD")
        
        return len(errors) == 0, errors


class InvoiceCore:
    """Main invoice management core class."""
    
    def __init__(self, storage_dir: str = "invoices"):
        """Initialize invoice core with storage."""
        self.storage = InvoiceStorage(storage_dir)
        self.number_generator = InvoiceNumberGenerator(storage_dir)
        self.validator = InvoiceValidator()
    
    def create_invoice(
        self,
        client_data: Dict[str, str],
        line_items_data: List[Dict[str, Any]],
        currency: str = "USD",
        due_date: str = "",
        notes: str = "",
        terms: str = "",
        business_name: str = "",
        business_address: str = "",
        business_email: str = "",
        business_phone: str = "",
        payment_instructions: str = ""
    ) -> Tuple[Optional[Invoice], str]:
        """Create a new invoice."""
        try:
            # Generate invoice number
            invoice_number = self.number_generator.get_next_number()
            
            # Create client
            client = ClientDetails(**client_data)
            
            # Create line items
            line_items = [LineItem(**item) for item in line_items_data]
            
            # Create invoice
            invoice = Invoice(
                invoice_number=invoice_number,
                client=client,
                line_items=line_items,
                currency=currency,
                due_date=due_date,
                notes=notes,
                terms=terms,
                business_name=business_name,
                business_address=business_address,
                business_email=business_email,
                business_phone=business_phone,
                payment_instructions=payment_instructions
            )
            
            # Validate
            is_valid, errors = self.validator.validate_invoice(invoice)
            if not is_valid:
                return None, f"Validation errors: {', '.join(errors)}"
            
            # Save
            success, message = self.storage.save(invoice)
            if not success:
                return None, message
            
            return invoice, f"Invoice created successfully: {invoice_number}"
        
        except ValueError as e:
            return None, f"Validation error: {str(e)}"
        except Exception as e:
            return None, f"Error creating invoice: {str(e)}"
    
    def update_invoice(
        self,
        invoice_id: str,
        **kwargs
    ) -> Tuple[Optional[Invoice], str]:
        """Update an existing invoice."""
        try:
            invoice, message = self.storage.load(invoice_id)
            if not invoice:
                return None, message
            
            # Update fields
            if 'client_data' in kwargs:
                invoice.client = ClientDetails(**kwargs['client_data'])
            if 'line_items_data' in kwargs:
                invoice.line_items = [LineItem(**item) for item in kwargs['line_items_data']]
            if 'currency' in kwargs:
                invoice.currency = kwargs['currency']
            if 'due_date' in kwargs:
                invoice.due_date = kwargs['due_date']
            if 'notes' in kwargs:
                invoice.notes = kwargs['notes']
            if 'terms' in kwargs:
                invoice.terms = kwargs['terms']
            if 'business_name' in kwargs:
                invoice.business_name = kwargs['business_name']
            if 'business_address' in kwargs:
                invoice.business_address = kwargs['business_address']
            if 'business_email' in kwargs:
                invoice.business_email = kwargs['business_email']
            if 'business_phone' in kwargs:
                invoice.business_phone = kwargs['business_phone']
            if 'payment_instructions' in kwargs:
                invoice.payment_instructions = kwargs['payment_instructions']
            if 'status' in kwargs:
                invoice.status = kwargs['status']
            
            invoice.updated_at = datetime.now().isoformat()
            invoice.update_status()
            
            # Validate
            is_valid, errors = self.validator.validate_invoice(invoice)
            if not is_valid:
                return None, f"Validation errors: {', '.join(errors)}"
            
            # Save
            success, message = self.storage.save(invoice)
            if not success:
                return None, message
            
            return invoice, f"Invoice updated successfully: {invoice.invoice_number}"
        
        except ValueError as e:
            return None, f"Validation error: {str(e)}"
        except Exception as e:
            return None, f"Error updating invoice: {str(e)}"
    
    def get_invoice(self, invoice_id: str) -> Tuple[Optional[Invoice], str]:
        """Get invoice by ID."""
        return self.storage.load(invoice_id)
    
    def list_invoices(self) -> List[Dict[str, Any]]:
        """List all invoices."""
        return self.storage.list_invoices()
    
    def delete_invoice(self, invoice_id: str) -> Tuple[bool, str]:
        """Delete invoice."""
        return self.storage.delete(invoice_id)
    
    def mark_as_paid(self, invoice_id: str) -> Tuple[Optional[Invoice], str]:
        """Mark invoice as paid."""
        return self.update_invoice(invoice_id, status=PaymentStatus.PAID.value)
    
    def mark_as_sent(self, invoice_id: str) -> Tuple[Optional[Invoice], str]:
        """Mark invoice as sent."""
        return self.update_invoice(invoice_id, status=PaymentStatus.SENT.value)
    
    def get_overdue_invoices(self) -> List[Invoice]:
        """Get all overdue invoices."""
        invoices, _ = self.storage.load_all()
        return [inv for inv in invoices if inv.is_overdue]
    
    def get_invoices_by_status(self, status: str) -> List[Invoice]:
        """Get invoices by payment status."""
        invoices, _ = self.storage.load_all()
        return [inv for inv in invoices if inv.status == status]


class InvoiceEmailSender:
    """Handles email sending for invoices."""
    
    def __init__(self, smtp_host: str = "", smtp_port: int = 587, 
                 smtp_user: str = "", smtp_password: str = "",
                 from_email: str = "", from_name: str = ""):
        """Initialize email sender with SMTP settings."""
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.from_name = from_name
    
    def send_invoice_email(
        self,
        invoice: Invoice,
        to_email: str,
        subject: str = "",
        body: str = "",
        pdf_path: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Send invoice email to client."""
        try:
            msg = MIMEMultipart()
            msg['From'] = f"{self.from_name} <{self.from_email}>" if self.from_name else self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject or f"Invoice {invoice.invoice_number} from {invoice.business_name}"
            
            # Email body
            if body:
                msg.attach(MIMEText(body, 'plain'))
            else:
                email_body = self._get_default_email_body(invoice)
                msg.attach(MIMEText(email_body, 'plain'))
            
            # Attach PDF if provided
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as f:
                    attachment = MIMEApplication(f.read(), _subtype='pdf')
                    attachment.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=f"Invoice-{invoice.invoice_number}.pdf"
                    )
                    msg.attach(attachment)
            
            # If SMTP is configured, send via SMTP
            if self.smtp_host and self.smtp_user:
                import smtplib
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
                server.quit()
                return True, "Invoice email sent successfully"
            
            # Otherwise, return email data (for testing/development)
            return True, f"Email prepared (SMTP not configured): To: {to_email}"
        
        except Exception as e:
            return False, f"Error sending email: {str(e)}"
    
    def _get_default_email_body(self, invoice: Invoice) -> str:
        """Generate default email body."""
        currency_symbol = invoice.currency_info["symbol"]
        return f"""
Dear {invoice.client.name},

Please find attached invoice {invoice.invoice_number} for {currency_symbol}{invoice.grand_total:,.2f}.

Invoice Details:
- Invoice Number: {invoice.invoice_number}
- Issue Date: {invoice.issue_date}
- Due Date: {invoice.due_date}
- Amount Due: {currency_symbol}{invoice.grand_total:,.2f}

{payment_instructions}

Please let us know if you have any questions.

Thank you for your business!

Best regards,
{invoice.business_name}
"""


class InvoicePDFGenerator:
    """Generates PDF invoices using HTML template."""
    
    def __init__(self, template_dir: str = "templates"):
        """Initialize PDF generator."""
        self.template_dir = template_dir
    
    def generate_pdf(self, invoice: Invoice, output_path: str) -> Tuple[bool, str]:
        """Generate PDF invoice from invoice object."""
        try:
            import pdfkit
            
            # Generate HTML
            html_content = self._generate_html(invoice)
            
            # Convert to PDF
            options = {
                'page-size': 'A4',
                'margin-top': '20mm',
                'margin-right': '20mm',
                'margin-bottom': '20mm',
                'margin-left': '20mm',
                'encoding': 'UTF-8',
                'no-outline': None
            }
            
            pdfkit.from_string(html_content, output_path, options=options)
            return True, f"PDF generated successfully: {output_path}"
        
        except ImportError:
            return False, "pdfkit not installed. Install with: pip install pdfkit"
        except Exception as e:
            return False, f"Error generating PDF: {str(e)}"
    
    def _generate_html(self, invoice: Invoice) -> str:
        """Generate HTML content for invoice."""
        currency_symbol = invoice.currency_info["symbol"]
        
        # Build line items HTML
        line_items_html = ""
        for item in invoice.line_items:
            line_items_html += f"""
            <tr>
                <td class="line-description">{item.description}</td>
                <td class="line-qty">{item.quantity}</td>
                <td class="line-price">{currency_symbol}{item.unit_price:,.2f}</td>
                <td class="line-discount">{item.discount_percent}%</td>
                <td class="line-tax">{item.tax_percent}%</td>
                <td class="line-total">{currency_symbol}{item.total:,.2f}</td>
            </tr>
            """
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Invoice {invoice.invoice_number}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; font-size: 12px; line-height: 1.4; color: #333; }}
        .invoice-container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
        .invoice-header {{ display: flex; justify-content: space-between; margin-bottom: 30px; }}
        .company-info {{ flex: 1; }}
        .company-info h1 {{ color: #007a55; font-size: 24px; margin-bottom: 10px; }}
        .invoice-details {{ text-align: right; }}
        .invoice-details h2 {{ color: #007a55; font-size: 28px; margin-bottom: 10px; }}
        .invoice-number {{ font-size: 16px; margin-bottom: 5px; }}
        .invoice-date {{ color: #666; }}
        .client-section {{ margin-bottom: 30px; }}
        .bill-to {{ background: #f9f9f9; padding: 15px; border-radius: 4px; }}
        .bill-to h3 {{ color: #007a55; margin-bottom: 10px; }}
        .line-items-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
        .line-items-table th {{ background: #007a55; color: white; padding: 10px; text-align: left; }}
        .line-items-table td {{ padding: 10px; border-bottom: 1px solid #eee; }}
        .line-items-table tr:last-child td {{ border-bottom: 2px solid #007a55; }}
        .line-items-table .text-right {{ text-align: right; }}
        .totals-section {{ display: flex; justify-content: flex-end; }}
        .totals {{ width: 300px; }}
        .total-row {{ display: flex; justify-content: space-between; padding: 5px 0; }}
        .total-row.grand-total {{ background: #007a55; color: white; padding: 10px; margin-top: 10px; font-size: 16px; font-weight: bold; }}
        .notes-section {{ margin-top: 30px; }}
        .notes-section h4 {{ color: #007a55; margin-bottom: 10px; }}
        .terms-section {{ margin-top: 20px; }}
        .terms-section h4 {{ color: #007a55; margin-bottom: 10px; }}
        .payment-instructions {{ background: #f9f9f9; padding: 15px; border-radius: 4px; margin-top: 20px; }}
        .status-badge {{ display: inline-block; padding: 5px 15px; border-radius: 20px; font-size: 12px; text-transform: uppercase; }}
        .status-draft {{ background: #6c757d; color: white; }}
        .status-sent {{ background: #007a55; color: white; }}
        .status-paid {{ background: #28a745; color: white; }}
        .status-overdue {{ background: #dc3545; color: white; }}
    </style>
</head>
<body>
    <div class="invoice-container">
        <div class="invoice-header">
            <div class="company-info">
                <h1>{invoice.business_name or 'Your Company'}</h1>
                <p>{invoice.business_address or ''}</p>
                <p>{invoice.business_email or ''}</p>
                <p>{invoice.business_phone or ''}</p>
            </div>
            <div class="invoice-details">
                <h2>INVOICE</h2>
                <p class="invoice-number">#{invoice.invoice_number}</p>
                <p class="invoice-date">Issue Date: {invoice.issue_date}</p>
                <p class="invoice-date">Due Date: {invoice.due_date or 'Upon Receipt'}</p>
                <span class="status-badge status-{invoice.status}">{invoice.status}</span>
            </div>
        </div>
        
        <div class="client-section">
            <div class="bill-to">
                <h3>Bill To:</h3>
                <p><strong>{invoice.client.name}</strong></p>
                <p>{invoice.client.company or ''}</p>
                <p>{invoice.client.address or ''}</p>
                <p>{invoice.client.city}{', ' + invoice.client.state if invoice.client.state else ''}{', ' + invoice.client.postal_code if invoice.client.postal_code else ''}</p>
                <p>{invoice.client.country or ''}</p>
                <p>{invoice.client.email}</p>
                <p>{invoice.client.phone or ''}</p>
            </div>
        </div>
        
        <table class="line-items-table">
            <thead>
                <tr>
                    <th style="width: 40%;">Description</th>
                    <th style="width: 10%;">Qty</th>
                    <th style="width: 15%;">Price</th>
                    <th style="width: 10%;">Discount</th>
                    <th style="width: 10%;">Tax</th>
                    <th style="width: 15%;">Total</th>
                </tr>
            </thead>
            <tbody>
                {line_items_html}
            </tbody>
        </table>
        
        <div class="totals-section">
            <div class="totals">
                <div class="total-row">
                    <span>Subtotal:</span>
                    <span>{currency_symbol}{invoice.subtotal:,.2f}</span>
                </div>
                <div class="total-row">
                    <span>Discount:</span>
                    <span>-{currency_symbol}{invoice.total_discount:,.2f}</span>
                </div>
                <div class="total-row">
                    <span>Tax:</span>
                    <span>{currency_symbol}{invoice.total_tax:,.2f}</span>
                </div>
                <div class="total-row grand-total">
                    <span>Total:</span>
                    <span>{currency_symbol}{invoice.grand_total:,.2f}</span>
                </div>
            </div>
        </div>
        
        {f'<div class="notes-section"><h4>Notes:</h4><p>{invoice.notes}</p></div>' if invoice.notes else ''}
        
        {f'<div class="terms-section"><h4>Terms:</h4><p>{invoice.terms}</p></div>' if invoice.terms else ''}
        
        {f'<div class="payment-instructions"><h4>Payment Instructions:</h4><p>{invoice.payment_instructions}</p></div>' if invoice.payment_instructions else ''}
    </div>
</body>
</html>
        """
        return html
    
    def generate_html_preview(self, invoice: Invoice) -> str:
        """Generate HTML preview for invoice."""
        return self._generate_html(invoice)


# Example usage and testing
if __name__ == "__main__":
    # Example invoice creation
    core = InvoiceCore()
    
    client_data = {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "+1 555-123-4567",
        "address": "123 Main Street",
        "city": "New York",
        "state": "NY",
        "postal_code": "10001",
        "country": "USA",
        "company": "Acme Corp",
        "tax_id": "XX-XXXXXXX"
    }
    
    line_items_data = [
        {
            "description": "Web Development Services",
            "quantity": 1,
            "unit_price": 1500.00,
            "discount_percent": 0,
            "tax_percent": 10
        },
        {
            "description": "Hosting Setup",
            "quantity": 5,
            "unit_price": 50.00,
            "discount_percent": 10,
            "tax_percent": 10,
            "sku": "HOST-001"
        }
    ]
    
    invoice, message = core.create_invoice(
        client_data=client_data,
        line_items_data=line_items_data,
        currency="USD",
        due_date="2024-02-15",
        business_name="My Business",
        business_email="billing@mybusiness.com",
        payment_instructions="Bank Transfer: Account XXXX-XXXX-XXXX"
    )
    
    if invoice:
        print(f"Success: {message}")
        print(f"Invoice ID: {invoice.invoice_id}")
        print(f"Grand Total: ${invoice.grand_total:,.2f}")
    else:
        print(f"Error: {message}")
