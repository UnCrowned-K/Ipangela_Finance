"""
Flask API for Profit Optimizer - Vercel Serverless Deployment
"""
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/")
def home():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "message": "Flask app running on Vercel!",
        "version": "1.0.0"
    })


@app.route("/api/health", methods=["GET"])
def health_check():
    """Detailed health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "profit-optimizer-api",
        "endpoints": ["/", "/api/health", "/api/calculate-profit"]
    })


@app.route("/api/calculate-profit", methods=["POST"])
def calculate_profit():
    """
    Calculate profit margins from invoice data.
    
    Expected JSON payload:
    {
        "revenue": 1000,
        "costs": 400,
        "items": [
            {"name": "Item1", "revenue": 500, "cost": 200},
            {"name": "Item2", "revenue": 500, "cost": 300}
        ]
    }
    
    Returns:
    {
        "total_revenue": 1000,
        "total_costs": 400,
        "total_profit": 600,
        "profit_margin": 60.0,
        "items": [
            {"name": "Item1", "profit": 300, "margin": 60.0},
            {"name": "Item2", "profit": 200, "margin": 40.0}
        ]
    }
    """
    try:
        # Validate content type
        if not request.is_json:
            return jsonify({
                "error": "Content-Type must be application/json"
            }), 400
        
        # Parse JSON data
        data = request.get_json()
        
        if data is None:
            return jsonify({
                "error": "Invalid JSON data"
            }), 400
        
        # Validate required fields
        if "revenue" not in data or "costs" not in data:
            return jsonify({
                "error": "Missing required fields: 'revenue' and 'costs' are required"
            }), 400
        
        revenue = float(data.get("revenue", 0))
        costs = float(data.get("costs", 0))
        
        # Validate input values
        if revenue < 0:
            return jsonify({
                "error": "Revenue cannot be negative"
            }), 400
        
        if costs < 0:
            return jsonify({
                "error": "Costs cannot be negative"
            }), 400
        
        # Calculate overall profit
        total_profit = revenue - costs
        profit_margin = (total_profit / revenue * 100) if revenue > 0 else 0
        
        # Process individual items if provided
        items = []
        if "items" in data and isinstance(data["items"], list):
            for item in data["items"]:
                try:
                    item_revenue = float(item.get("revenue", 0))
                    item_cost = float(item.get("cost", 0))
                    item_profit = item_revenue - item_cost
                    item_margin = (item_profit / item_revenue * 100) if item_revenue > 0 else 0
                    
                    items.append({
                        "name": item.get("name", "Unknown"),
                        "revenue": item_revenue,
                        "cost": item_cost,
                        "profit": item_profit,
                        "margin": round(item_margin, 2)
                    })
                except (ValueError, TypeError) as e:
                    items.append({
                        "name": item.get("name", "Unknown"),
                        "error": f"Invalid item data: {str(e)}"
                    })
        
        # Build response
        response = {
            "total_revenue": revenue,
            "total_costs": costs,
            "total_profit": total_profit,
            "profit_margin": round(profit_margin, 2),
            "items": items
        }
        
        return jsonify(response), 200
        
    except ValueError as e:
        return jsonify({
            "error": f"Invalid numeric value: {str(e)}"
        }), 400
    except Exception as e:
        return jsonify({
            "error": f"Internal server error: {str(e)}"
        }), 500


@app.route("/api/optimize-invoice", methods=["POST"])
def optimize_invoice():
    """
    Analyze invoice for optimization opportunities.
    
    Expected JSON payload:
    {
        "line_items": [
            {"description": "Service A", "quantity": 10, "unit_price": 50},
            {"description": "Service B", "quantity": 5, "unit_price": 100}
        ],
        "discount_percent": 0,
        "tax_rate": 15
    }
    """
    try:
        if not request.is_json:
            return jsonify({
                "error": "Content-Type must be application/json"
            }), 400
        
        data = request.get_json()
        
        if data is None:
            return jsonify({
                "error": "Invalid JSON data"
            }), 400
        
        line_items = data.get("line_items", [])
        discount_percent = float(data.get("discount_percent", 0))
        tax_rate = float(data.get("tax_rate", 0))
        
        if not line_items:
            return jsonify({
                "error": "No line items provided"
            }), 400
        
        # Calculate subtotal
        subtotal = 0
        processed_items = []
        
        for item in line_items:
            try:
                quantity = float(item.get("quantity", 1))
                unit_price = float(item.get("unit_price", 0))
                line_total = quantity * unit_price
                subtotal += line_total
                
                processed_items.append({
                    "description": item.get("description", "Item"),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_total": line_total
                })
            except (ValueError, TypeError) as e:
                return jsonify({
                    "error": f"Invalid item data: {str(e)}"
                }), 400
        
        # Calculate discount
        discount_amount = subtotal * (discount_percent / 100)
        after_discount = subtotal - discount_amount
        
        # Calculate tax
        tax_amount = after_discount * (tax_rate / 100)
        grand_total = after_discount + tax_amount
        
        return jsonify({
            "subtotal": round(subtotal, 2),
            "discount_percent": discount_percent,
            "discount_amount": round(discount_amount, 2),
            "after_discount": round(after_discount, 2),
            "tax_rate": tax_rate,
            "tax_amount": round(tax_amount, 2),
            "grand_total": round(grand_total, 2),
            "line_items": processed_items
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": f"Internal server error: {str(e)}"
        }), 500


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500
