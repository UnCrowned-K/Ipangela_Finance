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
- **Financial Reports**: Generate summary, income/expense, and category reports
- **Data Import/Export**: Export data as JSON or CSV, import from external sources
- **Visual Charts**: Interactive charts for income vs expenses and spending by category

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
- Email: [your-email@example.com]

---

Built with ❤️ using Flask and PuLP
