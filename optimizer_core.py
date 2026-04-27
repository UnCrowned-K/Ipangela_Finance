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

import math
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
    
    The optimizer works with UNITS as the primary quantity.
    
    Attributes:
        name: Name of the item/product
        lowerBound: Minimum number of units
        upperBound: Maximum number of units (None for unbounded)
        cost: Cost per unit (always per individual unit)
        profit: Profit per unit (always per individual unit)
        multiplier: Units per pack (1 = individual units, >1 = packed items)
    
    Example 1 - Individual units:
        cost=10, profit=2, multiplier=1
        Buying 1 unit costs R10, profit is R2
    
    Example 2 - Packed items:
        cost=2, profit=3, multiplier=6
        Buying 1 pack (6 units) costs R12 (6 × R2), profit is R18 (6 × R3)
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
            raise OptimizationError(f"Units per pack must be positive for {self.name}")

def create_integer_variable(name: str, lowerBound: int, upperBound: Optional[int], cost: float, profit: float, multiplier: int = 1) -> IntegerVariable:
    """
    Create and validate an IntegerVariable.
    
    The optimizer works with UNITS. All values are per unit.
    
    Args:
        name: Name of the item/product.
        lowerBound: Minimum number of units.
        upperBound: Maximum number of units (None for unbounded).
        cost: Cost per unit (always per individual unit).
        profit: Profit per unit (always per individual unit).
        multiplier: Units per pack (1 = individual units, >1 = packed items).
    
    Returns:
        Validated IntegerVariable instance.
    
    Raises:
        OptimizationError: If validation fails.
    """
    var = IntegerVariable(name=name, lowerBound=lowerBound, upperBound=upperBound, cost=cost, profit=profit, multiplier=multiplier)
    var.validate()
    return var

def optimize(variables: List['IntegerVariable'], budget: float) -> Tuple[float, Dict[str, Dict]]:
    """
    Set up and solve the integer programming problem to maximize profit.
    
    The optimizer works with UNITS as the primary quantity, with optional pack specification.
    
    Args:
        variables: List of variables to optimize.
        budget: Budget constraint value.
    
    Returns:
        Tuple of (max_profit, result_dict).
        max_profit is the maximum profit achieved.
        result_dict maps variable names to their details.
    
    Raises:
        OptimizationError: If optimization fails, produces invalid results, or bounds are impossible.
    """
    if not variables:
        raise OptimizationError("No variables to optimize")
    if budget <= 0:
        raise OptimizationError("Budget must be positive")

    # Create and set up the model
    model = LpProblem("Production_Optimization", LpMaximize)
    lp_vars = {}

    # Create PuLP variables - decision variable represents packs
    for var in variables:
        # Convert unit bounds to pack bounds using math.ceil for the lower bound
        if var.multiplier > 1:
            pack_lower = math.ceil(var.lowerBound / var.multiplier)
            pack_upper = None if var.upperBound is None else var.upperBound // var.multiplier
        else:
            pack_lower = var.lowerBound
            pack_upper = var.upperBound
        
        # Safety check: Catch impossible bounds before the solver fails
        if pack_upper is not None and pack_lower > pack_upper:
            raise OptimizationError(
                f"Impossible constraints for {var.name}: "
                f"Minimum {var.lowerBound} units and maximum {var.upperBound} units "
                f"cannot be satisfied with a pack size of {var.multiplier}."
            )
        
        # Note: PuLP prefers variable names without spaces, replacing them with underscores internally
        safe_name = var.name.replace(" ", "_")
        lp_vars[var.name] = LpVariable(safe_name, lowBound=pack_lower, upBound=pack_upper, cat='Integer')

    # Add constraints
    budget_terms = [var.cost * var.multiplier * lp_vars[var.name] for var in variables]
    model += (lpSum(budget_terms) <= budget, "Budget_Constraint")

    # Set objective function
    profit_terms = [var.profit * var.multiplier * lp_vars[var.name] for var in variables]
    model += lpSum(profit_terms), "Total_Profit"

    # Solve the model
    solver = PULP_CBC_CMD(msg=False)
    model.solve(solver)

    # Check solution status with a specific catch for budget infeasibility 
    if LpStatus[model.status] != 'Optimal':
        if LpStatus[model.status] == 'Infeasible':
            raise OptimizationError("Your budget is too low to meet the minimum unit requirements.")
        raise OptimizationError(f"Failed to find optimal solution: {LpStatus[model.status]}")

    # Process results
    max_profit = 0
    result = {}
    for var in variables:
        optimal_packs = lp_vars[var.name].varValue
        if optimal_packs is None:
            optimal_packs = 0
        optimal_packs = int(optimal_packs)
        
        if optimal_packs > 0:
            total_units = optimal_packs * var.multiplier
            total_cost = optimal_packs * var.cost * var.multiplier
            item_profit = optimal_packs * var.profit * var.multiplier
            
            result[var.name] = {
                'units': total_units,
                'packs': optimal_packs,
                'cost': total_cost,
                'profit': item_profit
            }
            max_profit += item_profit

    return float(f'{max_profit:.2f}'), result