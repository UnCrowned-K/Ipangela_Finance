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
- **Deployment**: Gunicorn 21.2.0, Vercel Serverless
- **Containerization**: Docker, Docker Compose
- **File Handling**: Werkzeug 3.0.1

## Quick Start

### Local Development

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

### Docker Development

1. **Start with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

2. **For hot-reloading development:**
   ```bash
   docker-compose -f docker-compose.yml up app-dev
   ```

### Vercel Deployment

1. **Install Vercel CLI:**
   ```bash
   npm i -g vercel
   ```

2. **Deploy to Vercel:**
   ```bash
   vercel --prod
   ```

   The API will be available at `https://your-project.vercel.app`

## Environment Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Application Settings
ENVIRONMENT=development
SECRET_KEY=your-secret-key

# Server Configuration
HOST=0.0.0.0
PORT=5000
DEBUG=true

# File Upload Settings
MAX_CONTENT_LENGTH=16777216  # 16MB
```

### Environment-Specific Configurations

| Environment | DEBUG | Workers | Features |
|-------------|-------|---------|----------|
| development | true | 1 | Hot-reload, detailed logs |
| staging | false | 2 | Limited logging |
| production | false | 2-4 | Full optimization |

## API Documentation

### Base URL

- **Local**: `http://localhost:5000`
- **Vercel**: `https://your-project.vercel.app`

### Endpoints

#### Health Check
- `GET /` - Health check and module status

#### Optimizer
- `GET /api/optimizer/variables` - List all optimization variables
- `POST /api/optimizer/variable` - Add a new variable
- `DELETE /api/optimizer/variable/<name>` - Delete a variable
- `POST /api/optimizer/clear` - Clear all variables
- `POST /api/optimizer/run` - Run optimization

#### Finance
- `GET /api/finance/data` - Get dashboard data
- `POST /api/finance/transaction` - Create transaction
- `GET /api/finance/transaction/<id>` - Get transaction
- `DELETE /api/finance/transaction/<id>` - Delete transaction
- `POST /api/finance/account` - Create account
- `GET /api/finance/account/<id>` - Get account
- `DELETE /api/finance/account/<id>` - Delete account
- `POST /api/finance/budget` - Create budget
- `GET /api/finance/budget/<id>` - Get budget
- `POST /api/finance/report` - Generate report

#### Invoices
- `GET /api/invoice/list` - List all invoices
- `POST /api/invoice` - Create invoice
- `GET /api/invoice/<id>` - Get invoice
- `DELETE /api/invoice/<id>` - Delete invoice

## Project Structure

```
Profit-Optimizer/
├── api/
│   └── index.py              # Vercel API entry point
├── server/
│   ├── app.py               # Main Flask application
│   ├── config.py            # Configuration settings
│   ├── optimizer_core.py    # Core optimization logic (ILP)
│   ├── invoice_core.py      # Invoice management system
│   ├── finance_core.py      # Finance management system
│   ├── data/                # JSON data storage
│   ├── templates/           # HTML templates
│   ├── static/              # CSS and JavaScript
│   ├── uploads/             # Uploaded files
│   ├── exports/             # Exported files
│   └── invoices/            # Saved invoices
├── tests/
│   └── test_api.py          # End-to-end tests
├── vercel.json             # Vercel deployment config
├── Dockerfile              # Production container
├── Dockerfile.dev          # Development container
├── docker-compose.yml      # Local development environment
├── .env.example            # Environment template
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=api --cov-report=html
```

## Deployment Options

### Vercel (Serverless)
- Automatic deployments from Git
- API routes in `api/` directory
- Configure in `vercel.json`

### Docker (Container)
```bash
# Build image
docker build -t profit-optimizer .

# Run container
docker run -p 5000:5000 profit-optimizer
```

### Heroku
```bash
# Create Heroku app
heroku create

# Set buildpack
heroku buildpacks:set heroku/python

# Deploy
git push heroku main
```

## Development Notes

- The application uses PuLP with the CBC solver for optimization
- Variables are stored in memory during runtime
- File operations use secure filename handling
- Input validation prevents invalid optimization problems
- The interface is designed to be mobile-responsive
- All financial data is persisted in JSON files in the `server/data/` directory
- Invoice files are stored in the `server/invoices/` directory
- CORS is enabled for cross-origin API access

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
