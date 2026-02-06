"""
optimizer_core.py

Core logic for defining and solving integer linear programming (ILP) problems.
This module is designed to be imported by a Flask app or other interfaces.

Classes:
    OptimizationError: Custom exception for optimization-related errors.
    IntegerVariable: Class representing an optimization variable.

Functions:
    create_integer_variable: Add a variable to the shared list.
    optimize: Solve the optimization problem.
    clear_variables: Clear the variables list.

@author: Bongani
@date: 2025-09-18
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Tuple
from pulp import LpProblem, LpVariable, LpMaximize, lpSum, PULP_CBC_CMD, LpStatus

class OptimizationError(Exception):
    """Custom exception for optimization-related errors."""
    pass

@dataclass
class IntegerVariable:
    """
    Represents an integer (or continuous) variable for optimization.
    Uses dataclass for automatic __init__, __repr__, etc.
    """
    name: str
    lowerBound: int = 0
    upperBound: Optional[int] = None
    cost: float = 0.0
    profit: float = 0.0
    multiplier: int = 1

    def to_dict(self) -> Dict:
        """Convert to a dictionary for JSON export."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'IntegerVariable':
        """Create an IntegerVariable from a dictionary."""
        return cls(**data)

    def validate(self) -> None:
        """
        Validate the variable's properties.
        Raises OptimizationError if validation fails.
        """
        if self.lowerBound < 0:
            raise OptimizationError(f"Lower bound must be non-negative for {self.name}")
        if self.upperBound is not None and self.upperBound < self.lowerBound:
            raise OptimizationError(f"Upper bound must be greater than lower bound for {self.name}")
        if self.multiplier <= 0:
            raise OptimizationError(f"Multiplier must be positive for {self.name}")

# Global variables list
variables_list: List[IntegerVariable] = []

def create_integer_variable(name: str, lowerBound: int, upperBound: Optional[int], cost: float, profit: float, multiplier: int = 1) -> None:
    """
    Create and validate an IntegerVariable, then add it to the global list.
    
    Args:
        name: Name of the variable.
        lowerBound: Minimum value.
        upperBound: Maximum value (None for unbounded).
        cost: Cost per unit.
        profit: Profit per unit.
        multiplier: Scaling factor.
    
    Raises:
        OptimizationError: If validation fails.
    """
    var = IntegerVariable(name=name, lowerBound=lowerBound, upperBound=upperBound, cost=cost, profit=profit, multiplier=multiplier)
    var.validate()
    variables_list.append(var)

def clear_variables() -> None:
    """Clear the global variables list."""
    variables_list.clear()

def optimize(variables: List[IntegerVariable], budget: float) -> Tuple[float, Dict[str, int]]:
    """
    Set up and solve the integer programming problem to maximize profit.
    
    Args:
        variables: List of variables to optimize.
        budget: Budget constraint value.
    
    Returns:
        Tuple of (max_profit, result_dict).
        max_profit is the maximum profit achieved.
        result_dict maps variable names to their optimal values.
    
    Raises:
        OptimizationError: If optimization fails or produces invalid results.
    """
    if not variables:
        raise OptimizationError("No variables to optimize")
    if budget <= 0:
        raise OptimizationError("Budget must be positive")

    # Create and set up the model
    model = LpProblem("Production_Optimization", LpMaximize)
    lp_vars = {}

    # Create PuLP variables
    for var in variables:
        lp_vars[var.name] = LpVariable(var.name, lowBound=var.lowerBound, upBound=var.upperBound)

    # Add constraints
    budget_constraint = lpSum([var.multiplier * lp_vars[var.name] for var in variables])
    model += (budget_constraint <= budget, "Budget_Constraint")

    # Set objective function
    total_profit = lpSum([var.profit * var.multiplier * lp_vars[var.name] for var in variables])
    model += total_profit, "Total_Profit"

    # Solve the model
    solver = PULP_CBC_CMD(msg=False)
    model.solve(solver)

    # Check solution status
    if LpStatus[model.status] != 'Optimal':
        raise OptimizationError(f"Failed to find optimal solution: {LpStatus[model.status]}")

    # Process results
    max_profit = 0
    result = {}
    for var in variables:
        optimal_value = lp_vars[var.name].varValue
        if optimal_value is None:
            optimal_value = 0
        optimal_value = int(optimal_value)
        scaled_value = optimal_value * var.multiplier
        result[var.name] = scaled_value
        max_profit += var.profit * scaled_value

    return float(f'{max_profit:.2f}'), result
