"""
Invoice blueprint: invoice CRUD, PDF generation, email sending and status updates.
"""

import json
import os

from flask import Blueprint, render_template, request, send_file

# Package lives in blueprints/, one level below the project root.
_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

invoice_bp = Blueprint('invoice', __name__)


@invoice_bp.route("/invoice", methods=["GET", "POST"])
def invoice():
    """Invoice maker main page."""
    from datetime import date
    today = date.today().isoformat()
    return render_template("invoice.html", today_date=today)


@invoice_bp.route("/save_invoice", methods=["POST"])
def save_invoice():
    """Save or update an invoice."""
    from invoice_core import InvoiceCore

    try:
        data = json.loads(request.form.get('invoice_data', '{}'))

        # Initialize invoice core
        invoice_core = InvoiceCore()

        # Prepare client data
        client_data = {
            "name": data.get('client', {}).get('name', ''),
            "email": data.get('client', {}).get('email', ''),
            "phone": data.get('client', {}).get('phone', ''),
            "address": data.get('client', {}).get('address', ''),
            "company": data.get('client', {}).get('company', ''),
            "tax_id": data.get('client', {}).get('tax_id', '')
        }

        # Check if updating existing invoice
        if data.get('invoice_id'):
            invoice, message = invoice_core.update_invoice(
                invoice_id=data['invoice_id'],
                client_data=client_data,
                line_items_data=data.get('line_items', []),
                currency=data.get('currency', 'ZAR'),
                due_date=data.get('due_date', ''),
                notes=data.get('notes', ''),
                terms=data.get('terms', ''),
                business_name=data.get('business', {}).get('name', ''),
                business_email=data.get('business', {}).get('email', ''),
                business_phone=data.get('business', {}).get('phone', ''),
                business_address=data.get('business', {}).get('address', ''),
                payment_instructions=data.get('payment_instructions', ''),
                status=data.get('status', 'draft')
            )
        else:
            invoice, message = invoice_core.create_invoice(
                client_data=client_data,
                line_items_data=data.get('line_items', []),
                currency=data.get('currency', 'ZAR'),
                due_date=data.get('due_date', ''),
                notes=data.get('notes', ''),
                terms=data.get('terms', ''),
                business_name=data.get('business', {}).get('name', ''),
                business_email=data.get('business', {}).get('email', ''),
                business_phone=data.get('business', {}).get('phone', ''),
                business_address=data.get('business', {}).get('address', ''),
                payment_instructions=data.get('payment_instructions', '')
            )

        if invoice:
            return {'success': True, 'message': message, 'invoice_id': invoice.invoice_id, 'invoice_number': invoice.invoice_number}
        else:
            return {'success': False, 'message': message}, 400

    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@invoice_bp.route("/get_invoice", methods=["GET"])
def get_invoice():
    """Get invoice by ID."""
    from invoice_core import InvoiceCore

    try:
        invoice_id = request.args.get('id')
        if not invoice_id:
            return {'success': False, 'message': 'Invoice ID required'}, 400

        invoice_core = InvoiceCore()
        invoice, message = invoice_core.get_invoice(invoice_id)

        if invoice:
            return {'success': True, 'invoice': invoice.to_dict()}
        else:
            return {'success': False, 'message': message}, 404

    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@invoice_bp.route("/list_invoices", methods=["GET"])
def list_invoices():
    """List all invoices."""
    from invoice_core import InvoiceCore

    try:
        invoice_core = InvoiceCore()
        invoices = invoice_core.list_invoices()
        return {'success': True, 'invoices': invoices}

    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@invoice_bp.route("/delete_invoice", methods=["POST"])
def delete_invoice():
    """Delete an invoice."""
    from invoice_core import InvoiceCore

    try:
        invoice_id = request.form.get('invoice_id')
        if not invoice_id:
            return {'success': False, 'message': 'Invoice ID required'}, 400

        invoice_core = InvoiceCore()
        success, message = invoice_core.delete_invoice(invoice_id)

        if success:
            return {'success': True, 'message': message}
        else:
            return {'success': False, 'message': message}, 400

    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@invoice_bp.route("/send_invoice_email", methods=["POST"])
def send_invoice_email():
    """Send invoice via email."""
    from invoice_core import InvoiceEmailSender

    try:
        data = json.loads(request.form.get('invoice_data', '{}'))
        to_email = request.form.get('to_email', '')
        subject = request.form.get('subject', '')
        email_body = request.form.get('email_body', '')

        if not to_email:
            return {'success': False, 'message': 'Recipient email required'}, 400

        # Create a minimal invoice object for email sending
        class MinimalInvoice:
            def __init__(self, data):
                self.invoice_id = data.get('invoice_id', '')
                self.invoice_number = data.get('invoice_number', '')
                self.client = type('Client', (), {
                    'name': data.get('client', {}).get('name', ''),
                    'email': data.get('client', {}).get('email', '')
                })()
                self.currency = data.get('currency', 'ZAR')
                self.currency_info = {'symbol': 'R'}
                self.business_name = data.get('business', {}).get('name', '')
                self.issue_date = data.get('issue_date', '')
                self.due_date = data.get('due_date', '')
                self.grand_total = data.get('totals', {}).get('grand_total', 0)
                self.payment_instructions = data.get('payment_instructions', '')

        invoice = MinimalInvoice(data)

        # Initialize email sender
        email_sender = InvoiceEmailSender(
            from_email=data.get('business', {}).get('email', 'noreply@example.com'),
            from_name=data.get('business', {}).get('name', 'Invoice System')
        )

        # Send email
        success, message = email_sender.send_invoice_email(
            invoice=invoice,
            to_email=to_email,
            subject=subject,
            body=email_body,
            pdf_path=None
        )

        if success:
            return {'success': True, 'message': message}
        else:
            return {'success': False, 'message': message}, 400

    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@invoice_bp.route("/generate_invoice_pdf/<invoice_id>", methods=["GET"])
def generate_invoice_pdf(invoice_id):
    """Generate PDF for an invoice."""
    from invoice_core import InvoiceCore, InvoicePDFGenerator

    try:
        invoice_core = InvoiceCore()
        invoice, message = invoice_core.get_invoice(invoice_id)

        if not invoice:
            return {'success': False, 'message': message}, 404

        # Generate PDF
        pdf_generator = InvoicePDFGenerator()
        output_dir = os.path.join(_APP_ROOT, 'exports')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f'invoice_{invoice_id}.pdf')

        success, message = pdf_generator.generate_pdf(invoice, output_path)

        if success:
            return send_file(output_path, as_attachment=True, download_name=f'Invoice-{invoice.invoice_number}.pdf')
        else:
            return {'success': False, 'message': message}, 500

    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@invoice_bp.route("/preview_invoice/<invoice_id>", methods=["GET"])
def preview_invoice(invoice_id):
    """Preview invoice as HTML."""
    from invoice_core import InvoiceCore, InvoicePDFGenerator

    try:
        invoice_core = InvoiceCore()
        invoice, message = invoice_core.get_invoice(invoice_id)

        if not invoice:
            return {'success': False, 'message': message}, 404

        pdf_generator = InvoicePDFGenerator()
        html = pdf_generator.generate_html_preview(invoice)

        return {'success': True, 'html': html}

    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@invoice_bp.route("/mark_invoice_paid/<invoice_id>", methods=["POST"])
def mark_invoice_paid(invoice_id):
    """Mark invoice as paid."""
    from invoice_core import InvoiceCore

    try:
        invoice_core = InvoiceCore()
        invoice, message = invoice_core.mark_as_paid(invoice_id)

        if invoice:
            return {'success': True, 'message': message}
        else:
            return {'success': False, 'message': message}, 400

    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@invoice_bp.route("/mark_invoice_sent/<invoice_id>", methods=["POST"])
def mark_invoice_sent(invoice_id):
    """Mark invoice as sent."""
    from invoice_core import InvoiceCore

    try:
        invoice_core = InvoiceCore()
        invoice, message = invoice_core.mark_as_sent(invoice_id)

        if invoice:
            return {'success': True, 'message': message}
        else:
            return {'success': False, 'message': message}, 400

    except Exception as e:
        return {'success': False, 'message': str(e)}, 500