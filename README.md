# Profit Optimizer

A web-based application for solving integer linear programming (ILP) problems to maximize profit under budget constraints. This Flask application provides an intuitive interface for defining optimization variables, setting constraints, and running optimization algorithms.

## Features

- **Web-based Interface**: Clean, responsive UI built with HTML, CSS, and JavaScript
- **Variable Management**: Add, edit, delete, import, and export optimization variables
- **Budget Optimization**: Set budget constraints and maximize profit using PuLP solver
- **Data Persistence**: Import/export variables as JSON files
- **Real-time Results**: View optimal solutions with detailed breakdowns
- **Input Validation**: Comprehensive validation for all input parameters

## Tech Stack

- **Backend**: Python 3.8+, Flask 3.0.0
- **Optimization**: PuLP 2.8.0 (CBC solver)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
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

### Adding Variables

1. Click "Add Item" to open the variable creation modal
2. Fill in the following fields:
   - **Item Name**: Unique identifier for the variable
   - **Minimum Item(s)**: Lower bound (default: 0)
   - **Maximum Item(s)**: Upper bound (optional, leave blank for unlimited)
   - **Cost per Item**: Cost associated with each unit
   - **Profit per Item**: Profit generated per unit
   - **Number of Item(s)**: Multiplier for the variable

### Setting Budget

1. Navigate to the "Budget" section
2. Enter your budget constraint in rands
3. Click "Update Budget" to save

### Running Optimization

1. Ensure you have added variables and set a budget
2. Click "Run Optimization" in the Constraints section
3. View results in the "Results" section showing:
   - Projected profit
   - Optimal quantities for each item
   - Total cost breakdown

### Data Management

- **Export**: Save current variables to the exports folder
- **Download**: Download variables as a JSON file
- **Import**: Upload JSON files to load previously saved variables
- **Edit/Delete**: Modify or remove existing variables

## API Endpoints

- `GET /` - Main optimization interface
- `POST /export` - Export variables to JSON
- `POST /import` - Import variables from JSON file
- `POST /download` - Download variables as JSON
- `POST /delete_variable/<name>` - Delete a variable by name
- `POST /update_variable` - Update an existing variable

## Project Structure

```
Profit-Optimizer/
├── server/
│   ├── app.py              # Main Flask application
│   ├── config.py           # Configuration settings
│   ├── optimizer_core.py   # Core optimization logic
│   ├── templates/          # HTML templates
│   │   ├── optimizer.html      # Main interface
│   │   ├── home.html       # Home page
│   │   ├── finance.html    # Finance page
│   │   └── invoice.html    # Invoice generator
│   ├── static/             # Static assets
│   │   └── style.css       # Stylesheet
│   ├── uploads/            # Uploaded files storage
│   └── exports/            # Exported files storage
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

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

## Dependencies

- **Flask**: Web framework for Python
- **PuLP**: Linear programming toolkit with CBC solver
- **Werkzeug**: WSGI utilities for file handling
- **Gunicorn**: WSGI HTTP server for production deployment

## Development Notes

- The application uses PuLP with the CBC solver for optimization
- Variables are stored in memory during runtime
- File operations use secure filename handling
- Input validation prevents invalid optimization problems
- The interface is designed to be mobile-responsive

---
