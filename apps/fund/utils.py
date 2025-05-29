"""
Utility functions for Fund operations
"""

from django.db.models import Q
from .models import FundToken


def get_oldest_available_tokens(fund_id, quantity=None):
    """
    Get the oldest available tokens in ascending order from FundTokens for multi-token purchases.
    
    Available tokens are defined as:
    - status=True (active)
    - owner_user=None (not yet owned by any user)
    
    Args:
        fund_id (int): ID of the fund to get tokens from
        quantity (int, optional): Maximum number of tokens to return. 
                                 If None, returns all available tokens.
    
    Returns:
        QuerySet: QuerySet of FundToken objects ordered by created_at (oldest first)
        
    Example:
        # Get 5 oldest available tokens for fund with ID 1
        tokens = get_oldest_available_tokens(fund_id=1, quantity=5)
        
        # Get all available tokens for fund with ID 1
        all_tokens = get_oldest_available_tokens(fund_id=1)
        
        # Convert to list of token IDs for use in purchase operations
        token_ids = list(tokens.values_list('token_id', flat=True))
    """
    queryset = FundToken.objects.filter(
        fund_id=fund_id,
        status=True,  # Active tokens only
        owner_user__isnull=True  # Not yet owned by any user
    ).order_by('created_at')  # Oldest first (ascending order)
    
    if quantity is not None:
        queryset = queryset[:quantity]
    
    return queryset


def get_available_tokens_count(fund_id):
    """
    Get the count of available tokens for a specific fund.
    
    Args:
        fund_id (int): ID of the fund to count available tokens for
        
    Returns:
        int: Number of available tokens
    """
    return FundToken.objects.filter(
        fund_id=fund_id,
        status=True,
        owner_user__isnull=True
    ).count()


def check_token_availability(fund_id, required_quantity):
    """
    Check if a fund has enough available tokens for a purchase.
    
    Args:
        fund_id (int): ID of the fund to check
        required_quantity (int): Number of tokens required
        
    Returns:
        dict: Dictionary with availability information
            - available (bool): Whether enough tokens are available
            - available_count (int): Number of available tokens
            - required_count (int): Number of tokens required
            - shortage (int): Number of tokens short (0 if enough available)
    """
    available_count = get_available_tokens_count(fund_id)
    
    return {
        'available': available_count >= required_quantity,
        'available_count': available_count,
        'required_count': required_quantity,
        'shortage': max(0, required_quantity - available_count)
    }


def reserve_oldest_tokens(fund_id, quantity, user):
    """
    Reserve the oldest available tokens for a user by setting the owner_user field.
    This is useful for multi-token purchases to prevent race conditions.
    
    Args:
        fund_id (int): ID of the fund
        quantity (int): Number of tokens to reserve
        user: User object to assign as owner
        
    Returns:
        list: List of reserved FundToken objects
        
    Raises:
        ValueError: If not enough tokens are available
    """
    from django.db import transaction
    
    with transaction.atomic():
        # Get oldest available tokens with select_for_update to prevent race conditions
        available_tokens = FundToken.objects.select_for_update().filter(
            fund_id=fund_id,
            status=True,
            owner_user__isnull=True
        ).order_by('created_at')[:quantity]
        
        available_tokens_list = list(available_tokens)
        
        if len(available_tokens_list) < quantity:
            raise ValueError(
                f"Not enough tokens available. Requested: {quantity}, "
                f"Available: {len(available_tokens_list)}"
            )
        
        # Update owner_user for all selected tokens
        token_ids = [token.id for token in available_tokens_list]
        FundToken.objects.filter(id__in=token_ids).update(owner_user=user)
        
        # Refresh objects to get updated data
        return list(FundToken.objects.filter(id__in=token_ids))
