# Profit Optimizer

A comprehensive web-based application for business management, featuring integer linear programming (ILP) optimization, invoice generation, and finance management. Built with Flask, this application provides an intuitive interface for maximizing profit under budget constraints, creating professional invoices, and tracking financial health.

## Features

### Profit Optimizer
- **Integer Linear Programming (ILP)**: Solve optimization problems using PuLP solver with CBC algorithm
- **Variable Management**: Add, edit, delete, import, and export optimization variables
- **Budget Constraints**: Set budget limits and maximize profit efficiently
- **Real-time Results**: View optimal solutions with detailed breakdowns
- **Data Persistence**: Import/export variables as JSON files

### Invoice Generator
- **Professional Invoices**: Create and manage professional invoices with customizable templates
- **Multi-currency Support**: Support for ZAR, USD, EUR, GBP, JPY, CAD, AUD, CHF
- **Line Items**: Add unlimited line items with quantity, price, discount, and tax calculations
- **Sequential Numbering**: Auto-generated invoice numbers (format: INV-YYYY-XXXXXX)
- **Payment Tracking**: Track payment status (Draft, Sent, Paid, Overdue, Cancelled)
- **PDF Generation**: Generate professional PDF invoices
- **Email Sending**: Send invoices directly to clients via email
- **Client Management**: Store and manage client information

### Finance Dashboard
- **Transaction Management**: Track income, expenses, and transfers
- **Multi-Account Support**: Manage checking, savings, credit, cash, investment, and loan accounts
- **Budget Planning**: Create and track budgets with alert thresholds
- **Category Management**: Pre-configured categories with auto-categorization
- **Money In / Out**: The five questions worth answering at any moment — what came in, what went out, what you owe, what you are owed, and what you actually made
- **Customer and Supplier Ledger**: Contacts, customer invoices and supplier bills with partial settlement, write-offs and aging buckets (not yet due, 1–30, 31–60, 61–90, 90+ days)
- **Financial Statements**: Profit and loss on both a cash and an accrual basis, balance sheet, cash flow, and expense analysis — built on ZAR and a configurable South African financial year
- **Tax and Payroll**: Business profile, structuring checklist, VAT/PAYE/UIF/provisional tax obligations with deadlines, and payroll runs with PAYE and UIF tracking
- **Records Health**: Scores your records completeness and names exactly what to fix
- **Funding Readiness**: Revenue, margin, current ratio, days sales outstanding, runway, income stability and growth, with blockers called out separately from warnings
- **Forecasting**: Scenarios built from your own recent averages, with break-even and cash-runway projections
- **Financial Reports**: Generate summary, income/expense, and category reports
- **Data Import/Export**: Export data as JSON or CSV, import from external sources
- **Visual Charts**: Interactive charts for income vs expenses and spending by category

> **Professional advice**: the tax, payroll and funding figures in this module are
> planning estimates produced from your own records. They support the advice of a
> registered tax practitioner or bookkeeper; they do not replace it. Confirm every
> amount, rate and deadline with SARS or your accountant before you file or pay.

## Tech Stack

- **Backend**: Python 3.8+, Flask 3.0.0
- **Optimization**: PuLP 2.8.0 (CBC solver)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript, Chart.js
- **Deployment**: Gunicorn 21.2.0
- **File Handling**: Werkzeug 3.0.1

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/UnCrowned-K/Profit-Optimizer.git
   cd Profit-Optimizer
   ```

2. **Set up a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python server/app.py
   ```

The application will start at `http://localhost:5000` and automatically open in your browser.

## Usage

### Profit Optimization

#### Adding Variables

1. Click "Add Item" to open the variable creation modal
2. Fill in the following fields:
   - **Item Name**: Unique identifier for the product
   - **Minimum Units**: Minimum quantity of units required (default: 0)
   - **Maximum Units**: Maximum quantity of units allowed (leave blank for unlimited)
   - **Cost per Unit**: Cost to purchase ONE unit (always per unit, not per pack)
   - **Profit per Unit**: Profit generated per individual unit sold
   - **Units per Pack (optional)**: Set to 1 for individual units, or specify pack size (e.g., 12 for a dozen)

**Note**: Everything is unit-based. If you have items in packs:
- Enter the cost for ONE unit (not the pack)
- Enter how many units are in a pack (multiplier)
- The optimizer will calculate pack costs as: cost_per_unit × units_per_pack

#### Setting Budget

1. Navigate to the "Budget" section
2. Enter your budget constraint in rands
3. Click "Update Budget" to save

#### Running Optimization

1. Ensure you have added variables and set a budget
2. Click "Run Optimization" in the Constraints section
3. View results in the "Results" section showing:
   - Projected profit
   - Optimal quantities for each item
   - Total cost breakdown

### Invoice Generator

#### Creating an Invoice

1. Navigate to the Invoice Generator page
2. Fill in your business details (name, email, phone, address)
3. Enter client information (name, email, company, tax ID)
4. Set invoice details (currency, issue date, due date)
5. Add line items with description, quantity, price, discount, and tax
6. Optionally add notes, terms, and payment instructions
7. Save as draft or send directly

#### Managing Invoices

- **View All Invoices**: Click "View All Invoices" to see all created invoices
- **Edit Invoice**: Click the edit button on any invoice
- **Delete Invoice**: Click the delete button (with confirmation)
- **Download PDF**: Generate a professional PDF for printing
- **Send Email**: Email the invoice directly to the client

### Finance Dashboard

#### Adding Accounts

1. Navigate to the Finance Dashboard
2. Click "Add Account"
3. Enter account details (name, type, balance, institution)
4. Save the account

#### Recording Transactions

1. Click "Add Transaction"
2. Select transaction type (Income, Expense, Transfer)
3. Enter amount, date, and description
4. Select category and account
5. Save the transaction

#### Managing Budgets

1. Click "Create Budget"
2. Enter budget name and allocate amount
3. Select category and period (weekly, monthly, quarterly, yearly)
4. Set alert threshold (default: 80%)
5. Track spending against budget

#### Generating Reports

1. Go to the Reports section
2. Select report type (Summary, Income vs Expense, Category Breakdown, Budget Performance)
3. Set date range
4. Click "Generate"

## API Endpoints

### Optimization
- `POST /optimize` - Run optimization with variables and budget

### Invoice
- `GET /invoice` - Invoice generator page
- `POST /save_invoice` - Save a new invoice or update existing
- `GET /list_invoices` - List all invoices
- `GET /get_invoice` - Get invoice by ID
- `POST /delete_invoice` - Delete an invoice
- `POST /send_invoice_email` - Send invoice via email

### Finance
- `GET /finance` - Finance dashboard page
- `GET /api/finance/data` - Get all finance data
- `POST /api/finance/transaction` - Create/update transaction
- `DELETE /api/finance/transaction/<id>` - Delete transaction
- `POST /api/finance/account` - Create/update account
- `DELETE /api/finance/account/<id>` - Delete account
- `POST /api/finance/budget` - Create/update budget
- `DELETE /api/finance/budget/<id>` - Delete budget
- `POST /api/finance/report` - Generate financial report
- `POST /api/finance/export` - Export financial data
- `POST /api/finance/export/csv` - Export transactions as CSV
- `POST /api/finance/import` - Import financial data

#### Contacts and ledger

- `GET /api/finance/contacts` - List or search contacts (`?q=`, `?role=`)
- `POST /api/finance/contact` - Create a customer or supplier
- `PUT /api/finance/contact/<id>` - Update a contact
- `DELETE /api/finance/contact/<id>` - Delete a contact with no ledger history
- `GET /api/finance/ledger` - Invoices, bills, totals and aging on both sides (`?as_of=`)
- `POST /api/finance/receivable` - Bill a customer
- `PUT /api/finance/receivable/<id>` - Edit a customer invoice
- `POST /api/finance/receivable/<id>/payment` - Record cash received (supports partial)
- `POST /api/finance/receivable/<id>/write-off` - Write off as uncollectable
- `DELETE /api/finance/receivable/<id>` - Delete an unpaid customer invoice
- `POST /api/finance/payable` - Record a supplier bill
- `PUT /api/finance/payable/<id>` - Edit a supplier bill
- `POST /api/finance/payable/<id>/payment` - Record cash paid (supports partial)
- `DELETE /api/finance/payable/<id>` - Delete an unpaid supplier bill

#### Compliance

- `GET /api/finance/compliance` - Profile, tax, payroll and structuring in one payload
- `POST /api/finance/entity-profile` - Save business profile (entity type, VAT, year end)
- `GET /api/finance/tax-schedule` - Planned South African filing periods
- `POST /api/finance/tax-schedule/seed` - Turn the planned schedule into tracked obligations
- `POST /api/finance/tax` - Record a tax obligation
- `POST /api/finance/tax/<id>/status` - Mark paid, filed or re-estimated
- `GET /api/finance/vat-estimate` - Rough net VAT payable for a period
- `POST /api/finance/payroll` - Record a payroll run
- `PUT /api/finance/payroll/<id>` - Update a payroll run
- `DELETE /api/finance/payroll/<id>` - Delete a payroll run

#### Statements and planning

- `GET /api/finance/money-position` - The five questions for a period (`?start=`, `?end=`)
- `GET /api/finance/statement` - `type=` `profit_loss`, `balance_sheet`, `cash_flow`,
  `expense_analysis`, `records_health` or `funding_readiness`
- `GET /api/finance/forecast` - List forecast scenarios
- `POST /api/finance/forecast` - Create a scenario
- `POST /api/finance/forecast/<id>/project` - Project a scenario

### Accounting basis and limitations

Worth knowing before you rely on the numbers:

- **Cash basis counts money that moved. Accrual basis counts what you earned and
  what it cost you.** Both are shown side by side, because they answer different
  questions and will not agree.
- **Settlements are not double counted.** A payment against a customer invoice or
  supplier bill is tagged, and accrual figures include the invoice or bill rather
  than the payment that settled it.
- **Owner equity is a balancing figure** (assets minus liabilities). Inventory, fixed
  assets and depreciation are not tracked, so a balance sheet is not a substitute for
  one prepared by your bookkeeper.
- **Opening cash in the cash flow statement is derived** by backing the period's net
  movement out of your current closing cash, because dated historical account
  balances are not recorded.
- **Cost of sales is detected automatically** from category names. Recategorise
  anything the heuristic gets wrong.
- **Tax and payroll figures are planning estimates** from your own records, not
  calculations or filings. Confirm them with SARS or your registered tax practitioner.
- **Funding readiness is an internal view** built from your own data. It is not a
  credit assessment and no lender will treat it as one.

## Project Structure

```
Profit-Optimizer/
├── server/
│   ├── app.py              # Main Flask application
│   ├── config.py           # Configuration settings
│   ├── optimizer_core.py   # Core optimization logic (ILP)
│   ├── invoice_core.py     # Invoice management system
│   ├── finance_core.py     # Finance management system
│   ├── data/
│   │   ├── transactions.json
│   │   ├── accounts.json
│   │   ├── budgets.json
│   │   ├── categories.json
│   │   ├── alerts.json
│   │   └── users.json
│   ├── templates/
│   │   ├── home.html       # Home page
│   │   ├── about.html       # About page
│   │   ├── contact.html    # Contact page
│   │   ├── optimizer.html   # Profit optimizer page
│   │   ├── finance.html    # Finance dashboard page
│   │   └── invoice.html    # Invoice generator page
│   ├── static/
│   │   ├── style.css       # Main stylesheet
│   │   ├── homestyle.css   # Home page styles
│   │   ├── invoice.css     # Invoice page styles
│   │   └── homestyle.css   # Home page styling
│   ├── uploads/            # Uploaded files storage
│   ├── exports/            # Exported files storage
│   └── invoices/           # Saved invoices storage
├── requirements.txt        # Python dependencies
├── vercel.json            # Vercel deployment config
├── makefile              # Build commands
└── README.md             # This file
```

## Dependencies

- **Flask**: Web framework for Python
- **PuLP**: Linear programming toolkit with CBC solver
- **Werkzeug**: WSGI utilities for file handling
- **Gunicorn**: WSGI HTTP server for production deployment
- **Chart.js**: Interactive charts for finance dashboard

## Development Notes

- The application uses PuLP with the CBC solver for optimization
- Variables are stored in memory during runtime
- File operations use secure filename handling
- Input validation prevents invalid optimization problems
- The interface is designed to be mobile-responsive
- All financial data is persisted in JSON files in the `server/data/` directory
- Invoice files are stored in the `server/invoices/` directory

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For questions, feedback, or support:
- Open an issue in the repository
- Email: MasanaboB@outlook.com
- Email: [Mafu's Email]

---

Built with ❤️ using Flask and PuLP
